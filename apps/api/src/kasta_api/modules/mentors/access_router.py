from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.mentors.dependencies import (
    MentorAccessServiceDependency,
    MentorIdentityDependency,
    SupportAccessServiceDependency,
)
from kasta_api.modules.mentors.schemas import (
    MentorAccessDecision,
    MentorAccessHistoryItem,
    MentorAccessRequestCreate,
    MentorAccessResponse,
    MentorAccessRevoke,
    SupportAccessGrantCreate,
    SupportAccessGrantResponse,
    SupportAccessGrantRevoke,
)

mentor_access_router = APIRouter(prefix="/mentors/me/access-requests", tags=["mentor-access"])
business_access_router = APIRouter(
    prefix="/businesses/{business_id}/mentor-access", tags=["mentor-access"]
)
support_access_router = APIRouter(
    prefix="/businesses/{business_id}/support-access-grants",
    tags=["support-access"],
)
OwnerPrincipal = Annotated[
    CurrentPrincipal,
    Depends(require_permission(PermissionCode.BUSINESS_MEMBER_MANAGE)),
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@mentor_access_router.post(
    "", response_model=MentorAccessResponse, status_code=status.HTTP_201_CREATED
)
async def request_access(
    payload: MentorAccessRequestCreate,
    request: Request,
    mentor: MentorIdentityDependency,
    service: MentorAccessServiceDependency,
) -> MentorAccessResponse:
    return await service.request_access(mentor, payload, request_id=_request_id(request))


@mentor_access_router.get("", response_model=list[MentorAccessResponse])
async def my_access_requests(
    mentor: MentorIdentityDependency,
    service: MentorAccessServiceDependency,
) -> list[MentorAccessResponse]:
    return await service.mentor_requests(mentor)


@business_access_router.get("", response_model=list[MentorAccessResponse])
async def list_business_access(
    business_id: UUID,
    principal: OwnerPrincipal,
    service: MentorAccessServiceDependency,
) -> list[MentorAccessResponse]:
    return await service.business_accesses(principal, business_id)


@business_access_router.patch("/{access_id}/decision", response_model=MentorAccessResponse)
async def decide_access(
    business_id: UUID,
    access_id: UUID,
    payload: MentorAccessDecision,
    request: Request,
    principal: OwnerPrincipal,
    service: MentorAccessServiceDependency,
) -> MentorAccessResponse:
    return await service.decide(
        principal,
        business_id,
        access_id,
        payload,
        request_id=_request_id(request),
    )


@business_access_router.post("/{access_id}/revoke", response_model=MentorAccessResponse)
async def revoke_access(
    business_id: UUID,
    access_id: UUID,
    payload: MentorAccessRevoke,
    request: Request,
    principal: OwnerPrincipal,
    service: MentorAccessServiceDependency,
) -> MentorAccessResponse:
    return await service.revoke(
        principal,
        business_id,
        access_id,
        payload,
        request_id=_request_id(request),
    )


@business_access_router.get("/history", response_model=list[MentorAccessHistoryItem])
async def access_history(
    business_id: UUID,
    principal: OwnerPrincipal,
    service: MentorAccessServiceDependency,
) -> list[MentorAccessHistoryItem]:
    return await service.access_history(principal, business_id)


@support_access_router.post(
    "", response_model=SupportAccessGrantResponse, status_code=status.HTTP_201_CREATED
)
async def create_support_grant(
    business_id: UUID,
    payload: SupportAccessGrantCreate,
    request: Request,
    principal: OwnerPrincipal,
    service: SupportAccessServiceDependency,
) -> SupportAccessGrantResponse:
    return await service.create(
        principal,
        business_id,
        payload,
        request_id=_request_id(request),
    )


@support_access_router.get("", response_model=list[SupportAccessGrantResponse])
async def list_support_grants(
    business_id: UUID,
    principal: OwnerPrincipal,
    service: SupportAccessServiceDependency,
) -> list[SupportAccessGrantResponse]:
    return await service.list(principal, business_id)


@support_access_router.post("/{grant_id}/revoke", response_model=SupportAccessGrantResponse)
async def revoke_support_grant(
    business_id: UUID,
    grant_id: UUID,
    payload: SupportAccessGrantRevoke,
    request: Request,
    principal: OwnerPrincipal,
    service: SupportAccessServiceDependency,
) -> SupportAccessGrantResponse:
    return await service.revoke(
        principal,
        business_id,
        grant_id,
        payload,
        request_id=_request_id(request),
    )
