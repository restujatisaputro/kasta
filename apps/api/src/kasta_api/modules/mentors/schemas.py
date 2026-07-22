from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from kasta_api.modules.mentors.constants import (
    HealthLevel,
    MentorAccessScope,
    MentorAccessStatus,
    RecommendationStatus,
    SessionStatus,
)

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3000)]


class MentorAccessRequestCreate(BaseModel):
    business_id: UUID
    requested_scope: set[MentorAccessScope] = Field(min_length=1)
    message: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None


class MentorAccessDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    scope: set[MentorAccessScope] = Field(default_factory=set)
    expires_at: datetime | None = None
    reason: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None


class MentorAccessRevoke(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class MentorAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    mentor_id: UUID
    requested_by_user_id: UUID
    granted_by_user_id: UUID | None
    scope: list[MentorAccessScope]
    status: MentorAccessStatus
    request_message: str | None
    requested_at: datetime
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    rejection_reason: str | None
    revocation_reason: str | None
    last_accessed_at: datetime | None
    revision_no: int


class MentorAccessHistoryItem(BaseModel):
    id: UUID
    action: str
    mentor_id: UUID | None
    actor_user_id: UUID | None
    scope: list[str]
    reason: str | None
    accessed_at: datetime


class SupportAccessGrantCreate(BaseModel):
    admin_user_id: UUID
    scope: set[MentorAccessScope] = Field(min_length=1)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]
    ticket_reference: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)
    ]
    expires_at: datetime


class SupportAccessGrantRevoke(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class SupportAccessGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    admin_user_id: UUID
    granted_by_user_id: UUID
    scope: list[MentorAccessScope]
    reason: str
    ticket_reference: str
    status: Literal["ACTIVE", "REVOKED", "EXPIRED"]
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RiskIndicator(BaseModel):
    code: str
    level: HealthLevel
    label: str
    message: str
    icon: str


class MentorTrendPoint(BaseModel):
    month: str
    revenue: Decimal
    expense: Decimal
    profit: Decimal


class MentorBusinessSummary(BaseModel):
    business_id: UUID
    business_name: str
    city: str | None
    province: str | None
    health_level: HealthLevel
    health_label: str
    health_icon: str
    last_recorded_date: date | None
    days_since_recording: int | None
    recording_consistency: Decimal
    month_revenue: Decimal
    month_expense: Decimal
    month_profit: Decimal
    payable_balance: Decimal
    receivable_balance: Decimal
    overdue_receivable: Decimal
    open_recommendations: int
    risk_indicators: list[RiskIndicator]


class MentorNoteCreate(BaseModel):
    content: LongText
    visibility: Literal["SHARED", "PRIVATE"] = "SHARED"


class MentorNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    mentor_id: UUID
    content: str
    visibility: str
    created_at: datetime


class RecommendationCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    description: LongText
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    due_date: date | None = None


class RecommendationUpdate(BaseModel):
    status: RecommendationStatus
    follow_up_note: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=1000)
    ] = None


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    mentor_id: UUID
    title: str
    description: str
    priority: str
    status: str
    due_date: date | None
    follow_up_note: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MentoringSessionCreate(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)
    mode: Literal["ONSITE", "ONLINE", "PHONE"] = "ONLINE"
    topic: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
    location: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None


class MentoringSessionUpdate(BaseModel):
    status: SessionStatus
    outcome: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=3000)] = None
    follow_up_date: date | None = None


class MentoringSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    mentor_id: UUID
    scheduled_at: datetime
    duration_minutes: int
    mode: str
    status: str
    topic: str
    location: str | None
    outcome: str | None
    follow_up_date: date | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MentorBusinessDetail(BaseModel):
    summary: MentorBusinessSummary
    revenue_trend: list[MentorTrendPoint]
    notes: list[MentorNoteResponse]
    recommendations: list[RecommendationResponse]
    sessions: list[MentoringSessionResponse]
    explanation: str


class MentorScheduleItem(BaseModel):
    id: UUID
    business_id: UUID
    business_name: str
    scheduled_at: datetime
    duration_minutes: int
    mode: str
    topic: str


class MentorDashboard(BaseModel):
    total_businesses: int
    active_businesses: int
    stale_businesses: int
    expense_over_income: int
    high_debt: int
    overdue_receivables: int
    open_recommendations: int
    health_green: int
    health_yellow: int
    health_red: int
    upcoming_sessions: list[MentorScheduleItem]
    businesses: list[MentorBusinessSummary]
    generated_at: datetime


class MentorAggregateReport(BaseModel):
    dashboard: MentorDashboard
    total_revenue: Decimal
    total_expense: Decimal
    total_profit: Decimal
    total_payables: Decimal
    total_receivables: Decimal
    explanation: str


class MentorAuditResponse(BaseModel):
    id: UUID
    business_id: UUID
    business_name: str
    action: str
    entity_type: str
    entity_id: UUID
    reason: str | None
    created_at: datetime
