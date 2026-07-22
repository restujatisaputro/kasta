from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

SyncId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)]


class PushOperation(BaseModel):
    operation_id: SyncId
    entity_type: Annotated[str, StringConstraints(to_upper=True, min_length=2, max_length=40)]
    action: Literal["CREATE", "UPSERT", "DELETE"]
    local_id: UUID
    server_id: UUID | None = None
    base_version: int = Field(default=0, ge=0)
    changed_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_server_identity(self) -> PushOperation:
        if self.action != "CREATE" and self.server_id is None:
            raise ValueError("server_id diperlukan untuk perubahan atau penghapusan.")
        return self


class SyncPushRequest(BaseModel):
    business_id: UUID
    device_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=200)
    ]
    batch_id: SyncId
    operations: list[PushOperation] = Field(min_length=1, max_length=100)


class PushResult(BaseModel):
    operation_id: str
    local_id: UUID
    status: Literal["SYNCED", "FAILED", "CONFLICT"]
    server_id: UUID | None = None
    server_version: int | None = None
    conflict_id: UUID | None = None
    canonical_payload: dict[str, Any] | None = None
    deleted_at: datetime | None = None
    message: str | None = None


class SyncPushResponse(BaseModel):
    batch_id: str
    results: list[PushResult]
    server_time: datetime


class SyncPullRequest(BaseModel):
    business_id: UUID
    device_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=200)
    ]
    cursor: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


class PullChange(BaseModel):
    cursor: int
    entity_type: str
    server_id: UUID
    version: int
    action: Literal["UPSERT", "DELETE"]
    payload: dict[str, Any]
    changed_at: datetime


class SyncPullResponse(BaseModel):
    changes: list[PullChange]
    next_cursor: int
    has_more: bool
    server_time: datetime


class SyncStatusResponse(BaseModel):
    business_id: UUID
    device_id: str
    last_push_at: datetime | None
    last_pull_at: datetime | None
    last_cursor: int
    open_conflicts: int
    server_time: datetime
