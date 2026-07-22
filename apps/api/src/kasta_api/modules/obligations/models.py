from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
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


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("business_id", "name", name="uq_customers_business_name"),
        Index("ix_customers_business_name", "business_id", "name"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("business_id", "name", name="uq_suppliers_business_name"),
        Index("ix_suppliers_business_name", "business_id", "name"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class Receivable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receivables"
    __table_args__ = (
        CheckConstraint("initial_amount > 0", name="receivable_initial_positive"),
        CheckConstraint("paid_amount >= 0", name="receivable_paid_non_negative"),
        CheckConstraint("remaining_amount >= 0", name="receivable_remaining_non_negative"),
        CheckConstraint(
            "initial_amount = paid_amount + remaining_amount",
            name="receivable_amount_consistent",
        ),
        CheckConstraint(
            "status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'CANCELLED')",
            name="receivable_status",
        ),
        CheckConstraint("reminder_days_before BETWEEN 0 AND 90", name="receivable_reminder_days"),
        Index("ix_receivables_business_due_status", "business_id", "due_date", "status"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    initial_transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    cancellation_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
    initial_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500))
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    reminder_days_before: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))


class Payable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payables"
    __table_args__ = (
        CheckConstraint("initial_amount > 0", name="payable_initial_positive"),
        CheckConstraint("paid_amount >= 0", name="payable_paid_non_negative"),
        CheckConstraint("remaining_amount >= 0", name="payable_remaining_non_negative"),
        CheckConstraint(
            "initial_amount = paid_amount + remaining_amount", name="payable_amount_consistent"
        ),
        CheckConstraint(
            "status IN ('OPEN', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'CANCELLED')",
            name="payable_status",
        ),
        CheckConstraint("reminder_days_before BETWEEN 0 AND 90", name="payable_reminder_days"),
        Index("ix_payables_business_due_status", "business_id", "due_date", "status"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    supplier_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    initial_transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    cancellation_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
    initial_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500))
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    reminder_days_before: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))


class ReceivablePayment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "receivable_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="receivable_payment_positive"),
        Index("ix_receivable_payments_business_receivable", "business_id", "receivable_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    receivable_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("receivables.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_account_key: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PayablePayment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payable_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="payable_payment_positive"),
        Index("ix_payable_payments_business_payable", "business_id", "payable_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payable_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("payables.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_account_key: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "user_id",
            "notification_type",
            "entity_type",
            "entity_id",
            "scheduled_for",
            name="uq_notifications_recipient_entity_schedule",
        ),
        Index("ix_notifications_business_read_created", "business_id", "read_at", "created_at"),
        Index("ix_notifications_recipient_read_created", "user_id", "read_at", "created_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    action_path: Mapped[str | None] = mapped_column(String(500))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
