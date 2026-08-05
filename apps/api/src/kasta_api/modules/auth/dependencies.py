from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select, text

from kasta_api.api.dependencies import DatabaseSession, SettingsDependency
from kasta_api.core.config import get_settings
from kasta_api.db.rls import set_rls_context
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.repository import (
    SCOPED_DATA_PERMISSIONS,
    AuthRepository,
)
from kasta_api.modules.auth.security import OutboxCipher, PasswordManager, TokenManager
from kasta_api.modules.auth.service import AuthService, assert_permission
from kasta_api.modules.mentors.models import Mentor, MentorBusinessAccess, SupportAccessGrant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class CurrentPrincipal(BaseModel):
    user_id: UUID
    session_id: UUID
    business_id: UUID
    role: str
    permissions: frozenset[str]
    support_grant_id: UUID | None = None


class SelectionPrincipal(BaseModel):
    user_id: UUID
    session_id: UUID


@lru_cache
def get_password_manager() -> PasswordManager:
    return PasswordManager()


@lru_cache
def get_token_manager() -> TokenManager:
    return TokenManager(get_settings())


@lru_cache
def get_outbox_cipher() -> OutboxCipher:
    return OutboxCipher(get_settings())


def get_auth_service(
    session: DatabaseSession,
    settings: SettingsDependency,
) -> AuthService:
    return AuthService(
        repository=AuthRepository(session),
        settings=settings,
        password_manager=get_password_manager(),
        token_manager=get_token_manager(),
        outbox_cipher=get_outbox_cipher(),
    )


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
BearerToken = Annotated[str, Depends(oauth2_scheme)]
PermissionDependency = Callable[..., Coroutine[Any, Any, CurrentPrincipal]]


def require_business_selection() -> Callable[..., Coroutine[Any, Any, SelectionPrincipal]]:
    async def dependency(
        token: BearerToken,
        session: DatabaseSession,
        settings: SettingsDependency,
    ) -> SelectionPrincipal:
        try:
            claims = TokenManager(settings).decode_access_token(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        device_session = await AuthRepository(session).get_device_session(claims.session_id)
        now = datetime.now(UTC)
        expires_at = device_session.expires_at if device_session is not None else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            claims.business_id is not None
            or device_session is None
            or device_session.user_id != claims.user_id
            or device_session.business_id is not None
            or device_session.revoked_at is not None
            or expires_at is None
            or expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi pemilihan usaha tidak aktif.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return SelectionPrincipal(user_id=claims.user_id, session_id=claims.session_id)

    return dependency


def require_permission(permission: PermissionCode | str) -> PermissionDependency:
    required_permission = permission.value if isinstance(permission, PermissionCode) else permission

    async def dependency(
        business_id: UUID,
        token: BearerToken,
        session: DatabaseSession,
        settings: SettingsDependency,
    ) -> CurrentPrincipal:
        token_manager = TokenManager(settings)
        try:
            claims = token_manager.decode_access_token(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if claims.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token tidak berlaku untuk usaha yang diminta.",
            )

        repository = AuthRepository(session)
        device_session = await repository.get_device_session(claims.session_id)
        now = datetime.now(UTC)
        expires_at = device_session.expires_at if device_session is not None else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            claims.business_id is None
            or device_session is None
            or device_session.user_id != claims.user_id
            or device_session.business_id != business_id
            or device_session.revoked_at is not None
            or expires_at is None
            or expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak aktif atau sudah dicabut.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        mentor = (
            await session.scalars(
                select(Mentor).where(
                    Mentor.user_id == claims.user_id,
                    Mentor.status == "ACTIVE",
                    Mentor.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        await set_rls_context(
            session,
            user_id=claims.user_id,
            business_id=business_id,
            actor_type="MENTOR" if mentor is not None else "BUSINESS",
            mentor_id=mentor.id if mentor is not None else None,
        )
        authorization = await repository.resolve_authorization(claims.user_id, business_id)
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ke usaha sudah tidak aktif.",
            )
        assert_permission(authorization, required_permission)
        actor_type = "BUSINESS"
        if authorization.role_code == "mentor":
            actor_type = "MENTOR"
        elif authorization.support_grant_id is not None:
            actor_type = "SUPPORT"
        await set_rls_context(
            session,
            user_id=claims.user_id,
            business_id=business_id,
            actor_type=actor_type,
            mentor_id=authorization.mentor_id,
            support_grant_id=authorization.support_grant_id,
        )
        if required_permission in SCOPED_DATA_PERMISSIONS and actor_type in {
            "MENTOR",
            "SUPPORT",
        }:
            await _record_scoped_access(
                session,
                user_id=claims.user_id,
                business_id=business_id,
                actor_type=actor_type,
                permission=required_permission,
                mentor_id=authorization.mentor_id,
                support_grant_id=authorization.support_grant_id,
            )
            await session.commit()
            await set_rls_context(
                session,
                user_id=claims.user_id,
                business_id=business_id,
                actor_type=actor_type,
                mentor_id=authorization.mentor_id,
                support_grant_id=authorization.support_grant_id,
            )
        return CurrentPrincipal(
            user_id=claims.user_id,
            session_id=claims.session_id,
            business_id=business_id,
            role=authorization.role_code,
            permissions=authorization.permissions,
            support_grant_id=authorization.support_grant_id,
        )

    return dependency


def require_token_permission(permission: PermissionCode | str) -> PermissionDependency:
    """Authorize endpoints whose tenant id is carried in the request body.

    Sync endpoints use the tenant from the signed access token and still compare it
    with ``business_id`` in their payload. This prevents a caller from selecting a
    different tenant while keeping the public routes at ``/sync/*``.
    """

    required_permission = permission.value if isinstance(permission, PermissionCode) else permission

    async def dependency(
        token: BearerToken,
        session: DatabaseSession,
        settings: SettingsDependency,
    ) -> CurrentPrincipal:
        token_manager = TokenManager(settings)
        try:
            claims = token_manager.decode_access_token(token)
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

        repository = AuthRepository(session)
        device_session = await repository.get_device_session(claims.session_id)
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

        await set_rls_context(
            session,
            user_id=claims.user_id,
            business_id=claims.business_id,
            actor_type="BUSINESS",
        )
        authorization = await repository.resolve_authorization(claims.user_id, claims.business_id)
        if authorization is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ke usaha sudah tidak aktif.",
            )
        assert_permission(authorization, required_permission)
        return CurrentPrincipal(
            user_id=claims.user_id,
            session_id=claims.session_id,
            business_id=claims.business_id,
            role=authorization.role_code,
            permissions=authorization.permissions,
            support_grant_id=authorization.support_grant_id,
        )

    return dependency


async def _record_scoped_access(
    session: DatabaseSession,
    *,
    user_id: UUID,
    business_id: UUID,
    actor_type: str,
    permission: str,
    mentor_id: UUID | None,
    support_grant_id: UUID | None,
) -> None:
    now = datetime.now(UTC)
    if session.get_bind().dialect.name == "postgresql":
        function_name = (
            "kasta_touch_mentor_access" if actor_type == "MENTOR" else "kasta_touch_support_access"
        )
        await session.execute(
            text(f"SELECT {function_name}(:business_id)"),
            {"business_id": business_id},
        )
    elif actor_type == "MENTOR" and mentor_id is not None:
        access = (
            await session.scalars(
                select(MentorBusinessAccess).where(
                    MentorBusinessAccess.mentor_id == mentor_id,
                    MentorBusinessAccess.business_id == business_id,
                    MentorBusinessAccess.status == "ACTIVE",
                )
            )
        ).one_or_none()
        if access is not None:
            access.last_accessed_at = now
    elif support_grant_id is not None:
        grant = await session.get(SupportAccessGrant, support_grant_id)
        if grant is not None:
            grant.last_accessed_at = now
    session.add(
        AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=user_id,
            action=(
                "MENTOR_DATA_ACCESSED" if actor_type == "MENTOR" else "ADMIN_SUPPORT_DATA_ACCESSED"
            ),
            entity_type="DATA_ACCESS",
            entity_id=business_id,
            after_data={
                "permission": permission,
                "support_grant_id": (str(support_grant_id) if support_grant_id else None),
            },
            created_at=now,
        )
    )
