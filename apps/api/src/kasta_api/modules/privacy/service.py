from __future__ import annotations

import secrets
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.repository import AuthRepository
from kasta_api.modules.auth.security import PasswordManager, utc_now
from kasta_api.modules.privacy.repository import PrivacyRepository
from kasta_api.modules.privacy.schemas import (
    AccountDeletionResponse,
    ExportedAuditEvent,
    ExportedMembership,
    ExportedSession,
    PersonalDataExportResponse,
)


class PrivacyService:
    def __init__(
        self,
        repository: PrivacyRepository,
        auth_repository: AuthRepository,
        password_manager: PasswordManager,
    ) -> None:
        self.repository = repository
        self.auth_repository = auth_repository
        self.password_manager = password_manager

    async def export_data(
        self, user_id: UUID, business_id: UUID, *, request_id: str | None
    ) -> PersonalDataExportResponse:
        user = await self.repository.get_user(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
        memberships = await self.repository.memberships(user_id)
        sessions = await self.repository.sessions(user_id)
        events = await self.repository.audit_events(user_id, business_id)
        now = utc_now()
        self.repository.add_audit(
            self._audit(
                user_id,
                business_id,
                "PERSONAL_DATA_EXPORTED",
                request_id=request_id,
            )
        )
        await self.repository.commit()
        return PersonalDataExportResponse(
            generated_at=now,
            subject_user_id=user.id,
            business_id=business_id,
            profile={
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "status": user.status,
            },
            memberships=[
                ExportedMembership(
                    business_id=business.id,
                    business_name=business.name,
                    role=role.code,
                    status=member.status,
                    joined_at=member.joined_at,
                )
                for member, business, role in memberships
            ],
            device_sessions=[
                ExportedSession(
                    id=session.id,
                    business_id=session.business_id,
                    platform=session.platform,
                    device_name=session.device_name,
                    app_version=session.app_version,
                    last_seen_at=session.last_seen_at,
                    expires_at=session.expires_at,
                    revoked_at=session.revoked_at,
                )
                for session in sessions
            ],
            audit_events=[
                ExportedAuditEvent(
                    action=event.action,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    created_at=event.created_at,
                    request_id=event.request_id,
                )
                for event in events
            ],
        )

    async def delete_account(
        self,
        user_id: UUID,
        business_id: UUID,
        current_password: str,
        *,
        reason: str | None,
        request_id: str | None,
    ) -> AccountDeletionResponse:
        user = await self.repository.get_user(user_id, lock=True)
        if user is None or not self.password_manager.verify(user.password_hash, current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password saat ini tidak sesuai.",
            )
        orphaned = await self.repository.owned_businesses_without_successor(user_id)
        if orphaned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Alihkan peran pemilik usaha kepada pengguna lain sebelum menghapus akun.",
            )
        now = utc_now()
        self.repository.add_audit(
            self._audit(
                user_id,
                business_id,
                "ACCOUNT_DELETED",
                request_id=request_id,
                reason=reason,
            )
        )
        await self.repository.flush()
        await self.auth_repository.revoke_user_sessions(user_id, now, "ACCOUNT_DELETED")
        await self.repository.deactivate_relationships(user_id, now)
        user.email = f"deleted-{user.id}@deleted.invalid"
        user.phone = None
        user.full_name = "Pengguna dihapus"
        user.password_hash = self.password_manager.hash(secrets.token_urlsafe(48))
        user.status = "SUSPENDED"
        user.failed_login_attempts = 0
        user.locked_until = None
        user.deleted_at = now
        await self.repository.commit()
        return AccountDeletionResponse(
            message="Akun telah dihapus dan data identitas telah dianonimkan.",
            deleted_at=now,
        )

    @staticmethod
    def _audit(
        user_id: UUID,
        business_id: UUID,
        action: str,
        *,
        request_id: str | None,
        reason: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=user_id,
            action=action,
            entity_type="USER",
            entity_id=user_id,
            after_data={"privacy_action": action},
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )
