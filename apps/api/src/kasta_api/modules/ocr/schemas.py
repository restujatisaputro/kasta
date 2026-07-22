from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.transactions.constants import EntryKind, PaymentMethod


class OcrFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    value: str
    confidence: Decimal
    source_text: str | None = None
    corrected_value: str | None = None


class ReceiptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_number: int
    description: str
    quantity: Decimal | None
    unit_price: Decimal | None
    line_total: Decimal
    confidence: Decimal


class DuplicateReceiptResponse(BaseModel):
    id: UUID
    merchant_name: str | None
    receipt_date: date | None
    receipt_number: str | None
    total_amount: Decimal | None
    hash_distance: int | None
    match_reasons: list[str]


class ReceiptReviewResponse(BaseModel):
    id: UUID
    business_id: UUID
    status: Literal["UPLOADED", "PROCESSING", "NEEDS_REVIEW", "CONFIRMED", "FAILED"]
    transaction_id: UUID | None
    fields: list[OcrFieldResponse]
    items: list[ReceiptItemResponse]
    duplicate_candidates: list[DuplicateReceiptResponse] = Field(default_factory=list)
    processing_duration_ms: int | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


CorrectedValue = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ReceiptConfirmRequest(BaseModel):
    corrections: dict[str, CorrectedValue | None] = Field(default_factory=dict)
    entry_kind: EntryKind | None = None
    category_account: AccountKey | None = None
    payment_method: PaymentMethod | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    acknowledge_duplicate: bool = False

    @model_validator(mode="after")
    def validate_known_corrections(self) -> ReceiptConfirmRequest:
        allowed = {
            "merchant_name",
            "receipt_date",
            "receipt_number",
            "subtotal",
            "discount",
            "tax",
            "total",
            "payment_method",
            "transaction_kind",
            "category_account",
        }
        unknown = set(self.corrections) - allowed
        if unknown:
            raise ValueError(f"Field koreksi tidak dikenal: {', '.join(sorted(unknown))}")
        return self


class ReceiptConfirmResponse(BaseModel):
    receipt: ReceiptReviewResponse
    transaction_id: UUID


class ReceiptImageUrlResponse(BaseModel):
    url: str
    expires_in: int
