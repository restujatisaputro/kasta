from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
    TransactionRevision,
)
from kasta_api.modules.accounting.templates import ACCOUNT_TEMPLATES


class AccountingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_account_templates(self, business_id: UUID) -> dict[AccountKey, Account]:
        accounts = list(
            (
                await self.session.scalars(
                    select(Account).where(
                        Account.business_id == business_id,
                        Account.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        by_key = {account.system_key: account for account in accounts if account.system_key}
        by_code = {account.code: account for account in accounts}
        for template in ACCOUNT_TEMPLATES:
            account = by_key.get(template.key.value) or by_code.get(template.code)
            if account is None:
                account = Account(
                    business_id=business_id,
                    code=template.code,
                    name=template.name,
                    system_key=template.key.value,
                    account_type=template.account_type.value,
                    normal_balance=template.normal_balance.value,
                    is_system=True,
                    is_active=True,
                )
                self.session.add(account)
                accounts.append(account)
            else:
                account.name = template.name
                account.system_key = template.key.value
                account.account_type = template.account_type.value
                account.normal_balance = template.normal_balance.value
                account.is_system = True
            by_key[template.key.value] = account
        await self.session.flush()
        return {template.key: by_key[template.key.value] for template in ACCOUNT_TEMPLATES}

    async def list_accounts(self, business_id: UUID) -> list[Account]:
        result = await self.session.scalars(
            select(Account)
            .where(
                Account.business_id == business_id,
                Account.deleted_at.is_(None),
            )
            .order_by(Account.code)
        )
        return list(result.all())

    async def get_by_idempotency_key(
        self, business_id: UUID, idempotency_key: str | None
    ) -> FinancialTransaction | None:
        if idempotency_key is None:
            return None
        return (
            await self.session.scalars(
                select(FinancialTransaction).where(
                    FinancialTransaction.business_id == business_id,
                    FinancialTransaction.idempotency_key == idempotency_key,
                )
            )
        ).one_or_none()

    async def get_transaction(
        self, business_id: UUID, transaction_id: UUID, *, for_update: bool = False
    ) -> FinancialTransaction | None:
        statement = select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.business_id == business_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def get_journal_entry(self, transaction_id: UUID) -> JournalEntry | None:
        return (
            await self.session.scalars(
                select(JournalEntry).where(JournalEntry.transaction_id == transaction_id)
            )
        ).one_or_none()

    async def get_journal_lines(self, entry_id: UUID) -> list[JournalLine]:
        result = await self.session.scalars(
            select(JournalLine)
            .where(JournalLine.journal_entry_id == entry_id)
            .order_by(JournalLine.created_at, JournalLine.id)
        )
        return list(result.all())

    async def get_revisions(
        self, business_id: UUID, transaction_ids: Iterable[UUID]
    ) -> list[TransactionRevision]:
        ids = tuple(transaction_ids)
        if not ids:
            return []
        result = await self.session.scalars(
            select(TransactionRevision)
            .where(
                TransactionRevision.business_id == business_id,
                TransactionRevision.transaction_id.in_(ids),
            )
            .order_by(TransactionRevision.created_at, TransactionRevision.event_sequence)
        )
        return list(result.all())

    async def get_revision_chain(
        self, business_id: UUID, transaction: FinancialTransaction
    ) -> list[FinancialTransaction]:
        root_id = transaction.root_transaction_id or transaction.id
        result = await self.session.scalars(
            select(FinancialTransaction)
            .where(
                FinancialTransaction.business_id == business_id,
                (
                    (FinancialTransaction.id == root_id)
                    | (FinancialTransaction.root_transaction_id == root_id)
                ),
            )
            .order_by(FinancialTransaction.revision_number, FinancialTransaction.posted_at)
        )
        return list(result.all())

    def add_all(self, instances: Iterable[object]) -> None:
        self.session.add_all(list(instances))

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
