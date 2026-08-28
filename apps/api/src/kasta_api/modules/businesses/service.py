from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from kasta_api.core.config import Settings
from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.models import JournalEntry, JournalLine
from kasta_api.modules.accounting.templates import create_template_accounts
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.models import DeviceSession
from kasta_api.modules.auth.schemas import TokenPairResponse
from kasta_api.modules.auth.security import TokenManager, normalize_identifier, utc_now
from kasta_api.modules.businesses.models import (
    Business,
    BusinessCategory,
    BusinessMember,
    BusinessPaymentMethod,
    BusinessProfile,
    OnboardingCompletion,
)
from kasta_api.modules.businesses.repository import BusinessRepository
from kasta_api.modules.businesses.schemas import (
    BusinessCategoryResponse,
    BusinessProfileResponse,
    BusinessProfileUpdate,
    CompleteOnboardingRequest,
    CompleteOnboardingResponse,
)

PAYMENT_METHOD_NAMES = {
    "CASH": "Tunai",
    "BANK_TRANSFER": "Transfer Bank",
    "QRIS": "QRIS",
    "E_WALLET": "Dompet Digital",
    "CARD": "Kartu Debit/Kredit",
}
PAYMENT_ACCOUNT_KEYS = {
    "CASH": AccountKey.CASH,
    "BANK_TRANSFER": AccountKey.BANK,
    "QRIS": AccountKey.DIGITAL_WALLET,
    "E_WALLET": AccountKey.DIGITAL_WALLET,
    "CARD": AccountKey.BANK,
}


class BusinessService:
    def __init__(
        self, repository: BusinessRepository, settings: Settings, token_manager: TokenManager
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.token_manager = token_manager

    async def list_categories(self) -> list[BusinessCategoryResponse]:
        return [
            BusinessCategoryResponse.model_validate(category)
            for category in await self.repository.list_categories()
        ]

    async def complete_onboarding(
        self,
        user_id: UUID,
        payload: CompleteOnboardingRequest,
        *,
        ip_address: str,
        user_agent: str | None,
    ) -> CompleteOnboardingResponse:
        previous = await self.repository.get_completion_for_user(user_id)
        if previous is not None:
            existing_profile = await self.get_profile(previous.business_id)
            tokens = await self._create_device_session(
                user_id,
                previous.business_id,
                payload.device,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.repository.commit()
            return CompleteOnboardingResponse(
                business_id=previous.business_id,
                profile=existing_profile,
                tokens=tokens,
                next_path=f"/usaha/{previous.business_id}/profil",
            )

        category = await self._active_category(payload.category_id)
        if category.business_type != payload.business_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Kategori usaha tidak sesuai dengan jenis usaha yang dipilih.",
            )
        phone = self._optional_phone(payload.phone)
        email = self._optional_email(str(payload.email) if payload.email is not None else None)
        now = utc_now()
        business_id = uuid4()
        business = Business(
            id=business_id,
            code=self._business_code(payload.business_name),
            name=payload.business_name,
            status="ACTIVE",
        )
        profile = BusinessProfile(
            id=uuid4(),
            business_id=business_id,
            category_id=category.id,
            business_type=payload.business_type,
            scale=payload.scale,
            established_year=payload.established_year,
            address=payload.address,
            village=payload.village,
            district=payload.district,
            city=payload.city,
            province=payload.province,
            phone=phone,
            email=email,
            employee_count=payload.employee_count,
            currency=payload.currency,
            timezone=payload.timezone,
            recording_method=payload.recording_method,
            inventory_mode="SIMPLE",
            closing_frequency="MONTHLY",
            status="ACTIVE",
            has_products_and_stock=payload.has_products_and_stock,
            tutorial_completed_at=now,
            onboarding_completed_at=now,
        )
        owner = BusinessMember(
            id=uuid4(),
            business_id=business_id,
            user_id=user_id,
            role_id=role_id(RoleCode.BUSINESS_OWNER),
            status="ACTIVE",
            joined_at=now,
        )
        accounts = create_template_accounts(business_id)
        accounts_by_key = {
            AccountKey(account.system_key): account
            for account in accounts
            if account.system_key is not None
        }
        owner_capital = accounts_by_key[AccountKey.OWNER_CAPITAL]
        payment_methods = [
            BusinessPaymentMethod(
                id=uuid4(),
                business_id=business_id,
                account_id=accounts_by_key[PAYMENT_ACCOUNT_KEYS[code]].id,
                code=code,
                name=PAYMENT_METHOD_NAMES[code],
            )
            for code in payload.payment_methods
        ]
        completion = OnboardingCompletion(
            id=uuid4(),
            user_id=user_id,
            business_id=business_id,
            opening_balance=payload.opening_balance,
        )
        objects: list[object] = [
            business,
            profile,
            owner,
            *accounts,
            completion,
            *payment_methods,
        ]
        if payload.opening_balance > Decimal("0.00"):
            opening_method = (
                "CASH" if "CASH" in payload.payment_methods else payload.payment_methods[0]
            )
            opening_account = accounts_by_key[PAYMENT_ACCOUNT_KEYS[opening_method]]
            entry = JournalEntry(
                id=uuid4(),
                business_id=business_id,
                entry_number="OPENING-0001",
                entry_date=now.date(),
                description="Saldo awal usaha",
                source="ONBOARDING",
                status="POSTED",
                total_debit=payload.opening_balance,
                total_credit=payload.opening_balance,
                posted_at=now,
            )
            objects.extend(
                [
                    entry,
                    JournalLine(
                        id=uuid4(),
                        business_id=business_id,
                        journal_entry_id=entry.id,
                        account_id=opening_account.id,
                        description="Saldo awal yang tersedia",
                        debit_amount=payload.opening_balance,
                        credit_amount=Decimal("0.00"),
                    ),
                    JournalLine(
                        id=uuid4(),
                        business_id=business_id,
                        journal_entry_id=entry.id,
                        account_id=owner_capital.id,
                        description="Modal awal pemilik",
                        debit_amount=Decimal("0.00"),
                        credit_amount=payload.opening_balance,
                    ),
                ]
            )
        self.repository.add_all(objects)
        await self.repository.flush()
        tokens = await self._create_device_session(
            user_id,
            business_id,
            payload.device,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.repository.commit()
        response = self._profile_response(
            business, profile, category, payment_methods, payload.opening_balance
        )
        return CompleteOnboardingResponse(
            business_id=business_id,
            profile=response,
            tokens=tokens,
            next_path=f"/usaha/{business_id}/profil",
        )

    async def _load_full_profile(
        self, business_id: UUID
    ) -> tuple[Business, BusinessProfile, BusinessCategory, list[BusinessPaymentMethod], Decimal]:
        business = await self.repository.get_business(business_id)
        profile = await self.repository.get_profile(business_id)
        completion = await self.repository.get_completion_for_business(business_id)
        if business is None or profile is None or completion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profil usaha tidak ditemukan."
            )
        category = await self.repository.get_category(profile.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kategori pada profil usaha sudah tidak tersedia.",
            )
        methods = await self.repository.get_payment_methods(business_id)
        return business, profile, category, methods, completion.opening_balance

    async def get_profile(self, business_id: UUID) -> BusinessProfileResponse:
        business, profile, category, methods, opening_balance = await self._load_full_profile(
            business_id
        )
        return self._profile_response(business, profile, category, methods, opening_balance)

    async def update_profile(
        self, business_id: UUID, payload: BusinessProfileUpdate
    ) -> BusinessProfileResponse:
        # Fetch everything the response needs *before* commit(): the RLS session
        # context (see kasta_api/db/rls.py) is set per-transaction via
        # `set_config(..., true)`, so it is cleared the moment commit() ends the
        # transaction. Querying again afterwards (as this used to, via
        # get_profile()) would run under `kasta_app` with no business context and
        # find nothing.
        business, profile, category, methods, opening_balance = await self._load_full_profile(
            business_id
        )
        values = payload.model_dump(exclude_unset=True)
        if "name" in values:
            business.name = values.pop("name")
        if "category_id" in values:
            category = await self._active_category(values.pop("category_id"))
            values["business_type"] = category.business_type
        elif "business_type" in values and values["business_type"] != profile.business_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Pilih kategori baru saat mengganti jenis usaha.",
            )
        if "phone" in values:
            values["phone"] = self._optional_phone(values["phone"])
        if "email" in values:
            email = values["email"]
            values["email"] = self._optional_email(str(email) if email is not None else None)
        for field, value in values.items():
            setattr(profile, field, value)
        await self.repository.commit()
        return self._profile_response(business, profile, category, methods, opening_balance)

    async def set_logo(self, business_id: UUID, object_key: str) -> BusinessProfileResponse:
        business, profile, category, methods, opening_balance = await self._load_full_profile(
            business_id
        )
        profile.logo_object_key = object_key
        await self.repository.commit()
        return self._profile_response(business, profile, category, methods, opening_balance)

    async def get_logo_key(self, business_id: UUID) -> str:
        profile = await self.repository.get_profile(business_id)
        if profile is None or profile.logo_object_key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Logo usaha belum tersedia."
            )
        return profile.logo_object_key

    async def _create_device_session(
        self,
        user_id: UUID,
        business_id: UUID,
        device: object,
        *,
        ip_address: str,
        user_agent: str | None,
    ) -> TokenPairResponse:
        from kasta_api.modules.auth.schemas import DeviceInfo

        if not isinstance(device, DeviceInfo):
            raise TypeError("Device information is invalid")
        now = utc_now()
        session_id = uuid4()
        refresh_token, refresh_hash = self.token_manager.create_opaque_token(session_id)
        self.repository.add_all(
            [
                DeviceSession(
                    id=session_id,
                    user_id=user_id,
                    business_id=business_id,
                    token_family_id=uuid4(),
                    refresh_token_hash=refresh_hash,
                    device_identifier_hash=self.token_manager.hash_value(device.device_id),
                    platform=device.platform,
                    device_name=device.device_name,
                    app_version=device.app_version,
                    user_agent=user_agent,
                    ip_address_hash=self.token_manager.hash_value(ip_address),
                    last_seen_at=now,
                    expires_at=now + timedelta(days=self.settings.refresh_token_days),
                )
            ]
        )
        await self.repository.flush()
        return TokenPairResponse(
            access_token=self.token_manager.create_access_token(user_id, session_id, business_id),
            refresh_token=refresh_token,
            expires_in=self.token_manager.access_token_seconds,
        )

    async def _active_category(self, category_id: UUID) -> BusinessCategory:
        category = await self.repository.get_category(category_id)
        if category is None or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Kategori usaha tidak tersedia.",
            )
        return category

    @staticmethod
    def _business_code(name: str) -> str:
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").upper()[:16]
        return f"{slug or 'USAHA'}-{secrets.token_hex(3).upper()}"

    @staticmethod
    def _optional_phone(value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            kind, normalized = normalize_identifier(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        if kind != "PHONE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Nomor telepon tidak valid.",
            )
        return normalized

    @staticmethod
    def _optional_email(value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            kind, normalized = normalize_identifier(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        if kind != "EMAIL":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Alamat email tidak valid.",
            )
        return normalized

    @staticmethod
    def _profile_response(
        business: Business,
        profile: BusinessProfile,
        category: BusinessCategory,
        methods: list[BusinessPaymentMethod],
        opening_balance: Decimal,
    ) -> BusinessProfileResponse:
        return BusinessProfileResponse(
            business_id=business.id,
            name=business.name,
            logo_path=(
                f"/businesses/{business.id}/profile/logo"
                if profile.logo_object_key is not None
                else None
            ),
            business_type=profile.business_type,
            category_id=profile.category_id,
            category_name=category.name,
            scale=profile.scale,
            established_year=profile.established_year,
            address=profile.address,
            village=profile.village,
            district=profile.district,
            city=profile.city,
            province=profile.province,
            phone=profile.phone,
            email=profile.email,
            employee_count=profile.employee_count,
            currency=profile.currency,
            timezone=profile.timezone,
            recording_method=profile.recording_method,
            inventory_mode=profile.inventory_mode,
            closing_frequency=profile.closing_frequency,
            status=profile.status,
            payment_methods=[method.code for method in methods],
            opening_balance=opening_balance,
            has_products_and_stock=profile.has_products_and_stock,
            tutorial_completed_at=profile.tutorial_completed_at,
            onboarding_completed_at=profile.onboarding_completed_at,
        )
