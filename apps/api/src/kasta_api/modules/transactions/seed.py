from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.accounting.repository import AccountingRepository


async def seed_transaction_reference_data(session: AsyncSession, business_id: UUID) -> None:
    """Ensure the system income and expense categories exist for one business."""
    await AccountingRepository(session).ensure_account_templates(business_id)
    await session.commit()
