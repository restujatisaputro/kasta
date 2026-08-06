from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select
from starlette.datastructures import Headers

from kasta_api.core.config import get_settings
from kasta_api.modules.auth.dependencies import get_password_manager
from kasta_api.modules.auth.security import TokenManager, normalize_identifier, utc_now
from kasta_api.modules.receipts.storage import MAX_RECEIPT_BYTES, ReceiptStorage
from kasta_api.modules.users.models import User
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), "white").save(output, format="PNG")
    return output.getvalue()


async def test_security_headers_and_restricted_cors(
    auth_environment: AuthTestEnvironment,
) -> None:
    response = await auth_environment.client.get("/api/v1/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

    preflight = await auth_environment.client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.headers.get("access-control-allow-origin") is None


async def test_argon2id_short_jwt_and_tamper_rejection() -> None:
    password_manager = get_password_manager()
    encoded = password_manager.hash("Password-panjang-dan-aman-2026")
    assert encoded.startswith("$argon2id$")
    assert password_manager.verify(encoded, "Password-panjang-dan-aman-2026")

    manager = TokenManager(get_settings())
    from uuid import uuid4

    token = manager.create_access_token(uuid4(), uuid4(), uuid4())
    claims = manager.decode_access_token(token)
    assert 0 < (claims.expires_at - utc_now()).total_seconds() <= 15 * 60
    with pytest.raises(ValueError, match="Token akses tidak valid"):
        manager.decode_access_token(f"{token[:-1]}x")


async def test_demo_seed_email_domain_can_be_normalized() -> None:
    assert normalize_identifier(" Demo.Owner01@Example.Test ") == (
        "EMAIL",
        "demo.owner01@example.test",
    )


async def test_cookie_only_authentication_and_sql_injection_are_rejected(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    cookie_only = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/auth/authorization",
        headers={"Cookie": f"access_token={tokens.access_token}"},
    )
    assert cookie_only.status_code == 401

    injection = await auth_environment.client.post(
        "/api/v1/auth/login",
        json={
            "business_id": str(auth_environment.business_a_id),
            "identifier": "' OR 1=1 --@example.com",
            "password": "anything",
            "device_id": "security-test-device",
            "platform": "WEB",
        },
    )
    assert injection.status_code in {401, 422}


async def test_account_lock_is_enforced_across_ip_rate_keys(
    auth_environment: AuthTestEnvironment,
) -> None:
    async with auth_environment.session_factory() as session:
        user = await session.scalar(select(User).where(User.id == auth_environment.owner_id))
        assert user is not None
        user.failed_login_attempts = 10
        user.locked_until = utc_now() + timedelta(minutes=10)
        await session.commit()

    response = await auth_environment.client.post(
        "/api/v1/auth/login",
        json={
            "business_id": str(auth_environment.business_a_id),
            "identifier": "owner@example.com",
            "password": auth_environment.password,
            "device_id": "locked-account-device",
            "platform": "WEB",
        },
    )
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


async def test_upload_rejects_mime_mismatch_and_oversize() -> None:
    storage = ReceiptStorage(get_settings())
    mismatch = UploadFile(
        file=BytesIO(_png()),
        filename="nota.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )
    with pytest.raises(Exception) as mismatch_error:
        await storage.validate_upload(mismatch)
    assert getattr(mismatch_error.value, "status_code", None) == 422

    oversize = UploadFile(
        file=BytesIO(b"x" * (MAX_RECEIPT_BYTES + 1)),
        filename="besar.png",
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(Exception) as size_error:
        await storage.validate_upload(oversize)
    assert getattr(size_error.value, "status_code", None) == 413


async def test_personal_export_and_account_deletion_controls(
    auth_environment: AuthTestEnvironment,
) -> None:
    staff = await login_as(auth_environment, identifier="staff@example.com")
    export = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_a_id}/privacy/export",
        headers=_headers(staff.access_token),
    )
    assert export.status_code == 200, export.text
    assert export.json()["subject_user_id"] == str(auth_environment.staff_id)
    assert export.json()["profile"]["email"] == "staff@example.com"

    wrong_password = await auth_environment.client.post(
        f"/api/v1/businesses/{auth_environment.business_a_id}/privacy/account-deletion",
        headers=_headers(staff.access_token),
        json={"current_password": "wrong", "confirmation": "HAPUS AKUN"},
    )
    assert wrong_password.status_code == 401

    deleted = await auth_environment.client.post(
        f"/api/v1/businesses/{auth_environment.business_a_id}/privacy/account-deletion",
        headers=_headers(staff.access_token),
        json={
            "current_password": auth_environment.password,
            "confirmation": "HAPUS AKUN",
            "reason": "Pengujian penghapusan mandiri",
        },
    )
    assert deleted.status_code == 202, deleted.text
    async with auth_environment.session_factory() as session:
        user = await session.get(User, auth_environment.staff_id)
        assert user is not None
        assert user.deleted_at is not None
        assert user.email is not None and user.email.endswith("@deleted.invalid")
        assert user.full_name == "Pengguna dihapus"


async def test_last_business_owner_cannot_orphan_business(
    auth_environment: AuthTestEnvironment,
) -> None:
    owner = await login_as(auth_environment, identifier="owner@example.com")
    response = await auth_environment.client.post(
        f"/api/v1/businesses/{auth_environment.business_a_id}/privacy/account-deletion",
        headers=_headers(owner.access_token),
        json={
            "current_password": auth_environment.password,
            "confirmation": "HAPUS AKUN",
        },
    )
    assert response.status_code == 409
