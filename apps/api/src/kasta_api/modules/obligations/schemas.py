from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kasta_api.modules.obligations.constants import ObligationKind, ObligationStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Money = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class PartyCreateRequest(BaseModel):
    name: Name
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=320)] = ""


class PartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str | None
    email: str | None
    is_active: bool


class ObligationCreateRequest(BaseModel):
    party_id: UUID | None = None
    party_name: Name | None = None
    party_phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    party_email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=320)] = ""
    initial_amount: Money
    transaction_date: date = Field(default_factory=date.today)
    due_date: date
    note: Note = ""
    reminder_enabled: bool = True
    reminder_days_before: int = Field(default=3, ge=0, le=90)

    @model_validator(mode="after")
    def validate_obligation(self) -> ObligationCreateRequest:
        if self.party_id is None and not self.party_name:
            raise ValueError("Pilih atau isi nama pelanggan/pemasok.")
        if self.due_date < self.transaction_date:
            raise ValueError("Tanggal jatuh tempo tidak boleh sebelum tanggal transaksi.")
        return self


class PaymentCreateRequest(BaseModel):
    amount: Money
    payment_date: date = Field(default_factory=date.today)
    payment_account: Literal["CASH", "BANK"] = "CASH"
    note: Note = ""


class CancellationRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    cancellation_date: date = Field(default_factory=date.today)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    amount: Decimal
    payment_date: date
    payment_account_key: str
    note: str | None
    created_by_user_id: UUID
    created_at: datetime


class ObligationResponse(BaseModel):
    id: UUID
    business_id: UUID
    kind: ObligationKind
    party: PartyResponse
    initial_transaction_id: UUID
    cancellation_transaction_id: UUID | None
    initial_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    transaction_date: date
    due_date: date
    status: ObligationStatus
    status_label: str
    note: str | None
    reminder_enabled: bool
    reminder_days_before: int
    days_until_due: int
    created_at: datetime
    updated_at: datetime


class ObligationDetailResponse(ObligationResponse):
    payments: list[PaymentResponse]


class ObligationListResponse(BaseModel):
    items: list[ObligationResponse]
    total: int
    limit: int
    offset: int


class AgingBucket(BaseModel):
    code: Literal["NOT_DUE", "DUE_1_30", "DUE_31_60", "DUE_61_90", "DUE_OVER_90"]
    label: str
    count: int
    amount: Decimal


class AgingSection(BaseModel):
    total_open: Decimal
    buckets: list[AgingBucket]


class AgingReportResponse(BaseModel):
    as_of: date
    receivables: AgingSection
    payables: AgingSection


class ReminderItem(BaseModel):
    kind: ObligationKind
    obligation_id: UUID
    party_name: str
    due_date: date
    remaining_amount: Decimal
    days_until_due: int
    message: str


class ReminderListResponse(BaseModel):
    as_of: date
    items: list[ReminderItem]


class ReminderGenerationResponse(BaseModel):
    generated_count: int
    notification_ids: list[UUID]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notification_type: str
    title: str
    message: str
    entity_type: str
    entity_id: UUID
    scheduled_for: date
    payload: dict[str, object]
    read_at: datetime | None
    created_at: datetime
