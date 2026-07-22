from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import StringIO
from typing import Protocol
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.inventory.constants import StockDirection, StockMovementType
from kasta_api.modules.inventory.excel import build_products_xlsx
from kasta_api.modules.inventory.models import Product, StockMovement, TransactionItem
from kasta_api.modules.inventory.repository import InventoryRepository
from kasta_api.modules.inventory.schemas import (
    BestSellerResponse,
    CsvImportResponse,
    InventorySummaryResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    StockHistoryResponse,
    StockMovementRequest,
    StockMovementResponse,
)

MONEY_QUANTUM = Decimal("0.01")
STOCK_QUANTUM = Decimal("0.001")
MAX_CSV_BYTES = 2 * 1024 * 1024
MAX_CSV_ROWS = 1000
CSV_COLUMNS = {
    "sku",
    "barcode",
    "nama",
    "kategori",
    "satuan",
    "harga_beli",
    "harga_jual",
    "stok_awal",
    "stok_minimum",
    "aktif",
}


class InventoryLine(Protocol):
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class ProductSnapshot:
    sku: str
    barcode: str | None
    name: str
    category: str
    unit: str
    purchase_price: str
    sale_price: str
    current_stock: str
    minimum_stock: str
    is_active: bool


class InventoryService:
    def __init__(self, repository: InventoryRepository) -> None:
        self.repository = repository

    async def create_product(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: ProductCreateRequest,
        *,
        request_id: str | None = None,
    ) -> ProductResponse:
        try:
            product = await self._new_product(
                business_id, actor_user_id, payload, request_id=request_id
            )
            await self.repository.commit()
            await self.repository.refresh(product)
            return self._product_response(product)
        except Exception:
            await self.repository.rollback()
            raise

    async def update_product(
        self,
        business_id: UUID,
        product_id: UUID,
        actor_user_id: UUID,
        payload: ProductUpdateRequest,
        *,
        request_id: str | None = None,
    ) -> ProductResponse:
        try:
            product = await self._required_product(business_id, product_id, for_update=True)
            conflict = await self.repository.identifier_conflict(
                business_id,
                sku=payload.sku,
                barcode=payload.barcode,
                exclude_id=product.id,
            )
            if conflict is not None:
                raise HTTPException(status_code=409, detail="SKU atau barcode sudah digunakan.")
            before = asdict(self._snapshot(product))
            product.sku = payload.sku
            product.barcode = payload.barcode
            product.name = payload.name
            product.category = payload.category
            product.unit = payload.unit
            product.purchase_price = self._money(payload.purchase_price)
            product.sale_price = self._money(payload.sale_price)
            product.minimum_stock = self._stock(payload.minimum_stock)
            product.is_active = payload.is_active
            self.repository.add(
                self._audit(
                    business_id,
                    actor_user_id,
                    "PRODUCT_UPDATED",
                    product.id,
                    before=before,
                    after=asdict(self._snapshot(product)),
                    request_id=request_id,
                )
            )
            await self.repository.commit()
            await self.repository.refresh(product)
            return self._product_response(product)
        except Exception:
            await self.repository.rollback()
            raise

    async def product(self, business_id: UUID, product_id: UUID) -> ProductResponse:
        return self._product_response(await self._required_product(business_id, product_id))

    async def product_by_barcode(self, business_id: UUID, barcode: str) -> ProductResponse:
        product = await self.repository.get_by_barcode(business_id, barcode.strip())
        if product is None:
            raise HTTPException(status_code=404, detail="Barcode belum terdaftar.")
        return self._product_response(product)

    async def list_products(
        self,
        business_id: UUID,
        *,
        query: str | None,
        category: str | None,
        active: bool | None,
        low_stock: bool,
        limit: int,
        offset: int,
    ) -> ProductListResponse:
        products, total = await self.repository.list_products(
            business_id,
            query=query,
            category=category,
            active=active,
            low_stock=low_stock,
            limit=limit,
            offset=offset,
        )
        return ProductListResponse(
            items=[self._product_response(product) for product in products],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def move_stock(
        self,
        business_id: UUID,
        product_id: UUID,
        actor_user_id: UUID,
        payload: StockMovementRequest,
        *,
        request_id: str | None = None,
    ) -> StockMovementResponse:
        try:
            product = await self._required_product(business_id, product_id, for_update=True)
            if not product.is_active:
                raise HTTPException(
                    status_code=409, detail="Aktifkan produk sebelum mengubah stok."
                )
            before = self._stock(product.current_stock)
            if payload.movement_type == "ADJUSTMENT":
                target = self._stock(payload.target_stock or Decimal("0"))
                delta = target - before
                if delta == 0:
                    raise HTTPException(
                        status_code=409, detail="Stok sudah sama dengan hasil hitung."
                    )
                movement_type = (
                    StockMovementType.ADJUSTMENT_IN
                    if delta > 0
                    else StockMovementType.ADJUSTMENT_OUT
                )
            else:
                quantity = self._stock(payload.quantity or Decimal("0"))
                outgoing = payload.movement_type in {"STOCK_OUT", "DAMAGED", "LOST"}
                delta = -quantity if outgoing else quantity
                movement_type = StockMovementType(payload.movement_type)
            unit_cost = self._money(payload.unit_cost or product.purchase_price)
            average_cost_before = product.purchase_price
            if delta > 0 and payload.unit_cost is not None:
                product.purchase_price = self._weighted_cost(
                    before,
                    product.purchase_price,
                    delta,
                    unit_cost,
                )
            movement = self._apply_delta(
                product,
                delta,
                movement_type,
                actor_user_id,
                unit_cost=unit_cost,
                average_cost_before=average_cost_before,
                reason=payload.reason,
                reference=payload.reference or None,
            )
            self.repository.add_all(
                [
                    movement,
                    self._audit(
                        business_id,
                        actor_user_id,
                        "STOCK_MOVED",
                        product.id,
                        after={
                            "movement_id": str(movement.id),
                            "movement_type": movement.movement_type,
                            "quantity_delta": str(movement.quantity_delta),
                            "stock_before": str(movement.stock_before),
                            "stock_after": str(movement.stock_after),
                        },
                        reason=payload.reason,
                        request_id=request_id,
                    ),
                ]
            )
            await self.repository.commit()
            return StockMovementResponse.model_validate(movement)
        except Exception:
            await self.repository.rollback()
            raise

    async def stock_history(
        self,
        business_id: UUID,
        *,
        product_id: UUID | None,
        movement_type: str | None,
        occurred_after: datetime | None,
        occurred_before: datetime | None,
        limit: int,
        offset: int,
    ) -> StockHistoryResponse:
        if product_id is not None:
            await self._required_product(business_id, product_id)
        rows, total = await self.repository.list_movements(
            business_id,
            product_id=product_id,
            movement_type=movement_type,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            limit=limit,
            offset=offset,
        )
        return StockHistoryResponse(
            items=[StockMovementResponse.model_validate(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def summary(self, business_id: UUID) -> InventorySummaryResponse:
        product_count, active_count, low_count, value = await self.repository.summary_counts(
            business_id
        )
        best = await self.repository.best_sellers(business_id)
        return InventorySummaryResponse(
            product_count=product_count,
            active_product_count=active_count,
            low_stock_count=low_count,
            inventory_value=self._money(value),
            best_sellers=[
                BestSellerResponse(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    unit=product.unit,
                    quantity_sold=self._stock(quantity),
                    sales_value=self._money(sales_value),
                )
                for product, quantity, sales_value in best
            ],
        )

    async def import_csv(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        upload: UploadFile,
        *,
        request_id: str | None = None,
    ) -> CsvImportResponse:
        data = await upload.read(MAX_CSV_BYTES + 1)
        await upload.close()
        if not data or len(data) > MAX_CSV_BYTES:
            raise HTTPException(status_code=413, detail="File CSV paling besar 2 MB.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="CSV harus memakai UTF-8.") from exc
        reader = csv.DictReader(StringIO(text))
        columns = set(reader.fieldnames or ())
        if not CSV_COLUMNS.issubset(columns):
            missing = ", ".join(sorted(CSV_COLUMNS - columns))
            raise HTTPException(status_code=422, detail=f"Kolom CSV belum lengkap: {missing}.")
        payloads: list[ProductCreateRequest] = []
        seen_skus: set[str] = set()
        seen_barcodes: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            if len(payloads) >= MAX_CSV_ROWS:
                raise HTTPException(
                    status_code=422, detail="CSV paling banyak berisi 1.000 produk."
                )
            try:
                payload = ProductCreateRequest(
                    sku=(row["sku"] or "").strip(),
                    barcode=(row["barcode"] or "").strip() or None,
                    name=(row["nama"] or "").strip(),
                    category=(row["kategori"] or "").strip(),
                    unit=(row["satuan"] or "").strip(),
                    purchase_price=self._csv_decimal(row["harga_beli"] or "0"),
                    sale_price=self._csv_decimal(row["harga_jual"] or "0"),
                    opening_stock=self._csv_decimal(row["stok_awal"] or "0"),
                    minimum_stock=self._csv_decimal(row["stok_minimum"] or "0"),
                    is_active=self._csv_bool(row["aktif"] or ""),
                )
            except (ValueError, InvalidOperation) as exc:
                raise HTTPException(
                    status_code=422, detail=f"Data CSV baris {row_number} tidak valid: {exc}"
                ) from exc
            if payload.sku in seen_skus or (
                payload.barcode is not None and payload.barcode in seen_barcodes
            ):
                raise HTTPException(
                    status_code=409, detail=f"SKU atau barcode ganda pada baris {row_number}."
                )
            seen_skus.add(payload.sku)
            if payload.barcode:
                seen_barcodes.add(payload.barcode)
            payloads.append(payload)
        if not payloads:
            raise HTTPException(status_code=422, detail="CSV tidak berisi produk.")
        try:
            products: list[Product] = []
            for payload in payloads:
                products.append(
                    await self._new_product(
                        business_id,
                        actor_user_id,
                        payload,
                        request_id=request_id,
                        audit_action="PRODUCT_IMPORTED",
                    )
                )
            await self.repository.commit()
            return CsvImportResponse(
                imported_count=len(products), product_ids=[product.id for product in products]
            )
        except Exception:
            await self.repository.rollback()
            raise

    async def export_excel(self, business_id: UUID) -> bytes:
        return build_products_xlsx(await self.repository.all_products(business_id))

    async def apply_transaction_lines(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        entry_kind: str,
        lines: Sequence[InventoryLine],
        *,
        revision: bool = False,
    ) -> None:
        if not lines:
            return
        if entry_kind not in {"INCOME", "EXPENSE"}:
            raise HTTPException(
                status_code=422, detail="Produk hanya untuk penjualan atau pembelian."
            )
        product_ids = {line.product_id for line in lines}
        products = await self.repository.lock_products(business_id, product_ids)
        if len(products) != len(product_ids):
            raise HTTPException(status_code=404, detail="Salah satu produk tidak ditemukan.")
        records: list[object] = []
        for line in lines:
            product = products[line.product_id]
            if not product.is_active:
                raise HTTPException(status_code=409, detail=f"Produk {product.name} tidak aktif.")
            quantity = self._stock(line.quantity)
            unit_price = self._money(line.unit_price)
            outgoing = entry_kind == "INCOME"
            delta = -quantity if outgoing else quantity
            average_cost_before = product.purchase_price
            if not outgoing:
                product.purchase_price = self._weighted_cost(
                    self._stock(product.current_stock),
                    product.purchase_price,
                    quantity,
                    unit_price,
                )
            item = TransactionItem(
                id=uuid4(),
                business_id=business_id,
                transaction_id=transaction_id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=self._money(quantity * unit_price),
                stock_direction=(StockDirection.OUT if outgoing else StockDirection.IN).value,
            )
            movement = self._apply_delta(
                product,
                delta,
                (
                    StockMovementType.REVISION_ADJUSTMENT
                    if revision
                    else StockMovementType.SALE
                    if outgoing
                    else StockMovementType.PURCHASE
                ),
                actor_user_id,
                unit_cost=product.purchase_price if outgoing else unit_price,
                average_cost_before=average_cost_before,
                reason="Perubahan transaksi" if revision else "Dibuat dari transaksi",
                transaction_id=transaction_id,
                transaction_item_id=item.id,
            )
            records.extend((item, movement))
        self.repository.add_all(records)
        await self.repository.flush()

    async def reverse_transaction_lines(
        self,
        business_id: UUID,
        original_transaction_id: UUID,
        reversal_transaction_id: UUID,
        actor_user_id: UUID,
        *,
        reason: str,
    ) -> None:
        original_items = await self.repository.transaction_items(
            business_id, original_transaction_id
        )
        if not original_items:
            return
        products = await self.repository.lock_products(
            business_id, {item.product_id for item in original_items}
        )
        original_movements = await self.repository.movements_for_items(
            business_id, {item.id for item in original_items}
        )
        if len(products) != len({item.product_id for item in original_items}):
            raise HTTPException(status_code=409, detail="Produk transaksi lama tidak tersedia.")
        records: list[object] = []
        for original in original_items:
            product = products[original.product_id]
            originally_out = original.stock_direction == StockDirection.OUT.value
            delta = original.quantity if originally_out else -original.quantity
            average_cost_before = product.purchase_price
            if not originally_out:
                remaining_stock = self._stock(product.current_stock - original.quantity)
                original_movement = original_movements.get(original.id)
                if (
                    original_movement is not None
                    and product.purchase_price == original_movement.average_cost_after
                ):
                    product.purchase_price = original_movement.average_cost_before
                elif remaining_stock > 0:
                    remaining_value = (
                        self._stock(product.current_stock) * product.purchase_price
                        - original.quantity * original.unit_price
                    )
                    product.purchase_price = self._money(
                        max(Decimal("0.00"), remaining_value) / remaining_stock
                    )
            reversal_item = TransactionItem(
                id=uuid4(),
                business_id=business_id,
                transaction_id=reversal_transaction_id,
                product_id=product.id,
                reverses_item_id=original.id,
                quantity=original.quantity,
                unit_price=original.unit_price,
                line_total=original.line_total,
                stock_direction=(StockDirection.IN if originally_out else StockDirection.OUT).value,
            )
            movement = self._apply_delta(
                product,
                delta,
                (
                    StockMovementType.SALE_REVERSAL
                    if originally_out
                    else StockMovementType.PURCHASE_REVERSAL
                ),
                actor_user_id,
                unit_cost=(product.purchase_price if originally_out else original.unit_price),
                average_cost_before=average_cost_before,
                reason=reason,
                transaction_id=reversal_transaction_id,
                transaction_item_id=reversal_item.id,
            )
            records.extend((reversal_item, movement))
        self.repository.add_all(records)
        await self.repository.flush()

    async def _new_product(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: ProductCreateRequest,
        *,
        request_id: str | None,
        audit_action: str = "PRODUCT_CREATED",
    ) -> Product:
        conflict = await self.repository.identifier_conflict(
            business_id, sku=payload.sku, barcode=payload.barcode
        )
        if conflict is not None:
            raise HTTPException(status_code=409, detail="SKU atau barcode sudah digunakan.")
        opening = self._stock(payload.opening_stock)
        now = utc_now()
        product = Product(
            id=uuid4(),
            business_id=business_id,
            sku=payload.sku,
            barcode=payload.barcode,
            name=payload.name,
            category=payload.category,
            unit=payload.unit,
            purchase_price=self._money(payload.purchase_price),
            sale_price=self._money(payload.sale_price),
            opening_stock=opening,
            current_stock=opening,
            minimum_stock=self._stock(payload.minimum_stock),
            is_active=payload.is_active,
        )
        records: list[object] = [product]
        if opening > 0:
            records.append(
                StockMovement(
                    id=uuid4(),
                    business_id=business_id,
                    product_id=product.id,
                    movement_type=StockMovementType.OPENING.value,
                    quantity_delta=opening,
                    stock_before=Decimal("0.000"),
                    stock_after=opening,
                    unit_cost=product.purchase_price,
                    total_cost=self._money(opening * product.purchase_price),
                    average_cost_before=product.purchase_price,
                    average_cost_after=product.purchase_price,
                    reason="Stok awal produk",
                    occurred_at=now,
                    created_by_user_id=actor_user_id,
                    created_at=now,
                )
            )
        records.append(
            self._audit(
                business_id,
                actor_user_id,
                audit_action,
                product.id,
                after=asdict(self._snapshot(product)),
                request_id=request_id,
            )
        )
        self.repository.add_all(records)
        await self.repository.flush()
        return product

    def _apply_delta(
        self,
        product: Product,
        delta: Decimal,
        movement_type: StockMovementType,
        actor_user_id: UUID,
        *,
        unit_cost: Decimal,
        average_cost_before: Decimal | None = None,
        reason: str,
        reference: str | None = None,
        transaction_id: UUID | None = None,
        transaction_item_id: UUID | None = None,
    ) -> StockMovement:
        delta = self._stock(delta)
        before = self._stock(product.current_stock)
        after = self._stock(before + delta)
        if after < 0:
            raise HTTPException(
                status_code=409,
                detail=f"Stok {product.name} tidak cukup. Tersedia {before} {product.unit}.",
            )
        now = utc_now()
        product.current_stock = after
        return StockMovement(
            id=uuid4(),
            business_id=product.business_id,
            product_id=product.id,
            transaction_id=transaction_id,
            transaction_item_id=transaction_item_id,
            movement_type=movement_type.value,
            quantity_delta=delta,
            stock_before=before,
            stock_after=after,
            unit_cost=self._money(unit_cost),
            total_cost=self._money(abs(delta) * unit_cost),
            average_cost_before=self._money(
                product.purchase_price if average_cost_before is None else average_cost_before
            ),
            average_cost_after=self._money(product.purchase_price),
            reason=reason,
            reference=reference,
            occurred_at=now,
            created_by_user_id=actor_user_id,
            created_at=now,
        )

    async def _required_product(
        self, business_id: UUID, product_id: UUID, *, for_update: bool = False
    ) -> Product:
        product = await self.repository.get_product(business_id, product_id, for_update=for_update)
        if product is None:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
        return product

    @classmethod
    def _product_response(cls, product: Product) -> ProductResponse:
        return ProductResponse(
            id=product.id,
            business_id=product.business_id,
            sku=product.sku,
            barcode=product.barcode,
            name=product.name,
            category=product.category,
            unit=product.unit,
            purchase_price=cls._money(product.purchase_price),
            sale_price=cls._money(product.sale_price),
            opening_stock=cls._stock(product.opening_stock),
            current_stock=cls._stock(product.current_stock),
            minimum_stock=cls._stock(product.minimum_stock),
            is_active=product.is_active,
            is_low_stock=product.is_active and product.current_stock <= product.minimum_stock,
            inventory_value=cls._money(product.current_stock * product.purchase_price),
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    @classmethod
    def _snapshot(cls, product: Product) -> ProductSnapshot:
        return ProductSnapshot(
            sku=product.sku,
            barcode=product.barcode,
            name=product.name,
            category=product.category,
            unit=product.unit,
            purchase_price=str(cls._money(product.purchase_price)),
            sale_price=str(cls._money(product.sale_price)),
            current_stock=str(cls._stock(product.current_stock)),
            minimum_stock=str(cls._stock(product.minimum_stock)),
            is_active=product.is_active,
        )

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _stock(value: Decimal) -> Decimal:
        return Decimal(value).quantize(STOCK_QUANTUM, rounding=ROUND_HALF_UP)

    @classmethod
    def _weighted_cost(
        cls,
        current_stock: Decimal,
        current_cost: Decimal,
        added_stock: Decimal,
        added_cost: Decimal,
    ) -> Decimal:
        total_stock = current_stock + added_stock
        if total_stock <= 0:
            return cls._money(added_cost)
        return cls._money(
            ((current_stock * current_cost) + (added_stock * added_cost)) / total_stock
        )

    @staticmethod
    def _csv_decimal(raw: str) -> Decimal:
        value = raw.strip().replace("Rp", "").replace("rp", "").replace(" ", "")
        if not value:
            return Decimal("0")
        if "." in value and "," in value:
            value = value.replace(".", "").replace(",", ".")
        elif value.count(".") > 1 or ("." in value and len(value.rsplit(".", 1)[1]) == 3):
            value = value.replace(".", "")
        elif "," in value:
            trailing = value.rsplit(",", 1)[1]
            value = value.replace(",", "" if len(trailing) == 3 else ".")
        return Decimal(value)

    @staticmethod
    def _csv_bool(raw: str) -> bool:
        normalized = raw.strip().lower()
        if normalized in {"ya", "yes", "true", "1", "aktif"}:
            return True
        if normalized in {"tidak", "no", "false", "0", "nonaktif"}:
            return False
        raise ValueError("kolom aktif harus Ya atau Tidak")

    @staticmethod
    def _audit(
        business_id: UUID,
        actor_user_id: UUID,
        action: str,
        entity_id: UUID,
        *,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type="PRODUCT",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )
