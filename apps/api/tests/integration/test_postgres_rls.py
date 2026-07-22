"""PostgreSQL RLS verification for the runtime database role.

The normal test suite uses SQLite for speed and therefore cannot exercise
PostgreSQL row-level security.  Set ``KASTA_TEST_DATABASE_URL`` to a
PostgreSQL URL for this test.  The URL must use the non-owner runtime role
(the role used by the API), otherwise PostgreSQL's owner bypass would make
the test meaningless.

The test inserts two synthetic rows in one rolled-back transaction and proves
that a business actor can only read rows for the business in its context.
No production data is modified or retained.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


def _database_url() -> str:
    raw_url = os.getenv("KASTA_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("KASTA_TEST_DATABASE_URL tidak diatur; test PostgreSQL dilewati")
    if raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url.removeprefix("postgres://")
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url.removeprefix("postgresql://")
    if raw_url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + raw_url.removeprefix("postgresql+asyncpg://")
    return raw_url


async def _set_context(
    connection: AsyncConnection,
    *,
    user_id: str,
    business_id: str,
) -> None:
    await connection.execute(
        text("SELECT set_config(:name, :value, true)"),
        {"name": "app.user_id", "value": user_id},
    )
    await connection.execute(
        text("SELECT set_config(:name, :value, true)"),
        {"name": "app.business_id", "value": business_id},
    )
    await connection.execute(
        text("SELECT set_config(:name, :value, true)"),
        {"name": "app.actor_type", "value": "BUSINESS"},
    )
    # Clear mentor/support context so a stale pooled connection cannot widen
    # the effective policy during this assertion.
    for name in ("app.mentor_id", "app.support_grant_id"):
        await connection.execute(
            text("SELECT set_config(:name, '', true)"),
            {"name": name},
        )


async def test_transactions_rls_is_enabled_and_business_policy_is_scoped() -> None:
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            rls_info = (
                await connection.execute(
                    text(
                        """
                        SELECT c.relrowsecurity,
                               c.relforcerowsecurity,
                               r.rolsuper,
                               r.rolbypassrls
                          FROM pg_class
                          JOIN pg_roles AS r ON r.rolname = current_user
                         WHERE pg_class.oid = 'transactions'::regclass
                        """
                    )
                )
            ).one_or_none()
            if rls_info is None:
                pytest.fail(
                    "Tabel transactions belum ada; jalankan seluruh migration terlebih dahulu"
                )
            assert rls_info.relrowsecurity, "RLS transactions harus diaktifkan"
            assert rls_info.relforcerowsecurity, "RLS transactions harus FORCE"
            assert not rls_info.rolsuper, "Test harus memakai role runtime, bukan SUPERUSER"
            assert not rls_info.rolbypassrls, "Role runtime tidak boleh BYPASSRLS"

            policy_names = {
                row.policy_name
                for row in (
                    await connection.execute(
                        text(
                            """
                            SELECT policyname AS policy_name
                              FROM pg_policies
                             WHERE schemaname = current_schema()
                               AND tablename = 'transactions'
                            """
                        )
                    )
                ).all()
            }
            assert {
                "transactions_business_all",
                "transactions_mentor_read",
                "transactions_support_read",
            } <= policy_names

            memberships = (
                await connection.execute(
                    text(
                        """
                        SELECT DISTINCT ON (m.business_id)
                               m.business_id::text AS business_id,
                               m.user_id::text AS user_id
                          FROM business_members AS m
                         WHERE m.status = 'ACTIVE'
                         ORDER BY m.business_id, m.user_id
                         LIMIT 2
                        """
                    )
                )
            ).all()
            if len(memberships) < 2:
                pytest.skip("Fixture PostgreSQL membutuhkan sedikitnya dua UMKM aktif")
            business_a, business_b = memberships

            # SQLAlchemy starts an implicit transaction for the catalog and
            # membership queries above.  End it before opening the explicit
            # rollback-only transaction that contains synthetic rows.
            await connection.rollback()
            transaction = await connection.begin()
            try:
                # Insert one synthetic transaction for each tenant.  Both
                # inserts are policy-checked and the enclosing transaction is
                # always rolled back in finally.
                for business, user in ((business_a, business_a), (business_b, business_b)):
                    await _set_context(
                        connection,
                        user_id=user.user_id,
                        business_id=business.business_id,
                    )
                    await connection.execute(
                        text(
                            """
                            INSERT INTO transactions (
                              id, business_id, transaction_number, transaction_type,
                              transaction_date, amount, description, status,
                              revision_number, posted_at, posted_by_user_id
                            ) VALUES (
                              :id, :business_id, :number, 'CASH_SALE', CURRENT_DATE,
                              1.00, 'RLS synthetic test', 'POSTED', 1, now(), :user_id
                            )
                            """
                        ),
                        {
                            "id": str(uuid4()),
                            "business_id": business.business_id,
                            "number": f"RLS-{uuid4().hex[:16]}",
                            "user_id": user.user_id,
                        },
                    )

                await _set_context(
                    connection,
                    user_id=business_a.user_id,
                    business_id=business_a.business_id,
                )
                visible = {
                    row.business_id
                    for row in (
                        await connection.execute(text("SELECT business_id::text FROM transactions"))
                    ).all()
                }
                assert visible == {business_a.business_id}

                await _set_context(
                    connection,
                    user_id=business_b.user_id,
                    business_id=business_b.business_id,
                )
                visible = {
                    row.business_id
                    for row in (
                        await connection.execute(text("SELECT business_id::text FROM transactions"))
                    ).all()
                }
                assert visible == {business_b.business_id}
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
