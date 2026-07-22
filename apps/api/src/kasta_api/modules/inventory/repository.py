from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.models import FinancialTransaction
from kasta_api.modules.inventory.models import Product, StockMovement, TransactionItem


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def add_all(self, instances: list[object]) -> None:
        self.session.add_all(instances)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, instance: object) -> None:
        await self.session.refresh(instance)

    async def get_product(
        self, business_id: UUID, product_id: UUID, *, for_update: bool = False
    ) -> Product | None:
        statement = select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
            Product.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def get_by_barcode(self, business_id: UUID, barcode: str) -> Product | None:
        return (
            await self.session.scalars(
                select(Product).where(
                    Product.business_id == business_id,
                    Product.barcode == barcode,
                    Product.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def identifier_conflict(
        self,
        business_id: UUID,
        *,
        sku: str,
        barcode: str | None,
        exclude_id: UUID | None = None,
    ) -> Product | None:
        identifiers = [Product.sku == sku]
        if barcode:
            identifiers.append(Product.barcode == barcode)
        filters = [
            Product.business_id == business_id,
            Product.deleted_at.is_(None),
            or_(*identifiers),
        ]
        if exclude_id is not None:
            filters.append(Product.id != exclude_id)
        return (await self.session.scalars(select(Product).where(*filters).limit(1))).first()

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
    ) -> tuple[list[Product], int]:
        filters = [Product.business_id == business_id, Product.deleted_at.is_(None)]
        if query:
            pattern = f"%{query.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.sku).like(pattern),
                    func.lower(func.coalesce(Product.barcode, "")).like(pattern),
                )
            )
        if category:
            filters.append(func.lower(Product.category) == category.strip().lower())
        if active is not None:
            filters.append(Product.is_active.is_(active))
        if low_stock:
            filters.extend(
                (Product.is_active.is_(True), Product.current_stock <= Product.minimum_stock)
            )
        products = list(
            (
                await self.session.scalars(
                    select(Product)
                    .where(*filters)
                    .order_by(Product.name, Product.sku)
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        total = await self.session.scalar(select(func.count(Product.id)).where(*filters))
        return products, int(total or 0)

    async def all_products(self, business_id: UUID) -> list[Product]:
        return list(
            (
                await self.session.scalars(
                    select(Product)
                    .where(Product.business_id == business_id, Product.deleted_at.is_(None))
                    .order_by(Product.name, Product.sku)
                )
            ).all()
        )

    async def lock_products(self, business_id: UUID, product_ids: set[UUID]) -> dict[UUID, Product]:
        if not product_ids:
            return {}
        products = list(
            (
                await self.session.scalars(
                    select(Product)
                    .where(
                        Product.business_id == business_id,
                        Product.id.in_(sorted(product_ids, key=str)),
                        Product.deleted_at.is_(None),
                    )
                    .order_by(Product.id)
                    .with_for_update()
                )
            ).all()
        )
        return {product.id: product for product in products}

    async def transaction_items(
        self, business_id: UUID, transaction_id: UUID
    ) -> list[TransactionItem]:
        return list(
            (
                await self.session.scalars(
                    select(TransactionItem)
                    .where(
                        TransactionItem.business_id == business_id,
                        TransactionItem.transaction_id == transaction_id,
                    )
                    .order_by(TransactionItem.created_at, TransactionItem.id)
                )
            ).all()
        )

    async def movements_for_items(
        self, business_id: UUID, item_ids: set[UUID]
    ) -> dict[UUID, StockMovement]:
        if not item_ids:
            return {}
        movements = (
            await self.session.scalars(
                select(StockMovement).where(
                    StockMovement.business_id == business_id,
                    StockMovement.transaction_item_id.in_(item_ids),
                )
            )
        ).all()
        return {
            movement.transaction_item_id: movement
            for movement in movements
            if movement.transaction_item_id is not None
        }

    async def list_movements(
        self,
        business_id: UUID,
        *,
        product_id: UUID | None,
        movement_type: str | None,
        occurred_after: datetime | None,
        occurred_before: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[StockMovement], int]:
        filters = [StockMovement.business_id == business_id]
        if product_id is not None:
            filters.append(StockMovement.product_id == product_id)
        if movement_type:
            filters.append(StockMovement.movement_type == movement_type)
        if occurred_after:
            filters.append(StockMovement.occurred_at >= occurred_after)
        if occurred_before:
            filters.append(StockMovement.occurred_at <= occurred_before)
        rows = list(
            (
                await self.session.scalars(
                    select(StockMovement)
                    .where(*filters)
                    .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        total = await self.session.scalar(select(func.count(StockMovement.id)).where(*filters))
        return rows, int(total or 0)

    async def summary_counts(self, business_id: UUID) -> tuple[int, int, int, Decimal]:
        filters = [Product.business_id == business_id, Product.deleted_at.is_(None)]
        row = (
            await self.session.execute(
                select(
                    func.count(Product.id),
                    func.count(Product.id).filter(Product.is_active.is_(True)),
                    func.count(Product.id).filter(
                        Product.is_active.is_(True), Product.current_stock <= Product.minimum_stock
                    ),
                    func.coalesce(func.sum(Product.current_stock * Product.purchase_price), 0),
                ).where(*filters)
            )
        ).one()
        return int(row[0]), int(row[1]), int(row[2]), Decimal(row[3])

    async def best_sellers(
        self, business_id: UUID, limit: int = 10
    ) -> list[tuple[Product, Decimal, Decimal]]:
        quantity = func.sum(TransactionItem.quantity).label("quantity_sold")
        value = func.sum(TransactionItem.line_total).label("sales_value")
        rows = (
            await self.session.execute(
                select(Product, quantity, value)
                .join(TransactionItem, TransactionItem.product_id == Product.id)
                .join(
                    FinancialTransaction, FinancialTransaction.id == TransactionItem.transaction_id
                )
                .where(
                    Product.business_id == business_id,
                    Product.deleted_at.is_(None),
                    FinancialTransaction.business_id == business_id,
                    FinancialTransaction.status == "POSTED",
                    FinancialTransaction.entry_kind == "INCOME",
                    TransactionItem.stock_direction == "OUT",
                )
                .group_by(Product.id)
                .order_by(quantity.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], Decimal(row[1]), Decimal(row[2])) for row in rows]
