from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from kasta_api.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def _mask_phone(value: object) -> str:
    # Nomor penerima adalah data pribadi; log cukup memuat empat digit terakhir
    # untuk mencocokkan dengan keluhan pengguna.
    text = str(value or "")
    return f"***{text[-4:]}" if len(text) > 4 else "***"


def _signature_is_valid(app_secret: str, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def _log_status(item: dict[str, Any]) -> None:
    extra: dict[str, object] = {
        "whatsapp_message_id": item.get("id"),
        "whatsapp_status": item.get("status"),
        "recipient": _mask_phone(item.get("recipient_id")),
    }
    errors = item.get("errors")
    if item.get("status") == "failed" and isinstance(errors, list):
        # Kegagalan asinkron (mis. 131026 nomor tidak terjangkau, 131047 jendela
        # 24 jam) hanya dilaporkan Meta lewat webhook, bukan lewat respons API.
        details = []
        for error in errors:
            if not isinstance(error, dict):
                continue
            error_data = error.get("error_data")
            detail = error_data.get("details") if isinstance(error_data, dict) else None
            details.append(
                ", ".join(
                    f"{key}={value}"
                    for key, value in (
                        ("code", error.get("code")),
                        ("title", error.get("title")),
                        ("details", detail),
                    )
                    if value not in (None, "")
                )
            )
        logger.warning(
            "WhatsApp message delivery failed: %s",
            "; ".join(details) or "tanpa detail",
            extra=extra,
        )
        return
    logger.info("WhatsApp message status updated", extra=extra)


def _handle_payload(payload: dict[str, Any]) -> None:
    if payload.get("object") != "whatsapp_business_account":
        logger.info("WhatsApp webhook ignored", extra={"object": payload.get("object")})
        return
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            for item in value.get("statuses") or []:
                if isinstance(item, dict):
                    _log_status(item)
            messages = value.get("messages") or []
            if messages:
                # KASTA belum melayani pesan masuk; isi pesan tidak dicatat.
                logger.info(
                    "WhatsApp inbound message ignored",
                    extra={"count": len(messages), "field": change.get("field")},
                )


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    settings: SettingsDependency,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> str:
    expected = settings.whatsapp_webhook_verify_token
    if expected is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook WhatsApp belum dikonfigurasi")
    if (
        mode != "subscribe"
        or verify_token is None
        or challenge is None
        or not hmac.compare_digest(verify_token, expected.get_secret_value())
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verifikasi webhook ditolak")
    return challenge


@router.post("/webhooks/whatsapp", status_code=status.HTTP_200_OK)
async def receive_whatsapp_webhook(
    request: Request, settings: SettingsDependency
) -> dict[str, str]:
    app_secret = settings.whatsapp_app_secret
    if app_secret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook WhatsApp belum dikonfigurasi")
    body = await request.body()
    if not _signature_is_valid(
        app_secret.get_secret_value(), body, request.headers.get("x-hub-signature-256")
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tanda tangan webhook tidak valid")
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Isi webhook bukan JSON") from exc
    if isinstance(payload, dict):
        _handle_payload(payload)
    # Meta mengirim ulang webhook yang tidak dijawab 200, jadi jawab cepat.
    return {"status": "ok"}
