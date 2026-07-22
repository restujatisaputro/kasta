from __future__ import annotations

import calendar
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.engine import round_money
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.accounting.schemas import TransactionResponse
from kasta_api.modules.accounting.service import JournalService
from kasta_api.modules.accounting.templates import ACCOUNT_TEMPLATE_BY_KEY
from kasta_api.modules.inventory.repository import InventoryRepository
from kasta_api.modules.inventory.service import InventoryService
from kasta_api.modules.receipts.models import ReceiptImage
from kasta_api.modules.receipts.storage import ReceiptStorage
from kasta_api.modules.transactions.constants import (
    EXPENSE_KEYS,
    INCOME_LABELS,
    PAYMENT_LABELS,
    EntryKind,
    RecurrenceFrequency,
)
from kasta_api.modules.transactions.models import (
    RecurringTransaction,
    TransactionDraft,
    TransactionSyncLog,
)
from kasta_api.modules.transactions.repository import TransactionRepository
from kasta_api.modules.transactions.schemas import (
    DraftCreateRequest,
    DraftResponse,
    OptionItem,
    ReceiptImageResponse,
    RecurringResponse,
    SimpleReversalRequest,
    SimpleRevisionRequest,
    SimpleTransactionInput,
    SimpleTransactionResponse,
    SyncOperation,
    SyncOperationResult,
    TransactionListItem,
    TransactionListResponse,
    TransactionOptionsResponse,
    TransactionProductItemResponse,
    TransactionSyncRequest,
    TransactionSyncResponse,
    draft_to_input,
    recurring_to_input,
)


class SimpleTransactionService:
    def __init__(
        self,
        repository: TransactionRepository,
        accounting_repository: AccountingRepository,
        inventory_repository: InventoryRepository,
    ) -> None:
        self.repository = repository
        self.journal = JournalService(accounting_repository)
        self.inventory = InventoryService(inventory_repository)

    async def create_transaction(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: SimpleTransactionInput,
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> SimpleTransactionResponse:
        effective_idempotency_key = idempotency_key or payload.idempotency_key
        existing = await self.journal.repository.get_by_idempotency_key(
            business_id, effective_idempotency_key
        )
        if existing is not None:
            existing_rule = (
                await self.repository.get_recurring(business_id, existing.recurring_rule_id)
                if existing.recurring_rule_id is not None
                else None
            )
            return SimpleTransactionResponse(
                transaction=TransactionResponse.from_model(existing),
                recurring=(
                    RecurringResponse.model_validate(existing_rule)
                    if existing_rule is not None
                    else None
                ),
            )
        rule = self._new_recurring_rule(business_id, actor_user_id, payload)
        if rule is not None:
            self.repository.add(rule)
        try:
            transaction = await self.journal.post_transaction(
                business_id,
                actor_user_id,
                payload.to_command(
                    idempotency_key=effective_idempotency_key,
                    recurring_rule_id=rule.id if rule is not None else None,
                ),
                request_id=request_id,
                auto_commit=False,
            )
            await self.inventory.apply_transaction_lines(
                business_id,
                transaction.id,
                actor_user_id,
                payload.entry_kind.value,
                payload.items,
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return SimpleTransactionResponse(
            transaction=TransactionResponse.from_model(transaction),
            recurring=(RecurringResponse.model_validate(rule) if rule is not None else None),
        )

    async def create_draft(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: DraftCreateRequest,
    ) -> TransactionDraft:
        existing = await self.repository.get_draft_by_reference(
            business_id, payload.client_reference
        )
        if existing is not None:
            return existing
        draft = TransactionDraft(
            id=uuid4(),
            business_id=business_id,
            client_reference=payload.client_reference,
            entry_kind=payload.entry_kind.value,
            transaction_date=payload.transaction_date,
            amount=round_money(payload.amount),
            category_account_key=(
                payload.category_account.value if payload.category_account is not None else None
            ),
            counterparty_name=payload.counterparty_name or None,
            payment_method_code=payload.payment_method.value,
            note=payload.note or self._fallback_note(payload.entry_kind),
            recurrence_frequency=(
                payload.recurrence_frequency.value
                if payload.recurrence_frequency is not None
                else None
            ),
            recurrence_interval=payload.recurrence_interval,
            items_data=[item.model_dump(mode="json") for item in payload.items] or None,
            status="ACTIVE",
            created_by_user_id=actor_user_id,
        )
        self.repository.add(draft)
        await self.repository.commit()
        return draft

    async def update_draft(
        self,
        business_id: UUID,
        draft_id: UUID,
        payload: DraftCreateRequest,
    ) -> TransactionDraft:
        draft = await self._required_draft(business_id, draft_id)
        if draft.status != "ACTIVE":
            raise HTTPException(status_code=409, detail="Draft ini sudah diposting.")
        draft.entry_kind = payload.entry_kind.value
        draft.transaction_date = payload.transaction_date
        draft.amount = round_money(payload.amount)
        draft.category_account_key = (
            payload.category_account.value if payload.category_account is not None else None
        )
        draft.counterparty_name = payload.counterparty_name or None
        draft.payment_method_code = payload.payment_method.value
        draft.note = payload.note or self._fallback_note(payload.entry_kind)
        draft.recurrence_frequency = (
            payload.recurrence_frequency.value if payload.recurrence_frequency is not None else None
        )
        draft.recurrence_interval = payload.recurrence_interval
        draft.items_data = [item.model_dump(mode="json") for item in payload.items] or None
        await self.repository.commit()
        await self.repository.refresh(draft)
        return draft

    async def delete_draft(self, business_id: UUID, draft_id: UUID) -> None:
        draft = await self._required_draft(business_id, draft_id)
        if draft.status != "ACTIVE":
            raise HTTPException(status_code=409, detail="Draft yang sudah diposting tidak dihapus.")
        draft.deleted_at = datetime.now(UTC)
        await self.repository.commit()

    async def post_draft(
        self,
        business_id: UUID,
        draft_id: UUID,
        actor_user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> SimpleTransactionResponse:
        draft = await self._required_draft(business_id, draft_id)
        if draft.status == "POSTED":
            if draft.posted_transaction_id is None:
                raise HTTPException(status_code=409, detail="Draft sudah diproses.")
            transaction = await self.journal.get_transaction(
                business_id, draft.posted_transaction_id
            )
            return SimpleTransactionResponse(
                transaction=TransactionResponse.from_model(transaction)
            )
        payload = draft_to_input(draft)
        transaction_id = uuid4()
        rule = self._new_recurring_rule(business_id, actor_user_id, payload)
        if rule is not None:
            self.repository.add(rule)
        draft.status = "POSTED"
        draft.posted_transaction_id = transaction_id
        try:
            transaction = await self.journal.post_transaction(
                business_id,
                actor_user_id,
                payload.to_command(
                    idempotency_key=draft.client_reference or f"draft:{draft.id}",
                    recurring_rule_id=rule.id if rule is not None else None,
                    transaction_id=transaction_id,
                ),
                request_id=request_id,
                auto_commit=False,
            )
            await self.inventory.apply_transaction_lines(
                business_id,
                transaction.id,
                actor_user_id,
                payload.entry_kind.value,
                payload.items,
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return SimpleTransactionResponse(
            transaction=TransactionResponse.from_model(transaction),
            recurring=(RecurringResponse.model_validate(rule) if rule is not None else None),
        )

    async def list_drafts(self, business_id: UUID) -> list[DraftResponse]:
        return [
            DraftResponse.model_validate(draft)
            for draft in await self.repository.list_drafts(business_id)
        ]

    async def list_transactions(
        self,
        business_id: UUID,
        *,
        query: str | None = None,
        entry_kind: str | None = None,
        transaction_status: str | None = None,
        payment_method: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        updated_after: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TransactionListResponse:
        rows, total = await self.repository.list_transactions(
            business_id,
            query=query,
            entry_kind=entry_kind,
            transaction_status=transaction_status,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
            updated_after=updated_after,
            limit=limit,
            offset=offset,
        )
        return TransactionListResponse(
            items=[
                TransactionListItem(
                    **TransactionResponse.from_model(transaction).model_dump(),
                    receipt_count=receipt_count,
                    items=[
                        TransactionProductItemResponse.model_validate(item)
                        for item in await self.inventory.repository.transaction_items(
                            business_id, transaction.id
                        )
                    ],
                )
                for transaction, receipt_count in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def options(self, business_id: UUID) -> TransactionOptionsResponse:
        recent = await self.repository.recent_category_keys(business_id)
        expense_keys = [AccountKey(value) for value in recent if value in EXPENSE_KEYS]
        expense_keys.extend(key for key in EXPENSE_KEYS if key not in expense_keys)
        return TransactionOptionsResponse(
            income_sources=[
                OptionItem(value=key.value, label=label) for key, label in INCOME_LABELS.items()
            ],
            expense_categories=[
                OptionItem(value=key.value, label=ACCOUNT_TEMPLATE_BY_KEY[key].name)
                for key in expense_keys
            ],
            payment_methods=[
                OptionItem(value=key.value, label=label) for key, label in PAYMENT_LABELS.items()
            ],
        )

    async def revise(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        payload: SimpleRevisionRequest,
        *,
        request_id: str | None = None,
    ) -> SimpleTransactionResponse:
        try:
            original, replacement = await self.journal.revise_transaction(
                business_id,
                transaction_id,
                actor_user_id,
                payload.replacement.to_command(),
                reason=payload.reason,
                request_id=request_id,
                auto_commit=False,
            )
            if original.reversed_by_transaction_id is None:
                raise RuntimeError("Transaksi pembatalan revisi tidak terbentuk")
            await self.inventory.reverse_transaction_lines(
                business_id,
                original.id,
                original.reversed_by_transaction_id,
                actor_user_id,
                reason=payload.reason,
            )
            await self.inventory.apply_transaction_lines(
                business_id,
                replacement.id,
                actor_user_id,
                payload.replacement.entry_kind.value,
                payload.replacement.items,
                revision=True,
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return SimpleTransactionResponse(transaction=TransactionResponse.from_model(replacement))

    async def reverse(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        payload: SimpleReversalRequest,
        *,
        request_id: str | None = None,
    ) -> TransactionResponse:
        try:
            reversal = await self.journal.reverse_transaction(
                business_id,
                transaction_id,
                actor_user_id,
                reason=payload.reason,
                transaction_date=payload.transaction_date,
                request_id=request_id,
                auto_commit=False,
            )
            await self.inventory.reverse_transaction_lines(
                business_id,
                transaction_id,
                reversal.id,
                actor_user_id,
                reason=payload.reason,
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return TransactionResponse.from_model(reversal)

    async def list_recurring(self, business_id: UUID) -> list[RecurringResponse]:
        return [
            RecurringResponse.model_validate(rule)
            for rule in await self.repository.list_recurring(business_id)
        ]

    async def set_recurring_status(
        self, business_id: UUID, recurring_id: UUID, next_status: str
    ) -> RecurringResponse:
        rule = await self.repository.get_recurring(business_id, recurring_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan.")
        rule.status = next_status
        await self.repository.commit()
        return RecurringResponse.model_validate(rule)

    async def run_due_recurring(
        self, business_id: UUID, actor_user_id: UUID, through_date: date
    ) -> list[TransactionResponse]:
        results: list[TransactionResponse] = []
        rules = await self.repository.due_recurring(business_id, through_date)
        for rule in rules:
            run_date = rule.next_run_date
            while run_date <= through_date:
                payload = recurring_to_input(rule, run_date)
                rule.next_run_date = self._advance_date(
                    run_date,
                    RecurrenceFrequency(rule.frequency),
                    rule.recurrence_interval,
                )
                rule.last_run_at = datetime.now(UTC)
                try:
                    transaction = await self.journal.post_transaction(
                        business_id,
                        actor_user_id,
                        payload.to_command(
                            idempotency_key=f"recurring:{rule.id}:{run_date.isoformat()}",
                            recurring_rule_id=rule.id,
                        ),
                        auto_commit=False,
                    )
                    await self.inventory.apply_transaction_lines(
                        business_id,
                        transaction.id,
                        actor_user_id,
                        payload.entry_kind.value,
                        payload.items,
                    )
                    await self.repository.commit()
                except Exception:
                    await self.repository.rollback()
                    raise
                results.append(TransactionResponse.from_model(transaction))
                run_date = rule.next_run_date
        return results

    async def add_receipt(
        self,
        business_id: UUID,
        transaction_id: UUID,
        actor_user_id: UUID,
        upload: UploadFile,
        storage: ReceiptStorage,
    ) -> ReceiptImageResponse:
        await self.journal.get_transaction(business_id, transaction_id)
        object_key, content_type, size_bytes = await storage.upload(
            business_id, transaction_id, upload
        )
        receipt = ReceiptImage(
            id=uuid4(),
            business_id=business_id,
            transaction_id=transaction_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_by_user_id=actor_user_id,
        )
        self.repository.add(receipt)
        await self.repository.commit()
        return ReceiptImageResponse.model_validate(receipt)

    async def receipt_data(
        self, business_id: UUID, receipt_id: UUID, storage: ReceiptStorage
    ) -> tuple[bytes, str]:
        receipt = await self.repository.get_receipt(business_id, receipt_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Foto bukti tidak ditemukan.")
        return await storage.download(receipt.object_key)

    async def receipt_url(
        self, business_id: UUID, receipt_id: UUID, storage: ReceiptStorage
    ) -> tuple[str, int]:
        receipt = await self.repository.get_receipt(business_id, receipt_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Foto bukti tidak ditemukan.")
        return await storage.presigned_download(receipt.object_key)

    async def sync(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        device_session_id: UUID,
        payload: TransactionSyncRequest,
        *,
        request_id: str | None = None,
    ) -> TransactionSyncResponse:
        results: list[SyncOperationResult] = []
        for operation in payload.operations:
            existing = await self.repository.get_sync_log(
                business_id, device_session_id, operation.client_operation_id
            )
            if existing is not None:
                results.append(
                    SyncOperationResult(
                        client_operation_id=operation.client_operation_id,
                        status=existing.status,
                        server_transaction_id=existing.server_transaction_id,
                        message=existing.error_message,
                    )
                )
                continue
            result = await self._apply_sync_operation(
                business_id,
                actor_user_id,
                operation,
                request_id=request_id,
            )
            self.repository.add(
                TransactionSyncLog(
                    id=uuid4(),
                    business_id=business_id,
                    device_session_id=device_session_id,
                    client_operation_id=operation.client_operation_id,
                    operation_type=operation.operation,
                    server_transaction_id=result.server_transaction_id,
                    status=result.status,
                    error_message=result.message,
                    created_at=datetime.now(UTC),
                )
            )
            await self.repository.commit()
            results.append(result)
        changes = await self.list_transactions(
            business_id,
            updated_after=payload.pull_updated_after,
            limit=100,
        )
        return TransactionSyncResponse(
            results=results,
            changes=changes.items,
            server_time=datetime.now(UTC),
        )

    async def _apply_sync_operation(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        operation: SyncOperation,
        *,
        request_id: str | None,
    ) -> SyncOperationResult:
        try:
            if operation.operation == "CREATE" and operation.payload is not None:
                created = await self.create_transaction(
                    business_id,
                    actor_user_id,
                    operation.payload,
                    request_id=request_id,
                    idempotency_key=operation.client_operation_id,
                )
                return SyncOperationResult(
                    client_operation_id=operation.client_operation_id,
                    status="APPLIED",
                    server_transaction_id=created.transaction.id,
                )
            if operation.operation == "SAVE_DRAFT" and operation.payload is not None:
                request = DraftCreateRequest(
                    **operation.payload.model_dump(),
                    client_reference=operation.client_operation_id,
                )
                draft = await self.create_draft(business_id, actor_user_id, request)
                return SyncOperationResult(
                    client_operation_id=operation.client_operation_id,
                    status="APPLIED",
                    draft_id=draft.id,
                )
            if (
                operation.operation == "REVISE"
                and operation.payload is not None
                and operation.transaction_id is not None
            ):
                revised = await self.revise(
                    business_id,
                    operation.transaction_id,
                    actor_user_id,
                    SimpleRevisionRequest(
                        reason=operation.reason or "Perubahan dari perangkat",
                        replacement=operation.payload,
                    ),
                    request_id=request_id,
                )
                return SyncOperationResult(
                    client_operation_id=operation.client_operation_id,
                    status="APPLIED",
                    server_transaction_id=revised.transaction.id,
                )
            if operation.operation == "REVERSE" and operation.transaction_id is not None:
                reversed_transaction = await self.reverse(
                    business_id,
                    operation.transaction_id,
                    actor_user_id,
                    SimpleReversalRequest(reason=operation.reason or "Pembatalan dari perangkat"),
                    request_id=request_id,
                )
                return SyncOperationResult(
                    client_operation_id=operation.client_operation_id,
                    status="APPLIED",
                    server_transaction_id=reversed_transaction.id,
                )
        except HTTPException as exc:
            await self.repository.rollback()
            return SyncOperationResult(
                client_operation_id=operation.client_operation_id,
                status="REJECTED",
                message=str(exc.detail),
            )
        raise RuntimeError("Operasi sinkronisasi tidak didukung")

    async def _required_draft(self, business_id: UUID, draft_id: UUID) -> TransactionDraft:
        draft = await self.repository.get_draft(business_id, draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft tidak ditemukan.")
        return draft

    @staticmethod
    def _fallback_note(entry_kind: EntryKind) -> str:
        return {
            EntryKind.INCOME: "Uang masuk",
            EntryKind.EXPENSE: "Uang keluar",
            EntryKind.CAPITAL: "Tambah modal",
            EntryKind.OWNER_DRAW: "Ambil uang pribadi",
        }[entry_kind]

    @staticmethod
    def _new_recurring_rule(
        business_id: UUID,
        actor_user_id: UUID,
        payload: SimpleTransactionInput,
    ) -> RecurringTransaction | None:
        if payload.recurrence_frequency is None or payload.recurrence_interval is None:
            return None
        return RecurringTransaction(
            id=uuid4(),
            business_id=business_id,
            entry_kind=payload.entry_kind.value,
            amount=round_money(payload.amount),
            category_account_key=(
                payload.category_account.value if payload.category_account is not None else None
            ),
            counterparty_name=payload.counterparty_name or None,
            payment_method_code=payload.payment_method.value,
            note=payload.note or SimpleTransactionService._fallback_note(payload.entry_kind),
            frequency=payload.recurrence_frequency.value,
            recurrence_interval=payload.recurrence_interval,
            items_data=[item.model_dump(mode="json") for item in payload.items] or None,
            next_run_date=SimpleTransactionService._advance_date(
                payload.transaction_date,
                payload.recurrence_frequency,
                payload.recurrence_interval,
            ),
            status="ACTIVE",
            created_by_user_id=actor_user_id,
        )

    @staticmethod
    def _advance_date(current: date, frequency: RecurrenceFrequency, interval: int) -> date:
        if frequency == RecurrenceFrequency.WEEKLY:
            return date.fromordinal(current.toordinal() + (7 * interval))
        month_index = (current.year * 12 + current.month - 1) + interval
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
