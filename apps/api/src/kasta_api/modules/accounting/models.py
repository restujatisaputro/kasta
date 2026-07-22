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


class Account(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("business_id", "code"),
        UniqueConstraint("business_id", "system_key", name="uq_accounts_business_system_key"),
        CheckConstraint(
            "account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE')",
            name="account_type",
        ),
        CheckConstraint("normal_balance IN ('DEBIT', 'CREDIT')", name="account_normal_balance"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_key: Mapped[str | None] = mapped_column(String(50))
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class FinancialTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "transaction_number", name="uq_transactions_business_number"
        ),
        UniqueConstraint(
            "business_id", "idempotency_key", name="uq_transactions_business_idempotency"
        ),
        UniqueConstraint("reverses_transaction_id"),
        UniqueConstraint("supersedes_transaction_id"),
        CheckConstraint(
            "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
            "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
            "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL')",
            name="financial_transaction_type",
        ),
        CheckConstraint("status IN ('POSTED', 'REVERSED')", name="financial_transaction_status"),
        CheckConstraint("amount > 0", name="financial_transaction_positive_amount"),
        CheckConstraint("revision_number >= 1", name="financial_transaction_revision_number"),
        Index("ix_transactions_business_date", "business_id", "transaction_date"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_number: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_account_key: Mapped[str | None] = mapped_column(String(50))
    category_account_key: Mapped[str | None] = mapped_column(String(50))
    entry_kind: Mapped[str | None] = mapped_column(String(20), index=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(200))
    payment_method_code: Mapped[str | None] = mapped_column(String(30), index=True)
    recurring_rule_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("recurring_transactions.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="POSTED", server_default="POSTED")
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    root_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    supersedes_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    reverses_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    reversed_by_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    posted_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("business_id", "entry_number"),
        CheckConstraint("status IN ('POSTED', 'REVERSED')", name="journal_entry_status"),
        CheckConstraint("total_debit = total_credit", name="journal_entry_balanced"),
        Index("ix_journal_entries_business_date", "business_id", "entry_date"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, index=True
    )
    reversal_of_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT"), unique=True
    )
    reversed_by_entry_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT")
    )
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="POSTED", server_default="POSTED")
    total_debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    posted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )


class JournalLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "debit_amount >= 0 AND credit_amount >= 0", name="journal_line_non_negative"
        ),
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="journal_line_one_side",
        ),
        Index("ix_journal_lines_business_entry", "business_id", "journal_entry_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    journal_entry_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )


class TransactionRevision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "transaction_revisions"
    __table_args__ = (
        UniqueConstraint("transaction_id", "event_sequence"),
        CheckConstraint("revision_number >= 1", name="transaction_revision_number"),
        CheckConstraint("event_sequence >= 1", name="transaction_event_sequence"),
        CheckConstraint(
            "event_type IN ('POSTED', 'REVERSED', 'REVISED')",
            name="transaction_revision_event_type",
        ),
        Index("ix_transaction_revisions_business_transaction", "business_id", "transaction_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    related_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
