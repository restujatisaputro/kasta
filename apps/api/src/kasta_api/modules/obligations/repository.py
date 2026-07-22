from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.auth.models import Role
from kasta_api.modules.businesses.models import BusinessMember
from kasta_api.modules.obligations.models import (
    Customer,
    Notification,
    Payable,
    PayablePayment,
    Receivable,
    ReceivablePayment,
    Supplier,
)


class ObligationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def add_all(self, instances: list[object]) -> None:
        self.session.add_all(instances)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, instance: object) -> None:
        await self.session.refresh(instance)

    async def customer(self, business_id: UUID, customer_id: UUID) -> Customer | None:
        return (
            await self.session.scalars(
                select(Customer).where(
                    Customer.id == customer_id,
                    Customer.business_id == business_id,
                    Customer.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def supplier(self, business_id: UUID, supplier_id: UUID) -> Supplier | None:
        return (
            await self.session.scalars(
                select(Supplier).where(
                    Supplier.id == supplier_id,
                    Supplier.business_id == business_id,
                    Supplier.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def party_by_name(
        self, business_id: UUID, name: str, *, receivable: bool
    ) -> Customer | Supplier | None:
        if receivable:
            return (
                await self.session.scalars(
                    select(Customer).where(
                        Customer.business_id == business_id,
                        func.lower(Customer.name) == name.strip().lower(),
                        Customer.deleted_at.is_(None),
                    )
                )
            ).one_or_none()
        return (
            await self.session.scalars(
                select(Supplier).where(
                    Supplier.business_id == business_id,
                    func.lower(Supplier.name) == name.strip().lower(),
                    Supplier.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def list_parties(
        self, business_id: UUID, *, receivable: bool
    ) -> list[Customer] | list[Supplier]:
        if receivable:
            return list(
                (
                    await self.session.scalars(
                        select(Customer)
                        .where(
                            Customer.business_id == business_id,
                            Customer.deleted_at.is_(None),
                        )
                        .order_by(Customer.name)
                    )
                ).all()
            )
        return list(
            (
                await self.session.scalars(
                    select(Supplier)
                    .where(
                        Supplier.business_id == business_id,
                        Supplier.deleted_at.is_(None),
                    )
                    .order_by(Supplier.name)
                )
            ).all()
        )

    async def receivable(
        self, business_id: UUID, receivable_id: UUID, *, for_update: bool = False
    ) -> Receivable | None:
        statement = select(Receivable).where(
            Receivable.id == receivable_id, Receivable.business_id == business_id
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def payable(
        self, business_id: UUID, payable_id: UUID, *, for_update: bool = False
    ) -> Payable | None:
        statement = select(Payable).where(
            Payable.id == payable_id, Payable.business_id == business_id
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def receivables(self, business_id: UUID) -> list[Receivable]:
        return list(
            (
                await self.session.scalars(
                    select(Receivable)
                    .where(Receivable.business_id == business_id)
                    .order_by(Receivable.due_date, Receivable.created_at.desc())
                )
            ).all()
        )

    async def payables(self, business_id: UUID) -> list[Payable]:
        return list(
            (
                await self.session.scalars(
                    select(Payable)
                    .where(Payable.business_id == business_id)
                    .order_by(Payable.due_date, Payable.created_at.desc())
                )
            ).all()
        )

    async def receivable_payments(
        self, business_id: UUID, receivable_id: UUID
    ) -> list[ReceivablePayment]:
        return list(
            (
                await self.session.scalars(
                    select(ReceivablePayment)
                    .where(
                        ReceivablePayment.business_id == business_id,
                        ReceivablePayment.receivable_id == receivable_id,
                    )
                    .order_by(ReceivablePayment.payment_date, ReceivablePayment.created_at)
                )
            ).all()
        )

    async def payable_payments(self, business_id: UUID, payable_id: UUID) -> list[PayablePayment]:
        return list(
            (
                await self.session.scalars(
                    select(PayablePayment)
                    .where(
                        PayablePayment.business_id == business_id,
                        PayablePayment.payable_id == payable_id,
                    )
                    .order_by(PayablePayment.payment_date, PayablePayment.created_at)
                )
            ).all()
        )

    async def notification_exists(
        self, business_id: UUID, entity_type: str, entity_id: UUID, scheduled_for: date
    ) -> bool:
        count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.business_id == business_id,
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.scheduled_for == scheduled_for,
            )
        )
        return bool(count)

    async def owner_user_id(self, business_id: UUID) -> UUID | None:
        return (
            await self.session.scalars(
                select(BusinessMember.user_id)
                .join(Role, Role.id == BusinessMember.role_id)
                .where(
                    BusinessMember.business_id == business_id,
                    BusinessMember.status == "ACTIVE",
                    BusinessMember.deleted_at.is_(None),
                    Role.code == "business_owner",
                )
                .limit(1)
            )
        ).one_or_none()

    async def notifications(self, business_id: UUID, unread_only: bool) -> list[Notification]:
        filters = [Notification.business_id == business_id]
        if unread_only:
            filters.append(Notification.read_at.is_(None))
        return list(
            (
                await self.session.scalars(
                    select(Notification)
                    .where(*filters)
                    .order_by(Notification.created_at.desc())
                    .limit(100)
                )
            ).all()
        )
