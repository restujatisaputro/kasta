"""Add receivables, payables, payments, reminders, and obligation permissions.

Revision ID: 20260721_0008
Revises: 20260721_0007
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0008"
down_revision: str | None = "20260721_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
PERMISSIONS = (
    "receivable.create",
    "receivable.read",
    "receivable.payment.create",
    "receivable.cancel",
    "payable.create",
    "payable.read",
    "payable.payment.create",
    "payable.cancel",
    "obligation.reminder.manage",
)
ROLE_PERMISSIONS = {
    "business_owner": PERMISSIONS,
    "business_staff": (
        "receivable.create",
        "receivable.read",
        "receivable.payment.create",
        "payable.create",
        "payable.read",
        "payable.payment.create",
    ),
    "organization_admin": ("receivable.read", "payable.read"),
    "super_admin": PERMISSIONS,
}


def _id(prefix: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{prefix}:{code}")


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _party_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("email", sa.String(320)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("business_id", "name", name=f"uq_{name}_business_name"),
    )
    op.create_index(f"ix_{name}_business_id", name, ["business_id"])
    op.create_index(f"ix_{name}_business_name", name, ["business_id", "name"])


def _obligation_table(name: str, party_table: str, party_column: str) -> None:
    singular = name.removesuffix("s")
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            party_column,
            sa.Uuid(),
            sa.ForeignKey(f"{party_table}.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "initial_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "cancellation_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("initial_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("remaining_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("reminder_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("reminder_days_before", sa.Integer(), server_default="3", nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column(
            "cancelled_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT")
        ),
        sa.Column("cancellation_reason", sa.String(500)),
        *_timestamps(),
        sa.CheckConstraint("initial_amount > 0", name=f"{singular}_initial_positive"),
        sa.CheckConstraint("paid_amount >= 0", name=f"{singular}_paid_non_negative"),
        sa.CheckConstraint("remaining_amount >= 0", name=f"{singular}_remaining_non_negative"),
        sa.CheckConstraint(
            "initial_amount = paid_amount + remaining_amount", name=f"{singular}_amount_consistent"
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','PARTIALLY_PAID','PAID','OVERDUE','CANCELLED')",
            name=f"{singular}_status",
        ),
        sa.CheckConstraint(
            "reminder_days_before BETWEEN 0 AND 90", name=f"{singular}_reminder_days"
        ),
    )
    op.create_index(f"ix_{name}_business_id", name, ["business_id"])
    op.create_index(f"ix_{name}_{party_column}", name, [party_column])
    op.create_index(f"ix_{name}_status", name, ["status"])
    op.create_index(f"ix_{name}_business_due_status", name, ["business_id", "due_date", "status"])


def _payment_table(name: str, obligation_table: str, obligation_column: str) -> None:
    singular = name.removesuffix("s")
    op.create_table(
        name,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            obligation_column,
            sa.Uuid(),
            sa.ForeignKey(f"{obligation_table}.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_account_key", sa.String(50), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name=f"{singular}_positive"),
    )
    op.create_index(f"ix_{name}_business_id", name, ["business_id"])
    op.create_index(f"ix_{name}_{obligation_column}", name, [obligation_column])
    op.create_index(f"ix_{name}_created_by_user_id", name, ["created_by_user_id"])
    op.create_index(
        f"ix_{name}_business_{obligation_column.removesuffix('_id')}",
        name,
        ["business_id", obligation_column],
    )


def upgrade() -> None:
    _party_table("customers")
    _party_table("suppliers")
    _obligation_table("receivables", "customers", "customer_id")
    _obligation_table("payables", "suppliers", "supplier_id")
    _payment_table("receivable_payments", "receivables", "receivable_id")
    _payment_table("payable_payments", "payables", "payable_id")
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint(
            "business_id",
            "entity_type",
            "entity_id",
            "scheduled_for",
            name="uq_notifications_entity_schedule",
        ),
    )
    op.create_index("ix_notifications_business_id", "notifications", ["business_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_business_read_created",
        "notifications",
        ["business_id", "read_at", "created_at"],
    )

    for table in ("receivables", "payables", "receivable_payments", "payable_payments"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION kasta_reject_financial_delete()"
        )
    for table in ("receivable_payments", "payable_payments"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_update BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION kasta_reject_immutable_update()"
        )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    links = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": _id("permission", code),
                "code": code,
                "module": code.split(".", 1)[0],
                "description": code,
            }
            for code in PERMISSIONS
        ],
    )
    op.bulk_insert(
        links,
        [
            {
                "id": _id("role-permission", f"{role}:{permission}"),
                "role_id": _id("role", role),
                "permission_id": _id("permission", permission),
            }
            for role, values in ROLE_PERMISSIONS.items()
            for permission in values
        ],
    )


def downgrade() -> None:
    link_ids = [
        _id("role-permission", f"{role}:{permission}")
        for role, values in ROLE_PERMISSIONS.items()
        for permission in values
    ]
    op.execute(
        "DELETE FROM role_permissions WHERE id IN ("
        + ",".join(f"'{value}'::uuid" for value in link_ids)
        + ")"
    )
    op.execute(
        "DELETE FROM permissions WHERE id IN ("
        + ",".join(f"'{_id('permission', code)}'::uuid" for code in PERMISSIONS)
        + ")"
    )
    for table in ("receivable_payments", "payable_payments"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_update ON {table}")
    for table in ("receivables", "payables", "receivable_payments", "payable_payments"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_delete ON {table}")
    for table in (
        "notifications",
        "payable_payments",
        "receivable_payments",
        "payables",
        "receivables",
        "suppliers",
        "customers",
    ):
        op.drop_table(table)
