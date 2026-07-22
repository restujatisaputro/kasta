from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_rls_context(
    session: AsyncSession,
    *,
    user_id: UUID,
    business_id: UUID | None,
    actor_type: str,
    mentor_id: UUID | None = None,
    support_grant_id: UUID | None = None,
) -> None:
    """Set transaction-local PostgreSQL context consumed by KASTA RLS policies."""

    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    values = {
        "app.user_id": str(user_id),
        "app.business_id": str(business_id) if business_id else "",
        "app.actor_type": actor_type,
        "app.mentor_id": str(mentor_id) if mentor_id else "",
        "app.support_grant_id": str(support_grant_id) if support_grant_id else "",
    }
    for setting_name, value in values.items():
        await session.execute(
            text("SELECT set_config(:setting_name, :value, true)"),
            {"setting_name": setting_name, "value": value},
        )
