from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from starlette.responses import Response

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import (
    AuthServiceDependency,
    CurrentPrincipal,
    get_token_manager,
    require_permission,
)
from kasta_api.modules.auth.schemas import (
    OnboardingVerificationResponse,
    RegistrationRequest,
    RegistrationResponse,
    VerificationConfirmRequest,
)
from kasta_api.modules.businesses.dependencies import (
    BusinessLogoStorageDependency,
    BusinessServiceDependency,
    OnboardingPrincipalDependency,
)
from kasta_api.modules.businesses.schemas import (
    BusinessCategoryResponse,
    BusinessProfileResponse,
    BusinessProfileUpdate,
    CompleteOnboardingRequest,
    CompleteOnboardingResponse,
)

router = APIRouter()


def _request_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


@router.post("/onboarding/account", response_model=RegistrationResponse, status_code=201)
async def create_account(
    payload: RegistrationRequest, service: AuthServiceDependency
) -> RegistrationResponse:
    user_id = await service.register_account(payload)
    return RegistrationResponse(
        user_id=user_id,
        message="Akun berhasil dibuat. Periksa email atau SMS untuk melakukan verifikasi.",
    )


@router.post("/onboarding/verify", response_model=OnboardingVerificationResponse)
async def verify_account(
    payload: VerificationConfirmRequest, service: AuthServiceDependency
) -> OnboardingVerificationResponse:
    user = await service.confirm_verification(payload.token)
    settings = service.settings
    return OnboardingVerificationResponse(
        onboarding_token=get_token_manager().create_onboarding_token(
            user.id, settings.onboarding_token_minutes
        ),
        expires_in=settings.onboarding_token_minutes * 60,
    )


@router.get("/onboarding/categories", response_model=list[BusinessCategoryResponse])
async def list_categories(
    service: BusinessServiceDependency,
) -> list[BusinessCategoryResponse]:
    return await service.list_categories()


@router.post("/onboarding/complete", response_model=CompleteOnboardingResponse, status_code=201)
async def complete_onboarding(
    payload: CompleteOnboardingRequest,
    request: Request,
    principal: OnboardingPrincipalDependency,
    service: BusinessServiceDependency,
) -> CompleteOnboardingResponse:
    return await service.complete_onboarding(
        principal.user_id,
        payload,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


ProfileReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.BUSINESS_PROFILE_READ))
]
ProfileUpdatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.BUSINESS_PROFILE_UPDATE))
]


@router.get(
    "/businesses/{business_id}/profile",
    response_model=BusinessProfileResponse,
)
async def get_business_profile(
    business_id: UUID,
    _: ProfileReadPrincipal,
    service: BusinessServiceDependency,
) -> BusinessProfileResponse:
    return await service.get_profile(business_id)


@router.patch(
    "/businesses/{business_id}/profile",
    response_model=BusinessProfileResponse,
)
async def update_business_profile(
    business_id: UUID,
    payload: BusinessProfileUpdate,
    _: ProfileUpdatePrincipal,
    service: BusinessServiceDependency,
) -> BusinessProfileResponse:
    return await service.update_profile(business_id, payload)


@router.put(
    "/businesses/{business_id}/profile/logo",
    response_model=BusinessProfileResponse,
)
async def upload_business_logo(
    business_id: UUID,
    _: ProfileUpdatePrincipal,
    storage: BusinessLogoStorageDependency,
    service: BusinessServiceDependency,
    logo: Annotated[UploadFile, File()],
) -> BusinessProfileResponse:
    object_key = await storage.upload(business_id, logo)
    return await service.set_logo(business_id, object_key)


@router.get("/businesses/{business_id}/profile/logo", response_class=Response)
async def get_business_logo(
    business_id: UUID,
    _: ProfileReadPrincipal,
    storage: BusinessLogoStorageDependency,
    service: BusinessServiceDependency,
) -> Response:
    object_key = await service.get_logo_key(business_id)
    data, content_type = await storage.download(object_key)
    return Response(content=data, media_type=content_type)
