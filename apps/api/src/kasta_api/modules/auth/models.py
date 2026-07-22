from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('BUSINESS', 'MENTOR', 'ORGANIZATION', 'PLATFORM')",
            name="role_scope",
        ),
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class RolePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )


class DeviceSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_sessions"
    __table_args__ = (
        CheckConstraint("platform IN ('ANDROID', 'WEB')", name="device_platform"),
        Index("ix_device_sessions_user_business_active", "user_id", "business_id", "revoked_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_family_id: Mapped[UUID] = mapped_column(Uuid, default=uuid4, nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    device_identifier_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(100))
    app_version: Mapped[str | None] = mapped_column(String(40))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(50))
    rotation_counter: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AuthOneTimeToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_one_time_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('VERIFY_EMAIL', 'VERIFY_PHONE', 'RESET_PASSWORD')",
            name="auth_token_purpose",
        ),
        Index("ix_auth_one_time_tokens_user_purpose", "user_id", "purpose", "consumed_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    target: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthDeliveryOutbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_delivery_outbox"
    __table_args__ = (
        CheckConstraint("channel IN ('EMAIL', 'SMS')", name="auth_outbox_channel"),
        Index("ix_auth_delivery_outbox_pending", "sent_at", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    destination: Mapped[str] = mapped_column(String(320), nullable=False)
    template: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_nonce: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    payload_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginRateLimit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "login_rate_limits"

    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
