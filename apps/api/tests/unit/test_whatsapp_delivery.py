from __future__ import annotations

import json
from datetime import timedelta

import pytest

from kasta_api.modules.auth.delivery import (
    _graph_error_detail,
    _is_ready_for_retry,
    _send_whatsapp_message,
)
from kasta_api.modules.auth.security import utc_now


class _Settings:
    """Setting minimal; hanya field yang dipakai _send_whatsapp_message."""

    whatsapp_api_base_url = "https://graph.facebook.com/"
    whatsapp_graph_api_version = "v23.0"
    whatsapp_phone_number_id = "123456"
    whatsapp_template_name = "kasta_verification"
    whatsapp_template_language = "id"
    whatsapp_template_otp_button = True

    class _Token:
        @staticmethod
        def get_secret_value() -> str:
            return "rahasia-token"

    whatsapp_access_token = _Token()


def _capture_request(monkeypatch):
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        @staticmethod
        def read() -> bytes:
            return json.dumps({"messages": [{"id": "wamid.TEST"}]}).encode()

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode())
        captured["headers"] = dict(request.headers)
        return _Response()

    monkeypatch.setattr("kasta_api.modules.auth.delivery.urlopen", fake_urlopen)
    return captured


def test_template_authentication_mengirim_komponen_tombol(monkeypatch):
    captured = _capture_request(monkeypatch)
    _send_whatsapp_message(
        _Settings(), "+628123456789", {"purpose": "VERIFY_PHONE", "token": "123456"}
    )

    components = captured["body"]["template"]["components"]
    assert [c["type"] for c in components] == ["body", "button"]
    button = components[1]
    assert button["sub_type"] == "url"
    assert button["index"] == "0"
    # Meta mewajibkan kode yang sama muncul di body dan di tombol.
    assert button["parameters"][0]["text"] == "123456"
    assert components[0]["parameters"][0]["text"] == "123456"


def test_tombol_dapat_dimatikan_untuk_template_non_authentication(monkeypatch):
    captured = _capture_request(monkeypatch)
    settings = _Settings()
    settings.whatsapp_template_otp_button = False
    _send_whatsapp_message(
        settings, "+628123456789", {"purpose": "VERIFY_PHONE", "token": "999888"}
    )

    components = captured["body"]["template"]["components"]
    assert [c["type"] for c in components] == ["body"]


def test_nomor_dikirim_tanpa_tanda_plus(monkeypatch):
    captured = _capture_request(monkeypatch)
    _send_whatsapp_message(_Settings(), "+628123456789", {"purpose": "VERIFY_PHONE", "token": "1"})
    assert captured["body"]["to"] == "628123456789"


def test_detail_error_graph_diuraikan():
    body = json.dumps(
        {
            "error": {
                "message": "(#132000) Number of parameters does not match",
                "type": "OAuthException",
                "code": 132000,
                "error_subcode": 2494010,
                "fbtrace_id": "AbCdEf",
                "error_data": {"details": "body: number of localizable_params (1) does not match"},
            }
        }
    ).encode()
    detail = _graph_error_detail(body)
    assert "code=132000" in detail
    assert "error_subcode=2494010" in detail
    assert "details=" in detail
    assert "fbtrace_id=AbCdEf" in detail


@pytest.mark.parametrize(
    "body,harapan",
    [
        (None, "tanpa isi respons"),
        (b"", "tanpa isi respons"),
        (b"bukan json", "isi respons bukan JSON"),
    ],
)
def test_detail_error_graph_tahan_isi_tidak_terduga(body, harapan):
    assert _graph_error_detail(body) == harapan


def test_backoff_menunda_percobaan_ulang():
    now = utc_now()
    # Percobaan pertama selalu boleh jalan.
    assert _is_ready_for_retry(0, now, now) is True
    # Setelah satu kegagalan, harus menunggu sebelum dicoba lagi.
    assert _is_ready_for_retry(1, now, now) is False
    assert _is_ready_for_retry(1, now - timedelta(seconds=10), now) is True
    # Jeda membesar seiring kegagalan berulang.
    assert _is_ready_for_retry(4, now - timedelta(seconds=60), now) is False
    assert _is_ready_for_retry(4, now - timedelta(seconds=601), now) is True


def test_purpose_tidak_didukung_ditolak(monkeypatch):
    _capture_request(monkeypatch)
    with pytest.raises(ValueError, match="Template WhatsApp tidak didukung"):
        _send_whatsapp_message(
            _Settings(), "+628123456789", {"purpose": "VERIFY_EMAIL", "token": "1"}
        )
