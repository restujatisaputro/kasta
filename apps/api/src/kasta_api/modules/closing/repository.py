from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.models import FinancialTransaction
from kasta_api.modules.businesses.models import BusinessProfile
from kasta_api.modules.closing.models import PeriodClosing


class ClosingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, instance: object) -> None:
        self.session.add(instance)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def get_closing_frequency(self, business_id: UUID) -> str:
        value = await self.session.scalar(
            select(BusinessProfile.closing_frequency).where(
                BusinessProfile.business_id == business_id
            )
        )
        return value or "MONTHLY"

    async def latest_closing(self, business_id: UUID) -> PeriodClosing | None:
        return await self.session.scalar(
            select(PeriodClosing)
            .where(PeriodClosing.business_id == business_id)
            .order_by(PeriodClosing.period_end.desc())
            .limit(1)
        )

    async def earliest_transaction_date(self, business_id: UUID) -> date | None:
        return await self.session.scalar(
            select(func.min(FinancialTransaction.transaction_date)).where(
                FinancialTransaction.business_id == business_id
            )
        )

    async def list_closings(
        self, business_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[PeriodClosing], int]:
        rows = list(
            (
                await self.session.scalars(
                    select(PeriodClosing)
                    .where(PeriodClosing.business_id == business_id)
                    .order_by(PeriodClosing.period_end.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        )
        total = await self.session.scalar(
            select(func.count()).select_from(PeriodClosing).where(
                PeriodClosing.business_id == business_id
            )
        )
        return rows, total or 0
