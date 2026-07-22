from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.businesses.models import (
    Business,
    BusinessCategory,
    BusinessPaymentMethod,
    BusinessProfile,
    OnboardingCompletion,
)


class BusinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(self) -> list[BusinessCategory]:
        result = await self.session.scalars(
            select(BusinessCategory)
            .where(BusinessCategory.is_active.is_(True))
            .order_by(BusinessCategory.display_order, BusinessCategory.name)
        )
        return list(result.all())

    async def get_category(self, category_id: UUID) -> BusinessCategory | None:
        return await self.session.get(BusinessCategory, category_id)

    async def get_completion_for_user(self, user_id: UUID) -> OnboardingCompletion | None:
        return (
            await self.session.scalars(
                select(OnboardingCompletion).where(OnboardingCompletion.user_id == user_id)
            )
        ).one_or_none()

    async def get_business(self, business_id: UUID) -> Business | None:
        return await self.session.get(Business, business_id)

    async def get_profile(self, business_id: UUID) -> BusinessProfile | None:
        return (
            await self.session.scalars(
                select(BusinessProfile).where(
                    BusinessProfile.business_id == business_id,
                    BusinessProfile.deleted_at.is_(None),
                )
            )
        ).one_or_none()

    async def get_payment_methods(self, business_id: UUID) -> list[BusinessPaymentMethod]:
        methods = await self.session.scalars(
            select(BusinessPaymentMethod)
            .where(
                BusinessPaymentMethod.business_id == business_id,
                BusinessPaymentMethod.is_active.is_(True),
                BusinessPaymentMethod.deleted_at.is_(None),
            )
            .order_by(BusinessPaymentMethod.created_at)
        )
        return list(methods.all())

    async def get_completion_for_business(self, business_id: UUID) -> OnboardingCompletion | None:
        return (
            await self.session.scalars(
                select(OnboardingCompletion).where(OnboardingCompletion.business_id == business_id)
            )
        ).one_or_none()

    def add_all(self, instances: list[object]) -> None:
        self.session.add_all(instances)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
