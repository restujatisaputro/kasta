from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.receipts.models import (
    OcrField,
    OcrResult,
    Receipt,
    ReceiptCorrection,
    ReceiptImage,
    ReceiptItem,
)


class ReceiptOcrRepository:
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

    async def refresh(self, instance: object) -> None:
        await self.session.refresh(instance)

    async def get_receipt(self, business_id: UUID, receipt_id: UUID) -> Receipt | None:
        return (
            await self.session.scalars(
                select(Receipt).where(
                    Receipt.id == receipt_id,
                    Receipt.business_id == business_id,
                )
            )
        ).one_or_none()

    async def get_result(self, receipt_id: UUID) -> OcrResult | None:
        return (
            await self.session.scalars(
                select(OcrResult)
                .where(OcrResult.receipt_id == receipt_id)
                .order_by(OcrResult.created_at.desc())
                .limit(1)
            )
        ).one_or_none()

    async def list_fields(self, receipt_id: UUID) -> list[OcrField]:
        return list(
            (
                await self.session.scalars(
                    select(OcrField)
                    .where(OcrField.receipt_id == receipt_id)
                    .order_by(OcrField.field_name)
                )
            ).all()
        )

    async def list_items(self, receipt_id: UUID) -> list[ReceiptItem]:
        return list(
            (
                await self.session.scalars(
                    select(ReceiptItem)
                    .where(ReceiptItem.receipt_id == receipt_id)
                    .order_by(ReceiptItem.line_number)
                )
            ).all()
        )

    async def list_images(self, receipt_id: UUID) -> list[ReceiptImage]:
        return list(
            (
                await self.session.scalars(
                    select(ReceiptImage).where(
                        ReceiptImage.receipt_id == receipt_id,
                        ReceiptImage.deleted_at.is_(None),
                    )
                )
            ).all()
        )

    async def duplicate_candidates(
        self,
        business_id: UUID,
        receipt_id: UUID,
        *,
        receipt_date: date | None,
        total: Decimal | None,
        merchant_normalized: str | None,
        receipt_number: str | None,
    ) -> list[Receipt]:
        filters = []
        if receipt_number:
            filters.append(Receipt.receipt_number == receipt_number)
        if merchant_normalized:
            filters.append(Receipt.merchant_normalized == merchant_normalized)
        if total is not None:
            filters.append(Receipt.total_amount == total)
        if receipt_date is not None:
            filters.append(
                Receipt.receipt_date.between(
                    receipt_date - timedelta(days=2), receipt_date + timedelta(days=2)
                )
            )
        if not filters:
            return []
        return list(
            (
                await self.session.scalars(
                    select(Receipt)
                    .where(
                        Receipt.business_id == business_id,
                        Receipt.id != receipt_id,
                        Receipt.status.in_(("NEEDS_REVIEW", "CONFIRMED")),
                        or_(*filters),
                    )
                    .order_by(Receipt.created_at.desc())
                    .limit(20)
                )
            ).all()
        )

    async def get_field_map(self, receipt_id: UUID) -> dict[str, OcrField]:
        return {field.field_name: field for field in await self.list_fields(receipt_id)}

    def add_correction(self, correction: ReceiptCorrection) -> None:
        self.session.add(correction)
