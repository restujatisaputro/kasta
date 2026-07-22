"""Add products, transaction items, stock movements, and inventory permissions.

Revision ID: 20260721_0007
Revises: 20260721_0006
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0007"
down_revision: str | None = "20260721_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
PERMISSIONS = (
    "product.create",
    "product.read",
    "product.update",
    "stock.manage",
    "inventory.import",
    "inventory.export",
)
ROLE_PERMISSIONS = {
    "business_owner": PERMISSIONS,
    "business_staff": (
        "product.create",
        "product.read",
        "product.update",
        "stock.manage",
    ),
    "organization_admin": ("product.read", "inventory.export"),
    "super_admin": PERMISSIONS,
}


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _role_id(code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"role:{code}")


def _permission_id(code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"permission:{code}")


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("barcode", sa.String(64)),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("purchase_price", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("sale_price", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("opening_stock", sa.Numeric(18, 3), server_default="0.000", nullable=False),
        sa.Column("current_stock", sa.Numeric(18, 3), server_default="0.000", nullable=False),
        sa.Column("minimum_stock", sa.Numeric(18, 3), server_default="0.000", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
        sa.UniqueConstraint("business_id", "barcode", name="uq_products_business_barcode"),
        sa.CheckConstraint("purchase_price >= 0", name="product_purchase_price_non_negative"),
        sa.CheckConstraint("sale_price >= 0", name="product_sale_price_non_negative"),
        sa.CheckConstraint("opening_stock >= 0", name="product_opening_stock_non_negative"),
        sa.CheckConstraint("current_stock >= 0", name="product_current_stock_non_negative"),
        sa.CheckConstraint("minimum_stock >= 0", name="product_minimum_stock_non_negative"),
    )
    op.create_index("ix_products_business_id", "products", ["business_id"])
    op.create_index(
        "ix_products_business_active_name", "products", ["business_id", "is_active", "name"]
    )
    op.create_index(
        "ix_products_business_low_stock",
        "products",
        ["business_id", "is_active", "current_stock"],
    )

    op.create_table(
        "transaction_items",
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
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reverses_item_id",
            sa.Uuid(),
            sa.ForeignKey("transaction_items.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("stock_direction", sa.String(3), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("quantity > 0", name="transaction_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="transaction_item_price_non_negative"),
        sa.CheckConstraint("line_total >= 0", name="transaction_item_total_non_negative"),
        sa.CheckConstraint("stock_direction IN ('IN', 'OUT')", name="transaction_item_direction"),
    )
    op.create_index("ix_transaction_items_business_id", "transaction_items", ["business_id"])
    op.create_index("ix_transaction_items_transaction_id", "transaction_items", ["transaction_id"])
    op.create_index("ix_transaction_items_product_id", "transaction_items", ["product_id"])
    op.create_index(
        "ix_transaction_items_business_transaction",
        "transaction_items",
        ["business_id", "transaction_id"],
    )
    op.create_index(
        "ix_transaction_items_business_product",
        "transaction_items",
        ["business_id", "product_id"],
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "transaction_item_id",
            sa.Uuid(),
            sa.ForeignKey("transaction_items.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(18, 3), nullable=False),
        sa.Column("stock_before", sa.Numeric(18, 3), nullable=False),
        sa.Column("stock_after", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("average_cost_before", sa.Numeric(18, 2), nullable=False),
        sa.Column("average_cost_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("reference", sa.String(100)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_delta <> 0", name="stock_movement_delta_non_zero"),
        sa.CheckConstraint("stock_before >= 0", name="stock_movement_before_non_negative"),
        sa.CheckConstraint("stock_after >= 0", name="stock_movement_after_non_negative"),
        sa.CheckConstraint("unit_cost >= 0", name="stock_movement_unit_cost_non_negative"),
        sa.CheckConstraint(
            "average_cost_before >= 0 AND average_cost_after >= 0",
            name="stock_movement_average_cost_non_negative",
        ),
        sa.CheckConstraint(
            "movement_type IN ('OPENING', 'STOCK_IN', 'STOCK_OUT', 'ADJUSTMENT_IN', "
            "'ADJUSTMENT_OUT', 'DAMAGED', 'LOST', 'SALE', 'PURCHASE', "
            "'SALE_REVERSAL', 'PURCHASE_REVERSAL', 'REVISION_ADJUSTMENT')",
            name="stock_movement_type",
        ),
    )
    op.create_index("ix_stock_movements_business_id", "stock_movements", ["business_id"])
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_transaction_id", "stock_movements", ["transaction_id"])
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index(
        "ix_stock_movements_created_by_user_id", "stock_movements", ["created_by_user_id"]
    )
    op.create_index(
        "ix_stock_movements_business_product_time",
        "stock_movements",
        ["business_id", "product_id", "occurred_at"],
    )
    op.create_index(
        "ix_stock_movements_business_transaction",
        "stock_movements",
        ["business_id", "transaction_id"],
    )

    op.add_column("transaction_drafts", sa.Column("items_data", sa.JSON()))
    op.add_column("recurring_transactions", sa.Column("items_data", sa.JSON()))

    for table_name in ("products", "transaction_items", "stock_movements"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete "
            f"BEFORE DELETE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_financial_delete()"
        )
    for table_name in ("transaction_items", "stock_movements"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update "
            f"BEFORE UPDATE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_immutable_update()"
        )

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": _permission_id(code),
                "code": code,
                "module": code.split(".", maxsplit=1)[0],
                "description": code,
            }
            for code in PERMISSIONS
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "id": uuid5(AUTH_NAMESPACE, f"role-permission:{role}:{permission}"),
                "role_id": _role_id(role),
                "permission_id": _permission_id(permission),
            }
            for role, permissions in ROLE_PERMISSIONS.items()
            for permission in permissions
        ],
    )


def downgrade() -> None:
    role_permission_ids = [
        uuid5(AUTH_NAMESPACE, f"role-permission:{role}:{permission}")
        for role, permissions in ROLE_PERMISSIONS.items()
        for permission in permissions
    ]
    role_permission_values = ", ".join(f"'{value}'::uuid" for value in role_permission_ids)
    permission_values = ", ".join(f"'{_permission_id(code)}'::uuid" for code in PERMISSIONS)
    op.execute(f"DELETE FROM role_permissions WHERE id IN ({role_permission_values})")
    op.execute(f"DELETE FROM permissions WHERE id IN ({permission_values})")
    for table_name in ("transaction_items", "stock_movements"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update ON {table_name}")
    for table_name in ("products", "transaction_items", "stock_movements"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete ON {table_name}")
    op.drop_column("recurring_transactions", "items_data")
    op.drop_column("transaction_drafts", "items_data")
    op.drop_table("stock_movements")
    op.drop_table("transaction_items")
    op.drop_table("products")
