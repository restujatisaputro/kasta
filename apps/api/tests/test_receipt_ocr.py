from __future__ import annotations

import json
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from PIL import Image, ImageDraw
from sqlalchemy import func, select

from kasta_api.main import app
from kasta_api.modules.accounting.models import FinancialTransaction
from kasta_api.modules.ocr.dependencies import get_receipt_storage
from kasta_api.modules.receipts.models import OcrField, Receipt, ReceiptCorrection
from kasta_api.modules.receipts.storage import ReceiptStorage, ValidatedImage
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


class InMemoryReceiptStorage(ReceiptStorage):
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def validate_upload(self, upload: UploadFile) -> ValidatedImage:
        data = await upload.read()
        await upload.close()
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
            image_format = image.format
        assert image_format in {"PNG", "JPEG"}
        return ValidatedImage(
            data=data,
            content_type="image/png" if image_format == "PNG" else "image/jpeg",
            extension="png" if image_format == "PNG" else "jpg",
            width=width,
            height=height,
        )

    async def upload_scan_image(
        self,
        business_id: UUID,
        receipt_id: UUID,
        image_kind: str,
        image: ValidatedImage,
    ) -> str:
        key = f"businesses/{business_id}/receipt-scans/{receipt_id}/{image_kind}-{uuid4()}"
        self.objects[key] = (image.data, image.content_type)
        return key

    async def download(self, object_key: str) -> tuple[bytes, str]:
        return self.objects[object_key]

    async def presigned_download(self, object_key: str) -> tuple[str, int]:
        assert object_key in self.objects
        return f"https://objects.kasta.invalid/{object_key}?signature=test", 300


class FailingReceiptStorage(InMemoryReceiptStorage):
    async def upload_scan_image(
        self,
        business_id: UUID,
        receipt_id: UUID,
        image_kind: str,
        image: ValidatedImage,
    ) -> str:
        del business_id, receipt_id, image_kind, image
        raise OSError("simulated object storage outage")


def receipt_image() -> bytes:
    image = Image.new("RGB", (480, 720), "#eeeeee")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 30, 440, 690), fill="white", outline="black", width=4)
    draw.text((80, 90), "TOKO MAJU", fill="black")
    draw.text((80, 140), "TOTAL 25.000", fill="black")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def url(environment: AuthTestEnvironment) -> str:
    return f"/api/v1/businesses/{environment.business_a_id}/receipt-scans"


async def upload_scan(
    environment: AuthTestEnvironment,
    token: str,
    storage: InMemoryReceiptStorage,
    *,
    raw_ocr: str = (
        "TOKO MAJU\nNo Nota: INV-2026-007\nTanggal 21/07/2026\nTepung 25.000\nTOTAL Rp 25.000\nQRIS"
    ),
) -> dict[str, object]:
    app.dependency_overrides[get_receipt_storage] = lambda: storage
    response = await environment.client.post(
        url(environment),
        headers=headers(token),
        files={"original": ("nota.png", receipt_image(), "image/png")},
        data={"raw_ocr": raw_ocr},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_stops_at_review_without_creating_transaction(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    review = await upload_scan(auth_environment, tokens.access_token, InMemoryReceiptStorage())

    assert review["status"] == "NEEDS_REVIEW"
    assert review["transaction_id"] is None
    assert {field["name"] for field in review["fields"]} >= {
        "merchant_name",
        "receipt_date",
        "total",
        "payment_method",
    }
    async with auth_environment.session_factory() as session:
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert transaction_count == 0


async def test_low_confidence_ocr_requires_review_and_never_creates_transaction(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    storage = InMemoryReceiptStorage()
    app.dependency_overrides[get_receipt_storage] = lambda: storage

    response = await auth_environment.client.post(
        url(auth_environment),
        headers=headers(tokens.access_token),
        files={"original": ("nota.png", receipt_image(), "image/png")},
        data={
            "raw_ocr": "",
            "client_fields": json.dumps(
                {
                    "merchant_name": {"value": "Toko Buram", "confidence": 0.18},
                    "total": {"value": "25000.00", "confidence": 0.20},
                }
            ),
        },
    )

    assert response.status_code == 201, response.text
    review = response.json()
    assert review["status"] == "NEEDS_REVIEW"
    assert review["transaction_id"] is None
    assert {field["name"] for field in review["fields"]} == {"merchant_name", "total"}
    assert all(float(field["confidence"]) <= 0.20 for field in review["fields"])
    async with auth_environment.session_factory() as session:
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert transaction_count == 0


async def test_object_storage_failure_is_structured_and_receipt_is_marked_failed(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    app.dependency_overrides[get_receipt_storage] = lambda: FailingReceiptStorage()

    response = await auth_environment.client.post(
        url(auth_environment),
        headers=headers(tokens.access_token),
        files={"original": ("nota.png", receipt_image(), "image/png")},
        data={"raw_ocr": "TOKO GAGAL\nTOTAL 25.000"},
    )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "Terjadi kesalahan internal. Silakan coba kembali."
    async with auth_environment.session_factory() as session:
        failed = (await session.scalars(select(Receipt))).one()
        transaction_count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert failed.status == "FAILED"
    assert (
        failed.failure_reason
        == "Pemrosesan nota gagal. Coba ambil foto dengan pencahayaan lebih baik."
    )
    assert transaction_count == 0


async def test_original_and_processed_images_can_be_read(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    storage = InMemoryReceiptStorage()
    review = await upload_scan(auth_environment, tokens.access_token, storage)

    for kind in ("ORIGINAL", "PROCESSED"):
        response = await auth_environment.client.get(
            f"{url(auth_environment)}/{review['id']}/images/{kind}",
            headers=headers(tokens.access_token),
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")
        assert response.content


async def test_signed_image_url_is_short_lived_and_tenant_scoped(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    storage = InMemoryReceiptStorage()
    review = await upload_scan(auth_environment, tokens.access_token, storage)
    endpoint = f"{url(auth_environment)}/{review['id']}/images/ORIGINAL/url"

    response = await auth_environment.client.get(endpoint, headers=headers(tokens.access_token))
    assert response.status_code == 200
    assert response.json()["expires_in"] == 300
    assert response.json()["url"].startswith("https://objects.kasta.invalid/")

    cross_tenant = endpoint.replace(
        str(auth_environment.business_a_id), str(auth_environment.business_b_id)
    )
    denied = await auth_environment.client.get(cross_tenant, headers=headers(tokens.access_token))
    assert denied.status_code == 403


async def test_confirmation_creates_transaction_and_records_correction(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    review = await upload_scan(auth_environment, tokens.access_token, InMemoryReceiptStorage())
    receipt_id = review["id"]

    confirmed = await auth_environment.client.post(
        f"{url(auth_environment)}/{receipt_id}/confirm",
        headers=headers(tokens.access_token),
        json={
            "corrections": {"merchant_name": "Toko Maju Bersama", "total": "27500.00"},
            "entry_kind": "EXPENSE",
            "category_account": "RAW_MATERIALS",
            "payment_method": "QRIS",
            "note": "Bahan untuk produksi",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["receipt"]["status"] == "CONFIRMED"
    assert body["transaction_id"] == body["receipt"]["transaction_id"]

    async with auth_environment.session_factory() as session:
        receipt = await session.get(Receipt, UUID(receipt_id))
        transaction = await session.get(FinancialTransaction, UUID(body["transaction_id"]))
        corrections = list(
            (
                await session.scalars(
                    select(ReceiptCorrection).where(
                        ReceiptCorrection.receipt_id == UUID(receipt_id)
                    )
                )
            ).all()
        )
        merchant_field = (
            await session.scalars(
                select(OcrField).where(
                    OcrField.receipt_id == UUID(receipt_id),
                    OcrField.field_name == "merchant_name",
                )
            )
        ).one()
    assert receipt is not None and transaction is not None
    assert receipt.total_amount is not None
    assert str(receipt.total_amount) == "27500.00"
    assert transaction.amount == receipt.total_amount
    assert {item.field_name for item in corrections} == {"merchant_name", "total"}
    assert merchant_field.is_user_corrected is True
    assert merchant_field.corrected_value == "Toko Maju Bersama"


async def test_confirmation_is_idempotent(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    review = await upload_scan(auth_environment, tokens.access_token, InMemoryReceiptStorage())
    endpoint = f"{url(auth_environment)}/{review['id']}/confirm"
    payload = {"corrections": {}, "entry_kind": "EXPENSE"}

    first = await auth_environment.client.post(
        endpoint, headers=headers(tokens.access_token), json=payload
    )
    replay = await auth_environment.client.post(
        endpoint, headers=headers(tokens.access_token), json=payload
    )
    assert first.status_code == replay.status_code == 200
    assert first.json()["transaction_id"] == replay.json()["transaction_id"]
    async with auth_environment.session_factory() as session:
        count = await session.scalar(select(func.count(FinancialTransaction.id)))
    assert count == 1


async def test_duplicate_requires_explicit_acknowledgement(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    storage = InMemoryReceiptStorage()
    first = await upload_scan(auth_environment, tokens.access_token, storage)
    second = await upload_scan(auth_environment, tokens.access_token, storage)
    assert second["duplicate_candidates"]
    assert second["duplicate_candidates"][0]["id"] == first["id"]

    endpoint = f"{url(auth_environment)}/{second['id']}/confirm"
    rejected = await auth_environment.client.post(
        endpoint,
        headers=headers(tokens.access_token),
        json={"corrections": {}, "entry_kind": "EXPENSE"},
    )
    assert rejected.status_code == 409

    accepted = await auth_environment.client.post(
        endpoint,
        headers=headers(tokens.access_token),
        json={
            "corrections": {},
            "entry_kind": "EXPENSE",
            "acknowledge_duplicate": True,
        },
    )
    assert accepted.status_code == 200, accepted.text


async def test_receipt_review_is_tenant_isolated(
    auth_environment: AuthTestEnvironment,
) -> None:
    owner_tokens = await login_as(auth_environment, identifier="owner@example.com")
    review = await upload_scan(
        auth_environment, owner_tokens.access_token, InMemoryReceiptStorage()
    )
    other_tokens = await login_as(
        auth_environment,
        identifier="owner-b@example.com",
        business_id=auth_environment.business_b_id,
    )
    response = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/receipt-scans/{review['id']}",
        headers=headers(other_tokens.access_token),
    )
    assert response.status_code == 404
