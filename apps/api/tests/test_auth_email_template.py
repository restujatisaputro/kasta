import pytest

from kasta_api.core.config import Settings
from kasta_api.modules.auth.delivery import _render_message, verification_link

TOKEN = "0d6f14d5-7b11-4f85-bd64-09338c9df3da.HP_71JzRgBT57mBeN2dtNP207m2bEsU0ECpl"


def _settings() -> Settings:
    return Settings(
        web_base_url="https://appkasta.admniaga.com/",
        mail_from="KASTA <noreply@admniaga.com>",
    )


def _plain_body(message) -> str:
    part = message.get_body(preferencelist=("plain",))
    assert part is not None
    return part.get_content()


def test_verification_link_memakai_basis_url_tanpa_garis_miring_ganda() -> None:
    link = verification_link(_settings(), TOKEN)

    assert link == f"https://appkasta.admniaga.com/verifikasi?token={TOKEN}"


def test_verification_link_meng_encode_karakter_khusus() -> None:
    link = verification_link(_settings(), "abc def&x=1")

    assert link.endswith("/verifikasi?token=abc%20def%26x%3D1")


def test_email_verifikasi_berisi_tautan_bukan_kode_manual() -> None:
    message = _render_message(
        _settings(), "pengguna@example.com", {"purpose": "VERIFY_EMAIL", "token": TOKEN}
    )
    body = _plain_body(message)

    assert message["Subject"] == "Verifikasi akun KASTA"
    assert f"https://appkasta.admniaga.com/verifikasi?token={TOKEN}" in body
    # Token tidak boleh muncul sebagai kode berdiri sendiri untuk disalin manual.
    assert f"\n{TOKEN}\n" not in body


def test_email_verifikasi_menyertakan_alternatif_html_yang_dapat_diklik() -> None:
    message = _render_message(
        _settings(), "pengguna@example.com", {"purpose": "VERIFY_EMAIL", "token": TOKEN}
    )
    html_part = message.get_body(preferencelist=("html",))

    assert html_part is not None
    assert f'href="https://appkasta.admniaga.com/verifikasi?token={TOKEN}"' in (
        html_part.get_content()
    )


def test_email_reset_password_masih_memakai_kode() -> None:
    message = _render_message(
        _settings(), "pengguna@example.com", {"purpose": "RESET_PASSWORD", "token": TOKEN}
    )

    assert message["Subject"] == "Kode pengaturan ulang password KASTA"
    assert f"\n{TOKEN}\n" in _plain_body(message)


def test_template_tidak_dikenal_ditolak() -> None:
    with pytest.raises(ValueError, match="Template email tidak didukung"):
        _render_message(
            _settings(), "pengguna@example.com", {"purpose": "VERIFY_PHONE", "token": TOKEN}
        )
