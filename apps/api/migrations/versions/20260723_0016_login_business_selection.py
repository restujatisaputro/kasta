"""Allow login sessions to select a business after authentication.

Revision ID: 20260723_0016
Revises: 20260722_0015
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260723_0016"
down_revision: str | None = "20260722_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("device_sessions", "business_id", nullable=True)


def downgrade() -> None:
    op.alter_column("device_sessions", "business_id", nullable=False)
