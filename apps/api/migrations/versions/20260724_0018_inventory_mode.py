"""Add a per-business simple/perpetual inventory mode and a COGS posting transaction type.

Revision ID: 20260724_0018
Revises: 20260723_0017
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0018"
down_revision: str | None = "20260723_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "business_profiles",
        sa.Column(
            "inventory_mode", sa.String(length=20), nullable=False, server_default="SIMPLE"
        ),
    )
    op.create_check_constraint(
        "business_inventory_mode",
        "business_profiles",
        "inventory_mode IN ('SIMPLE', 'PERPETUAL')",
    )
    op.drop_constraint("financial_transaction_type", "transactions", type_="check")
    op.create_check_constraint(
        "financial_transaction_type",
        "transactions",
        "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
        "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
        "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL', "
        "'COGS_POSTING')",
    )


def downgrade() -> None:
    op.drop_constraint("financial_transaction_type", "transactions", type_="check")
    op.create_check_constraint(
        "financial_transaction_type",
        "transactions",
        "transaction_type IN ('CASH_SALE', 'NON_CASH_SALE', 'CREDIT_SALE', "
        "'CASH_PURCHASE', 'CREDIT_PURCHASE', 'CAPITAL_CONTRIBUTION', 'OWNER_DRAW', "
        "'PAYABLE_PAYMENT', 'RECEIVABLE_RECEIPT', 'OPERATING_EXPENSE', 'REVERSAL')",
    )
    op.drop_constraint("business_inventory_mode", "business_profiles", type_="check")
    op.drop_column("business_profiles", "inventory_mode")
