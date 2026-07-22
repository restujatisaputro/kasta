from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from starlette.responses import Response as StarletteResponse

from kasta_api.modules.accounting.schemas import TransactionResponse
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.transactions.dependencies import (
    ReceiptStorageDependency,
    TransactionServiceDependency,
)
from kasta_api.modules.transactions.schemas import (
    DraftCreateRequest,
    DraftResponse,
    ReceiptImageResponse,
    ReceiptUrlResponse,
    RecurringResponse,
    RecurringStatusRequest,
    SimpleReversalRequest,
    SimpleRevisionRequest,
    SimpleTransactionInput,
    SimpleTransactionResponse,
    TransactionListResponse,
    TransactionOptionsResponse,
    TransactionSyncRequest,
    TransactionSyncResponse,
)

router = APIRouter(prefix="/businesses/{business_id}")

CreatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_CREATE))
]
ReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_READ))
]
UpdatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_UPDATE))
]
DeletePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_DELETE))
]
ReversePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_REVERSE))
]
ReceiptUploadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIPT_UPLOAD))
]
ReceiptReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIPT_READ))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/transactions/options", response_model=TransactionOptionsResponse)
async def transaction_options(
    business_id: UUID,
    _: ReadPrincipal,
    service: TransactionServiceDependency,
) -> TransactionOptionsResponse:
    return await service.options(business_id)


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    business_id: UUID,
    _: ReadPrincipal,
    service: TransactionServiceDependency,
    q: str | None = Query(default=None, max_length=100),
    entry_kind: Literal["INCOME", "EXPENSE", "CAPITAL", "OWNER_DRAW"] | None = None,
    transaction_status: Literal["POSTED", "REVERSED"] | None = None,
    payment_method: str | None = Query(default=None, max_length=30),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TransactionListResponse:
    return await service.list_transactions(
        business_id,
        query=q,
        entry_kind=entry_kind,
        transaction_status=transaction_status,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/transactions",
    response_model=SimpleTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    business_id: UUID,
    payload: SimpleTransactionInput,
    request: Request,
    principal: CreatePrincipal,
    service: TransactionServiceDependency,
) -> SimpleTransactionResponse:
    return await service.create_transaction(
        business_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.get("/transactions/drafts", response_model=list[DraftResponse])
async def list_drafts(
    business_id: UUID,
    _: ReadPrincipal,
    service: TransactionServiceDependency,
) -> list[DraftResponse]:
    return await service.list_drafts(business_id)


@router.post(
    "/transactions/drafts", response_model=DraftResponse, status_code=status.HTTP_201_CREATED
)
async def create_draft(
    business_id: UUID,
    payload: DraftCreateRequest,
    principal: CreatePrincipal,
    service: TransactionServiceDependency,
) -> DraftResponse:
    return DraftResponse.model_validate(
        await service.create_draft(business_id, principal.user_id, payload)
    )


@router.put("/transactions/drafts/{draft_id}", response_model=DraftResponse)
async def update_draft(
    business_id: UUID,
    draft_id: UUID,
    payload: DraftCreateRequest,
    _: UpdatePrincipal,
    service: TransactionServiceDependency,
) -> DraftResponse:
    return DraftResponse.model_validate(await service.update_draft(business_id, draft_id, payload))


@router.delete("/transactions/drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    business_id: UUID,
    draft_id: UUID,
    _: DeletePrincipal,
    service: TransactionServiceDependency,
) -> Response:
    await service.delete_draft(business_id, draft_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/transactions/drafts/{draft_id}/post", response_model=SimpleTransactionResponse)
async def post_draft(
    business_id: UUID,
    draft_id: UUID,
    request: Request,
    principal: CreatePrincipal,
    service: TransactionServiceDependency,
) -> SimpleTransactionResponse:
    return await service.post_draft(
        business_id,
        draft_id,
        principal.user_id,
        request_id=_request_id(request),
    )


@router.post("/transactions/{transaction_id}/revision", response_model=SimpleTransactionResponse)
async def revise_transaction(
    business_id: UUID,
    transaction_id: UUID,
    payload: SimpleRevisionRequest,
    request: Request,
    principal: UpdatePrincipal,
    service: TransactionServiceDependency,
) -> SimpleTransactionResponse:
    return await service.revise(
        business_id,
        transaction_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.post("/transactions/{transaction_id}/reversal", response_model=TransactionResponse)
async def reverse_transaction(
    business_id: UUID,
    transaction_id: UUID,
    payload: SimpleReversalRequest,
    request: Request,
    principal: ReversePrincipal,
    service: TransactionServiceDependency,
) -> TransactionResponse:
    return await service.reverse(
        business_id,
        transaction_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.get("/transactions/recurring", response_model=list[RecurringResponse])
async def list_recurring(
    business_id: UUID,
    _: ReadPrincipal,
    service: TransactionServiceDependency,
) -> list[RecurringResponse]:
    return await service.list_recurring(business_id)


@router.patch("/transactions/recurring/{recurring_id}", response_model=RecurringResponse)
async def update_recurring_status(
    business_id: UUID,
    recurring_id: UUID,
    payload: RecurringStatusRequest,
    _: UpdatePrincipal,
    service: TransactionServiceDependency,
) -> RecurringResponse:
    return await service.set_recurring_status(business_id, recurring_id, payload.status)


@router.post("/transactions/recurring/run-due", response_model=list[TransactionResponse])
async def run_due_recurring(
    business_id: UUID,
    principal: CreatePrincipal,
    service: TransactionServiceDependency,
    through_date: Annotated[date | None, Query()] = None,
) -> list[TransactionResponse]:
    return await service.run_due_recurring(
        business_id, principal.user_id, through_date or date.today()
    )


@router.post(
    "/transactions/{transaction_id}/receipts",
    response_model=ReceiptImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_receipt(
    business_id: UUID,
    transaction_id: UUID,
    principal: ReceiptUploadPrincipal,
    storage: ReceiptStorageDependency,
    service: TransactionServiceDependency,
    photo: Annotated[UploadFile, File()],
) -> ReceiptImageResponse:
    return await service.add_receipt(business_id, transaction_id, principal.user_id, photo, storage)


@router.get("/receipts/{receipt_id}", response_class=StarletteResponse)
async def download_receipt(
    business_id: UUID,
    receipt_id: UUID,
    _: ReceiptReadPrincipal,
    storage: ReceiptStorageDependency,
    service: TransactionServiceDependency,
) -> StarletteResponse:
    data, content_type = await service.receipt_data(business_id, receipt_id, storage)
    return StarletteResponse(content=data, media_type=content_type)


@router.get("/receipts/{receipt_id}/url", response_model=ReceiptUrlResponse)
async def receipt_url(
    business_id: UUID,
    receipt_id: UUID,
    _: ReceiptReadPrincipal,
    storage: ReceiptStorageDependency,
    service: TransactionServiceDependency,
) -> ReceiptUrlResponse:
    url, expires_in = await service.receipt_url(business_id, receipt_id, storage)
    return ReceiptUrlResponse(url=url, expires_in=expires_in)


@router.post("/sync/transactions", response_model=TransactionSyncResponse)
async def sync_transactions(
    business_id: UUID,
    payload: TransactionSyncRequest,
    request: Request,
    principal: ReadPrincipal,
    service: TransactionServiceDependency,
) -> TransactionSyncResponse:
    required = {
        "CREATE": PermissionCode.TRANSACTION_CREATE.value,
        "SAVE_DRAFT": PermissionCode.TRANSACTION_CREATE.value,
        "REVISE": PermissionCode.TRANSACTION_UPDATE.value,
        "REVERSE": PermissionCode.TRANSACTION_REVERSE.value,
    }
    missing = {
        required[operation.operation]
        for operation in payload.operations
        if required[operation.operation] not in principal.permissions
    }
    if missing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Izin tidak cukup: {', '.join(sorted(missing))}",
        )
    return await service.sync(
        business_id,
        principal.user_id,
        principal.session_id,
        payload,
        request_id=_request_id(request),
    )
