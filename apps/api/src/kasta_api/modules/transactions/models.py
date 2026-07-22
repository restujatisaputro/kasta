from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TransactionDraft(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "transaction_drafts"
    __table_args__ = (
        UniqueConstraint("business_id", "client_reference"),
        CheckConstraint(
            "entry_kind IN ('INCOME', 'EXPENSE', 'CAPITAL', 'OWNER_DRAW')",
            name="transaction_draft_kind",
        ),
        CheckConstraint("amount > 0", name="transaction_draft_positive_amount"),
        CheckConstraint("status IN ('ACTIVE', 'POSTED')", name="transaction_draft_status"),
        Index("ix_transaction_drafts_business_updated", "business_id", "updated_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    client_reference: Mapped[str | None] = mapped_column(String(100))
    entry_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    category_account_key: Mapped[str | None] = mapped_column(String(50))
    counterparty_name: Mapped[str | None] = mapped_column(String(200))
    payment_method_code: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str] = mapped_column(String(255), nullable=False)
    recurrence_frequency: Mapped[str | None] = mapped_column(String(20))
    recurrence_interval: Mapped[int | None] = mapped_column(Integer)
    items_data: Mapped[list[dict[str, str]] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")
    posted_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class RecurringTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        CheckConstraint(
            "entry_kind IN ('INCOME', 'EXPENSE', 'CAPITAL', 'OWNER_DRAW')",
            name="recurring_transaction_kind",
        ),
        CheckConstraint("amount > 0", name="recurring_transaction_positive_amount"),
        CheckConstraint("frequency IN ('WEEKLY', 'MONTHLY')", name="recurring_frequency"),
        CheckConstraint("recurrence_interval BETWEEN 1 AND 12", name="recurring_interval"),
        CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'CANCELLED')", name="recurring_status"),
        Index("ix_recurring_transactions_due", "business_id", "status", "next_run_date"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    category_account_key: Mapped[str | None] = mapped_column(String(50))
    counterparty_name: Mapped[str | None] = mapped_column(String(200))
    payment_method_code: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    recurrence_interval: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    items_data: Mapped[list[dict[str, str]] | None] = mapped_column(JSON)
    next_run_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class TransactionSyncLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "transaction_sync_logs"
    __table_args__ = (
        UniqueConstraint("business_id", "device_session_id", "client_operation_id"),
        CheckConstraint("status IN ('APPLIED', 'REJECTED')", name="transaction_sync_status"),
        Index("ix_transaction_sync_logs_business_created", "business_id", "created_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("device_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    client_operation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    server_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
