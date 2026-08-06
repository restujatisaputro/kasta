from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from kasta_api.core.config import get_settings
from kasta_api.core.security import client_ip
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import (
    AuthServiceDependency,
    CurrentPrincipal,
    SelectionPrincipal,
    require_business_selection,
    require_permission,
)
from kasta_api.modules.auth.schemas import (
    AccessTokenResponse,
    AuthorizationResponse,
    BusinessAccessResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenPairResponse,
    VerificationConfirmRequest,
    VerificationRequest,
)

router = APIRouter()


def _request_ip(request: Request) -> str:
    return client_ip(request, get_settings().trusted_proxy_cidrs)


@router.post("/auth/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest, request: Request, service: AuthServiceDependency
) -> TokenPairResponse:
    return await service.login(
        payload,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/auth/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest, request: Request, service: AuthServiceDependency
) -> TokenPairResponse:
    return await service.refresh(
        payload.refresh_token,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


BusinessSelection = Annotated[SelectionPrincipal, Depends(require_business_selection())]


@router.get("/auth/businesses", response_model=list[BusinessAccessResponse])
async def list_auth_businesses(
    principal: BusinessSelection, service: AuthServiceDependency
) -> list[BusinessAccessResponse]:
    return await service.accessible_businesses(principal.user_id)


@router.post("/auth/businesses/{business_id}/select", response_model=AccessTokenResponse)
async def select_auth_business(
    business_id: UUID,
    principal: BusinessSelection,
    service: AuthServiceDependency,
) -> AccessTokenResponse:
    return await service.select_business(principal.user_id, principal.session_id, business_id)


@router.post(
    "/auth/verification/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_verification(
    payload: VerificationRequest, service: AuthServiceDependency
) -> MessageResponse:
    return MessageResponse(message=await service.request_verification(payload.identifier))


@router.post("/auth/verification/confirm", response_model=MessageResponse)
async def confirm_verification(
    payload: VerificationConfirmRequest, service: AuthServiceDependency
) -> MessageResponse:
    await service.confirm_verification(payload.token)
    return MessageResponse(message="Verifikasi berhasil.")


@router.post(
    "/auth/password/forgot",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest, service: AuthServiceDependency
) -> MessageResponse:
    return MessageResponse(message=await service.forgot_password(payload.identifier))


@router.post("/auth/password/reset", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest, service: AuthServiceDependency
) -> MessageResponse:
    await service.reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password berhasil diperbarui. Semua sesi telah dicabut.")


SessionReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.SESSION_READ))
]
SessionRevokePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.SESSION_REVOKE_OWN))
]


@router.get(
    "/businesses/{business_id}/auth/authorization",
    response_model=AuthorizationResponse,
)
async def current_authorization(
    business_id: UUID, principal: SessionReadPrincipal
) -> AuthorizationResponse:
    return AuthorizationResponse(
        user_id=principal.user_id,
        session_id=principal.session_id,
        business_id=business_id,
        role=principal.role,
        permissions=sorted(principal.permissions),
    )


@router.get("/businesses/{business_id}/auth/sessions", response_model=list[SessionResponse])
async def list_sessions(
    business_id: UUID,
    principal: SessionReadPrincipal,
    service: AuthServiceDependency,
) -> list[SessionResponse]:
    sessions = await service.list_sessions(principal.user_id, business_id, principal.session_id)
    return [
        SessionResponse.model_validate(device_session).model_copy(update={"is_current": is_current})
        for device_session, is_current in sessions
    ]


@router.delete("/businesses/{business_id}/auth/sessions", response_model=MessageResponse)
async def logout_all_devices(
    business_id: UUID,
    principal: SessionRevokePrincipal,
    service: AuthServiceDependency,
) -> MessageResponse:
    count = await service.logout_all(principal.user_id, business_id)
    return MessageResponse(message=f"{count} sesi perangkat telah dicabut.")


@router.delete(
    "/businesses/{business_id}/auth/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_device(
    business_id: UUID,
    session_id: UUID,
    principal: SessionRevokePrincipal,
    service: AuthServiceDependency,
) -> Response:
    await service.logout_device(principal.user_id, business_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
