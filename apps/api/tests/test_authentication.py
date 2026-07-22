from uuid import UUID

import pytest
from sqlalchemy import select

from kasta_api.modules.auth.dependencies import get_outbox_cipher
from kasta_api.modules.auth.models import AuthDeliveryOutbox
from kasta_api.modules.auth.schemas import TokenPairResponse
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


async def _latest_delivery_token(environment: AuthTestEnvironment, user_id: UUID) -> str:
    async with environment.session_factory() as session:
        message = await session.scalar(
            select(AuthDeliveryOutbox)
            .where(AuthDeliveryOutbox.user_id == user_id)
            .order_by(AuthDeliveryOutbox.created_at.desc())
            .limit(1)
        )
        assert message is not None
        payload = get_outbox_cipher().decrypt(message.payload_nonce, message.payload_ciphertext)
        return payload["token"]


async def test_login_refresh_rotation_and_reuse_revokes_session(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="OWNER@example.com")
    refresh_response = await auth_environment.client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens.refresh_token}
    )
    assert refresh_response.status_code == 200
    rotated = TokenPairResponse.model_validate(refresh_response.json())
    assert rotated.refresh_token != tokens.refresh_token

    replay_response = await auth_environment.client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens.refresh_token}
    )
    assert replay_response.status_code == 401

    rotated_after_replay = await auth_environment.client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated.refresh_token}
    )
    assert rotated_after_replay.status_code == 401
    protected = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/authorization",
        headers={"Authorization": f"Bearer {rotated.access_token}"},
    )
    assert protected.status_code == 401


async def test_phone_login_accepts_indonesian_local_format(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="0812-3456-7890")
    assert tokens.token_type == "bearer"


async def test_email_verification_then_login(auth_environment: AuthTestEnvironment) -> None:
    before = await auth_environment.client.post(
        "/api/v1/auth/login",
        json={
            "business_id": str(auth_environment.business_a_id),
            "identifier": "unverified@example.com",
            "password": auth_environment.password,
            "device_id": "unverified-test-device",
            "platform": "WEB",
        },
    )
    assert before.status_code == 403

    requested = await auth_environment.client.post(
        "/api/v1/auth/verification/request",
        json={"identifier": "unverified@example.com"},
    )
    assert requested.status_code == 202
    raw_token = await _latest_delivery_token(auth_environment, auth_environment.unverified_user_id)
    confirmed = await auth_environment.client.post(
        "/api/v1/auth/verification/confirm", json={"token": raw_token}
    )
    assert confirmed.status_code == 200
    await login_as(auth_environment, identifier="unverified@example.com")


async def test_password_reset_revokes_all_existing_sessions(
    auth_environment: AuthTestEnvironment,
) -> None:
    existing = await login_as(auth_environment, identifier="owner@example.com")
    forgot = await auth_environment.client.post(
        "/api/v1/auth/password/forgot", json={"identifier": "owner@example.com"}
    )
    assert forgot.status_code == 202
    raw_token = await _latest_delivery_token(auth_environment, auth_environment.owner_id)
    reset = await auth_environment.client.post(
        "/api/v1/auth/password/reset",
        json={"token": raw_token, "new_password": "Password-baru-yang-aman-2026"},
    )
    assert reset.status_code == 200
    old_access = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/authorization",
        headers={"Authorization": f"Bearer {existing.access_token}"},
    )
    assert old_access.status_code == 401
    await login_as(
        auth_environment,
        identifier="owner@example.com",
        password="Password-baru-yang-aman-2026",
    )


async def test_login_rate_limit(auth_environment: AuthTestEnvironment) -> None:
    statuses: list[int] = []
    for index in range(5):
        response = await auth_environment.client.post(
            "/api/v1/auth/login",
            json={
                "business_id": str(auth_environment.business_a_id),
                "identifier": "staff@example.com",
                "password": "password-salah",
                "device_id": f"rate-limit-device-{index}",
                "platform": "WEB",
            },
        )
        statuses.append(response.status_code)
    assert statuses == [401, 401, 401, 401, 429]
    assert int(response.headers["Retry-After"]) > 0


async def test_logout_one_and_all_devices(auth_environment: AuthTestEnvironment) -> None:
    first = await login_as(auth_environment, identifier="owner@example.com")
    second = await login_as(auth_environment, identifier="owner@example.com")
    sessions = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/sessions",
        headers={"Authorization": f"Bearer {first.access_token}"},
    )
    assert sessions.status_code == 200
    first_session_id = next(item["id"] for item in sessions.json() if item["is_current"])
    one_logout = await auth_environment.client.delete(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/sessions/{first_session_id}",
        headers={"Authorization": f"Bearer {first.access_token}"},
    )
    assert one_logout.status_code == 204
    all_logout = await auth_environment.client.delete(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/sessions",
        headers={"Authorization": f"Bearer {second.access_token}"},
    )
    assert all_logout.status_code == 200
