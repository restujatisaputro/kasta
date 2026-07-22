from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.businesses.categories import (
    BUSINESS_CATEGORY_SEED,
    business_category_id,
)
from kasta_api.modules.businesses.models import BusinessCategory


async def seed_business_categories(session: AsyncSession) -> None:
    session.add_all(
        [
            BusinessCategory(
                id=business_category_id(code),
                code=code,
                name=name,
                business_type=business_type,
                display_order=display_order,
                is_active=True,
            )
            for code, name, business_type, display_order in BUSINESS_CATEGORY_SEED
        ]
    )
    await session.commit()
