from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
)
from kasta_api.modules.businesses.models import Business
from kasta_api.modules.inventory.models import Product, TransactionItem
from kasta_api.modules.obligations.models import Payable, Receivable


@dataclass(frozen=True, slots=True)
class LedgerRow:
    entry_id: UUID
    entry_date: date
    source: str
    description: str
    transaction_id: UUID | None
    transaction_type: str | None
    payment_account_key: str | None
    payment_method_code: str | None
    category_account_key: str | None
    account_key: str
    account_name: str
    account_type: str
    normal_balance: str
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True, slots=True)
class ProductSnapshot:
    id: UUID
    sku: str
    name: str
    unit: str
    current_stock: Decimal
    minimum_stock: Decimal
    purchase_price: Decimal
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProductSaleRow:
    product_id: UUID
    sku: str
    name: str
    unit: str
    quantity: Decimal
    line_total: Decimal
    transaction_type: str


@dataclass(frozen=True, slots=True)
class ObligationSnapshot:
    initial_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    due_date: date
    status: str
    transaction_date: date
    cancelled_at: datetime | None


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def business(self, business_id: UUID) -> Business | None:
        return (
            await self.session.scalars(
                select(Business).where(
                    Business.id == business_id,
                    Business.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def ledger_rows(
        self,
        business_id: UUID,
        *,
        date_from: date | None,
        date_to: date,
        category: str | None,
        payment_method: str | None,
    ) -> list[LedgerRow]:
        entry_ids = select(JournalEntry.id).where(JournalEntry.business_id == business_id)
        if date_from is not None:
            entry_ids = entry_ids.where(JournalEntry.entry_date >= date_from)
        entry_ids = entry_ids.where(JournalEntry.entry_date <= date_to)
        if category:
            entry_ids = (
                entry_ids.join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
                .join(Account, Account.id == JournalLine.account_id)
                .outerjoin(
                    FinancialTransaction,
                    FinancialTransaction.id == JournalEntry.transaction_id,
                )
                .where(
                    or_(
                        Account.system_key == category,
                        FinancialTransaction.category_account_key == category,
                    )
                )
            )
        if payment_method:
            if category is None:
                entry_ids = entry_ids.outerjoin(
                    FinancialTransaction,
                    FinancialTransaction.id == JournalEntry.transaction_id,
                )
            entry_ids = entry_ids.where(self._payment_filter(payment_method))
        entry_ids = entry_ids.distinct()

        statement = (
            select(
                JournalEntry.id,
                JournalEntry.entry_date,
                JournalEntry.source,
                JournalEntry.description,
                JournalEntry.transaction_id,
                FinancialTransaction.transaction_type,
                FinancialTransaction.payment_account_key,
                FinancialTransaction.payment_method_code,
                FinancialTransaction.category_account_key,
                Account.system_key,
                Account.name,
                Account.account_type,
                Account.normal_balance,
                JournalLine.debit_amount,
                JournalLine.credit_amount,
            )
            .join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
            .join(Account, Account.id == JournalLine.account_id)
            .outerjoin(
                FinancialTransaction,
                FinancialTransaction.id == JournalEntry.transaction_id,
            )
            .where(
                JournalEntry.business_id == business_id,
                JournalEntry.id.in_(entry_ids),
            )
            .order_by(JournalEntry.entry_date, JournalEntry.id, JournalLine.id)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            LedgerRow(
                entry_id=row[0],
                entry_date=row[1],
                source=row[2],
                description=row[3],
                transaction_id=row[4],
                transaction_type=row[5],
                payment_account_key=row[6],
                payment_method_code=row[7],
                category_account_key=row[8],
                account_key=row[9] or "UNMAPPED",
                account_name=row[10],
                account_type=row[11],
                normal_balance=row[12],
                debit=row[13],
                credit=row[14],
            )
            for row in rows
        ]

    async def products(self, business_id: UUID) -> list[ProductSnapshot]:
        rows = (
            await self.session.execute(
                select(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.unit,
                    Product.current_stock,
                    Product.minimum_stock,
                    Product.purchase_price,
                    Product.is_active,
                ).where(Product.business_id == business_id, Product.deleted_at.is_(None))
            )
        ).all()
        return [ProductSnapshot(*row) for row in rows]

    async def product_sales(
        self,
        business_id: UUID,
        *,
        date_from: date,
        date_to: date,
        category: str | None,
        payment_method: str | None,
    ) -> list[ProductSaleRow]:
        revenue_transactions = (
            select(JournalEntry.transaction_id)
            .join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
            .join(Account, Account.id == JournalLine.account_id)
            .outerjoin(
                FinancialTransaction,
                FinancialTransaction.id == JournalEntry.transaction_id,
            )
            .where(
                JournalEntry.business_id == business_id,
                JournalEntry.entry_date >= date_from,
                JournalEntry.entry_date <= date_to,
                Account.account_type == "REVENUE",
            )
        )
        if category:
            revenue_transactions = revenue_transactions.where(
                or_(
                    Account.system_key == category,
                    FinancialTransaction.category_account_key == category,
                )
            )
        if payment_method:
            revenue_transactions = revenue_transactions.where(self._payment_filter(payment_method))
        revenue_transactions = revenue_transactions.distinct()
        rows = (
            await self.session.execute(
                select(
                    Product.id,
                    Product.sku,
                    Product.name,
                    Product.unit,
                    TransactionItem.quantity,
                    TransactionItem.line_total,
                    FinancialTransaction.transaction_type,
                )
                .join(Product, Product.id == TransactionItem.product_id)
                .join(
                    FinancialTransaction,
                    FinancialTransaction.id == TransactionItem.transaction_id,
                )
                .where(
                    TransactionItem.business_id == business_id,
                    TransactionItem.transaction_id.in_(revenue_transactions),
                )
            )
        ).all()
        return [ProductSaleRow(*row) for row in rows]

    async def receivables(self, business_id: UUID) -> list[ObligationSnapshot]:
        rows = (
            await self.session.scalars(
                select(Receivable).where(Receivable.business_id == business_id)
            )
        ).all()
        return [self._obligation(row) for row in rows]

    async def payables(self, business_id: UUID) -> list[ObligationSnapshot]:
        rows = (
            await self.session.scalars(select(Payable).where(Payable.business_id == business_id))
        ).all()
        return [self._obligation(row) for row in rows]

    @staticmethod
    def _payment_filter(payment_method: str) -> ColumnElement[bool]:
        account_key = {
            "CASH": "CASH",
            "BANK_TRANSFER": "BANK",
            "QRIS": "DIGITAL_WALLET",
            "E_WALLET": "DIGITAL_WALLET",
            "CARD": "BANK",
        }.get(payment_method, payment_method)
        return or_(
            FinancialTransaction.payment_method_code == payment_method,
            FinancialTransaction.payment_account_key == account_key,
        )

    @staticmethod
    def _obligation(row: Receivable | Payable) -> ObligationSnapshot:
        return ObligationSnapshot(
            initial_amount=row.initial_amount,
            paid_amount=row.paid_amount,
            remaining_amount=row.remaining_amount,
            due_date=row.due_date,
            status=row.status,
            transaction_date=row.transaction_date,
            cancelled_at=row.cancelled_at,
        )
