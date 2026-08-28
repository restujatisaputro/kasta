from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from kasta_api.modules.auth.schemas import DeviceInfo, TokenPairResponse

BusinessType = Literal[
    "TRADE", "SERVICE", "PRODUCTION", "CULINARY", "AGRICULTURE", "CREATIVE", "OTHER"
]
BusinessScale = Literal["MICRO", "SMALL", "MEDIUM"]
Currency = Literal["IDR", "USD", "SGD", "MYR"]
Timezone = Literal["Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura"]
RecordingMethod = Literal["CASH", "ACCRUAL"]
InventoryMode = Literal["SIMPLE", "PERPETUAL"]
ClosingFrequency = Literal["MONTHLY", "SEMIANNUAL", "TRIANNUAL"]
PaymentMethodCode = Literal["CASH", "BANK_TRANSFER", "QRIS", "E_WALLET", "CARD"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class BusinessCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    business_type: BusinessType
    display_order: int


class CompleteOnboardingRequest(BaseModel):
    role_selection: Literal["BUSINESS_OWNER"]
    business_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)
    ]
    business_type: BusinessType
    category_id: UUID
    scale: BusinessScale
    established_year: int | None = Field(default=None, ge=1800, le=9999)
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    village: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    district: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    city: ShortText
    province: ShortText
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=24)] | None = None
    email: EmailStr | None = None
    employee_count: int = Field(default=0, ge=0, le=1_000_000)
    currency: Currency = "IDR"
    timezone: Timezone = "Asia/Jakarta"
    recording_method: RecordingMethod = "CASH"
    payment_methods: list[PaymentMethodCode] = Field(min_length=1, max_length=5)
    opening_balance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    has_products_and_stock: bool
    tutorial_completed: Literal[True]
    device: DeviceInfo

    @field_validator("payment_methods")
    @classmethod
    def payment_methods_must_be_unique(
        cls, value: list[PaymentMethodCode]
    ) -> list[PaymentMethodCode]:
        if len(value) != len(set(value)):
            raise ValueError("Metode pembayaran tidak boleh dipilih dua kali.")
        return value


class BusinessProfileUpdate(BaseModel):
    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
        | None
    ) = None
    category_id: UUID | None = None
    business_type: BusinessType | None = None
    scale: BusinessScale | None = None
    established_year: int | None = Field(default=None, ge=1800, le=9999)
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    village: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    district: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    city: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    province: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=24)] | None = None
    email: EmailStr | None = None
    employee_count: int | None = Field(default=None, ge=0, le=1_000_000)
    currency: Currency | None = None
    timezone: Timezone | None = None
    recording_method: RecordingMethod | None = None
    inventory_mode: InventoryMode | None = None
    closing_frequency: ClosingFrequency | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None
    has_products_and_stock: bool | None = None


class BusinessProfileResponse(BaseModel):
    business_id: UUID
    name: str
    logo_path: str | None
    business_type: BusinessType
    category_id: UUID
    category_name: str
    scale: BusinessScale
    established_year: int | None
    address: str | None
    village: str | None
    district: str | None
    city: str
    province: str
    phone: str | None
    email: str | None
    employee_count: int
    currency: Currency
    timezone: Timezone
    recording_method: RecordingMethod
    inventory_mode: InventoryMode
    closing_frequency: ClosingFrequency
    status: str
    payment_methods: list[PaymentMethodCode]
    opening_balance: Decimal
    has_products_and_stock: bool
    tutorial_completed_at: datetime | None
    onboarding_completed_at: datetime


class CompleteOnboardingResponse(BaseModel):
    business_id: UUID
    profile: BusinessProfileResponse
    tokens: TokenPairResponse
    next_path: str
