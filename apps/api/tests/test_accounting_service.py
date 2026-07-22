from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
    TransactionRevision,
)
from kasta_api.modules.audit.models import AuditLog
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def authorization(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def transaction_url(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}/accounting/transactions"


async def post_cash_sale(
    environment: AuthTestEnvironment, access_token: str, *, idempotency_key: str
) -> dict[str, object]:
    response = await environment.client.post(
        transaction_url(environment),
        headers=authorization(access_token),
        json={
            "transaction_type": "CASH_SALE",
            "amount": "150000.005",
            "transaction_date": "2026-07-21",
            "description": "Penjualan tunai harian",
            "idempotency_key": idempotency_key,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_account_templates_are_complete_and_tenant_scoped(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    response = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/accounting/accounts",
        headers=authorization(tokens.access_token),
    )

    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 24
    assert {item["name"] for item in accounts} >= {
        "Kas",
        "Utang Usaha",
        "Modal Pemilik",
        "Penjualan",
        "Beban Lain",
    }
    assert len({item["system_key"] for item in accounts}) == 24

    other_tenant = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/accounting/accounts",
        headers=authorization(tokens.access_token),
    )
    assert other_tenant.status_code == 403


async def test_posting_is_atomic_balanced_audited_and_idempotent(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    posted = await post_cash_sale(
        auth_environment, tokens.access_token, idempotency_key="sale-test-0001"
    )
    repeated = await post_cash_sale(
        auth_environment, tokens.access_token, idempotency_key="sale-test-0001"
    )

    assert repeated["id"] == posted["id"]
    assert posted["amount"] == "150000.01"
    transaction_id = UUID(str(posted["id"]))

    async with auth_environment.session_factory() as session:
        transaction = await session.get(FinancialTransaction, transaction_id)
        entry = (
            await session.scalars(
                select(JournalEntry).where(JournalEntry.transaction_id == transaction_id)
            )
        ).one()
        rows = (
            await session.execute(
                select(JournalLine, Account)
                .join(Account, Account.id == JournalLine.account_id)
                .where(JournalLine.journal_entry_id == entry.id)
            )
        ).all()
        revisions = await session.scalar(
            select(func.count(TransactionRevision.id)).where(
                TransactionRevision.transaction_id == transaction_id
            )
        )
        audits = await session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.entity_id == transaction_id)
        )

    assert transaction is not None
    assert entry.total_debit == entry.total_credit == Decimal("150000.01")
    amounts = {
        account.system_key: (line.debit_amount, line.credit_amount) for line, account in rows
    }
    assert amounts[AccountKey.CASH.value] == (Decimal("150000.01"), Decimal("0.00"))
    assert amounts[AccountKey.SALES.value] == (Decimal("0.00"), Decimal("150000.01"))
    assert sum((line.debit_amount for line, _ in rows), Decimal("0.00")) == sum(
        (line.credit_amount for line, _ in rows), Decimal("0.00")
    )
    assert revisions == 1
    assert audits == 1


async def test_invalid_post_rolls_back_all_database_changes(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    async with auth_environment.session_factory() as session:
        before = await session.scalar(select(func.count(FinancialTransaction.id)))

    response = await auth_environment.client.post(
        transaction_url(auth_environment),
        headers=authorization(tokens.access_token),
        json={
            "transaction_type": "OPERATING_EXPENSE",
            "amount": "50000.00",
            "description": "Bayar internet",
            "payment_account": "DIGITAL_WALLET",
            "category_account": "INTERNET",
        },
    )

    assert response.status_code == 422
    async with auth_environment.session_factory() as session:
        after = await session.scalar(select(func.count(FinancialTransaction.id)))
        account_count = await session.scalar(select(func.count(Account.id)))
    assert after == before
    assert account_count == 0


async def test_reversal_swaps_lines_and_posted_transaction_has_no_delete_endpoint(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    posted = await post_cash_sale(
        auth_environment, tokens.access_token, idempotency_key="sale-reversal-0001"
    )
    original_id = UUID(str(posted["id"]))
    endpoint = f"{transaction_url(auth_environment)}/{original_id}"

    response = await auth_environment.client.post(
        f"{endpoint}/reversal",
        headers=authorization(tokens.access_token),
        json={"reason": "Penjualan tercatat dua kali", "transaction_date": "2026-07-21"},
    )

    assert response.status_code == 200, response.text
    reversal = response.json()
    assert reversal["transaction_type"] == "REVERSAL"
    assert reversal["reverses_transaction_id"] == str(original_id)

    async with auth_environment.session_factory() as session:
        original = await session.get(FinancialTransaction, original_id)
        reversal_entry = (
            await session.scalars(
                select(JournalEntry).where(JournalEntry.transaction_id == UUID(reversal["id"]))
            )
        ).one()
        rows = (
            await session.execute(
                select(JournalLine, Account)
                .join(Account, Account.id == JournalLine.account_id)
                .where(JournalLine.journal_entry_id == reversal_entry.id)
            )
        ).all()

    assert original is not None
    assert original.status == "REVERSED"
    amounts = {
        account.system_key: (line.debit_amount, line.credit_amount) for line, account in rows
    }
    assert amounts[AccountKey.SALES.value] == (Decimal("150000.01"), Decimal("0.00"))
    assert amounts[AccountKey.CASH.value] == (Decimal("0.00"), Decimal("150000.01"))

    duplicate = await auth_environment.client.post(
        f"{endpoint}/reversal",
        headers=authorization(tokens.access_token),
        json={"reason": "Mencoba pembatalan kedua"},
    )
    deletion = await auth_environment.client.delete(
        endpoint, headers=authorization(tokens.access_token)
    )
    assert duplicate.status_code == 409
    assert deletion.status_code == 405


async def test_revision_keeps_original_and_records_history(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    posted = await post_cash_sale(
        auth_environment, tokens.access_token, idempotency_key="sale-revision-0001"
    )
    original_id = UUID(str(posted["id"]))
    endpoint = f"{transaction_url(auth_environment)}/{original_id}"

    response = await auth_environment.client.post(
        f"{endpoint}/revision",
        headers=authorization(tokens.access_token),
        json={
            "reason": "Jumlah penjualan perlu dikoreksi",
            "replacement": {
                "transaction_type": "CASH_SALE",
                "amount": "175000.00",
                "transaction_date": "2026-07-21",
                "description": "Penjualan tunai yang dikoreksi",
                "idempotency_key": "sale-revision-0002",
            },
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["reversed_transaction"]["status"] == "REVERSED"
    replacement = result["replacement_transaction"]
    assert replacement["revision_number"] == 2
    assert replacement["supersedes_transaction_id"] == str(original_id)
    assert replacement["root_transaction_id"] == str(original_id)

    history = await auth_environment.client.get(
        f"{endpoint}/history", headers=authorization(tokens.access_token)
    )
    assert history.status_code == 200
    assert {item["event_type"] for item in history.json()} >= {"POSTED", "REVISED"}


async def test_failed_revision_rolls_back_its_reversal(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    posted = await post_cash_sale(
        auth_environment, tokens.access_token, idempotency_key="sale-failed-revision-0001"
    )
    original_id = UUID(str(posted["id"]))
    endpoint = f"{transaction_url(auth_environment)}/{original_id}"

    response = await auth_environment.client.post(
        f"{endpoint}/revision",
        headers=authorization(tokens.access_token),
        json={
            "reason": "Koreksi ini sengaja tidak valid",
            "replacement": {
                "transaction_type": "NON_CASH_SALE",
                "amount": "175000.00",
                "description": "Penjualan tanpa akun pembayaran",
            },
        },
    )

    assert response.status_code == 422
    async with auth_environment.session_factory() as session:
        original = await session.get(FinancialTransaction, original_id)
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
        revision_count = await session.scalar(select(func.count(TransactionRevision.id)))
    assert original is not None
    assert original.status == "POSTED"
    assert original.reversed_by_transaction_id is None
    assert transaction_count == 1
    assert revision_count == 1
