from datetime import date, timedelta
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
from kasta_api.modules.obligations.models import PayablePayment, ReceivablePayment
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio

# Tanggal dibuat relatif terhadap hari berjalan supaya status tagihan tidak
# berubah menjadi OVERDUE saat kalender melewati tanggal tetap.
TODAY = date.today()
TRANSACTION_DATE = (TODAY - timedelta(days=30)).isoformat()
DUE_DATE = (TODAY + timedelta(days=30)).isoformat()
FIRST_PAYMENT_DATE = (TODAY - timedelta(days=20)).isoformat()
SECOND_PAYMENT_DATE = (TODAY - timedelta(days=10)).isoformat()
OVERDUE_TRANSACTION_DATE = (TODAY - timedelta(days=90)).isoformat()
OVERDUE_DUE_DATE = (TODAY - timedelta(days=60)).isoformat()
# 21 hari setelah jatuh tempo supaya jatuh di bucket aging "Terlambat 1-30 hari".
AGING_AS_OF = (TODAY - timedelta(days=39)).isoformat()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def url(environment: AuthTestEnvironment, resource: str) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}/{resource}"


def claim_payload(name: str, amount: str = "1000000.00") -> dict[str, object]:
    return {
        "party_name": name,
        "initial_amount": amount,
        "transaction_date": TRANSACTION_DATE,
        "due_date": DUE_DATE,
        "note": "Tagihan uji",
        "reminder_enabled": True,
        "reminder_days_before": 7,
    }


async def create_claim(
    environment: AuthTestEnvironment,
    token: str,
    resource: str,
    name: str,
    amount: str = "1000000.00",
) -> dict[str, object]:
    response = await environment.client.post(
        url(environment, resource),
        headers=headers(token),
        json=claim_payload(name, amount),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def journal_lines(
    environment: AuthTestEnvironment, transaction_id: str
) -> set[tuple[str, Decimal, Decimal]]:
    async with environment.session_factory() as session:
        rows = (
            await session.execute(
                select(Account.system_key, JournalLine.debit_amount, JournalLine.credit_amount)
                .join(JournalLine, JournalLine.account_id == Account.id)
                .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
                .where(JournalEntry.transaction_id == UUID(transaction_id))
            )
        ).all()
    return {(str(key), debit, credit) for key, debit, credit in rows}


async def test_partial_and_full_receivable_payment_with_automatic_journals(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    claim = await create_claim(
        auth_environment, tokens.access_token, "receivables", "Warung Melati"
    )
    assert claim["status"] == "OPEN"
    assert claim["status_label"] == "Belum Dibayar"
    assert await journal_lines(auth_environment, str(claim["initial_transaction_id"])) == {
        ("RECEIVABLE", Decimal("1000000.00"), Decimal("0.00")),
        ("SALES", Decimal("0.00"), Decimal("1000000.00")),
    }

    partial = await auth_environment.client.post(
        f"{url(auth_environment, 'receivables')}/{claim['id']}/payments",
        headers=headers(tokens.access_token),
        json={
            "amount": "400000.00",
            "payment_date": FIRST_PAYMENT_DATE,
            "payment_account": "BANK",
            "note": "Transfer pertama",
        },
    )
    assert partial.status_code == 201, partial.text
    body = partial.json()
    assert body["status"] == "PARTIALLY_PAID"
    assert body["status_label"] == "Dibayar Sebagian"
    assert body["remaining_amount"] == "600000.00"
    assert len(body["payments"]) == 1
    assert await journal_lines(auth_environment, body["payments"][0]["transaction_id"]) == {
        ("BANK", Decimal("400000.00"), Decimal("0.00")),
        ("RECEIVABLE", Decimal("0.00"), Decimal("400000.00")),
    }

    paid = await auth_environment.client.post(
        f"{url(auth_environment, 'receivables')}/{claim['id']}/payments",
        headers=headers(tokens.access_token),
        json={"amount": "600000.00", "payment_date": SECOND_PAYMENT_DATE},
    )
    assert paid.status_code == 201, paid.text
    assert paid.json()["status"] == "PAID"
    assert paid.json()["status_label"] == "Sudah Lunas"
    assert paid.json()["remaining_amount"] == "0.00"
    assert len(paid.json()["payments"]) == 2


async def test_overpayment_is_rejected_without_side_effect(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    claim = await create_claim(
        auth_environment, tokens.access_token, "payables", "CV Pemasok", "250000.00"
    )
    response = await auth_environment.client.post(
        f"{url(auth_environment, 'payables')}/{claim['id']}/payments",
        headers=headers(tokens.access_token),
        json={"amount": "250000.01", "payment_date": FIRST_PAYMENT_DATE},
    )
    assert response.status_code == 409

    detail = await auth_environment.client.get(
        f"{url(auth_environment, 'payables')}/{claim['id']}",
        headers=headers(tokens.access_token),
    )
    assert detail.status_code == 200
    assert detail.json()["remaining_amount"] == "250000.00"
    assert detail.json()["payments"] == []
    async with auth_environment.session_factory() as session:
        payments = await session.scalar(select(func.count(PayablePayment.id)))
    assert payments == 0

    partial = await auth_environment.client.post(
        f"{url(auth_environment, 'payables')}/{claim['id']}/payments",
        headers=headers(tokens.access_token),
        json={
            "amount": "100000.00",
            "payment_date": SECOND_PAYMENT_DATE,
            "payment_account": "CASH",
        },
    )
    assert partial.status_code == 201, partial.text
    assert partial.json()["status"] == "PARTIALLY_PAID"
    assert partial.json()["remaining_amount"] == "150000.00"
    assert await journal_lines(
        auth_environment, partial.json()["payments"][0]["transaction_id"]
    ) == {
        ("PAYABLE", Decimal("100000.00"), Decimal("0.00")),
        ("CASH", Decimal("0.00"), Decimal("100000.00")),
    }


async def test_unpaid_claim_can_be_cancelled_but_paid_claim_cannot(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    cancelled_claim = await create_claim(
        auth_environment, tokens.access_token, "receivables", "Toko Batal", "100000.00"
    )
    cancelled = await auth_environment.client.post(
        f"{url(auth_environment, 'receivables')}/{cancelled_claim['id']}/cancellation",
        headers=headers(tokens.access_token),
        json={"reason": "Pesanan pelanggan dibatalkan", "cancellation_date": FIRST_PAYMENT_DATE},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancellation_transaction_id"] is not None
    async with auth_environment.session_factory() as session:
        original = await session.get(
            FinancialTransaction, UUID(str(cancelled_claim["initial_transaction_id"]))
        )
    assert original is not None
    assert original.status == "REVERSED"

    paid_claim = await create_claim(
        auth_environment, tokens.access_token, "receivables", "Toko Ada Bayar", "90000.00"
    )
    payment = await auth_environment.client.post(
        f"{url(auth_environment, 'receivables')}/{paid_claim['id']}/payments",
        headers=headers(tokens.access_token),
        json={"amount": "10000.00", "payment_date": FIRST_PAYMENT_DATE},
    )
    assert payment.status_code == 201
    rejected = await auth_environment.client.post(
        f"{url(auth_environment, 'receivables')}/{paid_claim['id']}/cancellation",
        headers=headers(tokens.access_token),
        json={"reason": "Coba batalkan setelah bayar", "cancellation_date": SECOND_PAYMENT_DATE},
    )
    assert rejected.status_code == 409
    async with auth_environment.session_factory() as session:
        count = await session.scalar(select(func.count(ReceivablePayment.id)))
    assert count == 1


async def test_payable_payment_aging_due_filter_and_reminder_are_tenant_scoped(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    payload = claim_payload("PT Jatuh Tempo", "300000.00")
    payload.update({"transaction_date": OVERDUE_TRANSACTION_DATE, "due_date": OVERDUE_DUE_DATE})
    created = await auth_environment.client.post(
        url(auth_environment, "payables"), headers=headers(tokens.access_token), json=payload
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "OVERDUE"
    assert created.json()["status_label"] == "Terlambat"

    filtered = await auth_environment.client.get(
        url(auth_environment, "payables"),
        params={"overdue_only": "true", "due_to": OVERDUE_DUE_DATE},
        headers=headers(tokens.access_token),
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    aging = await auth_environment.client.get(
        url(auth_environment, "obligations/aging"),
        params={"as_of": AGING_AS_OF},
        headers=headers(tokens.access_token),
    )
    assert aging.status_code == 200
    assert aging.json()["payables"]["total_open"] == "300000.00"
    assert aging.json()["payables"]["buckets"][1]["amount"] == "300000.00"

    generated_once = await auth_environment.client.post(
        url(auth_environment, "obligations/reminders/generate"),
        params={"as_of": AGING_AS_OF},
        headers=headers(tokens.access_token),
    )
    generated_twice = await auth_environment.client.post(
        url(auth_environment, "obligations/reminders/generate"),
        params={"as_of": AGING_AS_OF},
        headers=headers(tokens.access_token),
    )
    assert generated_once.status_code == 200
    assert generated_once.json()["generated_count"] == 1
    assert generated_twice.json()["generated_count"] == 0

    other_tenant = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/payables",
        headers=headers(tokens.access_token),
    )
    assert other_tenant.status_code == 403
