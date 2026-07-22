from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import get_password_manager
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.mentors.models import MentorBusinessAccess, SupportAccessGrant
from kasta_api.modules.users.models import User
from tests.conftest import AuthTestEnvironment, login_as
from tests.test_mentors import headers, seed_mentor

pytestmark = pytest.mark.anyio


async def test_owner_approves_scoped_access_and_revoke_stops_access_immediately(
    auth_environment: AuthTestEnvironment,
) -> None:
    mentor_email, _ = await seed_mentor(auth_environment, [auth_environment.business_a_id])
    mentor = await login_as(auth_environment, identifier=mentor_email)

    hidden = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_b_id}",
        headers=headers(mentor.access_token),
    )
    assert hidden.status_code == 404

    requested = await auth_environment.client.post(
        "/api/v1/mentors/me/access-requests",
        headers=headers(mentor.access_token),
        json={
            "business_id": str(auth_environment.business_b_id),
            "requested_scope": ["SUMMARY", "REPORTS"],
            "message": "Perlu meninjau perkembangan usaha.",
        },
    )
    assert requested.status_code == 201, requested.text
    access_id = requested.json()["id"]
    assert requested.json()["status"] == "REQUESTED"

    owner_b = await login_as(
        auth_environment,
        identifier="owner-b@example.com",
        business_id=auth_environment.business_b_id,
    )
    approved = await auth_environment.client.patch(
        f"/api/v1/businesses/{auth_environment.business_b_id}/mentor-access/{access_id}/decision",
        headers=headers(owner_b.access_token),
        json={
            "decision": "APPROVE",
            "scope": ["SUMMARY", "REPORTS"],
            "expires_at": (utc_now() + timedelta(days=30)).isoformat(),
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "ACTIVE"
    assert set(approved.json()["scope"]) == {"SUMMARY", "REPORTS"}

    visible = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_b_id}",
        headers=headers(mentor.access_token),
    )
    assert visible.status_code == 200, visible.text

    revoked = await auth_environment.client.post(
        f"/api/v1/businesses/{auth_environment.business_b_id}/mentor-access/{access_id}/revoke",
        headers=headers(owner_b.access_token),
        json={"reason": "Pendampingan telah selesai."},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "REVOKED"

    no_longer_visible = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_b_id}",
        headers=headers(mentor.access_token),
    )
    assert no_longer_visible.status_code == 404

    history = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/mentor-access/history",
        headers=headers(owner_b.access_token),
    )
    assert history.status_code == 200, history.text
    actions = {item["action"] for item in history.json()}
    assert {
        "MENTOR_ACCESS_REQUESTED",
        "MENTOR_ACCESS_APPROVED",
        "MENTOR_DATA_ACCESSED",
        "MENTOR_ACCESS_REVOKED",
    }.issubset(actions)


async def test_staff_cannot_decide_mentor_access(
    auth_environment: AuthTestEnvironment,
) -> None:
    staff = await login_as(auth_environment, identifier="staff@example.com")
    response = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/mentor-access",
        headers=headers(staff.access_token),
    )
    assert response.status_code == 403


async def test_scope_does_not_grant_unapproved_data(
    auth_environment: AuthTestEnvironment,
) -> None:
    mentor_email, _ = await seed_mentor(auth_environment, [auth_environment.business_a_id])
    mentor = await login_as(auth_environment, identifier=mentor_email)
    response = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/transactions",
        headers=headers(mentor.access_token),
    )
    assert response.status_code == 403


async def test_expired_mentor_access_is_denied_without_manual_revocation(
    auth_environment: AuthTestEnvironment,
) -> None:
    mentor_email, mentor_id = await seed_mentor(auth_environment, [auth_environment.business_a_id])
    mentor = await login_as(auth_environment, identifier=mentor_email)
    now = utc_now()
    async with auth_environment.session_factory() as session:
        access = (
            await session.scalars(
                select(MentorBusinessAccess).where(
                    MentorBusinessAccess.mentor_id == mentor_id,
                    MentorBusinessAccess.business_id == auth_environment.business_a_id,
                )
            )
        ).one()
        access.granted_at = now - timedelta(days=2)
        access.expires_at = now - timedelta(days=1)
        await session.commit()

    detail = await auth_environment.client.get(
        f"/api/v1/mentors/me/businesses/{auth_environment.business_a_id}",
        headers=headers(mentor.access_token),
    )
    dashboard = await auth_environment.client.get(
        "/api/v1/mentors/me/dashboard",
        headers=headers(mentor.access_token),
    )

    assert detail.status_code == 403
    assert dashboard.status_code == 403
    assert "pembina UMKM" in detail.json()["detail"]


async def test_admin_requires_recorded_time_bound_support_grant(
    auth_environment: AuthTestEnvironment,
) -> None:
    admin_id = uuid4()
    now = utc_now()
    async with auth_environment.session_factory() as session:
        session.add(
            User(
                id=admin_id,
                platform_role_id=role_id(RoleCode.SUPER_ADMIN),
                email="support@example.com",
                password_hash=get_password_manager().hash(auth_environment.password),
                full_name="Dukungan KASTA",
                email_verified_at=now,
            )
        )
        await session.commit()

    admin = await login_as(auth_environment, identifier="support@example.com")
    endpoint = f"/api/v1/businesses/{auth_environment.business_a_id}/transactions"
    denied = await auth_environment.client.get(endpoint, headers=headers(admin.access_token))
    assert denied.status_code == 403

    grant_id = uuid4()
    async with auth_environment.session_factory() as session:
        session.add(
            SupportAccessGrant(
                id=grant_id,
                business_id=auth_environment.business_a_id,
                admin_user_id=admin_id,
                granted_by_user_id=auth_environment.owner_id,
                scope=["TRANSACTIONS"],
                reason="Menangani tiket gagal menampilkan transaksi.",
                ticket_reference="SUP-2026-0001",
                status="ACTIVE",
                granted_at=now,
                expires_at=now + timedelta(hours=2),
            )
        )
        await session.commit()

    allowed = await auth_environment.client.get(endpoint, headers=headers(admin.access_token))
    assert allowed.status_code == 200, allowed.text
    async with auth_environment.session_factory() as session:
        audit = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.actor_user_id == admin_id,
                    AuditLog.action == "ADMIN_SUPPORT_DATA_ACCESSED",
                )
            )
        ).one()
        grant = await session.get(SupportAccessGrant, grant_id)
        assert audit.after_data is not None
        assert audit.after_data["support_grant_id"] == str(grant_id)
        assert grant is not None and grant.last_accessed_at is not None


async def test_owner_can_create_list_and_revoke_official_support_grant(
    auth_environment: AuthTestEnvironment,
) -> None:
    admin_id = uuid4()
    now = utc_now()
    async with auth_environment.session_factory() as session:
        session.add(
            User(
                id=admin_id,
                platform_role_id=role_id(RoleCode.SUPER_ADMIN),
                email="official-support@example.com",
                password_hash=get_password_manager().hash(auth_environment.password),
                full_name="Dukungan Resmi KASTA",
                email_verified_at=now,
            )
        )
        await session.commit()

    owner = await login_as(auth_environment, identifier="owner@example.com")
    endpoint = f"/api/v1/businesses/{auth_environment.business_a_id}/support-access-grants"
    created = await auth_environment.client.post(
        endpoint,
        headers=headers(owner.access_token),
        json={
            "admin_user_id": str(admin_id),
            "scope": ["TRANSACTIONS", "REPORTS"],
            "reason": "Menyelidiki tiket laporan transaksi yang gagal dibuka.",
            "ticket_reference": "sup-2026-0099",
            "expires_at": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["ticket_reference"] == "SUP-2026-0099"
    grant_id = created.json()["id"]

    listed = await auth_environment.client.get(endpoint, headers=headers(owner.access_token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [grant_id]

    revoked = await auth_environment.client.post(
        f"{endpoint}/{grant_id}/revoke",
        headers=headers(owner.access_token),
        json={"reason": "Tiket dukungan telah selesai."},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "REVOKED"

    async with auth_environment.session_factory() as session:
        actions = set(
            await session.scalars(
                select(AuditLog.action).where(
                    AuditLog.entity_id == UUID(grant_id),
                    AuditLog.actor_user_id == auth_environment.owner_id,
                )
            )
        )
        assert actions == {
            "ADMIN_SUPPORT_GRANT_CREATED",
            "ADMIN_SUPPORT_GRANT_REVOKED",
        }
