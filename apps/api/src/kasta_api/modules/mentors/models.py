from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Mentor(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "mentors"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")


class MentorBusinessAccess(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "mentor_business_access"
    __table_args__ = (
        CheckConstraint(
            "status IN ('REQUESTED', 'ACTIVE', 'REJECTED', 'REVOKED', 'EXPIRED')",
            name="mentor_access_status",
        ),
        CheckConstraint("revision_no > 0", name="mentor_access_revision"),
        CheckConstraint(
            "status <> 'ACTIVE' OR (granted_by_user_id IS NOT NULL AND granted_at IS NOT NULL)",
            name="mentor_access_grant",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > COALESCE(granted_at, requested_at)",
            name="mentor_access_validity",
        ),
        CheckConstraint(
            "status <> 'REVOKED' OR revoked_at IS NOT NULL",
            name="mentor_access_revoked",
        ),
        Index(
            "uq_mentor_business_access_open",
            "mentor_id",
            "business_id",
            unique=True,
            postgresql_where=text("status IN ('REQUESTED', 'ACTIVE') AND deleted_at IS NULL"),
            sqlite_where=text("status IN ('REQUESTED', 'ACTIVE') AND deleted_at IS NULL"),
        ),
        Index("ix_mentor_business_access_active", "mentor_id", "status", "expires_at"),
        Index("ix_mentor_business_access_business_status", "business_id", "status"),
    )

    mentor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    scope: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        server_default="[]",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), default="REQUESTED", server_default="REQUESTED")
    request_message: Mapped[str | None] = mapped_column(String(500))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    revocation_reason: Mapped[str | None] = mapped_column(String(500))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision_no: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class SupportAccessGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "support_access_grants"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'REVOKED', 'EXPIRED')", name="support_access_status"),
        CheckConstraint("expires_at > granted_at", name="support_access_validity"),
        CheckConstraint(
            "status <> 'REVOKED' OR revoked_at IS NOT NULL",
            name="support_access_revoked",
        ),
        Index("ix_support_access_admin_active", "admin_user_id", "status", "expires_at"),
        Index("ix_support_access_business_active", "business_id", "status", "expires_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    admin_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scope: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    ticket_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MentorNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentor_notes"
    __table_args__ = (
        CheckConstraint("visibility IN ('SHARED', 'PRIVATE')", name="mentor_note_visibility"),
        Index("ix_mentor_notes_business_created", "business_id", "created_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mentors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="SHARED", server_default="SHARED")


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH')", name="recommendation_priority"),
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED')",
            name="recommendation_status",
        ),
        Index("ix_recommendations_business_status_due", "business_id", "status", "due_date"),
        Index("ix_recommendations_mentor_status", "mentor_id", "status"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mentors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", server_default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="OPEN", server_default="OPEN")
    due_date: Mapped[date | None] = mapped_column(Date)
    follow_up_note: Mapped[str | None] = mapped_column(String(1000))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MentoringSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentoring_sessions"
    __table_args__ = (
        CheckConstraint("mode IN ('ONSITE', 'ONLINE', 'PHONE')", name="mentoring_session_mode"),
        CheckConstraint(
            "status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')",
            name="mentoring_session_status",
        ),
        CheckConstraint("duration_minutes BETWEEN 15 AND 480", name="mentoring_session_duration"),
        Index("ix_mentoring_sessions_mentor_schedule", "mentor_id", "status", "scheduled_at"),
        Index("ix_mentoring_sessions_business_schedule", "business_id", "scheduled_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mentor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mentors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    mode: Mapped[str] = mapped_column(String(20), default="ONLINE", server_default="ONLINE")
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", server_default="SCHEDULED")
    topic: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500))
    outcome: Mapped[str | None] = mapped_column(Text)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
