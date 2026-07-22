from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.auth.dependencies import get_password_manager
from kasta_api.modules.auth.repository import AuthRepository
from kasta_api.modules.privacy.repository import PrivacyRepository
from kasta_api.modules.privacy.service import PrivacyService


def get_privacy_service(session: DatabaseSession) -> PrivacyService:
    return PrivacyService(
        PrivacyRepository(session),
        AuthRepository(session),
        get_password_manager(),
    )


PrivacyServiceDependency = Annotated[PrivacyService, Depends(get_privacy_service)]
