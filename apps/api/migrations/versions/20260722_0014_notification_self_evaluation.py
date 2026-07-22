"""Allow business staff to evaluate their own notification reminders.

Revision ID: 20260722_0014
Revises: 20260722_0013
Create Date: 2026-07-22
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0014"
down_revision: str | None = "20260722_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
ROLE_CODE = "business_staff"
PERMISSION_CODE = "notification.generate"


def _identifier(kind: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{kind}:{code}")


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "INSERT INTO role_permissions "
            "(id, role_id, permission_id, created_at, updated_at) "
            "VALUES (:id, :role_id, :permission_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        ),
        {
            "id": uuid5(
                AUTH_NAMESPACE,
                f"role-permission:{ROLE_CODE}:{PERMISSION_CODE}",
            ),
            "role_id": _identifier("role", ROLE_CODE),
            "permission_id": _identifier("permission", PERMISSION_CODE),
        },
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "DELETE FROM role_permissions "
            "WHERE role_id = :role_id AND permission_id = :permission_id"
        ),
        {
            "role_id": _identifier("role", ROLE_CODE),
            "permission_id": _identifier("permission", PERMISSION_CODE),
        },
    )
