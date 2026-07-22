from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import get_password_manager
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.mentors.models import Mentor, MentorBusinessAccess
from kasta_api.modules.users.models import User
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def seed_mentor(
    environment: AuthTestEnvironment, business_ids: list[UUID]
) -> tuple[str, UUID]:
    email = f"mentor-{uuid4()}@example.com"
    user_id = uuid4()
    mentor_id = uuid4()
    async with environment.session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                password_hash=get_password_manager().hash(environment.password),
                full_name="Pembina KASTA",
                email_verified_at=utc_now(),
            )
        )
        session.add(Mentor(id=mentor_id, user_id=user_id, status="ACTIVE"))
        session.add_all(
            [
                MentorBusinessAccess(
                    id=uuid4(),
                    mentor_id=mentor_id,
                    business_id=business_id,
                    role_id=role_id(RoleCode.MENTOR),
                    requested_by_user_id=user_id,
                    granted_by_user_id=user_id,
                    status="ACTIVE",
                    scope=[
                        "SUMMARY",
                        "REPORTS",
                        "RECEIPTS",
                        "INVENTORY",
                        "OBLIGATIONS",
                        "EXPORT_REPORTS",
                    ],
                    requested_at=utc_now(),
                    granted_at=utc_now(),
                    expires_at=utc_now() + timedelta(days=90),
                )
                for business_id in business_ids
            ]
        )
        await session.commit()
    return email, mentor_id


async def post_income(environment: AuthTestEnvironment, token: str) -> None:
    response = await environment.client.post(
        f"/api/v1/businesses/{environment.business_a_id}/transactions",
        headers=headers(token),
        json={
            "entry_kind": "INCOME",
            "transaction_date": date.today().isoformat(),
            "amount": "15000000.00",
            "category_account": "SALES",
            "payment_method": "CASH",
            "note": "Penjualan bulan berjalan",
        },
    )
    assert response.status_code == 201, response.text


async def test_dashboard_is_journal_backed_and_mentor_cannot_write_transactions(
    auth_environment: AuthTestEnvironment,
) -> None:
    owner = await login_as(auth_environment, identifier="owner@example.com")
    await post_income(auth_environment, owner.access_token)
    email, _ = await seed_mentor(
        auth_environment,
        [auth_environment.business_a_id, auth_environment.business_b_id],
    )
    mentor = await login_as(auth_environment, identifier=email)

    response = await auth_environment.client.get(
        "/api/v1/mentors/me/dashboard", headers=headers(mentor.access_token)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_businesses"] == 2
    assert body["active_businesses"] == 1
    assert body["stale_businesses"] == 1
    assert body["health_red"] == 1
    business_a = next(
        item
        for item in body["businesses"]
        if item["business_id"] == str(auth_environment.business_a_id)
    )
    assert business_a["month_revenue"] == "15000000.00"
    assert business_a["month_profit"] == "15000000.00"
    assert business_a["health_label"] == "Perlu perhatian"
    assert business_a["health_icon"]

    detail = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_a_id}",
        headers=headers(mentor.access_token),
    )
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["revenue_trend"]) == 6
    assert detail.json()["revenue_trend"][-1]["revenue"] == "15000000.00"

    forbidden = await auth_environment.client.post(
        f"/api/v1/businesses/{auth_environment.business_a_id}/transactions",
        headers=headers(mentor.access_token),
        json={
            "entry_kind": "INCOME",
            "transaction_date": date.today().isoformat(),
            "amount": "1000.00",
            "category_account": "SALES",
            "payment_method": "CASH",
            "note": "Tidak boleh dibuat pembina",
        },
    )
    assert forbidden.status_code == 403


async def test_notes_recommendations_sessions_notifications_and_audit(
    auth_environment: AuthTestEnvironment,
) -> None:
    email, _ = await seed_mentor(auth_environment, [auth_environment.business_a_id])
    mentor = await login_as(auth_environment, identifier=email)
    owner = await login_as(auth_environment, identifier="owner@example.com")
    root = f"/api/v1/mentors/me/businesses/{auth_environment.business_a_id}"

    note = await auth_environment.client.post(
        f"{root}/notes",
        headers=headers(mentor.access_token),
        json={"content": "Pisahkan uang usaha dari uang pribadi.", "visibility": "SHARED"},
    )
    assert note.status_code == 201, note.text

    recommendation = await auth_environment.client.post(
        f"{root}/recommendations",
        headers=headers(mentor.access_token),
        json={
            "title": "Catat setiap hari",
            "description": "Sisihkan sepuluh menit setelah toko tutup.",
            "priority": "HIGH",
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
        },
    )
    assert recommendation.status_code == 201, recommendation.text
    recommendation_id = recommendation.json()["id"]
    started = await auth_environment.client.patch(
        f"{root}/recommendations/{recommendation_id}",
        headers=headers(mentor.access_token),
        json={"status": "IN_PROGRESS", "follow_up_note": "Mulai ditindaklanjuti."},
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "IN_PROGRESS"
    completed = await auth_environment.client.patch(
        f"{root}/recommendations/{recommendation_id}",
        headers=headers(mentor.access_token),
        json={"status": "DONE", "follow_up_note": "Sudah diterapkan oleh pemilik."},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "DONE"
    assert completed.json()["completed_at"] is not None

    meeting = await auth_environment.client.post(
        f"{root}/sessions",
        headers=headers(mentor.access_token),
        json={
            "scheduled_at": (utc_now() + timedelta(days=2)).isoformat(),
            "duration_minutes": 60,
            "mode": "ONLINE",
            "topic": "Evaluasi arus uang",
            "location": "https://meeting.example.test/kasta",
        },
    )
    assert meeting.status_code == 201, meeting.text
    meeting_id = meeting.json()["id"]
    finished = await auth_environment.client.patch(
        f"{root}/sessions/{meeting_id}",
        headers=headers(mentor.access_token),
        json={
            "status": "COMPLETED",
            "outcome": "Pemilik memahami pemisahan uang usaha.",
            "follow_up_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == "COMPLETED"

    notifications = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/notifications",
        headers=headers(owner.access_token),
    )
    assert notifications.status_code == 200, notifications.text
    titles = {item["title"] for item in notifications.json()}
    assert {
        "Catatan baru dari pembina",
        "Rekomendasi baru dari pembina",
        "Jadwal pendampingan baru",
    }.issubset(titles)

    audit = await auth_environment.client.get(
        "/api/v1/mentors/me/audit", headers=headers(mentor.access_token)
    )
    assert audit.status_code == 200, audit.text
    actions = {item["action"] for item in audit.json()}
    assert {
        "MENTOR_NOTE_CREATED",
        "MENTOR_RECOMMENDATION_CREATED",
        "MENTOR_RECOMMENDATION_UPDATED",
        "MENTOR_SESSION_SCHEDULED",
        "MENTOR_SESSION_UPDATED",
    }.issubset(actions)


async def test_mentor_business_access_is_isolated_and_exports_are_valid(
    auth_environment: AuthTestEnvironment,
) -> None:
    email, _ = await seed_mentor(auth_environment, [auth_environment.business_a_id])
    mentor = await login_as(auth_environment, identifier=email)

    other_business = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_b_id}",
        headers=headers(mentor.access_token),
    )
    assert other_business.status_code == 404

    report = await auth_environment.client.get(
        "/api/v1/mentors/me/report", headers=headers(mentor.access_token)
    )
    assert report.status_code == 200, report.text
    assert report.json()["dashboard"]["total_businesses"] == 1

    expected = {
        "PDF": ("application/pdf", b"%PDF"),
        "XLSX": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            b"PK",
        ),
        "CSV": ("text/csv", b"\xef\xbb\xbf"),
    }
    for format_name, (content_type, signature) in expected.items():
        exported = await auth_environment.client.get(
            "/api/v1/mentors/me/report/export",
            params={"format": format_name},
            headers=headers(mentor.access_token),
        )
        assert exported.status_code == 200, exported.text
        assert content_type in exported.headers["content-type"]
        assert exported.content.startswith(signature)
