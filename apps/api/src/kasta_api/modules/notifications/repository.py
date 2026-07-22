from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.models import FinancialTransaction
from kasta_api.modules.businesses.models import BusinessMember
from kasta_api.modules.inventory.models import Product
from kasta_api.modules.notifications.models import NotificationPreference, PushSubscription
from kasta_api.modules.obligations.models import Notification, Payable, Receivable
from kasta_api.modules.receipts.models import Receipt
from kasta_api.modules.sync.models import DeviceSyncState


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def add_all(self, instances: list[object]) -> None:
        self.session.add_all(instances)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def preferences(self, business_id: UUID, user_id: UUID) -> list[NotificationPreference]:
        return list(
            (
                await self.session.scalars(
                    select(NotificationPreference)
                    .where(
                        NotificationPreference.business_id == business_id,
                        NotificationPreference.user_id == user_id,
                    )
                    .order_by(NotificationPreference.category)
                )
            ).all()
        )

    async def notification(
        self, business_id: UUID, user_id: UUID, notification_id: UUID
    ) -> Notification | None:
        return (
            await self.session.scalars(
                select(Notification).where(
                    Notification.id == notification_id,
                    Notification.business_id == business_id,
                    Notification.user_id == user_id,
                )
            )
        ).one_or_none()

    async def notifications(
        self,
        business_id: UUID,
        user_id: UUID,
        *,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int, int]:
        filters = [
            Notification.business_id == business_id,
            Notification.user_id == user_id,
        ]
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        total = int(
            await self.session.scalar(select(func.count(Notification.id)).where(*filters)) or 0
        )
        unread = int(
            await self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.business_id == business_id,
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )
        items = list(
            (
                await self.session.scalars(
                    select(Notification)
                    .where(*filters)
                    .order_by(Notification.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        return items, total, unread

    async def mark_all_read(self, business_id: UUID, user_id: UUID, read_at: object) -> int:
        rows = list(
            (
                await self.session.scalars(
                    select(Notification).where(
                        Notification.business_id == business_id,
                        Notification.user_id == user_id,
                        Notification.read_at.is_(None),
                    )
                )
            ).all()
        )
        for row in rows:
            row.read_at = read_at  # type: ignore[assignment]
        return len(rows)

    async def recipient_ids(self, business_id: UUID) -> list[UUID]:
        return list(
            (
                await self.session.scalars(
                    select(BusinessMember.user_id).where(
                        BusinessMember.business_id == business_id,
                        BusinessMember.status == "ACTIVE",
                        BusinessMember.deleted_at.is_(None),
                    )
                )
            ).all()
        )

    async def exists(
        self,
        business_id: UUID,
        user_id: UUID,
        category: str,
        entity_type: str,
        entity_id: UUID,
        scheduled_for: date,
    ) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.business_id == business_id,
                    Notification.user_id == user_id,
                    Notification.notification_type == category,
                    Notification.entity_type == entity_type,
                    Notification.entity_id == entity_id,
                    Notification.scheduled_for == scheduled_for,
                )
            )
        )

    async def has_transaction(self, business_id: UUID, on_date: date) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count(FinancialTransaction.id)).where(
                    FinancialTransaction.business_id == business_id,
                    FinancialTransaction.transaction_date == on_date,
                    FinancialTransaction.status.in_(("POSTED", "REVERSED")),
                )
            )
        )

    async def due_payables(self, business_id: UUID, as_of: date) -> list[Payable]:
        return list(
            (
                await self.session.scalars(
                    select(Payable).where(
                        Payable.business_id == business_id,
                        Payable.status.in_(("OPEN", "PARTIALLY_PAID", "OVERDUE")),
                        Payable.reminder_enabled.is_(True),
                        Payable.due_date <= as_of + timedelta(days=7),
                    )
                )
            ).all()
        )

    async def due_receivables(self, business_id: UUID, as_of: date) -> list[Receivable]:
        return list(
            (
                await self.session.scalars(
                    select(Receivable).where(
                        Receivable.business_id == business_id,
                        Receivable.status.in_(("OPEN", "PARTIALLY_PAID", "OVERDUE")),
                        Receivable.reminder_enabled.is_(True),
                        Receivable.due_date <= as_of + timedelta(days=7),
                    )
                )
            ).all()
        )

    async def low_stock(self, business_id: UUID) -> list[Product]:
        return list(
            (
                await self.session.scalars(
                    select(Product).where(
                        Product.business_id == business_id,
                        Product.is_active.is_(True),
                        Product.deleted_at.is_(None),
                        Product.minimum_stock > 0,
                        Product.current_stock <= Product.minimum_stock,
                    )
                )
            ).all()
        )

    async def receipts_needing_review(self, business_id: UUID) -> list[Receipt]:
        return list(
            (
                await self.session.scalars(
                    select(Receipt).where(
                        Receipt.business_id == business_id,
                        Receipt.status == "NEEDS_REVIEW",
                    )
                )
            ).all()
        )

    async def has_sync_failure(self, business_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(func.count(DeviceSyncState.id)).where(
                    DeviceSyncState.business_id == business_id,
                    DeviceSyncState.last_error.is_not(None),
                )
            )
        )

    async def subscription_for_session(self, session_id: UUID) -> PushSubscription | None:
        return (
            await self.session.scalars(
                select(PushSubscription).where(PushSubscription.device_session_id == session_id)
            )
        ).one_or_none()
