from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from kasta_api.api.dependencies import DatabaseSession, SettingsDependency
from kasta_api.db.rls import set_rls_context
from kasta_api.modules.auth.constants import PermissionCode, RoleCode
from kasta_api.modules.auth.dependencies import BearerToken
from kasta_api.modules.auth.repository import AuthRepository
from kasta_api.modules.auth.security import TokenManager
from kasta_api.modules.auth.service import assert_permission
from kasta_api.modules.mentors.access_service import MentorAccessService
from kasta_api.modules.mentors.models import Mentor
from kasta_api.modules.mentors.repository import MentorRepository
from kasta_api.modules.mentors.service import MentorService
from kasta_api.modules.mentors.support_access_service import SupportAccessService
from kasta_api.modules.reports.repository import ReportRepository

MentorDependency = Callable[..., Coroutine[Any, Any, Mentor]]


def require_mentor(permission: PermissionCode | None = None) -> MentorDependency:
    """Authenticate a mentor without binding the workspace to one business path."""

    async def dependency(
        token: BearerToken,
        session: DatabaseSession,
        settings: SettingsDependency,
    ) -> Mentor:
        try:
            claims = TokenManager(settings).decode_access_token(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if claims.business_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Pilih usaha terlebih dahulu.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        mentor = await MentorRepository(session).mentor_for_user(claims.user_id)
        if mentor is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Profil pembina tidak aktif.",
            )
        await set_rls_context(
            session,
            user_id=claims.user_id,
            business_id=claims.business_id,
            actor_type="MENTOR",
            mentor_id=mentor.id,
        )
        auth_repository = AuthRepository(session)
        device_session = await auth_repository.get_device_session(claims.session_id)
        now = datetime.now(UTC)
        expires_at = device_session.expires_at if device_session is not None else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            device_session is None
            or device_session.user_id != claims.user_id
            or device_session.business_id != claims.business_id
            or device_session.revoked_at is not None
            or expires_at is None
            or expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak aktif atau sudah dicabut.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        authorization = await auth_repository.resolve_authorization(
            claims.user_id, claims.business_id
        )
        if authorization is None or authorization.role_code != RoleCode.MENTOR.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Area ini hanya tersedia untuk pembina UMKM.",
            )
        if permission is not None:
            assert_permission(authorization, permission.value)
        return mentor

    return dependency


def get_mentor_service(session: DatabaseSession) -> MentorService:
    return MentorService(MentorRepository(session), ReportRepository(session))


MentorServiceDependency = Annotated[MentorService, Depends(get_mentor_service)]
MentorIdentityDependency = Annotated[Mentor, Depends(require_mentor())]


def get_mentor_access_service(session: DatabaseSession) -> MentorAccessService:
    return MentorAccessService(MentorRepository(session))


MentorAccessServiceDependency = Annotated[MentorAccessService, Depends(get_mentor_access_service)]


def get_support_access_service(session: DatabaseSession) -> SupportAccessService:
    return SupportAccessService(session)


SupportAccessServiceDependency = Annotated[
    SupportAccessService, Depends(get_support_access_service)
]
MentorReadDependency = Annotated[
    Mentor, Depends(require_mentor(PermissionCode.MENTOR_SUMMARY_READ))
]
MentorNoteDependency = Annotated[Mentor, Depends(require_mentor(PermissionCode.MENTOR_NOTE_CREATE))]
MentorRecommendationDependency = Annotated[
    Mentor, Depends(require_mentor(PermissionCode.MENTOR_RECOMMENDATION_MANAGE))
]
MentorSessionDependency = Annotated[
    Mentor, Depends(require_mentor(PermissionCode.MENTOR_SESSION_MANAGE))
]
MentorExportDependency = Annotated[
    Mentor, Depends(require_mentor(PermissionCode.MENTOR_REPORT_EXPORT))
]
