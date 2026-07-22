from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.auth.constants import PermissionCode, RoleCode
from kasta_api.modules.auth.models import (
    AuthDeliveryOutbox,
    AuthOneTimeToken,
    DeviceSession,
    LoginRateLimit,
    Permission,
    Role,
    RolePermission,
)
from kasta_api.modules.businesses.models import (
    Business,
    BusinessMember,
    OrganizationMember,
)
from kasta_api.modules.mentors.models import Mentor, MentorBusinessAccess, SupportAccessGrant
from kasta_api.modules.users.models import User


@dataclass(frozen=True, slots=True)
class AuthorizationRecord:
    role_id: UUID
    role_code: str
    permissions: frozenset[str]
    mentor_id: UUID | None = None
    support_grant_id: UUID | None = None


SCOPE_PERMISSIONS: dict[str, set[str]] = {
    "SUMMARY": {
        PermissionCode.MENTOR_SUMMARY_READ.value,
        PermissionCode.BUSINESS_PROFILE_READ.value,
        PermissionCode.MENTOR_NOTE_CREATE.value,
        PermissionCode.MENTOR_RECOMMENDATION_MANAGE.value,
        PermissionCode.MENTOR_SESSION_MANAGE.value,
    },
    "REPORTS": {PermissionCode.REPORT_READ.value},
    "TRANSACTIONS": {
        PermissionCode.TRANSACTION_READ.value,
        PermissionCode.MENTOR_TRANSACTION_READ.value,
    },
    "RECEIPTS": {PermissionCode.RECEIPT_READ.value},
    "INVENTORY": {PermissionCode.PRODUCT_READ.value},
    "OBLIGATIONS": {
        PermissionCode.RECEIVABLE_READ.value,
        PermissionCode.PAYABLE_READ.value,
    },
    "EXPORT_REPORTS": {
        PermissionCode.REPORT_EXPORT.value,
        PermissionCode.MENTOR_REPORT_EXPORT.value,
        PermissionCode.INVENTORY_EXPORT.value,
    },
}
SCOPED_DATA_PERMISSIONS = frozenset().union(*SCOPE_PERMISSIONS.values())
ADMIN_BUSINESS_PERMISSIONS = frozenset(
    permission.value
    for permission in PermissionCode
    if permission not in {PermissionCode.SESSION_READ, PermissionCode.SESSION_REVOKE_OWN}
)


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_user_by_identifier(
        self, kind: str, identifier: str, *, lock: bool = False
    ) -> User | None:
        column = User.email if kind == "EMAIL" else User.phone
        statement = select(User).where(column == identifier, User.deleted_at.is_(None))
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def add_user(self, user: User) -> None:
        self.session.add(user)
        await self.session.flush()

    async def resolve_authorization(
        self, user_id: UUID, business_id: UUID
    ) -> AuthorizationRecord | None:
        active_user = await self.session.scalar(
            select(User.id).where(
                User.id == user_id,
                User.status == "ACTIVE",
                User.deleted_at.is_(None),
            )
        )
        active_business = await self.session.scalar(
            select(Business.id).where(
                Business.id == business_id,
                Business.status == "ACTIVE",
                Business.deleted_at.is_(None),
            )
        )
        if active_user is None or active_business is None:
            return None

        platform_role = (
            await self.session.scalars(
                select(Role)
                .join(User, User.platform_role_id == Role.id)
                .where(User.id == user_id, Role.code == RoleCode.SUPER_ADMIN.value)
            )
        ).one_or_none()
        if platform_role is not None:
            return await self._support_authorization(platform_role, user_id, business_id)

        business_role = (
            await self.session.scalars(
                select(Role)
                .join(BusinessMember, BusinessMember.role_id == Role.id)
                .where(
                    BusinessMember.user_id == user_id,
                    BusinessMember.business_id == business_id,
                    BusinessMember.status == "ACTIVE",
                    BusinessMember.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if business_role is not None:
            return await self._authorization_for_role(business_role)

        organization_role = (
            await self.session.scalars(
                select(Role)
                .join(OrganizationMember, OrganizationMember.role_id == Role.id)
                .join(Business, Business.organization_id == OrganizationMember.organization_id)
                .where(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "ACTIVE",
                    OrganizationMember.deleted_at.is_(None),
                    Business.id == business_id,
                    Business.deleted_at.is_(None),
                    Role.code == RoleCode.ORGANIZATION_ADMIN.value,
                )
            )
        ).one_or_none()
        if organization_role is not None:
            return await self._support_authorization(organization_role, user_id, business_id)

        mentor_access = (
            await self.session.execute(
                select(Role, MentorBusinessAccess)
                .join(MentorBusinessAccess, MentorBusinessAccess.role_id == Role.id)
                .join(Mentor, Mentor.id == MentorBusinessAccess.mentor_id)
                .where(
                    Mentor.user_id == user_id,
                    Mentor.status == "ACTIVE",
                    Mentor.deleted_at.is_(None),
                    MentorBusinessAccess.business_id == business_id,
                    MentorBusinessAccess.status == "ACTIVE",
                    or_(
                        MentorBusinessAccess.expires_at.is_(None),
                        MentorBusinessAccess.expires_at > datetime.now(UTC),
                    ),
                    MentorBusinessAccess.deleted_at.is_(None),
                    Role.code == RoleCode.MENTOR.value,
                )
            )
        ).one_or_none()
        if mentor_access is None:
            return None
        mentor_role, access = mentor_access
        authorization = await self._authorization_for_role(mentor_role)
        allowed = self._permissions_for_scopes(access.scope)
        permissions = set(authorization.permissions) - set(SCOPED_DATA_PERMISSIONS)
        permissions.update(allowed)
        return AuthorizationRecord(
            role_id=authorization.role_id,
            role_code=authorization.role_code,
            permissions=frozenset(permissions),
            mentor_id=access.mentor_id,
        )

    async def _support_authorization(
        self, role: Role, user_id: UUID, business_id: UUID
    ) -> AuthorizationRecord:
        authorization = await self._authorization_for_role(role)
        now = datetime.now(UTC)
        grant = (
            await self.session.scalars(
                select(SupportAccessGrant)
                .where(
                    SupportAccessGrant.admin_user_id == user_id,
                    SupportAccessGrant.business_id == business_id,
                    SupportAccessGrant.status == "ACTIVE",
                    SupportAccessGrant.expires_at > now,
                )
                .order_by(SupportAccessGrant.expires_at.desc())
                .limit(1)
            )
        ).one_or_none()
        permissions = set(authorization.permissions) - set(ADMIN_BUSINESS_PERMISSIONS)
        if grant is not None:
            permissions.update(self._permissions_for_scopes(grant.scope))
        return AuthorizationRecord(
            role_id=authorization.role_id,
            role_code=authorization.role_code,
            permissions=frozenset(permissions),
            support_grant_id=grant.id if grant is not None else None,
        )

    @staticmethod
    def _permissions_for_scopes(scopes: list[str]) -> set[str]:
        return set().union(*(SCOPE_PERMISSIONS.get(scope, set()) for scope in scopes))

    async def _authorization_for_role(self, role: Role) -> AuthorizationRecord:
        codes = await self.session.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        return AuthorizationRecord(
            role_id=role.id,
            role_code=role.code,
            permissions=frozenset(codes.all()),
        )

    async def add_device_session(self, device_session: DeviceSession) -> None:
        self.session.add(device_session)
        await self.session.flush()

    async def get_device_session(
        self, session_id: UUID, *, lock: bool = False
    ) -> DeviceSession | None:
        statement = select(DeviceSession).where(DeviceSession.id == session_id)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def list_user_sessions(self, user_id: UUID, business_id: UUID) -> list[DeviceSession]:
        statement = (
            select(DeviceSession)
            .where(
                DeviceSession.user_id == user_id,
                DeviceSession.business_id == business_id,
                DeviceSession.revoked_at.is_(None),
            )
            .order_by(DeviceSession.last_seen_at.desc())
        )
        return list((await self.session.scalars(statement)).all())

    async def revoke_user_sessions(
        self, user_id: UUID, now: datetime, reason: str, business_id: UUID | None = None
    ) -> int:
        statement = select(DeviceSession).where(
            DeviceSession.user_id == user_id,
            DeviceSession.revoked_at.is_(None),
        )
        if business_id is not None:
            statement = statement.where(DeviceSession.business_id == business_id)
        sessions = (await self.session.scalars(statement.with_for_update())).all()
        for device_session in sessions:
            device_session.revoked_at = now
            device_session.revocation_reason = reason
        return len(sessions)

    async def add_one_time_token(self, token: AuthOneTimeToken) -> None:
        self.session.add(token)
        await self.session.flush()

    async def consume_previous_tokens(self, user_id: UUID, purpose: str, now: datetime) -> None:
        tokens = (
            await self.session.scalars(
                select(AuthOneTimeToken)
                .where(
                    AuthOneTimeToken.user_id == user_id,
                    AuthOneTimeToken.purpose == purpose,
                    AuthOneTimeToken.consumed_at.is_(None),
                )
                .with_for_update()
            )
        ).all()
        for token in tokens:
            token.consumed_at = now

    async def get_one_time_token(
        self, token_id: UUID, *, lock: bool = False
    ) -> AuthOneTimeToken | None:
        statement = select(AuthOneTimeToken).where(AuthOneTimeToken.id == token_id)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def add_outbox_message(self, message: AuthDeliveryOutbox) -> None:
        self.session.add(message)

    async def get_rate_limit(self, key_hash: str, *, lock: bool = False) -> LoginRateLimit | None:
        statement = select(LoginRateLimit).where(LoginRateLimit.key_hash == key_hash)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def clear_rate_limit(self, key_hash: str) -> None:
        await self.session.execute(
            delete(LoginRateLimit).where(LoginRateLimit.key_hash == key_hash)
        )

    def add_rate_limit(self, rate_limit: LoginRateLimit) -> None:
        self.session.add(rate_limit)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
