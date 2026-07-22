from datetime import date, time
from uuid import uuid4

import pytest

from kasta_api.modules.notifications.models import NotificationPreference
from kasta_api.modules.notifications.service import NotificationService
from tests.conftest import AuthTestEnvironment, login_as


@pytest.mark.anyio
async def test_preferences_inbox_read_and_tenant_isolation(
    auth_environment: AuthTestEnvironment,
) -> None:
    owner = await login_as(auth_environment, identifier="owner@example.com")
    headers = {"Authorization": f"Bearer {owner.access_token}"}
    base = f"/api/v1/businesses/{auth_environment.business_a_id}/notifications"

    preferences = await auth_environment.client.get(f"{base}/preferences", headers=headers)
    assert preferences.status_code == 200, preferences.text
    assert len(preferences.json()) == 10

    updated = await auth_environment.client.put(
        f"{base}/preferences",
        headers=headers,
        json={
            "items": [
                {
                    "category": "LOW_STOCK",
                    "enabled": False,
                    "local_enabled": False,
                    "push_enabled": False,
                    "email_enabled": False,
                    "reminder_time": "19:30:00",
                    "quiet_hours_start": "21:00:00",
                    "quiet_hours_end": "07:00:00",
                    "timezone": "Asia/Jakarta",
                }
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    low_stock = next(item for item in updated.json() if item["category"] == "LOW_STOCK")
    assert low_stock["enabled"] is False
    assert low_stock["reminder_time"] == "19:30:00"

    generated = await auth_environment.client.post(
        f"{base}/evaluate?as_of={date.today().isoformat()}", headers=headers
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["generated_count"] >= 1

    inbox = await auth_environment.client.get(base, headers=headers)
    assert inbox.status_code == 200, inbox.text
    unread = await auth_environment.client.get(f"{base}/unread-count", headers=headers)
    assert unread.json()["unread_count"] == 1
    item = inbox.json()[0]
    assert item["notification_type"] == "NO_TRANSACTION_TODAY"
    assert item["action_path"] == "/transaksi"

    marked = await auth_environment.client.post(f"{base}/{item['id']}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    wrong_tenant = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/notifications",
        headers=headers,
    )
    assert wrong_tenant.status_code == 403


@pytest.mark.anyio
async def test_notification_is_visible_only_to_recipient(
    auth_environment: AuthTestEnvironment,
) -> None:
    owner = await login_as(auth_environment, identifier="owner@example.com")
    staff = await login_as(auth_environment, identifier="staff@example.com")
    base = f"/api/v1/businesses/{auth_environment.business_a_id}/notifications"

    await auth_environment.client.post(
        f"{base}/evaluate?as_of={date.today().isoformat()}",
        headers={"Authorization": f"Bearer {owner.access_token}"},
    )
    await auth_environment.client.post(
        f"{base}/evaluate?as_of={date.today().isoformat()}",
        headers={"Authorization": f"Bearer {staff.access_token}"},
    )
    owner_inbox = await auth_environment.client.get(
        base, headers={"Authorization": f"Bearer {owner.access_token}"}
    )
    staff_inbox = await auth_environment.client.get(
        base, headers={"Authorization": f"Bearer {staff.access_token}"}
    )
    assert owner_inbox.status_code == 200
    assert staff_inbox.status_code == 200
    owner_id = owner_inbox.json()[0]["id"]
    staff_id = staff_inbox.json()[0]["id"]
    assert owner_id != staff_id

    cannot_mark_other_recipient = await auth_environment.client.post(
        f"{base}/{staff_id}/read",
        headers={"Authorization": f"Bearer {owner.access_token}"},
    )
    assert cannot_mark_other_recipient.status_code == 404


def test_quiet_hours_rolls_notification_to_morning() -> None:
    preference = NotificationPreference(
        id=uuid4(),
        business_id=uuid4(),
        user_id=uuid4(),
        category="NO_TRANSACTION_TODAY",
        reminder_time=time(22, 0),
        quiet_hours_start=time(21, 0),
        quiet_hours_end=time(7, 0),
        timezone="Asia/Jakarta",
    )

    result = NotificationService.next_allowed_at(preference, date(2099, 1, 1))

    assert result.isoformat() == "2099-01-02T00:00:00+00:00"
