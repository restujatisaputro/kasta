"""Add authentication, authorization, tenant access, and device sessions.

Revision ID: 20260721_0002
Revises: 20260721_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")

ROLE_DATA = {
    "business_owner": ("Pemilik UMKM", "BUSINESS"),
    "business_staff": ("Pegawai UMKM", "BUSINESS"),
    "mentor": ("Pembina UMKM", "MENTOR"),
    "organization_admin": ("Administrator Organisasi", "ORGANIZATION"),
    "super_admin": ("Super Administrator", "PLATFORM"),
}
PERMISSIONS = [
    "transaction.create",
    "transaction.read",
    "transaction.update",
    "transaction.delete",
    "report.read",
    "report.export",
    "receipt.upload",
    "receipt.read",
    "mentor.summary.read",
    "mentor.transaction.read",
    "mentor.note.create",
    "business.member.manage",
    "session.read",
    "session.revoke.own",
]
ROLE_PERMISSIONS = {
    "business_owner": {
        "transaction.create",
        "transaction.read",
        "transaction.update",
        "transaction.delete",
        "report.read",
        "report.export",
        "receipt.upload",
        "receipt.read",
        "business.member.manage",
        "session.read",
        "session.revoke.own",
    },
    "business_staff": {
        "transaction.create",
        "transaction.read",
        "transaction.update",
        "report.read",
        "receipt.upload",
        "receipt.read",
        "session.read",
        "session.revoke.own",
    },
    "mentor": {
        "mentor.summary.read",
        "mentor.transaction.read",
        "mentor.note.create",
        "receipt.read",
        "session.read",
        "session.revoke.own",
    },
    "organization_admin": {
        "transaction.read",
        "report.read",
        "report.export",
        "receipt.read",
        "mentor.summary.read",
        "mentor.transaction.read",
        "mentor.note.create",
        "business.member.manage",
        "session.read",
        "session.revoke.own",
    },
    "super_admin": set(PERMISSIONS),
}


def _role_id(code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"role:{code}")


def _permission_id(code: str) -> UUID:
    return uuid5(AUTH_NAMESPACE, f"permission:{code}")


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "scope IN ('BUSINESS', 'MENTOR', 'ORGANIZATION', 'PLATFORM')",
            name="role_scope",
        ),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "permission_id",
            sa.Uuid(),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *_timestamps(),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_id"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("platform_role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="RESTRICT")),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(16)),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="user_has_identifier"),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="user_status"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_index("ix_users_platform_role_id", "users", ["platform_role_id"])
    op.create_index("ix_users_active_email", "users", ["email", "deleted_at"])
    op.create_index("ix_users_active_phone", "users", ["phone", "deleted_at"])

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "businesses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="SET NULL")
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="business_status"),
        sa.UniqueConstraint("code", name="uq_businesses_code"),
    )
    op.create_index("ix_businesses_organization_id", "businesses", ["organization_id"])
    op.create_table(
        "business_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="business_member_status"),
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_members_business_id"),
    )
    op.create_index("ix_business_members_business_id", "business_members", ["business_id"])
    op.create_index("ix_business_members_user_id", "business_members", ["user_id"])
    op.create_index("ix_business_members_role_id", "business_members", ["role_id"])
    op.create_index(
        "ix_business_members_access",
        "business_members",
        ["user_id", "business_id", "status", "deleted_at"],
    )
    op.create_table(
        "organization_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="organization_member_status",
        ),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_organization_members_organization_id"
        ),
    )
    op.create_index(
        "ix_organization_members_organization_id", "organization_members", ["organization_id"]
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_index("ix_organization_members_role_id", "organization_members", ["role_id"])

    op.create_table(
        "mentors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", name="uq_mentors_user_id"),
    )
    op.create_table(
        "mentor_business_access",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "mentor_id", sa.Uuid(), sa.ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column("can_view_summary", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("can_view_transactions", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_create_notes", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REVOKED')",
            name="mentor_access_status",
        ),
        sa.UniqueConstraint("mentor_id", "business_id", name="uq_mentor_business_access_mentor_id"),
    )
    op.create_index("ix_mentor_business_access_mentor_id", "mentor_business_access", ["mentor_id"])
    op.create_index(
        "ix_mentor_business_access_business_id", "mentor_business_access", ["business_id"]
    )
    op.create_index(
        "ix_mentor_business_access_active",
        "mentor_business_access",
        ["mentor_id", "business_id", "status"],
    )

    op.create_table(
        "device_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_family_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("device_identifier_hash", sa.String(64), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("device_name", sa.String(100)),
        sa.Column("app_version", sa.String(40)),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("ip_address_hash", sa.String(64), nullable=False),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(50)),
        sa.Column("rotation_counter", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("platform IN ('ANDROID', 'WEB')", name="device_platform"),
    )
    op.create_index("ix_device_sessions_user_id", "device_sessions", ["user_id"])
    op.create_index("ix_device_sessions_business_id", "device_sessions", ["business_id"])
    op.create_index("ix_device_sessions_token_family_id", "device_sessions", ["token_family_id"])
    op.create_index("ix_device_sessions_expires_at", "device_sessions", ["expires_at"])
    op.create_index("ix_device_sessions_revoked_at", "device_sessions", ["revoked_at"])
    op.create_index(
        "ix_device_sessions_user_business_active",
        "device_sessions",
        ["user_id", "business_id", "revoked_at"],
    )
    op.create_table(
        "auth_one_time_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("target", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "purpose IN ('VERIFY_EMAIL', 'VERIFY_PHONE', 'RESET_PASSWORD')",
            name="auth_token_purpose",
        ),
        sa.UniqueConstraint("token_hash", name="uq_auth_one_time_tokens_token_hash"),
    )
    op.create_index("ix_auth_one_time_tokens_user_id", "auth_one_time_tokens", ["user_id"])
    op.create_index("ix_auth_one_time_tokens_expires_at", "auth_one_time_tokens", ["expires_at"])
    op.create_index(
        "ix_auth_one_time_tokens_user_purpose",
        "auth_one_time_tokens",
        ["user_id", "purpose", "consumed_at"],
    )
    op.create_table(
        "auth_delivery_outbox",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("destination", sa.String(320), nullable=False),
        sa.Column("template", sa.String(50), nullable=False),
        sa.Column("payload_nonce", sa.LargeBinary(12), nullable=False),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("channel IN ('EMAIL', 'SMS')", name="auth_outbox_channel"),
    )
    op.create_index("ix_auth_delivery_outbox_user_id", "auth_delivery_outbox", ["user_id"])
    op.create_index(
        "ix_auth_delivery_outbox_pending", "auth_delivery_outbox", ["sent_at", "created_at"]
    )
    op.create_table(
        "login_rate_limits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("key_hash", name="uq_login_rate_limits_key_hash"),
    )
    op.create_index("ix_login_rate_limits_key_hash", "login_rate_limits", ["key_hash"])
    op.create_index("ix_login_rate_limits_blocked_until", "login_rate_limits", ["blocked_until"])

    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("scope", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        roles_table,
        [
            {"id": _role_id(code), "code": code, "name": name, "scope": scope, "is_system": True}
            for code, (name, scope) in ROLE_DATA.items()
        ],
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": _permission_id(code),
                "code": code,
                "module": code.split(".", maxsplit=1)[0],
                "description": code,
            }
            for code in PERMISSIONS
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "id": uuid5(AUTH_NAMESPACE, f"role-permission:{role}:{permission}"),
                "role_id": _role_id(role),
                "permission_id": _permission_id(permission),
            }
            for role, permissions in ROLE_PERMISSIONS.items()
            for permission in permissions
        ],
    )


def downgrade() -> None:
    for table_name in [
        "login_rate_limits",
        "auth_delivery_outbox",
        "auth_one_time_tokens",
        "device_sessions",
        "mentor_business_access",
        "mentors",
        "organization_members",
        "business_members",
        "businesses",
        "organizations",
        "users",
        "role_permissions",
        "permissions",
        "roles",
    ]:
        op.drop_table(table_name)
