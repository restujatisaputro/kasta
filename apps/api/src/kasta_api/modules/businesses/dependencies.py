from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from kasta_api.api.dependencies import DatabaseSession, SettingsDependency
from kasta_api.modules.auth.dependencies import BearerToken, get_token_manager
from kasta_api.modules.auth.repository import AuthRepository
from kasta_api.modules.businesses.repository import BusinessRepository
from kasta_api.modules.businesses.service import BusinessService
from kasta_api.modules.businesses.storage import BusinessLogoStorage


class OnboardingPrincipal(BaseModel):
    user_id: UUID


async def require_onboarding_principal(
    token: BearerToken,
    session: DatabaseSession,
    settings: SettingsDependency,
) -> OnboardingPrincipal:
    try:
        claims = get_token_manager().decode_onboarding_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = await AuthRepository(session).get_user(claims.user_id)
    if (
        user is None
        or user.deleted_at is not None
        or user.status != "ACTIVE"
        or (user.email_verified_at is None and user.phone_verified_at is None)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun belum terverifikasi atau tidak aktif.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return OnboardingPrincipal(user_id=user.id)


def get_business_service(session: DatabaseSession, settings: SettingsDependency) -> BusinessService:
    return BusinessService(BusinessRepository(session), settings, get_token_manager())


OnboardingPrincipalDependency = Annotated[
    OnboardingPrincipal, Depends(require_onboarding_principal)
]
BusinessServiceDependency = Annotated[BusinessService, Depends(get_business_service)]


def get_business_logo_storage(settings: SettingsDependency) -> BusinessLogoStorage:
    return BusinessLogoStorage(settings)


BusinessLogoStorageDependency = Annotated[BusinessLogoStorage, Depends(get_business_logo_storage)]
