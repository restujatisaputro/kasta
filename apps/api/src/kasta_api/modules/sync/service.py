from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException

from kasta_api.db.rls import set_rls_context
from kasta_api.modules.accounting.schemas import TransactionResponse
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.dependencies import CurrentPrincipal
from kasta_api.modules.sync.models import (
    DeviceSyncState,
    SyncChange,
    SyncConflictRevision,
    SyncOperationLog,
    SyncRecord,
)
from kasta_api.modules.sync.repository import SyncRepository
from kasta_api.modules.sync.schemas import (
    PullChange,
    PushOperation,
    PushResult,
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStatusResponse,
)
from kasta_api.modules.transactions.schemas import (
    SimpleReversalRequest,
    SimpleRevisionRequest,
    SimpleTransactionInput,
)
from kasta_api.modules.transactions.service import SimpleTransactionService

FINANCIAL_ENTITY = "TRANSACTION"
NON_FINANCIAL_ENTITIES = {"PREFERENCE", "DRAFT"}


class OfflineSyncService:
    def __init__(
        self,
        repository: SyncRepository,
        transactions: SimpleTransactionService,
    ) -> None:
        self.repository = repository
        self.transactions = transactions

    async def push(
        self,
        principal: CurrentPrincipal,
        request: SyncPushRequest,
        *,
        request_id: str | None = None,
    ) -> SyncPushResponse:
        self._assert_tenant(principal, request.business_id)
        results: list[PushResult] = []
        for operation in request.operations:
            await self._set_tenant_context(principal)
            previous = await self.repository.operation(
                request.business_id, request.device_id, operation.operation_id
            )
            if previous is not None:
                results.append(PushResult.model_validate(previous.response_data))
                continue
            try:
                result = await self._apply(
                    principal,
                    request.device_id,
                    operation,
                    request_id=request_id,
                )
            except (HTTPException, ValueError) as exc:
                await self.repository.rollback()
                message = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
                result = PushResult(
                    operation_id=operation.operation_id,
                    local_id=operation.local_id,
                    status="FAILED",
                    server_id=operation.server_id,
                    message=message,
                )
            now = datetime.now(UTC)
            self.repository.add(
                SyncOperationLog(
                    id=uuid4(),
                    business_id=request.business_id,
                    device_session_id=principal.session_id,
                    device_id=request.device_id,
                    batch_id=request.batch_id,
                    operation_id=operation.operation_id,
                    response_data=result.model_dump(mode="json"),
                    created_at=now,
                )
            )
            state = await self._device_state(principal, request.device_id)
            state.last_push_at = now
            state.last_error = result.message if result.status == "FAILED" else None
            await self.repository.commit()
            results.append(result)
        return SyncPushResponse(
            batch_id=request.batch_id,
            results=results,
            server_time=datetime.now(UTC),
        )

    async def pull(self, principal: CurrentPrincipal, request: SyncPullRequest) -> SyncPullResponse:
        self._assert_tenant(principal, request.business_id)
        rows = await self.repository.changes(request.business_id, request.cursor, request.limit)
        has_more = len(rows) > request.limit
        selected = rows[: request.limit]
        next_cursor = selected[-1].sequence if selected else request.cursor
        state = await self._device_state(principal, request.device_id)
        state.last_pull_at = datetime.now(UTC)
        state.last_cursor = next_cursor
        await self.repository.commit()
        return SyncPullResponse(
            changes=[
                PullChange(
                    cursor=row.sequence,
                    entity_type=row.entity_type,
                    server_id=row.entity_id,
                    version=row.version,
                    action=row.action,
                    payload=row.payload,
                    changed_at=row.changed_at,
                )
                for row in selected
            ],
            next_cursor=next_cursor,
            has_more=has_more,
            server_time=datetime.now(UTC),
        )

    async def status(
        self, principal: CurrentPrincipal, business_id: UUID, device_id: str
    ) -> SyncStatusResponse:
        self._assert_tenant(principal, business_id)
        state = await self.repository.device_state(business_id, device_id)
        return SyncStatusResponse(
            business_id=business_id,
            device_id=device_id,
            last_push_at=state.last_push_at if state else None,
            last_pull_at=state.last_pull_at if state else None,
            last_cursor=state.last_cursor if state else 0,
            open_conflicts=await self.repository.open_conflict_count(business_id, device_id),
            server_time=datetime.now(UTC),
        )

    async def _apply(
        self,
        principal: CurrentPrincipal,
        device_id: str,
        operation: PushOperation,
        *,
        request_id: str | None,
    ) -> PushResult:
        if operation.entity_type == FINANCIAL_ENTITY:
            return await self._apply_financial(
                principal, device_id, operation, request_id=request_id
            )
        if operation.entity_type in NON_FINANCIAL_ENTITIES:
            return await self._apply_non_financial(principal, operation)
        raise ValueError(f"Jenis data {operation.entity_type} tidak didukung.")

    async def _apply_financial(
        self,
        principal: CurrentPrincipal,
        device_id: str,
        operation: PushOperation,
        *,
        request_id: str | None,
    ) -> PushResult:
        now = datetime.now(UTC)
        if operation.action == "CREATE":
            payload = SimpleTransactionInput.model_validate(operation.payload)
            response = await self.transactions.create_transaction(
                principal.business_id,
                principal.user_id,
                payload,
                request_id=request_id,
                idempotency_key=f"sync:{device_id}:{operation.operation_id}",
            )
            await self._set_tenant_context(principal)
            canonical = self._transaction_payload(payload, response.transaction)
            record = SyncRecord(
                id=uuid4(),
                business_id=principal.business_id,
                entity_type=FINANCIAL_ENTITY,
                entity_id=response.transaction.id,
                transaction_id=response.transaction.id,
                is_financial=True,
                version=1,
                payload=canonical,
            )
            self.repository.add(record)
            await self.repository.flush()
            self._add_change(record, "UPSERT", now)
            self._audit(principal, "OFFLINE_TRANSACTION_CREATED", record.entity_id, canonical)
            return PushResult(
                operation_id=operation.operation_id,
                local_id=operation.local_id,
                status="SYNCED",
                server_id=record.entity_id,
                server_version=record.version,
                canonical_payload=canonical,
            )

        assert operation.server_id is not None
        existing_record = await self.repository.record(
            principal.business_id,
            FINANCIAL_ENTITY,
            operation.server_id,
            lock=True,
        )
        if existing_record is None:
            raise HTTPException(status_code=404, detail="Transaksi sinkronisasi tidak ditemukan.")
        record = existing_record
        if operation.base_version != record.version:
            conflict = SyncConflictRevision(
                id=uuid4(),
                business_id=principal.business_id,
                device_session_id=principal.session_id,
                device_id=device_id,
                operation_id=operation.operation_id,
                entity_type=FINANCIAL_ENTITY,
                entity_id=record.entity_id,
                client_version=operation.base_version,
                server_version=record.version,
                client_payload=operation.payload,
                server_payload=record.payload,
                status="OPEN",
            )
            self.repository.add(conflict)
            self._audit(
                principal,
                "FINANCIAL_SYNC_CONFLICT",
                record.entity_id,
                {"conflict_id": str(conflict.id), "server_version": record.version},
            )
            return PushResult(
                operation_id=operation.operation_id,
                local_id=operation.local_id,
                status="CONFLICT",
                server_id=record.entity_id,
                server_version=record.version,
                conflict_id=conflict.id,
                canonical_payload=record.payload,
                deleted_at=record.deleted_at,
                message="Transaksi berubah di perangkat lain. Pilih versi secara manual.",
            )

        if record.transaction_id is None:
            raise RuntimeError("Referensi transaksi keuangan tidak lengkap.")
        if operation.action == "DELETE":
            reversal = await self.transactions.reverse(
                principal.business_id,
                record.transaction_id,
                principal.user_id,
                SimpleReversalRequest(
                    reason=str(operation.payload.get("reason") or "Dibatalkan dari perangkat")
                ),
                request_id=request_id,
            )
            await self._set_tenant_context(principal)
            record.transaction_id = reversal.id
            record.version += 1
            record.deleted_at = now
            record.payload = {**record.payload, "server_status": "REVERSED"}
            self._add_change(record, "DELETE", now)
        else:
            payload = SimpleTransactionInput.model_validate(operation.payload)
            response = await self.transactions.revise(
                principal.business_id,
                record.transaction_id,
                principal.user_id,
                SimpleRevisionRequest(
                    reason=str(
                        operation.payload.get("revision_reason") or "Diselesaikan dari perangkat"
                    ),
                    replacement=payload,
                ),
                request_id=request_id,
            )
            await self._set_tenant_context(principal)
            record.transaction_id = response.transaction.id
            record.version += 1
            record.payload = self._transaction_payload(payload, response.transaction)
            record.deleted_at = None
            self._add_change(record, "UPSERT", now)
        self._audit(principal, "OFFLINE_TRANSACTION_CHANGED", record.entity_id, record.payload)
        return PushResult(
            operation_id=operation.operation_id,
            local_id=operation.local_id,
            status="SYNCED",
            server_id=record.entity_id,
            server_version=record.version,
            canonical_payload=record.payload,
            deleted_at=record.deleted_at,
        )

    async def _apply_non_financial(
        self, principal: CurrentPrincipal, operation: PushOperation
    ) -> PushResult:
        now = datetime.now(UTC)
        entity_id = operation.server_id or uuid4()
        record = await self.repository.record(
            principal.business_id, operation.entity_type, entity_id, lock=True
        )
        if record is None:
            record = SyncRecord(
                id=uuid4(),
                business_id=principal.business_id,
                entity_type=operation.entity_type,
                entity_id=entity_id,
                is_financial=False,
                version=1,
                payload=operation.payload,
                deleted_at=now if operation.action == "DELETE" else None,
            )
            self.repository.add(record)
            await self.repository.flush()
        else:
            # Last-write-wins is allowed only for non-financial records.
            record.version += 1
            record.payload = operation.payload
            record.deleted_at = now if operation.action == "DELETE" else None
        self._add_change(record, "DELETE" if record.deleted_at else "UPSERT", now)
        return PushResult(
            operation_id=operation.operation_id,
            local_id=operation.local_id,
            status="SYNCED",
            server_id=record.entity_id,
            server_version=record.version,
            canonical_payload=record.payload,
            deleted_at=record.deleted_at,
        )

    async def _device_state(self, principal: CurrentPrincipal, device_id: str) -> DeviceSyncState:
        state = await self.repository.device_state(principal.business_id, device_id)
        if state is None:
            state = DeviceSyncState(
                id=uuid4(),
                business_id=principal.business_id,
                device_session_id=principal.session_id,
                device_id=device_id,
                last_cursor=0,
            )
            self.repository.add(state)
        else:
            state.device_session_id = principal.session_id
        return state

    def _add_change(self, record: SyncRecord, action: str, now: datetime) -> None:
        self.repository.add(
            SyncChange(
                id=uuid4(),
                business_id=record.business_id,
                record_id=record.id,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                version=record.version,
                action=action,
                payload=record.payload,
                changed_at=now,
            )
        )

    def _audit(
        self,
        principal: CurrentPrincipal,
        action: str,
        entity_id: UUID,
        data: dict[str, object],
    ) -> None:
        self.repository.add(
            AuditLog(
                id=uuid4(),
                business_id=principal.business_id,
                actor_user_id=principal.user_id,
                action=action,
                entity_type="TRANSACTION",
                entity_id=entity_id,
                after_data=data,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _transaction_payload(
        payload: SimpleTransactionInput, transaction: TransactionResponse
    ) -> dict[str, object]:
        return {
            **payload.model_dump(mode="json"),
            "server_status": transaction.status,
            "server_transaction_id": str(transaction.id),
        }

    @staticmethod
    def _assert_tenant(principal: CurrentPrincipal, business_id: UUID) -> None:
        if principal.business_id != business_id:
            raise HTTPException(
                status_code=403,
                detail="Token tidak berlaku untuk usaha yang diminta.",
            )

    async def _set_tenant_context(self, principal: CurrentPrincipal) -> None:
        await set_rls_context(
            self.repository.session,
            user_id=principal.user_id,
            business_id=principal.business_id,
            actor_type="BUSINESS",
        )
