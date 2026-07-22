from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.obligations.constants import ObligationKind, ObligationStatus
from kasta_api.modules.obligations.dependencies import ObligationServiceDependency
from kasta_api.modules.obligations.schemas import (
    AgingReportResponse,
    CancellationRequest,
    ObligationCreateRequest,
    ObligationDetailResponse,
    ObligationListResponse,
    ObligationResponse,
    PartyCreateRequest,
    PartyResponse,
    PaymentCreateRequest,
    PaymentResponse,
    ReminderGenerationResponse,
    ReminderListResponse,
)

router = APIRouter(prefix="/businesses/{business_id}")

ReceivableRead = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIVABLE_READ))
]
ReceivableWrite = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIVABLE_CREATE))
]
ReceivablePay = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIVABLE_PAYMENT_CREATE))
]
ReceivableCancel = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIVABLE_CANCEL))
]
PayableRead = Annotated[CurrentPrincipal, Depends(require_permission(PermissionCode.PAYABLE_READ))]
PayableWrite = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PAYABLE_CREATE))
]
PayablePay = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PAYABLE_PAYMENT_CREATE))
]
PayableCancel = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PAYABLE_CANCEL))
]
ReminderManage = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.OBLIGATION_REMINDER_MANAGE))
]
ReportRead = Annotated[CurrentPrincipal, Depends(require_permission(PermissionCode.REPORT_READ))]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/customers", response_model=list[PartyResponse], tags=["receivables"])
async def list_customers(
    business_id: UUID, _: ReceivableRead, service: ObligationServiceDependency
) -> list[PartyResponse]:
    return await service.list_parties(business_id, kind=ObligationKind.RECEIVABLE)


@router.post(
    "/customers",
    response_model=PartyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["receivables"],
)
async def create_customer(
    business_id: UUID,
    payload: PartyCreateRequest,
    _: ReceivableWrite,
    service: ObligationServiceDependency,
) -> PartyResponse:
    return await service.create_party(business_id, payload, kind=ObligationKind.RECEIVABLE)


@router.get("/suppliers", response_model=list[PartyResponse], tags=["payables"])
async def list_suppliers(
    business_id: UUID, _: PayableRead, service: ObligationServiceDependency
) -> list[PartyResponse]:
    return await service.list_parties(business_id, kind=ObligationKind.PAYABLE)


@router.post(
    "/suppliers",
    response_model=PartyResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payables"],
)
async def create_supplier(
    business_id: UUID,
    payload: PartyCreateRequest,
    _: PayableWrite,
    service: ObligationServiceDependency,
) -> PartyResponse:
    return await service.create_party(business_id, payload, kind=ObligationKind.PAYABLE)


async def _list(
    business_id: UUID,
    service: ObligationServiceDependency,
    kind: ObligationKind,
    q: str | None,
    obligation_status: ObligationStatus | None,
    due_from: date | None,
    due_to: date | None,
    overdue_only: bool,
    limit: int,
    offset: int,
) -> ObligationListResponse:
    return await service.list_obligations(
        business_id,
        kind=kind,
        query=q,
        status=obligation_status,
        due_from=due_from,
        due_to=due_to,
        overdue_only=overdue_only,
        limit=limit,
        offset=offset,
    )


@router.get("/receivables", response_model=ObligationListResponse, tags=["receivables"])
async def list_receivables(
    business_id: UUID,
    _: ReceivableRead,
    service: ObligationServiceDependency,
    q: str | None = Query(default=None, max_length=100),
    obligation_status: Annotated[ObligationStatus | None, Query(alias="status")] = None,
    due_from: date | None = None,
    due_to: date | None = None,
    overdue_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ObligationListResponse:
    return await _list(
        business_id,
        service,
        ObligationKind.RECEIVABLE,
        q,
        obligation_status,
        due_from,
        due_to,
        overdue_only,
        limit,
        offset,
    )


@router.post(
    "/receivables",
    response_model=ObligationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["receivables"],
)
async def create_receivable(
    business_id: UUID,
    payload: ObligationCreateRequest,
    request: Request,
    principal: ReceivableWrite,
    service: ObligationServiceDependency,
) -> ObligationResponse:
    return await service.create(
        business_id,
        principal.user_id,
        payload,
        kind=ObligationKind.RECEIVABLE,
        request_id=_request_id(request),
    )


@router.get(
    "/receivables/{obligation_id}",
    response_model=ObligationDetailResponse,
    tags=["receivables"],
)
async def receivable_detail(
    business_id: UUID,
    obligation_id: UUID,
    _: ReceivableRead,
    service: ObligationServiceDependency,
) -> ObligationDetailResponse:
    return await service.detail(business_id, obligation_id, kind=ObligationKind.RECEIVABLE)


@router.get(
    "/receivables/{obligation_id}/payments",
    response_model=list[PaymentResponse],
    tags=["receivables"],
)
async def receivable_payments(
    business_id: UUID,
    obligation_id: UUID,
    _: ReceivableRead,
    service: ObligationServiceDependency,
) -> list[PaymentResponse]:
    return (
        await service.detail(business_id, obligation_id, kind=ObligationKind.RECEIVABLE)
    ).payments


@router.post(
    "/receivables/{obligation_id}/payments",
    response_model=ObligationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["receivables"],
)
async def pay_receivable(
    business_id: UUID,
    obligation_id: UUID,
    payload: PaymentCreateRequest,
    request: Request,
    principal: ReceivablePay,
    service: ObligationServiceDependency,
) -> ObligationDetailResponse:
    return await service.pay(
        business_id,
        obligation_id,
        principal.user_id,
        payload,
        kind=ObligationKind.RECEIVABLE,
        request_id=_request_id(request),
    )


@router.post(
    "/receivables/{obligation_id}/cancellation",
    response_model=ObligationResponse,
    tags=["receivables"],
)
async def cancel_receivable(
    business_id: UUID,
    obligation_id: UUID,
    payload: CancellationRequest,
    request: Request,
    principal: ReceivableCancel,
    service: ObligationServiceDependency,
) -> ObligationResponse:
    return await service.cancel(
        business_id,
        obligation_id,
        principal.user_id,
        payload,
        kind=ObligationKind.RECEIVABLE,
        request_id=_request_id(request),
    )


@router.get("/payables", response_model=ObligationListResponse, tags=["payables"])
async def list_payables(
    business_id: UUID,
    _: PayableRead,
    service: ObligationServiceDependency,
    q: str | None = Query(default=None, max_length=100),
    obligation_status: Annotated[ObligationStatus | None, Query(alias="status")] = None,
    due_from: date | None = None,
    due_to: date | None = None,
    overdue_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ObligationListResponse:
    return await _list(
        business_id,
        service,
        ObligationKind.PAYABLE,
        q,
        obligation_status,
        due_from,
        due_to,
        overdue_only,
        limit,
        offset,
    )


@router.post(
    "/payables",
    response_model=ObligationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payables"],
)
async def create_payable(
    business_id: UUID,
    payload: ObligationCreateRequest,
    request: Request,
    principal: PayableWrite,
    service: ObligationServiceDependency,
) -> ObligationResponse:
    return await service.create(
        business_id,
        principal.user_id,
        payload,
        kind=ObligationKind.PAYABLE,
        request_id=_request_id(request),
    )


@router.get(
    "/payables/{obligation_id}",
    response_model=ObligationDetailResponse,
    tags=["payables"],
)
async def payable_detail(
    business_id: UUID,
    obligation_id: UUID,
    _: PayableRead,
    service: ObligationServiceDependency,
) -> ObligationDetailResponse:
    return await service.detail(business_id, obligation_id, kind=ObligationKind.PAYABLE)


@router.get(
    "/payables/{obligation_id}/payments",
    response_model=list[PaymentResponse],
    tags=["payables"],
)
async def payable_payments(
    business_id: UUID,
    obligation_id: UUID,
    _: PayableRead,
    service: ObligationServiceDependency,
) -> list[PaymentResponse]:
    return (await service.detail(business_id, obligation_id, kind=ObligationKind.PAYABLE)).payments


@router.post(
    "/payables/{obligation_id}/payments",
    response_model=ObligationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payables"],
)
async def pay_payable(
    business_id: UUID,
    obligation_id: UUID,
    payload: PaymentCreateRequest,
    request: Request,
    principal: PayablePay,
    service: ObligationServiceDependency,
) -> ObligationDetailResponse:
    return await service.pay(
        business_id,
        obligation_id,
        principal.user_id,
        payload,
        kind=ObligationKind.PAYABLE,
        request_id=_request_id(request),
    )


@router.post(
    "/payables/{obligation_id}/cancellation",
    response_model=ObligationResponse,
    tags=["payables"],
)
async def cancel_payable(
    business_id: UUID,
    obligation_id: UUID,
    payload: CancellationRequest,
    request: Request,
    principal: PayableCancel,
    service: ObligationServiceDependency,
) -> ObligationResponse:
    return await service.cancel(
        business_id,
        obligation_id,
        principal.user_id,
        payload,
        kind=ObligationKind.PAYABLE,
        request_id=_request_id(request),
    )


@router.get("/obligations/aging", response_model=AgingReportResponse, tags=["reports"])
async def aging_report(
    business_id: UUID,
    _: ReportRead,
    service: ObligationServiceDependency,
    as_of: date | None = None,
) -> AgingReportResponse:
    return await service.aging(business_id, as_of or date.today())


@router.get(
    "/obligations/reminders",
    response_model=ReminderListResponse,
    tags=["notifications"],
)
async def reminder_candidates(
    business_id: UUID,
    _: ReceivableRead,
    service: ObligationServiceDependency,
    as_of: date | None = None,
) -> ReminderListResponse:
    return await service.reminders(business_id, as_of or date.today())


@router.post(
    "/obligations/reminders/generate",
    response_model=ReminderGenerationResponse,
    tags=["notifications"],
)
async def generate_reminders(
    business_id: UUID,
    _: ReminderManage,
    service: ObligationServiceDependency,
    as_of: date | None = None,
) -> ReminderGenerationResponse:
    return await service.generate_reminders(business_id, as_of or date.today())
