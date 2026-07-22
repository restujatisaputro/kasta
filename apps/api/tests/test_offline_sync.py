from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from kasta_api.modules.accounting.models import JournalEntry
from kasta_api.modules.sync.models import SyncConflictRevision, SyncOperationLog

from .conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def transaction_payload(
    amount: str = "25000.00", note: str = "Penjualan offline"
) -> dict[str, object]:
    return {
        "entry_kind": "INCOME",
        "transaction_date": "2026-07-22",
        "amount": amount,
        "category_account": "SALES",
        "counterparty_name": "Pelanggan demo",
        "payment_method": "CASH",
        "note": note,
    }


def operation(
    *,
    operation_id: str,
    local_id: str,
    action: str = "CREATE",
    server_id: str | None = None,
    base_version: int = 0,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "operation_id": operation_id,
        "entity_type": "TRANSACTION",
        "action": action,
        "local_id": local_id,
        "server_id": server_id,
        "base_version": base_version,
        "changed_at": datetime.now(UTC).isoformat(),
        "payload": payload or transaction_payload(),
    }


async def test_offline_create_is_idempotent_and_pulled_by_second_device(
    auth_environment: AuthTestEnvironment,
) -> None:
    first = await login_as(auth_environment, identifier="owner@example.com")
    second = await login_as(auth_environment, identifier="owner@example.com")
    local_id = str(uuid4())
    request = {
        "business_id": str(auth_environment.business_a_id),
        "device_id": "android-device-one",
        "batch_id": "batch-offline-create",
        "operations": [
            operation(
                operation_id="offline-create-operation",
                local_id=local_id,
            )
        ],
    }
    headers = {"Authorization": f"Bearer {first.access_token}"}

    created = await auth_environment.client.post("/api/v1/sync/push", json=request, headers=headers)
    duplicate = await auth_environment.client.post(
        "/api/v1/sync/push", json=request, headers=headers
    )

    assert created.status_code == 200, created.text
    assert duplicate.status_code == 200, duplicate.text
    first_result = created.json()["results"][0]
    assert first_result["status"] == "SYNCED"
    assert first_result["server_version"] == 1
    assert duplicate.json()["results"][0] == first_result
    async with auth_environment.session_factory() as session:
        log_count = await session.scalar(select(func.count(SyncOperationLog.id)))
        assert log_count == 1
        journal_entries = list(await session.scalars(select(JournalEntry)))
        assert len(journal_entries) == 1
        assert journal_entries[0].total_debit == journal_entries[0].total_credit

    pulled = await auth_environment.client.post(
        "/api/v1/sync/pull",
        json={
            "business_id": str(auth_environment.business_a_id),
            "device_id": "android-device-two",
            "cursor": 0,
            "limit": 100,
        },
        headers={"Authorization": f"Bearer {second.access_token}"},
    )
    assert pulled.status_code == 200, pulled.text
    assert len(pulled.json()["changes"]) == 1
    assert pulled.json()["changes"][0]["server_id"] == first_result["server_id"]
    assert pulled.json()["next_cursor"] > 0


async def test_financial_version_conflict_creates_revision_record(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    business_id = str(auth_environment.business_a_id)
    create_response = await auth_environment.client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "business_id": business_id,
            "device_id": "android-primary-device",
            "batch_id": "batch-create-conflict-source",
            "operations": [
                operation(
                    operation_id="create-conflict-source",
                    local_id=str(uuid4()),
                )
            ],
        },
    )
    server_id = create_response.json()["results"][0]["server_id"]

    revised = await auth_environment.client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "business_id": business_id,
            "device_id": "android-primary-device",
            "batch_id": "batch-first-revision",
            "operations": [
                operation(
                    operation_id="first-valid-revision",
                    local_id=str(uuid4()),
                    action="UPSERT",
                    server_id=server_id,
                    base_version=1,
                    payload=transaction_payload("30000.00", "Revisi perangkat pertama"),
                )
            ],
        },
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["results"][0]["server_version"] == 2

    stale = await auth_environment.client.post(
        "/api/v1/sync/push",
        headers=headers,
        json={
            "business_id": business_id,
            "device_id": "android-second-device",
            "batch_id": "batch-stale-revision",
            "operations": [
                operation(
                    operation_id="stale-financial-revision",
                    local_id=str(uuid4()),
                    action="UPSERT",
                    server_id=server_id,
                    base_version=1,
                    payload=transaction_payload("35000.00", "Versi perangkat kedua"),
                )
            ],
        },
    )
    assert stale.status_code == 200, stale.text
    result = stale.json()["results"][0]
    assert result["status"] == "CONFLICT"
    assert result["server_version"] == 2
    assert result["conflict_id"] is not None
    async with auth_environment.session_factory() as session:
        conflict = (
            await session.scalars(
                select(SyncConflictRevision).where(
                    SyncConflictRevision.id == UUID(result["conflict_id"])
                )
            )
        ).one()
        assert conflict.client_version == 1
        assert conflict.server_version == 2
        assert conflict.status == "OPEN"

    status = await auth_environment.client.get(
        "/api/v1/sync/status",
        headers=headers,
        params={"business_id": business_id, "device_id": "android-second-device"},
    )
    assert status.status_code == 200
    assert status.json()["open_conflicts"] == 1


async def test_sync_rejects_business_id_from_another_tenant(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    response = await auth_environment.client.post(
        "/api/v1/sync/pull",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
        json={
            "business_id": str(auth_environment.business_b_id),
            "device_id": "android-wrong-tenant",
            "cursor": 0,
        },
    )
    assert response.status_code == 403
    assert "Token tidak berlaku" in response.text
