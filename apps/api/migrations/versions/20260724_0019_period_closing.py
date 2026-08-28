"""Add period closing (tutup buku), a closing_frequency business setting, and permissions.

Revision ID: 20260724_0019
Revises: 20260724_0018
Create Date: 2026-07-24
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0019"
down_revision: str | None = "20260724_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
PERMISSIONS = ("closing.read", "closing.create")
ROLE_PERMISSIONS = {
    "business_owner": PERMISSIONS,
    "business_staff": ("closing.read",),
    "mentor": ("closing.read",),
    "organization_admin": ("closing.read",),
    "super_admin": PERMISSIONS,
}


def _id(prefix: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{prefix}:{code}")


def upgrade() -> None:
    op.add_column(
        "business_profiles",
        sa.Column(
            "closing_frequency",
            sa.String(length=20),
            nullable=False,
            server_default="MONTHLY",
        ),
    )
    op.create_check_constraint(
        "business_closing_frequency",
        "business_profiles",
        "closing_frequency IN ('MONTHLY', 'SEMIANNUAL', 'TRIANNUAL')",
    )

    op.drop_constraint("financial_transaction_type", "transactions", type_="check")
    op.create_check_constraint(
        "financial_transaction_type",
        "transactions",
        "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
        "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
        "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL', "
        "'COGS_POSTING', 'PERIOD_CLOSING')",
    )

    op.create_table(
        "period_closings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_revenue", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_expense", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_profit", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "closing_transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "closed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("note", sa.String(500)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("business_id", "period_end", name="uq_period_closings_business_end"),
        sa.CheckConstraint("period_end >= period_start", name="period_closing_valid_range"),
        sa.CheckConstraint(
            "total_revenue >= 0 AND total_expense >= 0", name="period_closing_non_negative"
        ),
    )
    op.create_index(
        "ix_period_closings_business_id", "period_closings", ["business_id"]
    )
    op.create_index(
        "ix_period_closings_business_end", "period_closings", ["business_id", "period_end"]
    )
    # Closed periods are an audit record: once written, never edited or removed.
    op.execute(
        "CREATE TRIGGER trg_period_closings_no_delete BEFORE DELETE ON period_closings "
        "FOR EACH ROW EXECUTE FUNCTION kasta_reject_financial_delete()"
    )
    op.execute(
        "CREATE TRIGGER trg_period_closings_no_update BEFORE UPDATE ON period_closings "
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
    op.execute("DROP TRIGGER IF EXISTS trg_period_closings_no_update ON period_closings")
    op.execute("DROP TRIGGER IF EXISTS trg_period_closings_no_delete ON period_closings")
    op.drop_table("period_closings")
    op.drop_constraint("financial_transaction_type", "transactions", type_="check")
    op.create_check_constraint(
        "financial_transaction_type",
        "transactions",
        "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
        "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
        "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL', "
        "'COGS_POSTING')",
    )
    op.drop_constraint("business_closing_frequency", "business_profiles", type_="check")
    op.drop_column("business_profiles", "closing_frequency")
