"""Use WhatsApp as the phone authentication delivery channel."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0017"
down_revision: str | None = "20260723_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE auth_delivery_outbox SET channel = 'WHATSAPP' WHERE channel = 'SMS'")
    )
    op.drop_constraint("auth_outbox_channel", "auth_delivery_outbox", type_="check")
    op.create_check_constraint(
        "auth_outbox_channel",
        "auth_delivery_outbox",
        "channel IN ('EMAIL', 'WHATSAPP')",
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE auth_delivery_outbox SET channel = 'SMS' WHERE channel = 'WHATSAPP'")
    )
    op.drop_constraint("auth_outbox_channel", "auth_delivery_outbox", type_="check")
    op.create_check_constraint(
        "auth_outbox_channel",
        "auth_delivery_outbox",
        "channel IN ('EMAIL', 'SMS')",
    )
