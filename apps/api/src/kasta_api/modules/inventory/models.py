from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),
        UniqueConstraint("business_id", "barcode", name="uq_products_business_barcode"),
        CheckConstraint("purchase_price >= 0", name="product_purchase_price_non_negative"),
        CheckConstraint("sale_price >= 0", name="product_sale_price_non_negative"),
        CheckConstraint("opening_stock >= 0", name="product_opening_stock_non_negative"),
        CheckConstraint("current_stock >= 0", name="product_current_stock_non_negative"),
        CheckConstraint("minimum_stock >= 0", name="product_minimum_stock_non_negative"),
        Index("ix_products_business_active_name", "business_id", "is_active", "name"),
        Index("ix_products_business_low_stock", "business_id", "is_active", "current_stock"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
    opening_stock: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), default=Decimal("0.000"), server_default="0.000", nullable=False
    )
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), default=Decimal("0.000"), server_default="0.000", nullable=False
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), default=Decimal("0.000"), server_default="0.000", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )


class TransactionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transaction_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="transaction_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="transaction_item_price_non_negative"),
        CheckConstraint("line_total >= 0", name="transaction_item_total_non_negative"),
        CheckConstraint("stock_direction IN ('IN', 'OUT')", name="transaction_item_direction"),
        Index("ix_transaction_items_business_transaction", "business_id", "transaction_id"),
        Index("ix_transaction_items_business_product", "business_id", "product_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reverses_item_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transaction_items.id", ondelete="RESTRICT"), unique=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    stock_direction: Mapped[str] = mapped_column(String(3), nullable=False)


class StockMovement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity_delta <> 0", name="stock_movement_delta_non_zero"),
        CheckConstraint("stock_before >= 0", name="stock_movement_before_non_negative"),
        CheckConstraint("stock_after >= 0", name="stock_movement_after_non_negative"),
        CheckConstraint("unit_cost >= 0", name="stock_movement_unit_cost_non_negative"),
        CheckConstraint(
            "average_cost_before >= 0 AND average_cost_after >= 0",
            name="stock_movement_average_cost_non_negative",
        ),
        CheckConstraint(
            "movement_type IN ('OPENING', 'STOCK_IN', 'STOCK_OUT', 'ADJUSTMENT_IN', "
            "'ADJUSTMENT_OUT', 'DAMAGED', 'LOST', 'SALE', 'PURCHASE', "
            "'SALE_REVERSAL', 'PURCHASE_REVERSAL', 'REVISION_ADJUSTMENT')",
            name="stock_movement_type",
        ),
        Index(
            "ix_stock_movements_business_product_time", "business_id", "product_id", "occurred_at"
        ),
        Index("ix_stock_movements_business_transaction", "business_id", "transaction_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), index=True
    )
    transaction_item_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transaction_items.id", ondelete="RESTRICT"), unique=True
    )
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    stock_before: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    stock_after: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    average_cost_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    average_cost_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    reference: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
