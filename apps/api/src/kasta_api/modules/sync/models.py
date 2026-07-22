from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SyncRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Current server-side version of one syncable logical record."""

    __tablename__ = "sync_records"
    __table_args__ = (
        UniqueConstraint("business_id", "entity_type", "entity_id", name="uq_sync_record_entity"),
        CheckConstraint("version >= 1", name="sync_record_version"),
        Index("ix_sync_records_business_updated", "business_id", "updated_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), index=True
    )
    is_financial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class SyncOperationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sync_operation_logs"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "device_id", "operation_id", name="uq_sync_operation_device"
        ),
        Index("ix_sync_operations_business_created", "business_id", "created_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("device_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(200), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    response_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SyncConflictRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sync_conflict_revisions"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="sync_conflict_status"),
        Index("ix_sync_conflicts_business_status", "business_id", "status"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("device_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(200), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    client_version: Mapped[int] = mapped_column(Integer, nullable=False)
    server_version: Mapped[int] = mapped_column(Integer, nullable=False)
    client_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    server_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    resolution: Mapped[str | None] = mapped_column(String(30))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )


class SyncChange(Base):
    __tablename__ = "sync_changes"
    __table_args__ = (Index("ix_sync_changes_business_sequence", "business_id", "sequence"),)

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    record_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sync_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeviceSyncState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_sync_states"
    __table_args__ = (UniqueConstraint("business_id", "device_id", name="uq_device_sync_state"),)

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("device_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(200), nullable=False)
    last_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_pull_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(500))
