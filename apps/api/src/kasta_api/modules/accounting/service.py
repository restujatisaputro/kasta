from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.engine import (
    AccountingValidationError,
    JournalDraft,
    JournalEngine,
    JournalLineDraft,
    JournalValidator,
    TransactionCommand,
)
from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
    TransactionRevision,
)
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.security import utc_now


class JournalService:
    def __init__(self, repository: AccountingRepository) -> None:
        self.repository = repository
        self.engine = JournalEngine()

    async def post_transaction(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        command: TransactionCommand,
        *,
        request_id: str | None = None,
        auto_commit: bool = True,
    ) -> FinancialTransaction:
        existing = await self.repository.get_by_idempotency_key(
            business_id, command.idempotency_key
        )
        if existing is not None:
            return existing
        try:
            transaction = await self._create_posted_transaction(
                business_id,
                actor_user_id,
                command,
                request_id=request_id,
            )
            if auto_commit:
                await self.repository.commit()
            return transaction
        except AccountingValidationError as exc:
            await self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        except Exception:
            await self.repository.rollback()
            raise

    async def reverse_transaction(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        *,
        reason: str,
        transaction_date: date,
        request_id: str | None = None,
        auto_commit: bool = True,
    ) -> FinancialTransaction:
        try:
            original = await self._required_transaction(
                business_id, transaction_id, for_update=True
            )
            reversal = await self._create_reversal(
                original,
                actor_user_id,
                reason=reason,
                transaction_date=transaction_date,
                request_id=request_id,
                event_type="REVERSED",
            )
            if auto_commit:
                await self.repository.commit()
            return reversal
        except Exception:
            await self.repository.rollback()
            raise

    async def revise_transaction(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        replacement: TransactionCommand,
        *,
        reason: str,
        request_id: str | None = None,
        auto_commit: bool = True,
    ) -> tuple[FinancialTransaction, FinancialTransaction]:
        try:
            original = await self._required_transaction(
                business_id, transaction_id, for_update=True
            )
            await self._create_reversal(
                original,
                actor_user_id,
                reason=reason,
                transaction_date=replacement.transaction_date,
                request_id=request_id,
                event_type="REVISED",
            )
            root_id = original.root_transaction_id or original.id
            revised = await self._create_posted_transaction(
                business_id,
                actor_user_id,
                replacement,
                request_id=request_id,
                revision_number=original.revision_number + 1,
                root_transaction_id=root_id,
                supersedes_transaction_id=original.id,
                audit_action="TRANSACTION_REVISION_POSTED",
            )
            if auto_commit:
                await self.repository.commit()
            return original, revised
        except AccountingValidationError as exc:
            await self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        except Exception:
            await self.repository.rollback()
            raise

    async def get_transaction(
        self, business_id: UUID, transaction_id: UUID
    ) -> FinancialTransaction:
        return await self._required_transaction(business_id, transaction_id)

    async def get_history(
        self, business_id: UUID, transaction_id: UUID
    ) -> list[TransactionRevision]:
        transaction = await self._required_transaction(business_id, transaction_id)
        chain = await self.repository.get_revision_chain(business_id, transaction)
        return await self.repository.get_revisions(business_id, (item.id for item in chain))

    async def list_accounts(self, business_id: UUID) -> list[Account]:
        try:
            await self.repository.ensure_account_templates(business_id)
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return await self.repository.list_accounts(business_id)

    async def _create_posted_transaction(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        command: TransactionCommand,
        *,
        request_id: str | None,
        revision_number: int = 1,
        root_transaction_id: UUID | None = None,
        supersedes_transaction_id: UUID | None = None,
        audit_action: str = "TRANSACTION_POSTED",
    ) -> FinancialTransaction:
        draft = self.engine.create_draft(command)
        accounts = await self.repository.ensure_account_templates(business_id)
        self._validate_accounts(draft, accounts, business_id)
        now = utc_now()
        transaction = FinancialTransaction(
            id=command.transaction_id or uuid4(),
            business_id=business_id,
            transaction_number=self._number("TRX", command.transaction_date),
            transaction_type=command.transaction_type.value,
            transaction_date=command.transaction_date,
            amount=draft.total_debit,
            description=command.description,
            payment_account_key=(
                command.payment_account.value if command.payment_account is not None else None
            ),
            category_account_key=(
                command.category_account.value if command.category_account is not None else None
            ),
            entry_kind=command.entry_kind,
            counterparty_name=command.counterparty_name,
            payment_method_code=command.payment_method_code,
            recurring_rule_id=(
                UUID(command.recurring_rule_id) if command.recurring_rule_id is not None else None
            ),
            status="POSTED",
            idempotency_key=command.idempotency_key,
            root_transaction_id=root_transaction_id,
            supersedes_transaction_id=supersedes_transaction_id,
            revision_number=revision_number,
            posted_at=now,
            posted_by_user_id=actor_user_id,
        )
        entry = JournalEntry(
            id=uuid4(),
            business_id=business_id,
            transaction_id=transaction.id,
            entry_number=self._number("JRN", command.transaction_date),
            entry_date=command.transaction_date,
            description=command.description,
            source=command.transaction_type.value,
            status="POSTED",
            total_debit=draft.total_debit,
            total_credit=draft.total_credit,
            posted_at=now,
            posted_by_user_id=actor_user_id,
        )
        lines = [
            JournalLine(
                id=uuid4(),
                business_id=business_id,
                journal_entry_id=entry.id,
                account_id=accounts[line.account_key].id,
                description=command.description,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
            )
            for line in draft.lines
        ]
        snapshot = self._snapshot(transaction)
        self.repository.add_all(
            [
                transaction,
                entry,
                *lines,
                TransactionRevision(
                    id=uuid4(),
                    business_id=business_id,
                    transaction_id=transaction.id,
                    revision_number=revision_number,
                    event_sequence=1,
                    event_type="POSTED",
                    snapshot=snapshot,
                    actor_user_id=actor_user_id,
                    created_at=now,
                ),
                self._audit(
                    business_id,
                    actor_user_id,
                    audit_action,
                    transaction.id,
                    after=snapshot,
                    request_id=request_id,
                    created_at=now,
                ),
            ]
        )
        await self.repository.flush()
        return transaction

    async def _create_reversal(
        self,
        original: FinancialTransaction,
        actor_user_id: UUID,
        *,
        reason: str,
        transaction_date: date,
        request_id: str | None,
        event_type: str,
    ) -> FinancialTransaction:
        if original.transaction_type == "REVERSAL":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Catatan pembatalan tidak dapat dibatalkan kembali.",
            )
        if original.status == "REVERSED" or original.reversed_by_transaction_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaksi ini sudah dibatalkan.",
            )
        entry = await self.repository.get_journal_entry(original.id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Catatan pasangan transaksi tidak ditemukan.",
            )
        source_lines = await self.repository.get_journal_lines(entry.id)
        if entry.total_debit != entry.total_credit or len(source_lines) < 2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Catatan lama tidak seimbang dan tidak dapat dibatalkan otomatis.",
            )
        now = utc_now()
        before = self._snapshot(original)
        reversal = FinancialTransaction(
            id=uuid4(),
            business_id=original.business_id,
            transaction_number=self._number("REV", transaction_date),
            transaction_type="REVERSAL",
            transaction_date=transaction_date,
            amount=original.amount,
            description=f"Pembatalan: {original.description}"[:255],
            status="POSTED",
            root_transaction_id=original.root_transaction_id or original.id,
            reverses_transaction_id=original.id,
            revision_number=original.revision_number,
            posted_at=now,
            posted_by_user_id=actor_user_id,
        )
        reversal_entry = JournalEntry(
            id=uuid4(),
            business_id=original.business_id,
            transaction_id=reversal.id,
            reversal_of_entry_id=entry.id,
            entry_number=self._number("JRN-REV", transaction_date),
            entry_date=transaction_date,
            description=reversal.description,
            source="REVERSAL",
            status="POSTED",
            total_debit=entry.total_credit,
            total_credit=entry.total_debit,
            posted_at=now,
            posted_by_user_id=actor_user_id,
        )
        reversal_lines = [
            JournalLine(
                id=uuid4(),
                business_id=original.business_id,
                journal_entry_id=reversal_entry.id,
                account_id=line.account_id,
                description=reversal.description,
                debit_amount=line.credit_amount,
                credit_amount=line.debit_amount,
            )
            for line in source_lines
        ]
        JournalValidator.validate(
            JournalDraft(
                lines=tuple(
                    self._line_draft(line.debit_amount, line.credit_amount)
                    for line in reversal_lines
                ),
                total_debit=reversal_entry.total_debit,
                total_credit=reversal_entry.total_credit,
            )
        )
        original.status = "REVERSED"
        original.reversed_by_transaction_id = reversal.id
        entry.status = "REVERSED"
        entry.reversed_by_entry_id = reversal_entry.id
        after = self._snapshot(original)
        reversal_snapshot = self._snapshot(reversal)
        self.repository.add_all(
            [
                reversal,
                reversal_entry,
                *reversal_lines,
                TransactionRevision(
                    id=uuid4(),
                    business_id=original.business_id,
                    transaction_id=original.id,
                    related_transaction_id=reversal.id,
                    revision_number=original.revision_number,
                    event_sequence=2,
                    event_type=event_type,
                    snapshot=after,
                    reason=reason,
                    actor_user_id=actor_user_id,
                    created_at=now,
                ),
                TransactionRevision(
                    id=uuid4(),
                    business_id=original.business_id,
                    transaction_id=reversal.id,
                    related_transaction_id=original.id,
                    revision_number=reversal.revision_number,
                    event_sequence=1,
                    event_type="POSTED",
                    snapshot=reversal_snapshot,
                    reason=reason,
                    actor_user_id=actor_user_id,
                    created_at=now,
                ),
                self._audit(
                    original.business_id,
                    actor_user_id,
                    f"TRANSACTION_{event_type}",
                    original.id,
                    before=before,
                    after=after,
                    reason=reason,
                    request_id=request_id,
                    created_at=now,
                ),
                self._audit(
                    original.business_id,
                    actor_user_id,
                    "REVERSAL_POSTED",
                    reversal.id,
                    after=reversal_snapshot,
                    reason=reason,
                    request_id=request_id,
                    created_at=now,
                ),
            ]
        )
        await self.repository.flush()
        return reversal

    async def _required_transaction(
        self, business_id: UUID, transaction_id: UUID, *, for_update: bool = False
    ) -> FinancialTransaction:
        transaction = await self.repository.get_transaction(
            business_id, transaction_id, for_update=for_update
        )
        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transaksi tidak ditemukan."
            )
        return transaction

    @staticmethod
    def _validate_accounts(
        draft: JournalDraft, accounts: dict[AccountKey, Account], business_id: UUID
    ) -> None:
        for line in draft.lines:
            account = accounts.get(line.account_key)
            if (
                account is None
                or account.business_id != business_id
                or not account.is_active
                or account.deleted_at is not None
            ):
                raise AccountingValidationError("Akun sistem untuk transaksi tidak tersedia.")

    @staticmethod
    def _line_draft(debit: Decimal, credit: Decimal) -> JournalLineDraft:
        return JournalLineDraft(
            account_key=AccountKey.CASH,
            debit_amount=debit,
            credit_amount=credit,
        )

    @staticmethod
    def _number(prefix: str, transaction_date: date) -> str:
        return f"{prefix}-{transaction_date:%Y%m%d}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _snapshot(transaction: FinancialTransaction) -> dict[str, object]:
        return {
            "id": str(transaction.id),
            "business_id": str(transaction.business_id),
            "transaction_number": transaction.transaction_number,
            "transaction_type": transaction.transaction_type,
            "transaction_date": transaction.transaction_date.isoformat(),
            "amount": str(transaction.amount),
            "description": transaction.description,
            "payment_account_key": transaction.payment_account_key,
            "category_account_key": transaction.category_account_key,
            "entry_kind": transaction.entry_kind,
            "counterparty_name": transaction.counterparty_name,
            "payment_method_code": transaction.payment_method_code,
            "recurring_rule_id": (
                str(transaction.recurring_rule_id)
                if transaction.recurring_rule_id is not None
                else None
            ),
            "status": transaction.status,
            "revision_number": transaction.revision_number,
            "root_transaction_id": (
                str(transaction.root_transaction_id)
                if transaction.root_transaction_id is not None
                else None
            ),
            "supersedes_transaction_id": (
                str(transaction.supersedes_transaction_id)
                if transaction.supersedes_transaction_id is not None
                else None
            ),
            "reverses_transaction_id": (
                str(transaction.reverses_transaction_id)
                if transaction.reverses_transaction_id is not None
                else None
            ),
            "reversed_by_transaction_id": (
                str(transaction.reversed_by_transaction_id)
                if transaction.reversed_by_transaction_id is not None
                else None
            ),
        }

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
        created_at: datetime,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type="FINANCIAL_TRANSACTION",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=created_at,
        )
