from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from kasta_api.db import models as _mapped_models  # noqa: F401
from kasta_api.db.base import Base
from kasta_api.modules.accounting.models import FinancialTransaction, JournalEntry, JournalLine
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.businesses.models import Business, Organization
from kasta_api.modules.inventory.models import Product
from kasta_api.modules.mentors.models import (
    Mentor,
    MentorBusinessAccess,
    MentoringSession,
    Recommendation,
)
from kasta_api.modules.obligations.models import (
    Payable,
    PayablePayment,
    Receivable,
    ReceivablePayment,
)
from kasta_api.modules.receipts.models import Receipt
from kasta_api.modules.users.models import User
from kasta_api.seed_demo import DemoSeedCounts, seed_demo_data


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def demo_session() -> tuple[async_sessionmaker[AsyncSession], object]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with factory() as session:
            yield factory, session
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_demo_seed_has_requested_counts_and_balanced_journals(demo_session) -> None:
    _factory, session = demo_session
    counts = await seed_demo_data(session)
    assert counts == DemoSeedCounts()

    expected = {
        Organization: 1,
        Mentor: 3,
        Business: 10,
        User: 20,
        Product: 100,
        FinancialTransaction: 500,
        JournalEntry: 500,
        JournalLine: 1000,
        Payable: 30,
        Receivable: 30,
        PayablePayment: 15,
        ReceivablePayment: 15,
        Receipt: 100,
        Recommendation: 20,
        MentoringSession: 20,
        AuditLog: 500,
    }
    for model, total in expected.items():
        assert len((await session.scalars(select(model))).all()) == total

    entries = list((await session.scalars(select(JournalEntry))).all())
    lines = list((await session.scalars(select(JournalLine))).all())
    by_entry: dict[object, list[JournalLine]] = defaultdict(list)
    for line in lines:
        by_entry[line.journal_entry_id].append(line)
    assert all(entry.total_debit == entry.total_credit for entry in entries)
    assert all(
        sum((line.debit_amount for line in by_entry[entry.id]), Decimal("0.00"))
        == sum((line.credit_amount for line in by_entry[entry.id]), Decimal("0.00"))
        == entry.total_debit
        for entry in entries
    )
    assert all(len(by_entry[entry.id]) == 2 for entry in entries)
    payables = list((await session.scalars(select(Payable))).all())
    receivables = list((await session.scalars(select(Receivable))).all())
    assert all(
        obligation.due_date < date.today()
        for obligation in [*payables, *receivables]
        if obligation.status == "OVERDUE"
    )
    accesses = list((await session.scalars(select(MentorBusinessAccess))).all())
    assert len(accesses) >= 10
    assert all(
        set(access.scope)
        >= {"SUMMARY", "REPORTS", "TRANSACTIONS", "RECEIPTS", "INVENTORY", "OBLIGATIONS"}
        for access in accesses
        if len(access.scope) > 2
    )


@pytest.mark.anyio
async def test_demo_seed_is_idempotent_and_contains_only_fictitious_users(demo_session) -> None:
    _factory, session = demo_session
    await seed_demo_data(session)
    await seed_demo_data(session)

    users = list((await session.scalars(select(User))).all())
    assert len(users) == 20
    assert all(user.email and user.email.endswith("@example.test") for user in users)
    assert all("@example.test" in (user.email or "") for user in users)
    assert len((await session.scalars(select(FinancialTransaction))).all()) == 500
    assert len((await session.scalars(select(Receipt))).all()) == 100
