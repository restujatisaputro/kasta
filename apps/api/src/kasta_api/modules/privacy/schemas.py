from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


class ExportedMembership(BaseModel):
    business_id: UUID
    business_name: str
    role: str
    status: str
    joined_at: datetime


class ExportedSession(BaseModel):
    id: UUID
    business_id: UUID
    platform: str
    device_name: str | None
    app_version: str | None
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class ExportedAuditEvent(BaseModel):
    action: str
    entity_type: str
    entity_id: UUID
    created_at: datetime
    request_id: str | None


class PersonalDataExportResponse(BaseModel):
    generated_at: datetime
    subject_user_id: UUID
    business_id: UUID
    profile: dict[str, str | None]
    memberships: list[ExportedMembership]
    device_sessions: list[ExportedSession]
    audit_events: list[ExportedAuditEvent]


class AccountDeletionRequest(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    confirmation: Literal["HAPUS AKUN"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = Field(
        default=None
    )


class AccountDeletionResponse(BaseModel):
    message: str
    deleted_at: datetime
