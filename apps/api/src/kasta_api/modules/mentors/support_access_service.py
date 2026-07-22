from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import CurrentPrincipal
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.mentors.models import SupportAccessGrant
from kasta_api.modules.mentors.schemas import (
    SupportAccessGrantCreate,
    SupportAccessGrantResponse,
    SupportAccessGrantRevoke,
)
from kasta_api.modules.users.models import User

MAX_SUPPORT_DURATION = timedelta(hours=24)


class SupportAccessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        principal: CurrentPrincipal,
        business_id: UUID,
        payload: SupportAccessGrantCreate,
        *,
        request_id: str | None,
    ) -> SupportAccessGrantResponse:
        self._assert_owner(principal, business_id)
        admin = await self.session.get(User, payload.admin_user_id)
        if (
            admin is None
            or admin.deleted_at is not None
            or admin.status != "ACTIVE"
            or admin.platform_role_id
            not in {
                role_id(RoleCode.ORGANIZATION_ADMIN),
                role_id(RoleCode.SUPER_ADMIN),
            }
        ):
            raise HTTPException(
                status_code=422,
                detail="Pengguna tujuan bukan administrator aktif.",
            )
        now = utc_now()
        expires_at = self._aware(payload.expires_at)
        if expires_at <= now or expires_at > now + MAX_SUPPORT_DURATION:
            raise HTTPException(
                status_code=422,
                detail="Grant dukungan harus berakhir di masa depan dan maksimal 24 jam.",
            )
        existing = (
            await self.session.scalars(
                select(SupportAccessGrant).where(
                    SupportAccessGrant.business_id == business_id,
                    SupportAccessGrant.admin_user_id == payload.admin_user_id,
                    SupportAccessGrant.status == "ACTIVE",
                    SupportAccessGrant.expires_at > now,
                )
            )
        ).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Administrator ini masih memiliki grant dukungan aktif.",
            )
        grant = SupportAccessGrant(
            id=uuid4(),
            business_id=business_id,
            admin_user_id=payload.admin_user_id,
            granted_by_user_id=principal.user_id,
            scope=sorted(scope.value for scope in payload.scope),
            reason=payload.reason,
            ticket_reference=payload.ticket_reference.upper(),
            status="ACTIVE",
            granted_at=now,
            expires_at=expires_at,
        )
        self.session.add(grant)
        await self.session.flush()
        self.session.add(
            self._audit(
                principal,
                grant,
                "ADMIN_SUPPORT_GRANT_CREATED",
                request_id=request_id,
                after=self._snapshot(grant),
                reason=payload.reason,
            )
        )
        await self._commit(grant)
        return SupportAccessGrantResponse.model_validate(grant)

    async def list(
        self, principal: CurrentPrincipal, business_id: UUID
    ) -> list[SupportAccessGrantResponse]:
        self._assert_owner(principal, business_id)
        now = utc_now()
        grants = list(
            await self.session.scalars(
                select(SupportAccessGrant)
                .where(SupportAccessGrant.business_id == business_id)
                .order_by(SupportAccessGrant.created_at.desc())
            )
        )
        changed = False
        for grant in grants:
            if grant.status == "ACTIVE" and self._aware(grant.expires_at) <= now:
                grant.status = "EXPIRED"
                changed = True
        if changed:
            await self.session.commit()
        return [SupportAccessGrantResponse.model_validate(grant) for grant in grants]

    async def revoke(
        self,
        principal: CurrentPrincipal,
        business_id: UUID,
        grant_id: UUID,
        payload: SupportAccessGrantRevoke,
        *,
        request_id: str | None,
    ) -> SupportAccessGrantResponse:
        self._assert_owner(principal, business_id)
        grant = (
            await self.session.scalars(
                select(SupportAccessGrant)
                .where(
                    SupportAccessGrant.id == grant_id,
                    SupportAccessGrant.business_id == business_id,
                )
                .with_for_update()
            )
        ).one_or_none()
        if grant is None:
            raise HTTPException(status_code=404, detail="Grant dukungan tidak ditemukan.")
        if grant.status != "ACTIVE" or self._aware(grant.expires_at) <= utc_now():
            raise HTTPException(status_code=409, detail="Grant dukungan sudah tidak aktif.")
        before = self._snapshot(grant)
        grant.status = "REVOKED"
        grant.revoked_at = utc_now()
        self.session.add(
            self._audit(
                principal,
                grant,
                "ADMIN_SUPPORT_GRANT_REVOKED",
                request_id=request_id,
                before=before,
                after=self._snapshot(grant),
                reason=payload.reason,
            )
        )
        await self._commit(grant)
        return SupportAccessGrantResponse.model_validate(grant)

    async def _commit(self, grant: SupportAccessGrant) -> None:
        try:
            await self.session.commit()
            await self.session.refresh(grant)
        except Exception:
            await self.session.rollback()
            raise

    @staticmethod
    def _assert_owner(principal: CurrentPrincipal, business_id: UUID) -> None:
        if principal.business_id != business_id or principal.role != RoleCode.BUSINESS_OWNER.value:
            raise HTTPException(
                status_code=403,
                detail="Hanya pemilik UMKM yang dapat mengatur akses dukungan.",
            )

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _snapshot(grant: SupportAccessGrant) -> dict[str, object]:
        return {
            "admin_user_id": str(grant.admin_user_id),
            "scope": list(grant.scope),
            "status": grant.status,
            "ticket_reference": grant.ticket_reference,
            "expires_at": grant.expires_at.isoformat(),
        }

    @staticmethod
    def _audit(
        principal: CurrentPrincipal,
        grant: SupportAccessGrant,
        action: str,
        *,
        request_id: str | None,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=grant.business_id,
            actor_user_id=principal.user_id,
            action=action,
            entity_type="SUPPORT_ACCESS_GRANT",
            entity_id=grant.id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )
