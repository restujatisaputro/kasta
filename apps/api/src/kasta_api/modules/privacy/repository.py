from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.models import DeviceSession, Role
from kasta_api.modules.businesses.models import (
    Business,
    BusinessMember,
    OrganizationMember,
)
from kasta_api.modules.mentors.models import Mentor
from kasta_api.modules.users.models import User


class PrivacyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user(self, user_id: UUID, *, lock: bool = False) -> User | None:
        statement = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def memberships(self, user_id: UUID) -> list[tuple[BusinessMember, Business, Role]]:
        rows = await self.session.execute(
            select(BusinessMember, Business, Role)
            .join(Business, Business.id == BusinessMember.business_id)
            .join(Role, Role.id == BusinessMember.role_id)
            .where(BusinessMember.user_id == user_id)
            .order_by(BusinessMember.created_at)
        )
        return list(rows.tuples().all())

    async def sessions(self, user_id: UUID) -> list[DeviceSession]:
        return list(
            (
                await self.session.scalars(
                    select(DeviceSession)
                    .where(DeviceSession.user_id == user_id)
                    .order_by(DeviceSession.created_at)
                )
            ).all()
        )

    async def audit_events(self, user_id: UUID, business_id: UUID) -> list[AuditLog]:
        return list(
            (
                await self.session.scalars(
                    select(AuditLog)
                    .where(
                        AuditLog.actor_user_id == user_id,
                        AuditLog.business_id == business_id,
                    )
                    .order_by(AuditLog.created_at)
                )
            ).all()
        )

    async def owned_businesses_without_successor(self, user_id: UUID) -> list[UUID]:
        owner_role_id = role_id(RoleCode.BUSINESS_OWNER)
        owned = list(
            (
                await self.session.scalars(
                    select(BusinessMember.business_id).where(
                        BusinessMember.user_id == user_id,
                        BusinessMember.role_id == owner_role_id,
                        BusinessMember.status == "ACTIVE",
                        BusinessMember.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        orphaned: list[UUID] = []
        for business_id in owned:
            successor_count = await self.session.scalar(
                select(func.count())
                .select_from(BusinessMember)
                .where(
                    BusinessMember.business_id == business_id,
                    BusinessMember.user_id != user_id,
                    BusinessMember.role_id == owner_role_id,
                    BusinessMember.status == "ACTIVE",
                    BusinessMember.deleted_at.is_(None),
                )
            )
            if not successor_count:
                orphaned.append(business_id)
        return orphaned

    async def deactivate_relationships(self, user_id: UUID, now: datetime) -> None:
        business_members = (
            await self.session.scalars(
                select(BusinessMember).where(
                    BusinessMember.user_id == user_id,
                    BusinessMember.status == "ACTIVE",
                    BusinessMember.deleted_at.is_(None),
                )
            )
        ).all()
        for business_member in business_members:
            business_member.status = "INACTIVE"
            business_member.deleted_at = now
        organization_members = (
            await self.session.scalars(
                select(OrganizationMember).where(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == "ACTIVE",
                    OrganizationMember.deleted_at.is_(None),
                )
            )
        ).all()
        for organization_member in organization_members:
            organization_member.status = "INACTIVE"
            organization_member.deleted_at = now
        mentors = (
            await self.session.scalars(
                select(Mentor).where(Mentor.user_id == user_id, Mentor.deleted_at.is_(None))
            )
        ).all()
        for mentor in mentors:
            mentor.status = "INACTIVE"
            mentor.deleted_at = now

    def add_audit(self, audit: AuditLog) -> None:
        self.session.add(audit)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
