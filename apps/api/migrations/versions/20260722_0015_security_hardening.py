"""Harden account lockout, RLS enforcement, and audit immutability.

Revision ID: 20260722_0015
Revises: 20260722_0014
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0015"
down_revision: str | None = "20260722_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "business_profiles",
    "accounts",
    "journal_entries",
    "journal_lines",
    "transactions",
    "transaction_items",
    "transaction_revisions",
    "transaction_drafts",
    "recurring_transactions",
    "transaction_sync_logs",
    "receipts",
    "receipt_images",
    "receipt_items",
    "receipt_corrections",
    "ocr_results",
    "ocr_fields",
    "products",
    "stock_movements",
    "customers",
    "suppliers",
    "receivables",
    "receivable_payments",
    "payables",
    "payable_payments",
    "mentor_business_access",
    "mentor_notes",
    "recommendations",
    "mentoring_sessions",
    "audit_logs",
    "notifications",
    "support_access_grants",
    "device_sync_states",
    "sync_records",
    "sync_operation_logs",
    "sync_changes",
    "sync_conflict_revisions",
    "notification_preferences",
    "push_subscriptions",
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("user_failed_login_attempts", "users", "failed_login_attempts >= 0")
    op.create_index("ix_users_locked_until", "users", ["locked_until"])

    connection = op.get_bind()
    if connection.dialect.name != "postgresql":
        return
    for table_name in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION kasta_reject_audit_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only' USING ERRCODE = '42501';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_audit_logs_append_only BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION kasta_reject_audit_mutation()"
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS kasta_reject_audit_mutation()")
        for table_name in TENANT_TABLES:
            op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
    op.drop_index("ix_users_locked_until", table_name="users")
    op.drop_constraint("user_failed_login_attempts", "users", type_="check")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
