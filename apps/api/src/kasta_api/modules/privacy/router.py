from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.privacy.dependencies import PrivacyServiceDependency
from kasta_api.modules.privacy.schemas import (
    AccountDeletionRequest,
    AccountDeletionResponse,
    PersonalDataExportResponse,
)

router = APIRouter(prefix="/businesses/{business_id}/privacy")

ExportPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.SESSION_READ))
]
DeletePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.SESSION_REVOKE_OWN))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/export", response_model=PersonalDataExportResponse)
async def export_personal_data(
    business_id: UUID,
    request: Request,
    principal: ExportPrincipal,
    service: PrivacyServiceDependency,
) -> PersonalDataExportResponse:
    return await service.export_data(
        principal.user_id,
        business_id,
        request_id=_request_id(request),
    )


@router.post(
    "/account-deletion",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_account(
    business_id: UUID,
    payload: AccountDeletionRequest,
    request: Request,
    principal: DeletePrincipal,
    service: PrivacyServiceDependency,
) -> AccountDeletionResponse:
    return await service.delete_account(
        principal.user_id,
        business_id,
        payload.current_password,
        reason=payload.reason,
        request_id=_request_id(request),
    )
