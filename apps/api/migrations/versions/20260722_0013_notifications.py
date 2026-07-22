"""Add recipient notification preferences, deep links, and device push subscriptions.

Revision ID: 20260722_0013
Revises: 20260722_0012
Create Date: 2026-07-22
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0013"
down_revision: str | None = "20260722_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
PERMISSIONS = {
    "notification.read": (
        "business_owner",
        "business_staff",
        "mentor",
        "organization_admin",
        "super_admin",
    ),
    "notification.preference.manage": (
        "business_owner",
        "business_staff",
        "mentor",
        "organization_admin",
        "super_admin",
    ),
    "notification.generate": ("business_owner", "super_admin"),
}


def _identifier(kind: str, code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"{kind}:{code}")


def upgrade() -> None:
    op.add_column("notifications", sa.Column("action_path", sa.String(500)))
    op.add_column("notifications", sa.Column("available_at", sa.DateTime(timezone=True)))
    op.create_index("ix_notifications_available_at", "notifications", ["available_at"])
    op.drop_constraint("uq_notifications_entity_schedule", "notifications", type_="unique")
    op.create_unique_constraint(
        "uq_notifications_recipient_entity_schedule",
        "notifications",
        [
            "business_id",
            "user_id",
            "notification_type",
            "entity_type",
            "entity_id",
            "scheduled_for",
        ],
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("local_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reminder_time", sa.Time(), server_default=sa.text("'18:00:00'"), nullable=False),
        sa.Column("quiet_hours_start", sa.Time()),
        sa.Column("quiet_hours_end", sa.Time()),
        sa.Column("timezone", sa.String(64), server_default="Asia/Jakarta", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "business_id", "user_id", "category", name="uq_notification_preferences_recipient"
        ),
    )
    op.create_index(
        "ix_notification_preferences_business_id",
        "notification_preferences",
        ["business_id"],
    )
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_index(
        "ix_notification_preferences_recipient",
        "notification_preferences",
        ["business_id", "user_id"],
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_session_id",
            sa.Uuid(),
            sa.ForeignKey("device_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("platform IN ('ANDROID', 'WEB')", name="push_subscription_platform"),
        sa.UniqueConstraint("device_session_id", name="uq_push_subscriptions_device_session"),
        sa.UniqueConstraint("token", name="uq_push_subscriptions_token"),
    )
    op.create_index("ix_push_subscriptions_business_id", "push_subscriptions", ["business_id"])
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index(
        "ix_push_subscriptions_device_session_id",
        "push_subscriptions",
        ["device_session_id"],
    )
    op.create_index(
        "ix_push_subscriptions_recipient_active",
        "push_subscriptions",
        ["business_id", "user_id", "is_active"],
    )

    connection = op.get_bind()
    for code, role_codes in PERMISSIONS.items():
        permission_id = _identifier("permission", code)
        connection.execute(
            sa.text(
                "INSERT INTO permissions (id, code, module, description, created_at, updated_at) "
                "VALUES (:id, :code, 'notification', :description, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"id": permission_id, "code": code, "description": code},
        )
        for role_code in role_codes:
            connection.execute(
                sa.text(
                    "INSERT INTO role_permissions "
                    "(id, role_id, permission_id, created_at, updated_at) "
                    "VALUES (:id, :role_id, :permission_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ),
                {
                    "id": uuid5(AUTH_NAMESPACE, f"role-permission:{role_code}:{code}"),
                    "role_id": _identifier("role", role_code),
                    "permission_id": permission_id,
                },
            )

    if connection.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS notifications_business_all ON notifications")
        op.execute(
            "CREATE POLICY notifications_recipient_select ON notifications FOR SELECT "
            "USING (kasta_is_business_actor(business_id) "
            "AND user_id = kasta_context_uuid('app.user_id'))"
        )
        op.execute(
            "CREATE POLICY notifications_recipient_update ON notifications FOR UPDATE "
            "USING (kasta_is_business_actor(business_id) "
            "AND user_id = kasta_context_uuid('app.user_id')) "
            "WITH CHECK (kasta_is_business_actor(business_id) "
            "AND user_id = kasta_context_uuid('app.user_id'))"
        )
        op.execute(
            "CREATE POLICY notifications_business_insert ON notifications FOR INSERT "
            "WITH CHECK (kasta_is_business_actor(business_id))"
        )
        for table_name in ("notification_preferences", "push_subscriptions"):
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY {table_name}_own_all ON {table_name} FOR ALL "
                "USING (kasta_is_business_actor(business_id) "
                "AND user_id = kasta_context_uuid('app.user_id')) "
                "WITH CHECK (kasta_is_business_actor(business_id) "
                "AND user_id = kasta_context_uuid('app.user_id'))"
            )
        op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS notifications_recipient_select ON notifications")
        op.execute("DROP POLICY IF EXISTS notifications_recipient_update ON notifications")
        op.execute("DROP POLICY IF EXISTS notifications_business_insert ON notifications")
        op.execute(
            "CREATE POLICY notifications_business_all ON notifications FOR ALL "
            "USING (kasta_is_business_actor(business_id)) "
            "WITH CHECK (kasta_is_business_actor(business_id))"
        )
    for code in PERMISSIONS:
        permission_id = _identifier("permission", code)
        connection.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :permission_id"),
            {"permission_id": permission_id},
        )
        connection.execute(sa.text("DELETE FROM permissions WHERE id = :id"), {"id": permission_id})
    op.drop_table("push_subscriptions")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notifications_recipient_read_created", table_name="notifications")
    op.drop_constraint(
        "uq_notifications_recipient_entity_schedule", "notifications", type_="unique"
    )
    op.create_unique_constraint(
        "uq_notifications_entity_schedule",
        "notifications",
        ["business_id", "entity_type", "entity_id", "scheduled_for"],
    )
    op.drop_index("ix_notifications_available_at", table_name="notifications")
    op.drop_column("notifications", "available_at")
    op.drop_column("notifications", "action_path")
