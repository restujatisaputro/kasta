from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from kasta_api.modules.accounting.models import JournalEntry, JournalLine
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import get_outbox_cipher
from kasta_api.modules.auth.models import AuthDeliveryOutbox
from kasta_api.modules.businesses.models import BusinessMember, OnboardingCompletion
from kasta_api.modules.businesses.schemas import CompleteOnboardingResponse
from tests.conftest import AuthTestEnvironment

pytestmark = pytest.mark.anyio


async def _verification_token(environment: AuthTestEnvironment, user_id: UUID) -> str:
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


async def _create_verified_account(
    environment: AuthTestEnvironment, email: str = "pemilik-baru@example.com"
) -> tuple[UUID, str]:
    created = await environment.client.post(
        "/api/v1/onboarding/account",
        json={
            "full_name": "Sari Pemilik Usaha",
            "email": email,
            "password": "Kasta-onboarding-aman-2026",
        },
    )
    assert created.status_code == 201, created.text
    user_id = UUID(created.json()["user_id"])
    verification_token = await _verification_token(environment, user_id)
    verified = await environment.client.post(
        "/api/v1/onboarding/verify", json={"token": verification_token}
    )
    assert verified.status_code == 200, verified.text
    return user_id, str(verified.json()["onboarding_token"])


async def test_complete_onboarding_creates_owner_profile_and_balanced_opening_entry(
    auth_environment: AuthTestEnvironment,
) -> None:
    user_id, onboarding_token = await _create_verified_account(auth_environment)
    categories = await auth_environment.client.get("/api/v1/onboarding/categories")
    assert categories.status_code == 200
    food = next(item for item in categories.json() if item["code"] == "food")

    completed = await auth_environment.client.post(
        "/api/v1/onboarding/complete",
        headers={"Authorization": f"Bearer {onboarding_token}"},
        json={
            "role_selection": "BUSINESS_OWNER",
            "business_name": "Dapur Sari",
            "business_type": "CULINARY",
            "category_id": food["id"],
            "scale": "MICRO",
            "established_year": 2024,
            "address": "Jalan Melati",
            "village": "Sukamaju",
            "district": "Cempaka",
            "city": "Bandung",
            "province": "Jawa Barat",
            "phone": "0812-1111-2222",
            "email": "usaha@example.com",
            "employee_count": 3,
            "currency": "IDR",
            "timezone": "Asia/Jakarta",
            "recording_method": "CASH",
            "payment_methods": ["CASH", "QRIS"],
            "opening_balance": "1500000.00",
            "has_products_and_stock": True,
            "tutorial_completed": True,
            "device": {
                "device_id": "onboarding-web-device",
                "platform": "WEB",
                "device_name": "Chrome",
                "app_version": "0.1.0",
            },
        },
    )
    assert completed.status_code == 201, completed.text
    result = CompleteOnboardingResponse.model_validate(completed.json())
    assert result.profile.name == "Dapur Sari"
    assert result.profile.category_name == "Makanan"
    assert result.profile.opening_balance == Decimal("1500000.00")
    assert result.profile.payment_methods == ["CASH", "QRIS"]

    profile = await auth_environment.client.get(
        f"/api/v1/businesses/{result.business_id}/profile",
        headers={"Authorization": f"Bearer {result.tokens.access_token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["recording_method"] == "CASH"

    updated = await auth_environment.client.patch(
        f"/api/v1/businesses/{result.business_id}/profile",
        headers={"Authorization": f"Bearer {result.tokens.access_token}"},
        json={
            "village": "Sukaresmi",
            "district": "Coblong",
            "employee_count": 4,
            "timezone": "Asia/Makassar",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["village"] == "Sukaresmi"
    assert updated.json()["employee_count"] == 4
    assert updated.json()["timezone"] == "Asia/Makassar"

    async with auth_environment.session_factory() as session:
        member = await session.scalar(
            select(BusinessMember).where(
                BusinessMember.business_id == result.business_id,
                BusinessMember.user_id == user_id,
            )
        )
        assert member is not None
        assert member.role_id == role_id(RoleCode.BUSINESS_OWNER)
        entry = await session.scalar(
            select(JournalEntry).where(JournalEntry.business_id == result.business_id)
        )
        assert entry is not None
        assert entry.total_debit == entry.total_credit == Decimal("1500000.00")
        lines = list(
            (
                await session.scalars(
                    select(JournalLine).where(JournalLine.journal_entry_id == entry.id)
                )
            ).all()
        )
        assert sum((line.debit_amount for line in lines), Decimal("0")) == sum(
            (line.credit_amount for line in lines), Decimal("0")
        )


async def test_onboarding_rejects_category_from_another_business_type(
    auth_environment: AuthTestEnvironment,
) -> None:
    user_id, token = await _create_verified_account(auth_environment, "kategori-salah@example.com")
    categories = (await auth_environment.client.get("/api/v1/onboarding/categories")).json()
    food = next(item for item in categories if item["code"] == "food")
    response = await auth_environment.client.post(
        "/api/v1/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "role_selection": "BUSINESS_OWNER",
            "business_name": "Toko Salah Kategori",
            "business_type": "TRADE",
            "category_id": food["id"],
            "scale": "MICRO",
            "city": "Jakarta",
            "province": "DKI Jakarta",
            "currency": "IDR",
            "timezone": "Asia/Jakarta",
            "recording_method": "CASH",
            "payment_methods": ["CASH"],
            "opening_balance": "0.00",
            "has_products_and_stock": False,
            "tutorial_completed": True,
            "device": {
                "device_id": "wrong-category-device",
                "platform": "WEB",
            },
        },
    )
    assert response.status_code == 422
    async with auth_environment.session_factory() as session:
        completion = await session.scalar(
            select(OnboardingCompletion).where(OnboardingCompletion.user_id == user_id)
        )
        assert completion is None


async def test_account_identifier_must_be_unique(
    auth_environment: AuthTestEnvironment,
) -> None:
    payload = {
        "full_name": "Pemilik",
        "email": "duplikat@example.com",
        "password": "Kasta-password-aman-2026",
    }
    first = await auth_environment.client.post("/api/v1/onboarding/account", json=payload)
    second = await auth_environment.client.post("/api/v1/onboarding/account", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
