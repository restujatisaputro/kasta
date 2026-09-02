from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.closing.dependencies import ClosingServiceDependency
from kasta_api.modules.closing.schemas import (
    ClosePeriodRequest,
    CurrentPeriodResponse,
    PeriodClosingListResponse,
    PeriodClosingResponse,
)

router = APIRouter(prefix="/businesses/{business_id}/closing")

ClosingRead = Annotated[CurrentPrincipal, Depends(require_permission(PermissionCode.CLOSING_READ))]
ClosingWrite = Annotated[CurrentPrincipal, Depends(require_permission(PermissionCode.CLOSING_CREATE))]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/current", response_model=CurrentPeriodResponse)
async def current_period(
    business_id: UUID,
    _: ClosingRead,
    service: ClosingServiceDependency,
    as_of: date | None = None,
) -> CurrentPeriodResponse:
    return await service.current_period(business_id, as_of)


@router.get("", response_model=PeriodClosingListResponse)
async def closing_history(
    business_id: UUID,
    _: ClosingRead,
    service: ClosingServiceDependency,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PeriodClosingListResponse:
    return await service.history(business_id, limit=limit, offset=offset)


@router.post("", response_model=PeriodClosingResponse, status_code=201)
async def close_period(
    business_id: UUID,
    payload: ClosePeriodRequest,
    request: Request,
    principal: ClosingWrite,
    service: ClosingServiceDependency,
) -> PeriodClosingResponse:
    return await service.close_period(
        business_id, principal.user_id, payload, request_id=_request_id(request)
    )
