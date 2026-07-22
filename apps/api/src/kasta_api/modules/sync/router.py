from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_token_permission
from kasta_api.modules.sync.repository import SyncRepository
from kasta_api.modules.sync.schemas import (
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStatusResponse,
)
from kasta_api.modules.sync.service import OfflineSyncService
from kasta_api.modules.transactions.dependencies import TransactionServiceDependency

router = APIRouter(prefix="/sync", tags=["sync"])
PushPrincipal = Annotated[
    CurrentPrincipal, Depends(require_token_permission(PermissionCode.TRANSACTION_READ))
]
ReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_token_permission(PermissionCode.TRANSACTION_READ))
]


def service(
    session: DatabaseSession, transactions: TransactionServiceDependency
) -> OfflineSyncService:
    return OfflineSyncService(SyncRepository(session), transactions)


SyncService = Annotated[OfflineSyncService, Depends(service)]


@router.post("/push", response_model=SyncPushResponse)
async def push(
    payload: SyncPushRequest,
    request: Request,
    principal: PushPrincipal,
    sync: SyncService,
) -> SyncPushResponse:
    required = {
        "CREATE": PermissionCode.TRANSACTION_CREATE.value,
        "UPSERT": PermissionCode.TRANSACTION_UPDATE.value,
        "DELETE": PermissionCode.TRANSACTION_REVERSE.value,
    }
    for operation in payload.operations:
        permission = required[operation.action]
        if permission not in principal.permissions:
            raise HTTPException(status_code=403, detail=f"Izin tidak cukup: {permission}")
    request_id = getattr(request.state, "request_id", None)
    return await sync.push(
        principal,
        payload,
        request_id=str(request_id) if request_id is not None else None,
    )


@router.post("/pull", response_model=SyncPullResponse)
async def pull(
    payload: SyncPullRequest,
    principal: ReadPrincipal,
    sync: SyncService,
) -> SyncPullResponse:
    return await sync.pull(principal, payload)


@router.get("/status", response_model=SyncStatusResponse)
async def status(
    principal: ReadPrincipal,
    sync: SyncService,
    business_id: Annotated[UUID, Query()],
    device_id: Annotated[str, Query(min_length=8, max_length=200)],
) -> SyncStatusResponse:
    return await sync.status(principal, business_id, device_id)
