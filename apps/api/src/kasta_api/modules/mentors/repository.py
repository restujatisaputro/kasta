from datetime import date, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.models import JournalEntry
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import RoleCode
from kasta_api.modules.auth.models import Role
from kasta_api.modules.businesses.models import Business, BusinessMember, BusinessProfile
from kasta_api.modules.mentors.models import (
    Mentor,
    MentorBusinessAccess,
    MentoringSession,
    MentorNote,
    Recommendation,
)
from kasta_api.modules.obligations.models import Notification
from kasta_api.modules.users.models import User


class MentorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def add_all(self, instances: list[object]) -> None:
        self.session.add_all(instances)

    async def flush(self) -> None:
        await self.session.flush()

    async def touch_access(self, access: MentorBusinessAccess, now: datetime) -> None:
        if self.session.get_bind().dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT kasta_touch_mentor_access(:business_id)"),
                {"business_id": access.business_id},
            )
        else:
            access.last_accessed_at = now

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, instance: object) -> None:
        await self.session.refresh(instance)

    async def mentor_for_user(self, user_id: UUID) -> Mentor | None:
        return (
            await self.session.scalars(
                select(Mentor).where(
                    Mentor.user_id == user_id,
                    Mentor.status == "ACTIVE",
                    Mentor.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def access_businesses(
        self, mentor_id: UUID, *, now: datetime
    ) -> list[tuple[MentorBusinessAccess, Business, BusinessProfile | None]]:
        rows = (
            await self.session.execute(
                select(MentorBusinessAccess, Business, BusinessProfile)
                .join(Business, Business.id == MentorBusinessAccess.business_id)
                .outerjoin(BusinessProfile, BusinessProfile.business_id == Business.id)
                .where(
                    MentorBusinessAccess.mentor_id == mentor_id,
                    MentorBusinessAccess.status == "ACTIVE",
                    or_(
                        MentorBusinessAccess.expires_at.is_(None),
                        MentorBusinessAccess.expires_at > now,
                    ),
                    MentorBusinessAccess.deleted_at.is_(None),
                    Business.status == "ACTIVE",
                    Business.deleted_at.is_(None),
                )
                .order_by(Business.name)
            )
        ).all()
        return [(row[0], row[1], row[2]) for row in rows]

    async def access(
        self, mentor_id: UUID, business_id: UUID, *, now: datetime
    ) -> MentorBusinessAccess | None:
        return (
            await self.session.scalars(
                select(MentorBusinessAccess).where(
                    MentorBusinessAccess.mentor_id == mentor_id,
                    MentorBusinessAccess.business_id == business_id,
                    MentorBusinessAccess.status == "ACTIVE",
                    or_(
                        MentorBusinessAccess.expires_at.is_(None),
                        MentorBusinessAccess.expires_at > now,
                    ),
                    MentorBusinessAccess.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def open_access(self, mentor_id: UUID, business_id: UUID) -> MentorBusinessAccess | None:
        return (
            await self.session.scalars(
                select(MentorBusinessAccess).where(
                    MentorBusinessAccess.mentor_id == mentor_id,
                    MentorBusinessAccess.business_id == business_id,
                    MentorBusinessAccess.status.in_(("REQUESTED", "ACTIVE")),
                    MentorBusinessAccess.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def access_by_id(
        self, business_id: UUID, access_id: UUID, *, lock: bool = False
    ) -> MentorBusinessAccess | None:
        statement = select(MentorBusinessAccess).where(
            MentorBusinessAccess.id == access_id,
            MentorBusinessAccess.business_id == business_id,
            MentorBusinessAccess.deleted_at.is_(None),
        )
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def mentor_access_requests(self, mentor_id: UUID) -> list[MentorBusinessAccess]:
        return list(
            (
                await self.session.scalars(
                    select(MentorBusinessAccess)
                    .where(
                        MentorBusinessAccess.mentor_id == mentor_id,
                        MentorBusinessAccess.deleted_at.is_(None),
                    )
                    .order_by(MentorBusinessAccess.requested_at.desc())
                )
            ).all()
        )

    async def business_access_history(self, business_id: UUID) -> list[MentorBusinessAccess]:
        return list(
            (
                await self.session.scalars(
                    select(MentorBusinessAccess)
                    .where(
                        MentorBusinessAccess.business_id == business_id,
                        MentorBusinessAccess.deleted_at.is_(None),
                    )
                    .order_by(MentorBusinessAccess.requested_at.desc())
                )
            ).all()
        )

    async def business_by_code(self, code: str) -> Business | None:
        return (
            await self.session.scalars(
                select(Business).where(
                    func.lower(Business.code) == code.strip().lower(),
                    Business.status == "ACTIVE",
                    Business.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def access_audits(self, business_id: UUID, limit: int = 250) -> list[AuditLog]:
        return list(
            (
                await self.session.scalars(
                    select(AuditLog)
                    .where(
                        AuditLog.business_id == business_id,
                        AuditLog.action.in_(
                            (
                                "MENTOR_ACCESS_REQUESTED",
                                "MENTOR_ACCESS_APPROVED",
                                "MENTOR_ACCESS_REJECTED",
                                "MENTOR_ACCESS_REVOKED",
                                "MENTOR_DATA_ACCESSED",
                            )
                        ),
                    )
                    .order_by(AuditLog.created_at.desc())
                    .limit(limit)
                )
            ).all()
        )

    async def business(self, business_id: UUID) -> Business | None:
        return (
            await self.session.scalars(
                select(Business).where(Business.id == business_id, Business.deleted_at.is_(None))
            )
        ).one_or_none()

    async def latest_recorded_date(self, business_id: UUID) -> date | None:
        return cast(
            date | None,
            await self.session.scalar(
                select(func.max(JournalEntry.entry_date)).where(
                    JournalEntry.business_id == business_id
                )
            ),
        )

    async def recording_dates(self, business_id: UUID, since: date) -> list[date]:
        values = await self.session.scalars(
            select(JournalEntry.entry_date)
            .where(
                JournalEntry.business_id == business_id,
                JournalEntry.entry_date >= since,
            )
            .distinct()
        )
        return list(values.all())

    async def notes(self, mentor_id: UUID, business_id: UUID) -> list[MentorNote]:
        return list(
            (
                await self.session.scalars(
                    select(MentorNote)
                    .where(
                        MentorNote.mentor_id == mentor_id,
                        MentorNote.business_id == business_id,
                    )
                    .order_by(MentorNote.created_at.desc())
                    .limit(100)
                )
            ).all()
        )

    async def recommendations(self, mentor_id: UUID, business_id: UUID) -> list[Recommendation]:
        return list(
            (
                await self.session.scalars(
                    select(Recommendation)
                    .where(
                        Recommendation.mentor_id == mentor_id,
                        Recommendation.business_id == business_id,
                    )
                    .order_by(Recommendation.created_at.desc())
                )
            ).all()
        )

    async def recommendation(
        self, mentor_id: UUID, business_id: UUID, recommendation_id: UUID
    ) -> Recommendation | None:
        return (
            await self.session.scalars(
                select(Recommendation).where(
                    Recommendation.id == recommendation_id,
                    Recommendation.mentor_id == mentor_id,
                    Recommendation.business_id == business_id,
                )
            )
        ).one_or_none()

    async def sessions(self, mentor_id: UUID, business_id: UUID) -> list[MentoringSession]:
        return list(
            (
                await self.session.scalars(
                    select(MentoringSession)
                    .where(
                        MentoringSession.mentor_id == mentor_id,
                        MentoringSession.business_id == business_id,
                    )
                    .order_by(MentoringSession.scheduled_at.desc())
                )
            ).all()
        )

    async def mentoring_session(
        self, mentor_id: UUID, business_id: UUID, session_id: UUID
    ) -> MentoringSession | None:
        return (
            await self.session.scalars(
                select(MentoringSession).where(
                    MentoringSession.id == session_id,
                    MentoringSession.mentor_id == mentor_id,
                    MentoringSession.business_id == business_id,
                )
            )
        ).one_or_none()

    async def upcoming_sessions(
        self, mentor_id: UUID, now: datetime, limit: int = 10
    ) -> list[tuple[MentoringSession, str]]:
        rows = (
            await self.session.execute(
                select(MentoringSession, Business.name)
                .join(Business, Business.id == MentoringSession.business_id)
                .where(
                    MentoringSession.mentor_id == mentor_id,
                    MentoringSession.status == "SCHEDULED",
                    MentoringSession.scheduled_at >= now,
                )
                .order_by(MentoringSession.scheduled_at)
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def owner_user_id(self, business_id: UUID) -> UUID | None:
        return cast(
            UUID | None,
            await self.session.scalar(
                select(BusinessMember.user_id)
                .join(Role, Role.id == BusinessMember.role_id)
                .where(
                    BusinessMember.business_id == business_id,
                    BusinessMember.status == "ACTIVE",
                    BusinessMember.deleted_at.is_(None),
                    Role.code == RoleCode.BUSINESS_OWNER.value,
                )
                .limit(1)
            ),
        )

    async def audits(
        self, actor_user_id: UUID, business_ids: list[UUID], limit: int = 100
    ) -> list[tuple[AuditLog, str]]:
        if not business_ids:
            return []
        rows = (
            await self.session.execute(
                select(AuditLog, Business.name)
                .join(Business, Business.id == AuditLog.business_id)
                .where(
                    AuditLog.business_id.in_(business_ids),
                    AuditLog.actor_user_id == actor_user_id,
                    AuditLog.action.like("MENTOR_%"),
                )
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def notification_exists(
        self, business_id: UUID, entity_type: str, entity_id: UUID, scheduled_for: date
    ) -> bool:
        count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.business_id == business_id,
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.scheduled_for == scheduled_for,
            )
        )
        return bool(count)
