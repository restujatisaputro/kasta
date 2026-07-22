from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import CurrentPrincipal
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.mentors.constants import MentorAccessScope, MentorAccessStatus
from kasta_api.modules.mentors.models import Mentor, MentorBusinessAccess
from kasta_api.modules.mentors.repository import MentorRepository
from kasta_api.modules.mentors.schemas import (
    MentorAccessDecision,
    MentorAccessHistoryItem,
    MentorAccessRequestCreate,
    MentorAccessResponse,
    MentorAccessRevoke,
)
from kasta_api.modules.obligations.models import Notification

MAX_GRANT_DURATION = timedelta(days=366)


class MentorAccessService:
    def __init__(self, repository: MentorRepository) -> None:
        self.repository = repository

    async def request_access(
        self,
        mentor: Mentor,
        payload: MentorAccessRequestCreate,
        *,
        request_id: str | None,
    ) -> MentorAccessResponse:
        business = await self.repository.business(payload.business_id)
        if business is None:
            raise HTTPException(status_code=404, detail="UMKM tidak ditemukan.")
        existing = await self.repository.open_access(mentor.id, business.id)
        now = utc_now()
        if existing is not None and self._is_expired(existing, now):
            existing.status = MentorAccessStatus.EXPIRED.value
            existing.revision_no += 1
            await self.repository.flush()
            existing = None
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Permintaan atau izin aktif untuk UMKM ini sudah ada.",
            )

        access = MentorBusinessAccess(
            id=uuid4(),
            mentor_id=mentor.id,
            business_id=business.id,
            role_id=role_id(RoleCode.MENTOR),
            requested_by_user_id=mentor.user_id,
            scope=self._scope_values(payload.requested_scope),
            status=MentorAccessStatus.REQUESTED.value,
            request_message=payload.message,
            requested_at=now,
        )
        # RLS untuk audit/notifikasi memverifikasi baris permintaan ini. Flush lebih
        # dahulu agar baris terlihat di transaksi database yang sama.
        self.repository.add(access)
        await self.repository.flush()
        owner_user_id = await self.repository.owner_user_id(business.id)
        records: list[object] = [
            self._audit(
                business.id,
                mentor.user_id,
                "MENTOR_ACCESS_REQUESTED",
                access.id,
                request_id=request_id,
                after=self._snapshot(access),
            ),
            Notification(
                id=uuid4(),
                business_id=business.id,
                user_id=owner_user_id,
                notification_type="MENTOR_ACCESS_REQUEST",
                title="Permintaan akses dari pembina",
                message=(
                    "Seorang pembina meminta akses. Periksa dan pilih data yang boleh dilihat."
                ),
                entity_type="MENTOR_ACCESS",
                entity_id=access.id,
                scheduled_for=date.today(),
                payload={"mentor_id": str(mentor.id), "scope": access.scope},
                action_path="/akses-pembina",
            ),
        ]
        await self._save(access, records)
        return MentorAccessResponse.model_validate(access)

    async def mentor_requests(self, mentor: Mentor) -> list[MentorAccessResponse]:
        items = await self.repository.mentor_access_requests(mentor.id)
        await self._expire(items)
        return [MentorAccessResponse.model_validate(item) for item in items]

    async def business_accesses(
        self, principal: CurrentPrincipal, business_id: UUID
    ) -> list[MentorAccessResponse]:
        self._assert_owner(principal, business_id)
        items = await self.repository.business_access_history(business_id)
        await self._expire(items)
        return [MentorAccessResponse.model_validate(item) for item in items]

    async def decide(
        self,
        principal: CurrentPrincipal,
        business_id: UUID,
        access_id: UUID,
        payload: MentorAccessDecision,
        *,
        request_id: str | None,
    ) -> MentorAccessResponse:
        self._assert_owner(principal, business_id)
        access = await self.repository.access_by_id(business_id, access_id, lock=True)
        if access is None:
            raise HTTPException(status_code=404, detail="Permintaan akses tidak ditemukan.")
        if access.status != MentorAccessStatus.REQUESTED.value:
            raise HTTPException(status_code=409, detail="Permintaan ini sudah diproses.")

        before = self._snapshot(access)
        now = utc_now()
        if payload.decision == "APPROVE":
            if not payload.scope:
                raise HTTPException(status_code=422, detail="Pilih minimal satu jenis akses.")
            if payload.expires_at is None:
                raise HTTPException(status_code=422, detail="Tentukan masa berlaku izin.")
            expires_at = self._aware(payload.expires_at)
            if expires_at <= now or expires_at > now + MAX_GRANT_DURATION:
                raise HTTPException(
                    status_code=422,
                    detail="Masa berlaku harus di masa depan dan maksimal 366 hari.",
                )
            access.status = MentorAccessStatus.ACTIVE.value
            access.scope = self._scope_values(payload.scope)
            access.granted_by_user_id = principal.user_id
            access.granted_at = now
            access.expires_at = expires_at
            action = "MENTOR_ACCESS_APPROVED"
            title = "Akses pembina disetujui"
            message = "Akses pembina telah aktif sesuai pilihan pemilik UMKM."
        else:
            if not payload.reason:
                raise HTTPException(status_code=422, detail="Alasan penolakan wajib diisi.")
            access.status = MentorAccessStatus.REJECTED.value
            access.rejection_reason = payload.reason
            access.granted_by_user_id = principal.user_id
            action = "MENTOR_ACCESS_REJECTED"
            title = "Permintaan akses ditolak"
            message = "Pemilik UMKM menolak permintaan akses pembina."
        access.revision_no += 1
        records: list[object] = [
            self._audit(
                business_id,
                principal.user_id,
                action,
                access.id,
                request_id=request_id,
                before=before,
                after=self._snapshot(access),
                reason=payload.reason,
            ),
            self._mentor_notification(access, title, message),
        ]
        await self._save(access, records)
        return MentorAccessResponse.model_validate(access)

    async def revoke(
        self,
        principal: CurrentPrincipal,
        business_id: UUID,
        access_id: UUID,
        payload: MentorAccessRevoke,
        *,
        request_id: str | None,
    ) -> MentorAccessResponse:
        self._assert_owner(principal, business_id)
        access = await self.repository.access_by_id(business_id, access_id, lock=True)
        if access is None:
            raise HTTPException(status_code=404, detail="Izin pembina tidak ditemukan.")
        if access.status != MentorAccessStatus.ACTIVE.value:
            raise HTTPException(status_code=409, detail="Hanya izin aktif yang dapat dicabut.")
        before = self._snapshot(access)
        access.status = MentorAccessStatus.REVOKED.value
        access.revoked_at = utc_now()
        access.revocation_reason = payload.reason
        access.revision_no += 1
        records: list[object] = [
            self._audit(
                business_id,
                principal.user_id,
                "MENTOR_ACCESS_REVOKED",
                access.id,
                request_id=request_id,
                before=before,
                after=self._snapshot(access),
                reason=payload.reason,
            ),
            self._mentor_notification(
                access,
                "Akses pembina dicabut",
                "Pemilik UMKM telah mencabut akses Anda.",
            ),
        ]
        await self._save(access, records)
        return MentorAccessResponse.model_validate(access)

    async def access_history(
        self, principal: CurrentPrincipal, business_id: UUID
    ) -> list[MentorAccessHistoryItem]:
        self._assert_owner(principal, business_id)
        result: list[MentorAccessHistoryItem] = []
        for audit in await self.repository.access_audits(business_id):
            data = audit.after_data or audit.before_data or {}
            result.append(
                MentorAccessHistoryItem(
                    id=audit.id,
                    action=audit.action,
                    mentor_id=self._optional_uuid(data.get("mentor_id")),
                    actor_user_id=audit.actor_user_id,
                    scope=self._history_scope(data.get("scope")),
                    reason=audit.reason,
                    accessed_at=audit.created_at,
                )
            )
        return result

    async def _expire(self, items: list[MentorBusinessAccess]) -> None:
        now = utc_now()
        changed = False
        for item in items:
            if self._is_expired(item, now):
                item.status = MentorAccessStatus.EXPIRED.value
                item.revision_no += 1
                changed = True
        if changed:
            await self.repository.commit()

    @staticmethod
    def _is_expired(access: MentorBusinessAccess, now: datetime) -> bool:
        return (
            access.status == MentorAccessStatus.ACTIVE.value
            and access.expires_at is not None
            and MentorAccessService._aware(access.expires_at) <= now
        )

    @staticmethod
    def _assert_owner(principal: CurrentPrincipal, business_id: UUID) -> None:
        if principal.business_id != business_id or principal.role != RoleCode.BUSINESS_OWNER.value:
            raise HTTPException(
                status_code=403,
                detail="Hanya pemilik UMKM yang dapat mengatur izin pembina.",
            )

    async def _save(self, instance: object, records: list[object]) -> None:
        self.repository.add_all(records)
        try:
            await self.repository.commit()
            await self.repository.refresh(instance)
        except Exception:
            await self.repository.rollback()
            raise

    def _mentor_notification(
        self, access: MentorBusinessAccess, title: str, message: str
    ) -> Notification:
        return Notification(
            id=uuid4(),
            business_id=access.business_id,
            user_id=access.requested_by_user_id,
            notification_type="MENTOR_ACCESS_CHANGED",
            title=title,
            message=message,
            entity_type=f"MENTOR_ACCESS_{access.status}",
            entity_id=access.id,
            scheduled_for=date.today(),
            payload={"status": access.status, "scope": access.scope},
        )

    @staticmethod
    def _audit(
        business_id: UUID,
        actor_user_id: UUID,
        action: str,
        entity_id: UUID,
        *,
        request_id: str | None,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type="MENTOR_ACCESS",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )

    @staticmethod
    def _snapshot(access: MentorBusinessAccess) -> dict[str, object]:
        return {
            "mentor_id": str(access.mentor_id),
            "status": access.status,
            "scope": list(access.scope),
            "expires_at": access.expires_at.isoformat() if access.expires_at else None,
            "revision_no": access.revision_no,
        }

    @staticmethod
    def _scope_values(scopes: set[MentorAccessScope]) -> list[str]:
        return sorted(scope.value for scope in scopes)

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _optional_uuid(value: object) -> UUID | None:
        try:
            return UUID(str(value)) if value else None
        except ValueError:
            return None

    @staticmethod
    def _history_scope(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]
