from datetime import datetime, time
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "user_id", "category", name="uq_notification_preferences_recipient"
        ),
        Index("ix_notification_preferences_recipient", "business_id", "user_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    local_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_time: Mapped[time] = mapped_column(
        Time, default=time(18, 0), server_default="18:00:00", nullable=False
    )
    quiet_hours_start: Mapped[time | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(
        String(64), default="Asia/Jakarta", server_default="Asia/Jakarta", nullable=False
    )


class PushSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("device_session_id", name="uq_push_subscriptions_device_session"),
        UniqueConstraint("token", name="uq_push_subscriptions_token"),
        CheckConstraint("platform IN ('ANDROID', 'WEB')", name="push_subscription_platform"),
        Index("ix_push_subscriptions_recipient_active", "business_id", "user_id", "is_active"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("device_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
