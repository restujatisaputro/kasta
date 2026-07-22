from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from kasta_api.modules.accounting.constants import AccountKey, TransactionType
from kasta_api.modules.accounting.engine import TransactionCommand
from kasta_api.modules.accounting.models import FinancialTransaction

Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=255)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class PostTransactionRequest(BaseModel):
    transaction_type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    transaction_date: date = Field(default_factory=date.today)
    description: Description
    payment_account: AccountKey | None = None
    category_account: AccountKey | None = None
    idempotency_key: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)]
        | None
    ) = None

    def to_command(self) -> TransactionCommand:
        return TransactionCommand(
            transaction_type=self.transaction_type,
            amount=self.amount,
            transaction_date=self.transaction_date,
            description=self.description,
            payment_account=self.payment_account,
            category_account=self.category_account,
            idempotency_key=self.idempotency_key,
        )


class ReverseTransactionRequest(BaseModel):
    reason: Reason
    transaction_date: date = Field(default_factory=date.today)


class ReviseTransactionRequest(BaseModel):
    reason: Reason
    replacement: PostTransactionRequest


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    system_key: str | None
    account_type: str
    normal_balance: Literal["DEBIT", "CREDIT"]
    is_active: bool


class TransactionResponse(BaseModel):
    id: UUID
    business_id: UUID
    transaction_number: str
    transaction_type: str
    transaction_date: date
    amount: Decimal
    description: str
    status: Literal["POSTED", "REVERSED"]
    revision_number: int
    root_transaction_id: UUID | None
    supersedes_transaction_id: UUID | None
    reverses_transaction_id: UUID | None
    reversed_by_transaction_id: UUID | None
    posted_at: datetime
    entry_kind: str | None = None
    counterparty_name: str | None = None
    payment_method_code: str | None = None
    recurring_rule_id: UUID | None = None
    category_account_key: str | None = None

    @classmethod
    def from_model(cls, transaction: FinancialTransaction) -> TransactionResponse:
        return cls.model_validate(transaction, from_attributes=True)


class TransactionRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    related_transaction_id: UUID | None
    revision_number: int
    event_sequence: int
    event_type: Literal["POSTED", "REVERSED", "REVISED"]
    snapshot: dict[str, object]
    reason: str | None
    actor_user_id: UUID
    created_at: datetime


class RevisionResultResponse(BaseModel):
    reversed_transaction: TransactionResponse
    replacement_transaction: TransactionResponse
