#!/usr/bin/env python3
"""Uji kirim template WhatsApp KASTA tanpa menyentuh database atau API.

Payload yang dikirim SAMA PERSIS dengan yang dibentuk
apps/api/src/kasta_api/modules/auth/delivery.py, sehingga hasil skrip ini
memberi tahu apakah masalahnya ada di konfigurasi/template Meta atau di kode.

Token dibaca dari environment, bukan argumen, supaya tidak tersimpan di
riwayat shell. Jalankan:

  export KASTA_WHATSAPP_PHONE_NUMBER_ID=...
  export KASTA_WHATSAPP_ACCESS_TOKEN=...
  python scripts/check-whatsapp.py +628123456789

Di PowerShell:
  $env:KASTA_WHATSAPP_PHONE_NUMBER_ID="..."
  $env:KASTA_WHATSAPP_ACCESS_TOKEN="..."
  python scripts/check-whatsapp.py +628123456789
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def graph_error_detail(body: bytes | None) -> str:
    if not body:
        return "tanpa isi respons"
    try:
        error = json.loads(body.decode("utf-8", errors="replace")).get("error", {})
    except ValueError, AttributeError:
        return "isi respons bukan JSON"
    if not isinstance(error, dict):
        return "isi respons bukan JSON"
    parts = []
    for key in ("code", "error_subcode", "type", "message", "fbtrace_id"):
        value = error.get(key)
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    details = error.get("error_data", {})
    if isinstance(details, dict) and details.get("details"):
        parts.append(f"details={details['details']}")
    return ", ".join(parts) or "error kosong"


def main() -> int:
    if len(sys.argv) != 2:
        print("Pemakaian: python scripts/check-whatsapp.py <nomor-tujuan>", file=sys.stderr)
        print("Contoh   : python scripts/check-whatsapp.py +628123456789", file=sys.stderr)
        return 2

    phone_id = os.environ.get("KASTA_WHATSAPP_PHONE_NUMBER_ID")
    token = os.environ.get("KASTA_WHATSAPP_ACCESS_TOKEN")
    if not phone_id or not token:
        print(
            "KASTA_WHATSAPP_PHONE_NUMBER_ID dan KASTA_WHATSAPP_ACCESS_TOKEN "
            "harus diisi lewat environment.",
            file=sys.stderr,
        )
        return 2

    base = os.environ.get("KASTA_WHATSAPP_API_BASE_URL", "https://graph.facebook.com")
    version = os.environ.get("KASTA_WHATSAPP_GRAPH_API_VERSION", "v23.0")
    template = os.environ.get("KASTA_WHATSAPP_TEMPLATE_NAME", "kasta_verification")
    language = os.environ.get("KASTA_WHATSAPP_TEMPLATE_LANGUAGE", "id")
    use_button = os.environ.get("KASTA_WHATSAPP_TEMPLATE_OTP_BUTTON", "true").lower() != "false"

    destination = sys.argv[1].lstrip("+")
    kode = "123456"  # kode contoh; bukan OTP sungguhan

    components: list[dict[str, object]] = [
        {"type": "body", "parameters": [{"type": "text", "text": kode}]}
    ]
    if use_button:
        components.append(
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": kode}],
            }
        )

    endpoint = f"{base.rstrip('/')}/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": destination,
        "type": "template",
        "template": {"name": template, "language": {"code": language}, "components": components},
    }

    print(f"endpoint : {endpoint}")
    tombol = "ya" if use_button else "tidak"
    print(f"template : {template} (bahasa {language}, tombol OTP: {tombol})")
    print(f"tujuan   : {destination}")
    print("-" * 60)

    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            raw = exc.read()
        except Exception:
            raw = None
        print(f"GAGAL  HTTP {exc.code}")
        print(f"sebab  {graph_error_detail(raw)}")
        print()
        print("Petunjuk berdasarkan kode error Meta:")
        print("  132000 -> jumlah parameter tidak cocok. Template punya tombol copy-code")
        print("            tapi KASTA_WHATSAPP_TEMPLATE_OTP_BUTTON=false, atau sebaliknya.")
        print("  132001 -> template tidak ditemukan pada bahasa itu. Cek nama dan kode bahasa.")
        print("  132015 -> template belum disetujui atau sedang dijeda Meta.")
        print("  131030 -> nomor tujuan belum terdaftar sebagai penerima tes.")
        print("  190    -> access token tidak valid atau kedaluwarsa.")
        print("  133010 -> nomor pengirim belum terdaftar di Cloud API.")
        return 1
    except URLError as exc:
        print(f"GAGAL  tidak dapat menghubungi Graph API: {exc.reason}")
        return 1

    if not payload.get("messages"):
        print("GAGAL  Graph API tidak mengembalikan message id")
        print(json.dumps(payload, indent=2))
        return 1

    print("BERHASIL")
    print(f"message id : {payload['messages'][0].get('id')}")
    print("Cek WhatsApp di nomor tujuan; kode contohnya 123456.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
