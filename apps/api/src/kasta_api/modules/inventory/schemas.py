from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kasta_api.modules.inventory.constants import PRODUCT_UNITS

NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=3)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=3)]
Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class ProductCreateRequest(BaseModel):
    sku: OptionalCode
    barcode: OptionalCode | None = None
    name: NameText
    category: ShortText
    unit: str
    purchase_price: Money = Decimal("0.00")
    sale_price: Money = Decimal("0.00")
    opening_stock: Quantity = Decimal("0.000")
    minimum_stock: Quantity = Decimal("0.000")
    is_active: bool = True

    @model_validator(mode="after")
    def normalize_product(self) -> ProductCreateRequest:
        self.sku = self.sku.upper()
        self.barcode = self.barcode or None
        self.category = self.category.strip()
        self.unit = self.unit.strip().upper()
        if self.unit not in PRODUCT_UNITS:
            raise ValueError("Satuan produk belum didukung.")
        return self


class ProductUpdateRequest(BaseModel):
    sku: OptionalCode
    barcode: OptionalCode | None = None
    name: NameText
    category: ShortText
    unit: str
    purchase_price: Money
    sale_price: Money
    minimum_stock: Quantity
    is_active: bool

    @model_validator(mode="after")
    def normalize_product(self) -> ProductUpdateRequest:
        self.sku = self.sku.upper()
        self.barcode = self.barcode or None
        self.category = self.category.strip()
        self.unit = self.unit.strip().upper()
        if self.unit not in PRODUCT_UNITS:
            raise ValueError("Satuan produk belum didukung.")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    sku: str
    barcode: str | None
    name: str
    category: str
    unit: str
    purchase_price: Decimal
    sale_price: Decimal
    opening_stock: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    is_active: bool
    is_low_stock: bool
    inventory_value: Decimal
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


class StockMovementRequest(BaseModel):
    movement_type: Literal["STOCK_IN", "STOCK_OUT", "ADJUSTMENT", "DAMAGED", "LOST"]
    quantity: PositiveQuantity | None = None
    target_stock: Quantity | None = None
    unit_cost: Money | None = None
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    reference: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ""

    @model_validator(mode="after")
    def validate_movement(self) -> StockMovementRequest:
        if self.movement_type == "ADJUSTMENT":
            if self.target_stock is None or self.quantity is not None:
                raise ValueError("Isi stok hasil perhitungan untuk penyesuaian.")
        elif self.quantity is None or self.target_stock is not None:
            raise ValueError("Isi jumlah pergerakan stok.")
        return self


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    product_id: UUID
    transaction_id: UUID | None
    movement_type: str
    quantity_delta: Decimal
    stock_before: Decimal
    stock_after: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    average_cost_before: Decimal
    average_cost_after: Decimal
    reason: str | None
    reference: str | None
    occurred_at: datetime
    created_by_user_id: UUID
    created_at: datetime


class StockHistoryResponse(BaseModel):
    items: list[StockMovementResponse]
    total: int
    limit: int
    offset: int


class BestSellerResponse(BaseModel):
    product_id: UUID
    sku: str
    name: str
    unit: str
    quantity_sold: Decimal
    sales_value: Decimal


class InventorySummaryResponse(BaseModel):
    product_count: int
    active_product_count: int
    low_stock_count: int
    inventory_value: Decimal
    best_sellers: list[BestSellerResponse]


class CsvImportResponse(BaseModel):
    imported_count: int
    product_ids: list[UUID]
