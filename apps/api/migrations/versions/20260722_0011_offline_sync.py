"""Add versioned offline synchronization records and conflict history.

Revision ID: 20260722_0011
Revises: 20260721_0010
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0011"
down_revision: str | None = "20260721_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_records",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("is_financial", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("version >= 1", name="ck_sync_records_sync_record_version"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id", "entity_type", "entity_id", name="uq_sync_record_entity"
        ),
    )
    op.create_index("ix_sync_records_business_id", "sync_records", ["business_id"])
    op.create_index("ix_sync_records_transaction_id", "sync_records", ["transaction_id"])
    op.create_index("ix_sync_records_deleted_at", "sync_records", ["deleted_at"])
    op.create_index(
        "ix_sync_records_business_updated", "sync_records", ["business_id", "updated_at"]
    )

    op.create_table(
        "sync_operation_logs",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("device_session_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(200), nullable=False),
        sa.Column("batch_id", sa.String(100), nullable=False),
        sa.Column("operation_id", sa.String(100), nullable=False),
        sa.Column("response_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_session_id"], ["device_sessions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id", "device_id", "operation_id", name="uq_sync_operation_device"
        ),
    )
    op.create_index("ix_sync_operation_logs_business_id", "sync_operation_logs", ["business_id"])
    op.create_index(
        "ix_sync_operation_logs_device_session_id", "sync_operation_logs", ["device_session_id"]
    )
    op.create_index(
        "ix_sync_operations_business_created", "sync_operation_logs", ["business_id", "created_at"]
    )

    op.create_table(
        "sync_conflict_revisions",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("device_session_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(200), nullable=False),
        sa.Column("operation_id", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("client_version", sa.Integer(), nullable=False),
        sa.Column("server_version", sa.Integer(), nullable=False),
        sa.Column("client_payload", sa.JSON(), nullable=False),
        sa.Column("server_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.String(30), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED')", name="ck_sync_conflict_revisions_sync_conflict_status"
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_session_id"], ["device_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sync_conflict_revisions_business_id", "sync_conflict_revisions", ["business_id"]
    )
    op.create_index(
        "ix_sync_conflict_revisions_device_session_id",
        "sync_conflict_revisions",
        ["device_session_id"],
    )
    op.create_index(
        "ix_sync_conflict_revisions_entity_id", "sync_conflict_revisions", ["entity_id"]
    )
    op.create_index(
        "ix_sync_conflicts_business_status", "sync_conflict_revisions", ["business_id", "status"]
    )

    op.create_table(
        "sync_changes",
        sa.Column("sequence", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["record_id"], ["sync_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sequence"),
        sa.UniqueConstraint("id"),
    )
    op.create_index("ix_sync_changes_business_id", "sync_changes", ["business_id"])
    op.create_index("ix_sync_changes_record_id", "sync_changes", ["record_id"])
    op.create_index(
        "ix_sync_changes_business_sequence", "sync_changes", ["business_id", "sequence"]
    )

    op.create_table(
        "device_sync_states",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("device_session_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(200), nullable=False),
        sa.Column("last_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_cursor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_session_id"], ["device_sessions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "device_id", name="uq_device_sync_state"),
    )
    op.create_index("ix_device_sync_states_business_id", "device_sync_states", ["business_id"])
    op.create_index(
        "ix_device_sync_states_device_session_id", "device_sync_states", ["device_session_id"]
    )

    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "sync_records",
            "sync_operation_logs",
            "sync_conflict_revisions",
            "sync_changes",
            "device_sync_states",
        ):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
                USING (business_id = NULLIF(current_setting('app.business_id', true), '')::uuid)
                WITH CHECK (
                    business_id = NULLIF(current_setting('app.business_id', true), '')::uuid
                )'''
            )


def downgrade() -> None:
    op.drop_table("device_sync_states")
    op.drop_table("sync_changes")
    op.drop_table("sync_conflict_revisions")
    op.drop_table("sync_operation_logs")
    op.drop_table("sync_records")
