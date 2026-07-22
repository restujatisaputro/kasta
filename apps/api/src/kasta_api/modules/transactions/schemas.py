from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from kasta_api.modules.accounting.constants import (
    EXPENSE_ACCOUNT_KEYS,
    INCOME_ACCOUNT_KEYS,
    AccountKey,
    TransactionType,
)
from kasta_api.modules.accounting.engine import TransactionCommand
from kasta_api.modules.accounting.schemas import TransactionResponse
from kasta_api.modules.transactions.constants import (
    PAYMENT_ACCOUNT,
    EntryKind,
    PaymentMethod,
    RecurrenceFrequency,
)
from kasta_api.modules.transactions.models import RecurringTransaction, TransactionDraft

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
Counterparty = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class TransactionProductItemInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class SimpleTransactionInput(BaseModel):
    entry_kind: EntryKind
    transaction_date: date = Field(default_factory=date.today)
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    category_account: AccountKey | None = None
    counterparty_name: Counterparty | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    note: ShortText = ""
    recurrence_frequency: RecurrenceFrequency | None = None
    recurrence_interval: int | None = Field(default=None, ge=1, le=12)
    idempotency_key: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)]
        | None
    ) = None
    items: list[TransactionProductItemInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_category_and_recurrence(self) -> SimpleTransactionInput:
        if self.entry_kind == EntryKind.INCOME and self.category_account not in INCOME_ACCOUNT_KEYS:
            raise ValueError("Pilih sumber pemasukan.")
        if (
            self.entry_kind == EntryKind.EXPENSE
            and self.category_account not in EXPENSE_ACCOUNT_KEYS
        ):
            raise ValueError("Pilih kategori pengeluaran.")
        if (self.recurrence_frequency is None) != (self.recurrence_interval is None):
            raise ValueError("Isi jadwal transaksi berulang secara lengkap.")
        if self.items and self.entry_kind not in {EntryKind.INCOME, EntryKind.EXPENSE}:
            raise ValueError("Produk hanya dapat dipilih untuk Uang Masuk atau Uang Keluar.")
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Produk yang sama cukup ditambahkan satu kali.")
        if self.items:
            item_total = sum(
                (
                    (item.quantity * item.unit_price).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    for item in self.items
                ),
                Decimal("0.00"),
            )
            transaction_total = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if item_total != transaction_total:
                raise ValueError("Nominal transaksi harus sama dengan jumlah produk.")
        return self

    def to_command(
        self,
        *,
        idempotency_key: str | None = None,
        recurring_rule_id: UUID | None = None,
        transaction_id: UUID | None = None,
    ) -> TransactionCommand:
        payment_account = PAYMENT_ACCOUNT[self.payment_method]
        if self.entry_kind == EntryKind.EXPENSE and self.payment_method == PaymentMethod.QRIS:
            payment_account = AccountKey.BANK
        transaction_type = {
            EntryKind.INCOME: (
                TransactionType.CASH_SALE
                if payment_account == AccountKey.CASH
                else TransactionType.NON_CASH_SALE
            ),
            EntryKind.EXPENSE: TransactionType.OPERATING_EXPENSE,
            EntryKind.CAPITAL: TransactionType.CAPITAL_CONTRIBUTION,
            EntryKind.OWNER_DRAW: TransactionType.OWNER_DRAW,
        }[self.entry_kind]
        category_account = self.category_account
        if self.entry_kind == EntryKind.EXPENSE and self.items:
            transaction_type = TransactionType.CASH_PURCHASE
            category_account = AccountKey.INVENTORY
        fallback_note = {
            EntryKind.INCOME: "Uang masuk",
            EntryKind.EXPENSE: "Uang keluar",
            EntryKind.CAPITAL: "Tambah modal",
            EntryKind.OWNER_DRAW: "Ambil uang pribadi",
        }[self.entry_kind]
        return TransactionCommand(
            transaction_type=transaction_type,
            amount=self.amount,
            transaction_date=self.transaction_date,
            description=self.note or fallback_note,
            payment_account=payment_account,
            category_account=category_account,
            idempotency_key=idempotency_key or self.idempotency_key,
            entry_kind=self.entry_kind.value,
            counterparty_name=self.counterparty_name or None,
            payment_method_code=self.payment_method.value,
            recurring_rule_id=str(recurring_rule_id) if recurring_rule_id is not None else None,
            transaction_id=transaction_id,
        )


class DraftCreateRequest(SimpleTransactionInput):
    client_reference: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)]
        | None
    ) = None


class DraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    client_reference: str | None
    entry_kind: str
    transaction_date: date
    amount: Decimal
    category_account_key: str | None
    counterparty_name: str | None
    payment_method_code: str
    note: str
    recurrence_frequency: str | None
    recurrence_interval: int | None
    status: Literal["ACTIVE", "POSTED"]
    items_data: list[dict[str, str]] | None
    posted_transaction_id: UUID | None
    created_at: datetime
    updated_at: datetime


class RecurringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    entry_kind: str
    amount: Decimal
    category_account_key: str | None
    counterparty_name: str | None
    payment_method_code: str
    note: str
    frequency: Literal["WEEKLY", "MONTHLY"]
    recurrence_interval: int
    next_run_date: date
    last_run_at: datetime | None
    status: Literal["ACTIVE", "PAUSED", "CANCELLED"]
    items_data: list[dict[str, str]] | None


class RecurringStatusRequest(BaseModel):
    status: Literal["ACTIVE", "PAUSED", "CANCELLED"]


class SimpleTransactionResponse(BaseModel):
    transaction: TransactionResponse
    recurring: RecurringResponse | None = None


class TransactionProductItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    stock_direction: Literal["IN", "OUT"]


class TransactionListItem(TransactionResponse):
    receipt_count: int = 0
    items: list[TransactionProductItemResponse] = Field(default_factory=list)


class TransactionListResponse(BaseModel):
    items: list[TransactionListItem]
    total: int
    limit: int
    offset: int


class OptionItem(BaseModel):
    value: str
    label: str


class TransactionOptionsResponse(BaseModel):
    income_sources: list[OptionItem]
    expense_categories: list[OptionItem]
    payment_methods: list[OptionItem]


class SimpleRevisionRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    replacement: SimpleTransactionInput


class SimpleReversalRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    transaction_date: date = Field(default_factory=date.today)


class ReceiptImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    content_type: str
    size_bytes: int
    created_at: datetime


class ReceiptUrlResponse(BaseModel):
    url: str
    expires_in: int


class SyncOperation(BaseModel):
    client_operation_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)
    ]
    operation: Literal["CREATE", "SAVE_DRAFT", "REVISE", "REVERSE"]
    transaction_id: UUID | None = None
    payload: SimpleTransactionInput | None = None
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> SyncOperation:
        if self.operation in {"CREATE", "SAVE_DRAFT", "REVISE"} and self.payload is None:
            raise ValueError("Data transaksi diperlukan.")
        if self.operation in {"REVISE", "REVERSE"} and self.transaction_id is None:
            raise ValueError("ID transaksi diperlukan.")
        if self.operation in {"REVISE", "REVERSE"} and not (self.reason or "").strip():
            raise ValueError("Alasan perubahan diperlukan.")
        return self


class TransactionSyncRequest(BaseModel):
    operations: list[SyncOperation] = Field(min_length=1, max_length=100)
    pull_updated_after: datetime | None = None


class SyncOperationResult(BaseModel):
    client_operation_id: str
    status: Literal["APPLIED", "REJECTED"]
    server_transaction_id: UUID | None = None
    draft_id: UUID | None = None
    message: str | None = None


class TransactionSyncResponse(BaseModel):
    results: list[SyncOperationResult]
    changes: list[TransactionListItem]
    server_time: datetime


def draft_to_input(draft: TransactionDraft) -> SimpleTransactionInput:
    return SimpleTransactionInput(
        entry_kind=EntryKind(draft.entry_kind),
        transaction_date=draft.transaction_date,
        amount=draft.amount,
        category_account=(
            AccountKey(draft.category_account_key)
            if draft.category_account_key is not None
            else None
        ),
        counterparty_name=draft.counterparty_name,
        payment_method=PaymentMethod(draft.payment_method_code),
        note=draft.note,
        recurrence_frequency=(
            RecurrenceFrequency(draft.recurrence_frequency)
            if draft.recurrence_frequency is not None
            else None
        ),
        recurrence_interval=draft.recurrence_interval,
        idempotency_key=draft.client_reference,
        items=[
            TransactionProductItemInput.model_validate(item) for item in (draft.items_data or [])
        ],
    )


def recurring_to_input(rule: RecurringTransaction, run_date: date) -> SimpleTransactionInput:
    return SimpleTransactionInput(
        entry_kind=EntryKind(rule.entry_kind),
        transaction_date=run_date,
        amount=rule.amount,
        category_account=(
            AccountKey(rule.category_account_key) if rule.category_account_key is not None else None
        ),
        counterparty_name=rule.counterparty_name,
        payment_method=PaymentMethod(rule.payment_method_code),
        note=rule.note,
        items=[
            TransactionProductItemInput.model_validate(item) for item in (rule.items_data or [])
        ],
    )
