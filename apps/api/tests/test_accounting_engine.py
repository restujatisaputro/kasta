from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from kasta_api.modules.accounting.constants import AccountKey, TransactionType
from kasta_api.modules.accounting.engine import (
    AccountingValidationError,
    JournalDraft,
    JournalEngine,
    JournalLineDraft,
    JournalValidator,
    TransactionCommand,
    round_money,
)


def command(
    transaction_type: TransactionType,
    *,
    amount: str = "125000.00",
    payment_account: AccountKey | None = None,
    category_account: AccountKey | None = None,
) -> TransactionCommand:
    return TransactionCommand(
        transaction_type=transaction_type,
        amount=Decimal(amount),
        transaction_date=date(2026, 7, 21),
        description="Transaksi pengujian",
        payment_account=payment_account,
        category_account=category_account,
    )


SCENARIOS = (
    (command(TransactionType.CASH_SALE), AccountKey.CASH, AccountKey.SALES),
    (
        command(TransactionType.NON_CASH_SALE, payment_account=AccountKey.BANK),
        AccountKey.BANK,
        AccountKey.SALES,
    ),
    (
        command(
            TransactionType.NON_CASH_SALE,
            payment_account=AccountKey.DIGITAL_WALLET,
        ),
        AccountKey.DIGITAL_WALLET,
        AccountKey.SALES,
    ),
    (
        command(TransactionType.CREDIT_SALE),
        AccountKey.RECEIVABLE,
        AccountKey.SALES,
    ),
    (
        command(TransactionType.CASH_PURCHASE, category_account=AccountKey.INVENTORY),
        AccountKey.INVENTORY,
        AccountKey.CASH,
    ),
    (
        command(TransactionType.CREDIT_PURCHASE, category_account=AccountKey.PURCHASES),
        AccountKey.PURCHASES,
        AccountKey.PAYABLE,
    ),
    (
        command(TransactionType.CAPITAL_CONTRIBUTION),
        AccountKey.CASH,
        AccountKey.OWNER_CAPITAL,
    ),
    (
        command(TransactionType.OWNER_DRAW),
        AccountKey.OWNER_DRAW,
        AccountKey.CASH,
    ),
    (
        command(TransactionType.PAYABLE_PAYMENT),
        AccountKey.PAYABLE,
        AccountKey.CASH,
    ),
    (
        command(TransactionType.RECEIVABLE_RECEIPT),
        AccountKey.CASH,
        AccountKey.RECEIVABLE,
    ),
    (
        command(
            TransactionType.OPERATING_EXPENSE,
            payment_account=AccountKey.BANK,
            category_account=AccountKey.TRANSPORTATION,
        ),
        AccountKey.TRANSPORTATION,
        AccountKey.BANK,
    ),
)


@pytest.mark.parametrize(("input_command", "debit_key", "credit_key"), SCENARIOS)
def test_each_transaction_scenario_uses_expected_accounts(
    input_command: TransactionCommand,
    debit_key: AccountKey,
    credit_key: AccountKey,
) -> None:
    draft = JournalEngine().create_draft(input_command)

    assert draft.lines == (
        JournalLineDraft(account_key=debit_key, debit_amount=Decimal("125000.00")),
        JournalLineDraft(account_key=credit_key, credit_amount=Decimal("125000.00")),
    )
    assert draft.total_debit == draft.total_credit == Decimal("125000.00")


@pytest.mark.parametrize(
    ("raw", "expected"),
    (("10.004", "10.00"), ("10.005", "10.01"), ("10.006", "10.01")),
)
def test_money_uses_half_up_rounding(raw: str, expected: str) -> None:
    assert round_money(Decimal(raw)) == Decimal(expected)


@pytest.mark.parametrize(
    "invalid_command",
    (
        command(TransactionType.NON_CASH_SALE, payment_account=AccountKey.CASH),
        command(TransactionType.CASH_PURCHASE, category_account=AccountKey.EQUIPMENT),
        command(
            TransactionType.OPERATING_EXPENSE,
            payment_account=AccountKey.DIGITAL_WALLET,
            category_account=AccountKey.RENT,
        ),
    ),
)
def test_invalid_account_choices_are_rejected(invalid_command: TransactionCommand) -> None:
    with pytest.raises(AccountingValidationError):
        JournalEngine().create_draft(invalid_command)


def test_unbalanced_journal_is_rejected() -> None:
    draft = JournalDraft(
        lines=(
            JournalLineDraft(account_key=AccountKey.CASH, debit_amount=Decimal("100.00")),
            JournalLineDraft(account_key=AccountKey.SALES, credit_amount=Decimal("99.99")),
        ),
        total_debit=Decimal("100.00"),
        total_credit=Decimal("99.99"),
    )

    with pytest.raises(AccountingValidationError, match="tidak seimbang"):
        JournalValidator.validate(draft)


@given(
    scenario=st.sampled_from(SCENARIOS),
    amount=st.decimals(
        min_value=Decimal("0.005"),
        max_value=Decimal("999999999999.9999"),
        places=4,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_generated_journals_are_always_balanced(
    scenario: tuple[TransactionCommand, AccountKey, AccountKey], amount: Decimal
) -> None:
    input_command, _, _ = scenario
    draft = JournalEngine().create_draft(replace(input_command, amount=amount))

    total_debit = sum((line.debit_amount for line in draft.lines), Decimal("0.00"))
    total_credit = sum((line.credit_amount for line in draft.lines), Decimal("0.00"))
    assert total_debit == total_credit == round_money(amount)
