"""Add simple transactions, drafts, recurring schedules, receipts, and sync.

Revision ID: 20260721_0005
Revises: 20260721_0004
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0005"
down_revision: str | None = "20260721_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "transaction_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("client_reference", sa.String(100)),
        sa.Column("entry_kind", sa.String(20), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("category_account_key", sa.String(50)),
        sa.Column("counterparty_name", sa.String(200)),
        sa.Column("payment_method_code", sa.String(30), nullable=False),
        sa.Column("note", sa.String(255), nullable=False),
        sa.Column("recurrence_frequency", sa.String(20)),
        sa.Column("recurrence_interval", sa.Integer()),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column(
            "posted_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "entry_kind IN ('INCOME', 'EXPENSE', 'CAPITAL', 'OWNER_DRAW')",
            name="transaction_draft_kind",
        ),
        sa.CheckConstraint("amount > 0", name="transaction_draft_positive_amount"),
        sa.CheckConstraint("status IN ('ACTIVE', 'POSTED')", name="transaction_draft_status"),
        sa.UniqueConstraint(
            "business_id", "client_reference", name="uq_transaction_drafts_business_id"
        ),
    )
    op.create_index("ix_transaction_drafts_business_id", "transaction_drafts", ["business_id"])
    op.create_index(
        "ix_transaction_drafts_business_updated",
        "transaction_drafts",
        ["business_id", "updated_at"],
    )

    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("entry_kind", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("category_account_key", sa.String(50)),
        sa.Column("counterparty_name", sa.String(200)),
        sa.Column("payment_method_code", sa.String(30), nullable=False),
        sa.Column("note", sa.String(255), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("recurrence_interval", sa.Integer(), server_default="1", nullable=False),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "entry_kind IN ('INCOME', 'EXPENSE', 'CAPITAL', 'OWNER_DRAW')",
            name="recurring_transaction_kind",
        ),
        sa.CheckConstraint("amount > 0", name="recurring_transaction_positive_amount"),
        sa.CheckConstraint("frequency IN ('WEEKLY', 'MONTHLY')", name="recurring_frequency"),
        sa.CheckConstraint("recurrence_interval BETWEEN 1 AND 12", name="recurring_interval"),
        sa.CheckConstraint("status IN ('ACTIVE', 'PAUSED', 'CANCELLED')", name="recurring_status"),
    )
    op.create_index(
        "ix_recurring_transactions_business_id", "recurring_transactions", ["business_id"]
    )
    op.create_index(
        "ix_recurring_transactions_due",
        "recurring_transactions",
        ["business_id", "status", "next_run_date"],
    )

    op.add_column("transactions", sa.Column("entry_kind", sa.String(20)))
    op.add_column("transactions", sa.Column("counterparty_name", sa.String(200)))
    op.add_column("transactions", sa.Column("payment_method_code", sa.String(30)))
    op.add_column("transactions", sa.Column("recurring_rule_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_transactions_recurring_rule_id_recurring_transactions",
        "transactions",
        "recurring_transactions",
        ["recurring_rule_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_transactions_entry_kind", "transactions", ["entry_kind"])
    op.create_index("ix_transactions_payment_method_code", "transactions", ["payment_method_code"])
    op.create_index("ix_transactions_recurring_rule_id", "transactions", ["recurring_rule_id"])

    op.create_table(
        "receipt_images",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(500), nullable=False, unique=True),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_receipt_images_business_id", "receipt_images", ["business_id"])
    op.create_index("ix_receipt_images_transaction_id", "receipt_images", ["transaction_id"])
    op.create_index(
        "ix_receipt_images_business_transaction",
        "receipt_images",
        ["business_id", "transaction_id"],
    )

    op.create_table(
        "transaction_sync_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_session_id",
            sa.Uuid(),
            sa.ForeignKey("device_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("client_operation_id", sa.String(100), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column(
            "server_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('APPLIED', 'REJECTED')", name="transaction_sync_status"),
        sa.UniqueConstraint(
            "business_id",
            "device_session_id",
            "client_operation_id",
            name="uq_transaction_sync_logs_business_id",
        ),
    )
    op.create_index(
        "ix_transaction_sync_logs_business_id", "transaction_sync_logs", ["business_id"]
    )
    op.create_index(
        "ix_transaction_sync_logs_device_session_id",
        "transaction_sync_logs",
        ["device_session_id"],
    )
    op.create_index(
        "ix_transaction_sync_logs_business_created",
        "transaction_sync_logs",
        ["business_id", "created_at"],
    )

    for table_name in ("recurring_transactions", "receipt_images", "transaction_sync_logs"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete "
            f"BEFORE DELETE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_financial_delete()"
        )
    op.execute(
        "CREATE TRIGGER trg_transaction_sync_logs_no_update "
        "BEFORE UPDATE ON transaction_sync_logs FOR EACH ROW "
        "EXECUTE FUNCTION kasta_reject_immutable_update()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_transaction_sync_logs_no_update ON transaction_sync_logs"
    )
    for table_name in ("recurring_transactions", "receipt_images", "transaction_sync_logs"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete ON {table_name}")

    op.drop_table("transaction_sync_logs")
    op.drop_table("receipt_images")
    op.drop_index("ix_transactions_recurring_rule_id", table_name="transactions")
    op.drop_index("ix_transactions_payment_method_code", table_name="transactions")
    op.drop_index("ix_transactions_entry_kind", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_recurring_rule_id_recurring_transactions",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "recurring_rule_id")
    op.drop_column("transactions", "payment_method_code")
    op.drop_column("transactions", "counterparty_name")
    op.drop_column("transactions", "entry_kind")
    op.drop_table("recurring_transactions")
    op.drop_table("transaction_drafts")
