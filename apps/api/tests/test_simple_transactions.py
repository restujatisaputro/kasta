from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
)
from kasta_api.modules.transactions.models import (
    RecurringTransaction,
    TransactionDraft,
    TransactionSyncLog,
)
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def base_url(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}"


def income_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "entry_kind": "INCOME",
        "transaction_date": "2026-07-21",
        "amount": "275000.00",
        "category_account": "SERVICE_REVENUE",
        "counterparty_name": "Pelanggan Sari",
        "payment_method": "BANK_TRANSFER",
        "note": "Pembayaran jasa desain",
    }
    payload.update(changes)
    return payload


def expense_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "entry_kind": "EXPENSE",
        "transaction_date": "2026-07-21",
        "amount": "75000.00",
        "category_account": "TRANSPORTATION",
        "counterparty_name": "Toko Angkut",
        "payment_method": "CASH",
        "note": "Biaya kirim barang",
    }
    payload.update(changes)
    return payload


async def test_simple_income_posts_automatic_journal_and_searches(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    created = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=income_payload(idempotency_key="simple-income-0001"),
    )

    assert created.status_code == 201, created.text
    transaction = created.json()["transaction"]
    assert transaction["entry_kind"] == "INCOME"
    assert transaction["counterparty_name"] == "Pelanggan Sari"
    assert transaction["payment_method_code"] == "BANK_TRANSFER"

    transaction_id = UUID(transaction["id"])
    async with auth_environment.session_factory() as session:
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
    amounts = {
        account.system_key: (line.debit_amount, line.credit_amount) for line, account in rows
    }
    assert amounts["BANK"] == (Decimal("275000.00"), Decimal("0.00"))
    assert amounts["SERVICE_REVENUE"] == (Decimal("0.00"), Decimal("275000.00"))

    found = await auth_environment.client.get(
        f"{base_url(auth_environment)}/transactions",
        params={"q": "sari", "entry_kind": "INCOME", "payment_method": "BANK_TRANSFER"},
        headers=headers(tokens.access_token),
    )
    assert found.status_code == 200
    assert found.json()["total"] == 1
    assert found.json()["items"][0]["id"] == str(transaction_id)


async def test_last_expense_category_is_returned_first(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    posted = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=expense_payload(category_account="INTERNET"),
    )
    assert posted.status_code == 201, posted.text

    options = await auth_environment.client.get(
        f"{base_url(auth_environment)}/transactions/options",
        headers=headers(tokens.access_token),
    )
    assert options.status_code == 200
    assert options.json()["expense_categories"][0] == {
        "value": "INTERNET",
        "label": "Internet",
    }


async def test_draft_can_be_updated_and_posted_once(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    created = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/drafts",
        headers=headers(tokens.access_token),
        json=expense_payload(client_reference="android-draft-0001"),
    )
    assert created.status_code == 201, created.text
    draft_id = created.json()["id"]

    updated = await auth_environment.client.put(
        f"{base_url(auth_environment)}/transactions/drafts/{draft_id}",
        headers=headers(tokens.access_token),
        json=expense_payload(
            client_reference="android-draft-0001",
            amount="85000.00",
            note="Biaya kirim yang dikoreksi",
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "85000.00"

    posted = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/drafts/{draft_id}/post",
        headers=headers(tokens.access_token),
    )
    repeated = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/drafts/{draft_id}/post",
        headers=headers(tokens.access_token),
    )
    assert posted.status_code == repeated.status_code == 200
    assert posted.json()["transaction"]["id"] == repeated.json()["transaction"]["id"]

    async with auth_environment.session_factory() as session:
        draft = await session.get(TransactionDraft, UUID(draft_id))
        count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert draft is not None
    assert draft.status == "POSTED"
    assert draft.posted_transaction_id == UUID(posted.json()["transaction"]["id"])
    assert count == 1


async def test_recurring_transaction_generates_due_occurrences_idempotently(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    created = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=expense_payload(
            transaction_date="2026-06-01",
            recurrence_frequency="WEEKLY",
            recurrence_interval=1,
        ),
    )
    assert created.status_code == 201, created.text
    rule_id = created.json()["recurring"]["id"]
    assert created.json()["recurring"]["next_run_date"] == "2026-06-08"

    first_run = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/recurring/run-due",
        params={"through_date": "2026-06-22"},
        headers=headers(tokens.access_token),
    )
    second_run = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/recurring/run-due",
        params={"through_date": "2026-06-22"},
        headers=headers(tokens.access_token),
    )
    assert first_run.status_code == 200, first_run.text
    assert len(first_run.json()) == 3
    assert second_run.json() == []

    async with auth_environment.session_factory() as session:
        rule = await session.get(RecurringTransaction, UUID(rule_id))
        count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert rule is not None
    assert rule.next_run_date == date(2026, 6, 29)
    assert count == 4


async def test_recurring_create_replay_does_not_duplicate_rule(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    payload = expense_payload(
        recurrence_frequency="MONTHLY",
        recurrence_interval=1,
        idempotency_key="monthly-expense-0001",
    )
    first = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=payload,
    )
    replay = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=payload,
    )

    assert first.status_code == replay.status_code == 201
    assert first.json()["transaction"]["id"] == replay.json()["transaction"]["id"]
    assert first.json()["recurring"]["id"] == replay.json()["recurring"]["id"]

    async with auth_environment.session_factory() as session:
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
        recurring_count = await session.scalar(select(func.count(RecurringTransaction.id)))
    assert transaction_count == 1
    assert recurring_count == 1


async def test_sync_replay_does_not_duplicate_transaction(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    request = {
        "operations": [
            {
                "client_operation_id": "offline-operation-0001",
                "operation": "CREATE",
                "payload": income_payload(),
            }
        ]
    }
    first = await auth_environment.client.post(
        f"{base_url(auth_environment)}/sync/transactions",
        headers=headers(tokens.access_token),
        json=request,
    )
    second = await auth_environment.client.post(
        f"{base_url(auth_environment)}/sync/transactions",
        headers=headers(tokens.access_token),
        json=request,
    )

    assert first.status_code == second.status_code == 200
    first_id = first.json()["results"][0]["server_transaction_id"]
    assert second.json()["results"][0]["server_transaction_id"] == first_id
    assert first.json()["changes"][0]["id"] == first_id

    async with auth_environment.session_factory() as session:
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
        log_count = await session.scalar(select(func.count(TransactionSyncLog.id)))
    assert transaction_count == 1
    assert log_count == 1


async def test_simple_revision_and_reversal_keep_history(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    created = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions",
        headers=headers(tokens.access_token),
        json=income_payload(),
    )
    transaction_id = created.json()["transaction"]["id"]

    revised = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/{transaction_id}/revision",
        headers=headers(tokens.access_token),
        json={
            "reason": "Nominal perlu diperbaiki",
            "replacement": income_payload(amount="300000.00"),
        },
    )
    assert revised.status_code == 200, revised.text
    replacement = revised.json()["transaction"]
    assert replacement["revision_number"] == 2
    assert replacement["supersedes_transaction_id"] == transaction_id

    cancelled = await auth_environment.client.post(
        f"{base_url(auth_environment)}/transactions/{replacement['id']}/reversal",
        headers=headers(tokens.access_token),
        json={"reason": "Pembayaran dibatalkan pelanggan"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["transaction_type"] == "REVERSAL"
