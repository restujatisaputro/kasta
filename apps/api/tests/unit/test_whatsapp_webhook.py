from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient, Response
from pydantic import ValidationError

from kasta_api.core.config import Settings, get_settings
from kasta_api.main import app

WEBHOOK_PATH = "/api/v1/webhooks/whatsapp"
VERIFY_TOKEN = "token-verifikasi-tes"
APP_SECRET = "rahasia-aplikasi-tes"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "whatsapp_webhook_verify_token": VERIFY_TOKEN,
        "whatsapp_app_secret": APP_SECRET,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def configured() -> Iterator[None]:
    app.dependency_overrides[get_settings] = lambda: _settings()
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def unconfigured() -> Iterator[None]:
    app.dependency_overrides[get_settings] = lambda: _settings(
        whatsapp_webhook_verify_token=None, whatsapp_app_secret=None
    )
    yield
    app.dependency_overrides.pop(get_settings, None)


def _request(method: str, *, params=None, content: bytes = b"", headers=None) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return await client.request(
                method, WEBHOOK_PATH, params=params, content=content, headers=headers
            )

    return asyncio.run(send())


def _signed(body: bytes, secret: str = APP_SECRET) -> dict[str, str]:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}", "Content-Type": "application/json"}


def _status_payload(status: str, errors: list[dict[str, object]] | None = None) -> bytes:
    item: dict[str, object] = {"id": "wamid.ABC", "status": status, "recipient_id": "628123456789"}
    if errors is not None:
        item["errors"] = errors
    return json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {"id": "1", "changes": [{"field": "messages", "value": {"statuses": [item]}}]}
            ],
        }
    ).encode()


def test_verification_returns_challenge(configured: None) -> None:
    response = _request(
        "GET",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "42"},
    )

    assert response.status_code == 200
    assert response.text == "42"


def test_verification_rejects_wrong_token(configured: None) -> None:
    response = _request(
        "GET",
        params={"hub.mode": "subscribe", "hub.verify_token": "salah", "hub.challenge": "42"},
    )

    assert response.status_code == 403


def test_unconfigured_webhook_is_not_found(unconfigured: None) -> None:
    body = _status_payload("sent")

    assert _request("GET", params={"hub.mode": "subscribe"}).status_code == 404
    assert _request("POST", content=body, headers=_signed(body, "")).status_code == 404


def test_post_rejects_invalid_signature(configured: None) -> None:
    body = _status_payload("delivered")

    assert _request("POST", content=body, headers=_signed(body, "bukan-rahasia")).status_code == 401
    assert _request("POST", content=body).status_code == 401


def test_post_logs_failed_status_without_full_phone(
    configured: None, caplog: pytest.LogCaptureFixture
) -> None:
    body = _status_payload(
        "failed",
        [{"code": 131026, "title": "Message undeliverable", "error_data": {"details": "x"}}],
    )

    with caplog.at_level(logging.INFO, logger="kasta_api.modules.auth.whatsapp_webhook"):
        response = _request("POST", content=body, headers=_signed(body))

    assert response.status_code == 200
    record = next(r for r in caplog.records if r.levelno == logging.WARNING)
    assert "131026" in record.getMessage()
    assert record.whatsapp_message_id == "wamid.ABC"
    assert record.recipient == "***6789"
    assert "628123456789" not in caplog.text


def test_blank_secrets_mean_unconfigured() -> None:
    settings = Settings(whatsapp_webhook_verify_token="", whatsapp_app_secret="  ")  # type: ignore[arg-type]

    assert settings.whatsapp_webhook_verify_token is None
    assert settings.whatsapp_app_secret is None


def test_secrets_must_be_set_together() -> None:
    with pytest.raises(ValidationError):
        Settings(whatsapp_webhook_verify_token=VERIFY_TOKEN)  # type: ignore[arg-type]
