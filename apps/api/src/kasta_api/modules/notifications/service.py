from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.notifications.constants import (
    CATEGORY_LABELS,
    DEFAULT_ACTION_PATHS,
    NotificationCategory,
)
from kasta_api.modules.notifications.models import NotificationPreference, PushSubscription
from kasta_api.modules.notifications.repository import NotificationRepository
from kasta_api.modules.notifications.schemas import (
    NotificationEvaluationResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    PushSubscriptionRequest,
)
from kasta_api.modules.obligations.models import Notification


@dataclass(frozen=True, slots=True)
class Candidate:
    category: NotificationCategory
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    payload: dict[str, object]


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    async def preferences(
        self, business_id: UUID, user_id: UUID
    ) -> list[NotificationPreferenceResponse]:
        rows = await self._ensure_preferences(business_id, user_id)
        return [self._preference_response(row) for row in sorted(rows, key=lambda x: x.category)]

    async def update_preferences(
        self,
        business_id: UUID,
        user_id: UUID,
        payload: NotificationPreferencesUpdate,
        *,
        request_id: str | None,
    ) -> list[NotificationPreferenceResponse]:
        rows = {row.category: row for row in await self._ensure_preferences(business_id, user_id)}
        before: dict[str, object] = {}
        after: dict[str, object] = {}
        for item in payload.items:
            try:
                ZoneInfo(item.timezone)
            except ZoneInfoNotFoundError as exc:
                raise HTTPException(status_code=422, detail="Zona waktu tidak dikenali.") from exc
            row = rows[item.category.value]
            before[item.category.value] = self._preference_snapshot(row)
            row.enabled = item.enabled
            row.local_enabled = item.local_enabled
            row.push_enabled = item.push_enabled
            row.email_enabled = item.email_enabled
            row.reminder_time = item.reminder_time
            row.quiet_hours_start = item.quiet_hours_start
            row.quiet_hours_end = item.quiet_hours_end
            row.timezone = item.timezone
            after[item.category.value] = self._preference_snapshot(row)
        self.repository.add(
            self._audit(
                business_id,
                user_id,
                "NOTIFICATION_PREFERENCES_UPDATED",
                user_id,
                before=before,
                after=after,
                request_id=request_id,
            )
        )
        await self._commit()
        return await self.preferences(business_id, user_id)

    async def list_notifications(
        self,
        business_id: UUID,
        user_id: UUID,
        *,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> NotificationListResponse:
        items, total, unread = await self.repository.notifications(
            business_id, user_id, unread_only=unread_only, limit=limit, offset=offset
        )
        return NotificationListResponse(
            items=[NotificationResponse.model_validate(item) for item in items],
            unread_count=unread,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def mark_read(
        self, business_id: UUID, user_id: UUID, notification_id: UUID
    ) -> NotificationResponse:
        item = await self.repository.notification(business_id, user_id, notification_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan.")
        if item.read_at is None:
            item.read_at = utc_now()
            await self._commit()
        return NotificationResponse.model_validate(item)

    async def mark_all_read(self, business_id: UUID, user_id: UUID) -> int:
        count = await self.repository.mark_all_read(business_id, user_id, utc_now())
        await self._commit()
        return count

    async def register_push(
        self,
        business_id: UUID,
        user_id: UUID,
        session_id: UUID,
        payload: PushSubscriptionRequest,
    ) -> None:
        row = await self.repository.subscription_for_session(session_id)
        if row is None:
            row = PushSubscription(
                id=uuid4(),
                business_id=business_id,
                user_id=user_id,
                device_session_id=session_id,
                platform=payload.platform,
                token=payload.token,
                is_active=True,
                last_seen_at=utc_now(),
            )
            self.repository.add(row)
        else:
            row.token = payload.token
            row.platform = payload.platform
            row.is_active = True
            row.last_seen_at = utc_now()
        await self._commit()

    async def evaluate(
        self, business_id: UUID, actor_user_id: UUID, as_of: date
    ) -> NotificationEvaluationResponse:
        candidates = await self._candidates(business_id, as_of)
        generated: list[Notification] = []
        skipped = 0
        preferences = {
            row.category: row for row in await self._ensure_preferences(business_id, actor_user_id)
        }
        for candidate in candidates:
            preference = preferences[candidate.category.value]
            if not preference.enabled or await self.repository.exists(
                business_id,
                actor_user_id,
                candidate.category.value,
                candidate.entity_type,
                candidate.entity_id,
                as_of,
            ):
                skipped += 1
                continue
            generated.append(
                Notification(
                    id=uuid4(),
                    business_id=business_id,
                    user_id=actor_user_id,
                    notification_type=candidate.category.value,
                    title=candidate.title,
                    message=candidate.message[:500],
                    entity_type=candidate.entity_type,
                    entity_id=candidate.entity_id,
                    scheduled_for=as_of,
                    payload={
                        **candidate.payload,
                        "local_enabled": preference.local_enabled,
                        "push_enabled": preference.push_enabled,
                        "email_enabled": preference.email_enabled,
                    },
                    action_path=DEFAULT_ACTION_PATHS[candidate.category],
                    available_at=self.next_allowed_at(preference, as_of),
                )
            )
        if generated:
            self.repository.add_all(list(generated))
            self.repository.add(
                self._audit(
                    business_id,
                    actor_user_id,
                    "NOTIFICATIONS_GENERATED",
                    business_id,
                    after={"count": len(generated), "as_of": as_of.isoformat()},
                )
            )
        await self._commit()
        return NotificationEvaluationResponse(generated_count=len(generated), skipped_count=skipped)

    async def _ensure_preferences(
        self, business_id: UUID, user_id: UUID
    ) -> list[NotificationPreference]:
        rows = await self.repository.preferences(business_id, user_id)
        existing = {row.category for row in rows}
        missing = [category for category in NotificationCategory if category.value not in existing]
        if missing:
            created = [
                NotificationPreference(
                    id=uuid4(),
                    business_id=business_id,
                    user_id=user_id,
                    category=category.value,
                )
                for category in missing
            ]
            self.repository.add_all(list(created))
            await self._commit()
            rows.extend(created)
        return rows

    async def _candidates(self, business_id: UUID, as_of: date) -> list[Candidate]:
        items: list[Candidate] = []
        if not await self.repository.has_transaction(business_id, as_of):
            items.append(
                Candidate(
                    NotificationCategory.NO_TRANSACTION_TODAY,
                    "Belum ada catatan hari ini",
                    "Catat uang masuk atau uang keluar hari ini agar laporan tetap lengkap.",
                    "BUSINESS",
                    business_id,
                    {},
                )
            )
        for payable in await self.repository.due_payables(business_id, as_of):
            days = (payable.due_date - as_of).days
            items.append(
                Candidate(
                    NotificationCategory.PAYABLE_DUE_SOON,
                    "Utang perlu diperhatikan",
                    self._due_message("Utang", days),
                    "PAYABLE",
                    payable.id,
                    {
                        "due_date": payable.due_date.isoformat(),
                        "remaining_amount": str(payable.remaining_amount),
                    },
                )
            )
        for receivable in await self.repository.due_receivables(business_id, as_of):
            days = (receivable.due_date - as_of).days
            items.append(
                Candidate(
                    NotificationCategory.RECEIVABLE_DUE_SOON,
                    "Piutang perlu ditagih",
                    self._due_message("Piutang", days),
                    "RECEIVABLE",
                    receivable.id,
                    {
                        "due_date": receivable.due_date.isoformat(),
                        "remaining_amount": str(receivable.remaining_amount),
                    },
                )
            )
        for product in await self.repository.low_stock(business_id):
            items.append(
                Candidate(
                    NotificationCategory.LOW_STOCK,
                    "Stok menipis",
                    f"Stok {product.name} tersisa {product.current_stock} {product.unit}.",
                    "PRODUCT",
                    product.id,
                    {
                        "current_stock": str(product.current_stock),
                        "minimum_stock": str(product.minimum_stock),
                    },
                )
            )
        for receipt in await self.repository.receipts_needing_review(business_id):
            items.append(
                Candidate(
                    NotificationCategory.OCR_NEEDS_REVIEW,
                    "Hasil foto nota perlu diperiksa",
                    "Ada hasil pembacaan nota yang perlu Anda periksa sebelum menjadi transaksi.",
                    "RECEIPT",
                    receipt.id,
                    {},
                )
            )
        if await self.repository.has_sync_failure(business_id):
            items.append(
                Candidate(
                    NotificationCategory.SYNC_FAILED,
                    "Sinkronisasi belum berhasil",
                    "Sebagian data perangkat belum terkirim. Buka status sinkronisasi "
                    "untuk mencoba lagi.",
                    "BUSINESS",
                    business_id,
                    {},
                )
            )
        if as_of.day == 1:
            month = (as_of.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            items.append(
                Candidate(
                    NotificationCategory.MONTHLY_REPORT_AVAILABLE,
                    "Laporan bulanan tersedia",
                    "Ringkasan keuangan bulan lalu sudah dapat dilihat.",
                    "BUSINESS",
                    business_id,
                    {"month": month},
                )
            )
        return items

    @staticmethod
    def next_allowed_at(preference: NotificationPreference, on_date: date) -> datetime:
        zone = ZoneInfo(preference.timezone)
        candidate = datetime.combine(on_date, preference.reminder_time, zone)
        now = datetime.now(zone)
        if candidate < now:
            candidate = now
        start = preference.quiet_hours_start
        end = preference.quiet_hours_end
        if start is None or end is None:
            return candidate.astimezone(UTC)
        current = candidate.timetz().replace(tzinfo=None)
        in_quiet = start <= current < end if start < end else current >= start or current < end
        if in_quiet:
            after_midnight = start > end and current >= start
            end_date = candidate.date() + (timedelta(days=1) if after_midnight else timedelta())
            candidate = datetime.combine(end_date, end, zone)
        return candidate.astimezone(UTC)

    @staticmethod
    def _due_message(subject: str, days: int) -> str:
        if days < 0:
            return f"{subject} sudah terlambat {abs(days)} hari."
        if days == 0:
            return f"{subject} jatuh tempo hari ini."
        return f"{subject} jatuh tempo dalam {days} hari."

    @staticmethod
    def _preference_response(row: NotificationPreference) -> NotificationPreferenceResponse:
        return NotificationPreferenceResponse(
            category=NotificationCategory(row.category),
            label=CATEGORY_LABELS[NotificationCategory(row.category)],
            enabled=row.enabled,
            local_enabled=row.local_enabled,
            push_enabled=row.push_enabled,
            email_enabled=row.email_enabled,
            reminder_time=row.reminder_time,
            quiet_hours_start=row.quiet_hours_start,
            quiet_hours_end=row.quiet_hours_end,
            timezone=row.timezone,
        )

    @staticmethod
    def _preference_snapshot(row: NotificationPreference) -> dict[str, object]:
        return {
            "enabled": row.enabled,
            "local_enabled": row.local_enabled,
            "push_enabled": row.push_enabled,
            "email_enabled": row.email_enabled,
            "reminder_time": row.reminder_time.isoformat(),
            "quiet_hours_start": (
                row.quiet_hours_start.isoformat() if row.quiet_hours_start else None
            ),
            "quiet_hours_end": row.quiet_hours_end.isoformat() if row.quiet_hours_end else None,
            "timezone": row.timezone,
        }

    async def _commit(self) -> None:
        try:
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise

    @staticmethod
    def _audit(
        business_id: UUID,
        actor_user_id: UUID,
        action: str,
        entity_id: UUID,
        *,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type="NOTIFICATION",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            request_id=request_id,
            created_at=utc_now(),
        )
