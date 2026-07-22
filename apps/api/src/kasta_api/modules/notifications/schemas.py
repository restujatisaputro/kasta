from datetime import datetime, time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kasta_api.modules.notifications.constants import NotificationCategory


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    notification_type: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    payload: dict[str, object]
    action_path: str | None
    available_at: datetime | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: NotificationCategory
    label: str
    enabled: bool
    local_enabled: bool
    push_enabled: bool
    email_enabled: bool
    reminder_time: time
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    timezone: str


class NotificationPreferenceUpdate(BaseModel):
    category: NotificationCategory
    enabled: bool = True
    local_enabled: bool = True
    push_enabled: bool = True
    email_enabled: bool = False
    reminder_time: time = time(18, 0)
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    timezone: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ] = "Asia/Jakarta"

    @model_validator(mode="after")
    def validate_quiet_hours(self) -> NotificationPreferenceUpdate:
        if (self.quiet_hours_start is None) != (self.quiet_hours_end is None):
            raise ValueError("Waktu mulai dan selesai jam tenang harus diisi bersama.")
        if self.quiet_hours_start == self.quiet_hours_end and self.quiet_hours_start is not None:
            raise ValueError("Waktu mulai dan selesai jam tenang tidak boleh sama.")
        return self


class NotificationPreferencesUpdate(BaseModel):
    items: list[NotificationPreferenceUpdate] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_categories(self) -> NotificationPreferencesUpdate:
        categories = [item.category for item in self.items]
        if len(categories) != len(set(categories)):
            raise ValueError("Setiap kategori hanya boleh dikirim satu kali.")
        return self


class PushSubscriptionRequest(BaseModel):
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=512)]
    platform: str = Field(pattern="^(ANDROID|WEB)$")


class PushSubscriptionResponse(BaseModel):
    registered: bool = True


class NotificationEvaluationResponse(BaseModel):
    generated_count: int
    skipped_count: int
