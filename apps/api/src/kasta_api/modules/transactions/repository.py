from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.models import FinancialTransaction
from kasta_api.modules.receipts.models import ReceiptImage
from kasta_api.modules.transactions.models import (
    RecurringTransaction,
    TransactionDraft,
    TransactionSyncLog,
)


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, instance: object) -> None:
        await self.session.refresh(instance)

    async def get_draft(self, business_id: UUID, draft_id: UUID) -> TransactionDraft | None:
        return (
            await self.session.scalars(
                select(TransactionDraft).where(
                    TransactionDraft.id == draft_id,
                    TransactionDraft.business_id == business_id,
                    TransactionDraft.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def get_draft_by_reference(
        self, business_id: UUID, client_reference: str | None
    ) -> TransactionDraft | None:
        if client_reference is None:
            return None
        return (
            await self.session.scalars(
                select(TransactionDraft).where(
                    TransactionDraft.business_id == business_id,
                    TransactionDraft.client_reference == client_reference,
                    TransactionDraft.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def list_drafts(self, business_id: UUID) -> list[TransactionDraft]:
        return list(
            (
                await self.session.scalars(
                    select(TransactionDraft)
                    .where(
                        TransactionDraft.business_id == business_id,
                        TransactionDraft.status == "ACTIVE",
                        TransactionDraft.deleted_at.is_(None),
                    )
                    .order_by(TransactionDraft.updated_at.desc())
                )
            ).all()
        )

    async def list_transactions(
        self,
        business_id: UUID,
        *,
        query: str | None,
        entry_kind: str | None,
        transaction_status: str | None,
        payment_method: str | None,
        date_from: date | None,
        date_to: date | None,
        updated_after: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[FinancialTransaction, int]], int]:
        filters = [
            FinancialTransaction.business_id == business_id,
            FinancialTransaction.transaction_type != "REVERSAL",
        ]
        if query:
            pattern = f"%{query.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(FinancialTransaction.description).like(pattern),
                    func.lower(func.coalesce(FinancialTransaction.counterparty_name, "")).like(
                        pattern
                    ),
                    func.lower(FinancialTransaction.transaction_number).like(pattern),
                )
            )
        if entry_kind:
            filters.append(FinancialTransaction.entry_kind == entry_kind)
        if transaction_status:
            filters.append(FinancialTransaction.status == transaction_status)
        if payment_method:
            filters.append(FinancialTransaction.payment_method_code == payment_method)
        if date_from:
            filters.append(FinancialTransaction.transaction_date >= date_from)
        if date_to:
            filters.append(FinancialTransaction.transaction_date <= date_to)
        if updated_after:
            filters.append(FinancialTransaction.updated_at > updated_after)

        receipt_count = func.count(ReceiptImage.id).label("receipt_count")
        statement = (
            select(FinancialTransaction, receipt_count)
            .outerjoin(
                ReceiptImage,
                (ReceiptImage.transaction_id == FinancialTransaction.id)
                & (ReceiptImage.deleted_at.is_(None)),
            )
            .where(*filters)
            .group_by(FinancialTransaction.id)
            .order_by(
                FinancialTransaction.transaction_date.desc(),
                FinancialTransaction.posted_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(statement)).all())
        total = await self.session.scalar(
            select(func.count(FinancialTransaction.id)).where(*filters)
        )
        return [(row[0], int(row[1])) for row in rows], int(total or 0)

    async def recent_category_keys(self, business_id: UUID) -> list[str]:
        rows = await self.session.execute(
            select(
                FinancialTransaction.category_account_key,
                func.max(FinancialTransaction.posted_at).label("last_used"),
            )
            .where(
                FinancialTransaction.business_id == business_id,
                FinancialTransaction.category_account_key.is_not(None),
                FinancialTransaction.entry_kind == "EXPENSE",
            )
            .group_by(FinancialTransaction.category_account_key)
            .order_by(func.max(FinancialTransaction.posted_at).desc())
        )
        return [str(row[0]) for row in rows if row[0] is not None]

    async def list_recurring(self, business_id: UUID) -> list[RecurringTransaction]:
        return list(
            (
                await self.session.scalars(
                    select(RecurringTransaction)
                    .where(RecurringTransaction.business_id == business_id)
                    .order_by(RecurringTransaction.next_run_date)
                )
            ).all()
        )

    async def get_recurring(
        self, business_id: UUID, recurring_id: UUID
    ) -> RecurringTransaction | None:
        return (
            await self.session.scalars(
                select(RecurringTransaction).where(
                    RecurringTransaction.id == recurring_id,
                    RecurringTransaction.business_id == business_id,
                )
            )
        ).one_or_none()

    async def due_recurring(
        self, business_id: UUID, through_date: date
    ) -> list[RecurringTransaction]:
        return list(
            (
                await self.session.scalars(
                    select(RecurringTransaction)
                    .where(
                        RecurringTransaction.business_id == business_id,
                        RecurringTransaction.status == "ACTIVE",
                        RecurringTransaction.next_run_date <= through_date,
                    )
                    .order_by(RecurringTransaction.next_run_date)
                    .with_for_update()
                )
            ).all()
        )

    async def get_receipt(self, business_id: UUID, receipt_id: UUID) -> ReceiptImage | None:
        return (
            await self.session.scalars(
                select(ReceiptImage).where(
                    ReceiptImage.id == receipt_id,
                    ReceiptImage.business_id == business_id,
                    ReceiptImage.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def get_sync_log(
        self, business_id: UUID, device_session_id: UUID, client_operation_id: str
    ) -> TransactionSyncLog | None:
        return (
            await self.session.scalars(
                select(TransactionSyncLog).where(
                    TransactionSyncLog.business_id == business_id,
                    TransactionSyncLog.device_session_id == device_session_id,
                    TransactionSyncLog.client_operation_id == client_operation_id,
                )
            )
        ).one_or_none()
