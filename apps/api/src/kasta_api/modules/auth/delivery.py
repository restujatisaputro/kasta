from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select

from kasta_api.core.config import Settings
from kasta_api.db.session import AsyncSessionFactory
from kasta_api.modules.auth.models import AuthDeliveryOutbox
from kasta_api.modules.auth.security import OutboxCipher, utc_now

logger = logging.getLogger(__name__)


def _render_message(settings: Settings, destination: str, payload: dict[str, str]) -> EmailMessage:
    purpose = payload["purpose"]
    token = payload["token"]
    if purpose == "VERIFY_EMAIL":
        subject = "Kode verifikasi akun KASTA"
        heading = "Verifikasi akun KASTA Anda"
        explanation = "Masukkan kode berikut pada halaman verifikasi akun:"
    elif purpose == "RESET_PASSWORD":
        subject = "Kode pengaturan ulang password KASTA"
        heading = "Atur ulang password KASTA Anda"
        explanation = "Masukkan kode berikut pada halaman pengaturan ulang password:"
    else:
        raise ValueError(f"Template email tidak didukung: {purpose}")

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = destination
    message["Subject"] = subject
    message.set_content(
        f"{heading}\n\n{explanation}\n\n{token}\n\n"
        "Kode ini bersifat rahasia dan akan kedaluwarsa. Jika Anda tidak meminta kode ini, "
        "abaikan email ini.\n"
    )
    return message


def _send_message(settings: Settings, message: EmailMessage) -> None:
    smtp_factory = smtplib.SMTP_SSL if settings.smtp_ssl else smtplib.SMTP
    with smtp_factory(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.ehlo()
        if settings.smtp_starttls and not settings.smtp_ssl:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_username:
            password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
            smtp.login(settings.smtp_username, password)
        smtp.send_message(message, from_addr=parseaddr(settings.mail_from)[1])


def _send_whatsapp_message(settings: Settings, destination: str, payload: dict[str, str]) -> None:
    purpose = payload["purpose"]
    if purpose not in {"VERIFY_PHONE", "RESET_PASSWORD"}:
        raise ValueError(f"Template WhatsApp tidak didukung: {purpose}")
    if settings.whatsapp_access_token is None or settings.whatsapp_phone_number_id is None:
        raise ValueError("Konfigurasi WhatsApp belum lengkap")

    endpoint = (
        f"{str(settings.whatsapp_api_base_url).rstrip('/')}/"
        f"{settings.whatsapp_graph_api_version}/{settings.whatsapp_phone_number_id}/messages"
    )
    request_body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": destination.lstrip("+"),
        "type": "template",
        "template": {
            "name": settings.whatsapp_template_name,
            "language": {"code": settings.whatsapp_template_language},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": payload["token"]}],
                }
            ],
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.whatsapp_access_token.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"WhatsApp API HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("WhatsApp API tidak dapat dihubungi") from exc

    if not response_body.get("messages"):
        raise RuntimeError("WhatsApp API tidak mengembalikan message id")


async def _deliver_batch(settings: Settings, cipher: OutboxCipher) -> int:
    enabled_channels = [
        channel
        for channel, enabled in (
            ("EMAIL", settings.mail_enabled),
            ("WHATSAPP", settings.whatsapp_enabled),
        )
        if enabled
    ]
    if not enabled_channels:
        return 0

    async with AsyncSessionFactory() as session:
        rows = list(
            (
                await session.scalars(
                    select(AuthDeliveryOutbox)
                    .where(
                        AuthDeliveryOutbox.sent_at.is_(None),
                        AuthDeliveryOutbox.channel.in_(enabled_channels),
                        AuthDeliveryOutbox.attempts < 10,
                    )
                    .order_by(AuthDeliveryOutbox.created_at)
                    .limit(settings.mail_outbox_batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for row in rows:
            try:
                payload = cipher.decrypt(row.payload_nonce, row.payload_ciphertext)
                if row.channel == "EMAIL":
                    message = _render_message(settings, row.destination, payload)
                    await asyncio.to_thread(_send_message, settings, message)
                    log_message = "Authentication email delivered"
                else:
                    await asyncio.to_thread(
                        _send_whatsapp_message, settings, row.destination, payload
                    )
                    log_message = "Authentication WhatsApp message delivered"
                row.sent_at = utc_now()
                logger.info(
                    log_message,
                    extra={"outbox_id": str(row.id), "template": row.template},
                )
            except Exception:
                logger.exception(
                    "Authentication message delivery failed",
                    extra={"outbox_id": str(row.id), "template": row.template},
                )
            finally:
                row.attempts += 1
        await session.commit()
        return len(rows)


async def run_delivery_worker(settings: Settings) -> None:
    cipher = OutboxCipher(settings)
    logger.info(
        "Authentication delivery worker started",
        extra={
            "email_enabled": settings.mail_enabled,
            "whatsapp_enabled": settings.whatsapp_enabled,
        },
    )
    while True:
        try:
            delivered = await _deliver_batch(settings, cipher)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Authentication email delivery worker iteration failed")
            delivered = 0
        delay = (
            0 if delivered >= settings.mail_outbox_batch_size else settings.mail_outbox_poll_seconds
        )
        await asyncio.sleep(delay)
