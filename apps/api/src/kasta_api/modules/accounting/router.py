from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from kasta_api.modules.accounting.dependencies import JournalServiceDependency
from kasta_api.modules.accounting.schemas import (
    AccountResponse,
    PostTransactionRequest,
    ReverseTransactionRequest,
    ReviseTransactionRequest,
    RevisionResultResponse,
    TransactionResponse,
    TransactionRevisionResponse,
)
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission

router = APIRouter(prefix="/businesses/{business_id}/accounting")

TransactionCreatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_CREATE))
]
TransactionReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_READ))
]
TransactionUpdatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_UPDATE))
]
TransactionReversePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_REVERSE))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    business_id: UUID,
    _: TransactionReadPrincipal,
    service: JournalServiceDependency,
) -> list[AccountResponse]:
    return [
        AccountResponse.model_validate(account)
        for account in await service.list_accounts(business_id)
    ]


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_transaction(
    business_id: UUID,
    payload: PostTransactionRequest,
    request: Request,
    principal: TransactionCreatePrincipal,
    service: JournalServiceDependency,
) -> TransactionResponse:
    transaction = await service.post_transaction(
        business_id,
        principal.user_id,
        payload.to_command(),
        request_id=_request_id(request),
    )
    return TransactionResponse.from_model(transaction)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    business_id: UUID,
    transaction_id: UUID,
    _: TransactionReadPrincipal,
    service: JournalServiceDependency,
) -> TransactionResponse:
    return TransactionResponse.from_model(
        await service.get_transaction(business_id, transaction_id)
    )


@router.get(
    "/transactions/{transaction_id}/history",
    response_model=list[TransactionRevisionResponse],
)
async def get_transaction_history(
    business_id: UUID,
    transaction_id: UUID,
    _: TransactionReadPrincipal,
    service: JournalServiceDependency,
) -> list[TransactionRevisionResponse]:
    return [
        TransactionRevisionResponse.model_validate(item)
        for item in await service.get_history(business_id, transaction_id)
    ]


@router.post(
    "/transactions/{transaction_id}/reversal",
    response_model=TransactionResponse,
)
async def reverse_transaction(
    business_id: UUID,
    transaction_id: UUID,
    payload: ReverseTransactionRequest,
    request: Request,
    principal: TransactionReversePrincipal,
    service: JournalServiceDependency,
) -> TransactionResponse:
    return TransactionResponse.from_model(
        await service.reverse_transaction(
            business_id,
            transaction_id,
            principal.user_id,
            reason=payload.reason,
            transaction_date=payload.transaction_date,
            request_id=_request_id(request),
        )
    )


@router.post(
    "/transactions/{transaction_id}/revision",
    response_model=RevisionResultResponse,
)
async def revise_transaction(
    business_id: UUID,
    transaction_id: UUID,
    payload: ReviseTransactionRequest,
    request: Request,
    principal: TransactionUpdatePrincipal,
    service: JournalServiceDependency,
) -> RevisionResultResponse:
    reversed_transaction, replacement = await service.revise_transaction(
        business_id,
        transaction_id,
        principal.user_id,
        payload.replacement.to_command(),
        reason=payload.reason,
        request_id=_request_id(request),
    )
    return RevisionResultResponse(
        reversed_transaction=TransactionResponse.from_model(reversed_transaction),
        replacement_transaction=TransactionResponse.from_model(replacement),
    )
