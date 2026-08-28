from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from kasta_api.modules.closing.constants import ClosingFrequency

Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class AccountActivityLine(BaseModel):
    account_key: str
    account_name: str
    amount: Decimal


class CurrentPeriodResponse(BaseModel):
    period_start: date
    period_end_suggested: date
    as_of: date
    frequency: ClosingFrequency
    revenues: list[AccountActivityLine]
    expenses: list[AccountActivityLine]
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal
    is_loss: bool
    has_activity: bool
    is_overdue: bool
    explanation: str


class ClosePeriodRequest(BaseModel):
    period_end: date = Field(default_factory=date.today)
    note: Note = ""
    acknowledge_adjustments: bool


class PeriodClosingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    period_start: date
    period_end: date
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal
    closing_transaction_id: UUID | None
    closed_by_user_id: UUID
    note: str | None
    created_at: datetime


class PeriodClosingListResponse(BaseModel):
    items: list[PeriodClosingResponse]
    total: int
