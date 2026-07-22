"""Seed deterministic, entirely fictitious KASTA demonstration data.

The command is intentionally idempotent: records are identified by stable UUID5
values and existing rows are left untouched.  It can therefore be run after
``alembic upgrade head`` without deleting a developer's local data.

Run from ``apps/api``::

    python -m kasta_api.seed_demo

The generated accounts and journals use the same double-entry templates as the
application.  Every seeded transaction has exactly two journal lines whose
debit and credit totals equal the transaction amount.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.db.session import AsyncSessionFactory, dispose_engine
from kasta_api.modules.accounting.constants import AccountKey
from kasta_api.modules.accounting.models import (
    Account,
    FinancialTransaction,
    JournalEntry,
    JournalLine,
    TransactionRevision,
)
from kasta_api.modules.accounting.templates import ACCOUNT_TEMPLATES
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.constants import (
    AUTH_NAMESPACE,
    ROLE_NAMES,
    ROLE_PERMISSIONS,
    ROLE_SCOPES,
    PermissionCode,
    RoleCode,
    permission_id,
    role_id,
)
from kasta_api.modules.auth.models import Permission, Role, RolePermission
from kasta_api.modules.auth.security import PasswordManager
from kasta_api.modules.businesses.categories import BUSINESS_CATEGORY_SEED, business_category_id
from kasta_api.modules.businesses.models import (
    Business,
    BusinessCategory,
    BusinessMember,
    BusinessPaymentMethod,
    BusinessProfile,
    OnboardingCompletion,
    Organization,
    OrganizationMember,
)
from kasta_api.modules.inventory.models import Product
from kasta_api.modules.mentors.models import (
    Mentor,
    MentorBusinessAccess,
    MentoringSession,
    Recommendation,
)
from kasta_api.modules.obligations.models import (
    Customer,
    Payable,
    PayablePayment,
    Receivable,
    ReceivablePayment,
    Supplier,
)
from kasta_api.modules.receipts.models import OcrField, OcrResult, Receipt, ReceiptImage
from kasta_api.modules.users.models import User

DEMO_NAMESPACE = UUID("3a4b3a9d-b4b4-4b63-8b7f-ec8b1bbbc4e1")
PASSWORD = "DemoKasta123!"
# Dates are relative to the seed run so overdue and upcoming reminders remain
# meaningful when the demo is refreshed in a later year. UUIDs remain stable.
DEMO_TODAY = date.today()
DEMO_CATEGORIES = {
    "warung makan": ("food", "CULINARY"),
    "toko kelontong": ("retail", "TRADE"),
    "kopi": ("beverage", "CULINARY"),
    "laundry": ("personal_service", "SERVICE"),
    "fesyen": ("fashion", "CREATIVE"),
    "kerajinan": ("craft", "PRODUCTION"),
    "jasa digital": ("professional_service", "SERVICE"),
    "bengkel": ("personal_service", "SERVICE"),
    "katering": ("food", "CULINARY"),
    "toko online": ("retail", "TRADE"),
}
BUSINESS_TYPES = list(DEMO_CATEGORIES)
BUSINESS_NAMES = [
    "Warung Rasa Nusa",
    "Toko Sembada",
    "Kopi Senja",
    "Laundry Bersih Ceria",
    "Rona Fesyen",
    "Anyam Arunika",
    "Pixel Pagi Studio",
    "Bengkel Maju Jaya",
    "Dapur Pagi Katering",
    "PasarKita Online",
]


@dataclass(frozen=True, slots=True)
class DemoSeedCounts:
    """Expected deterministic row counts produced by :func:`seed_demo_data`."""

    organizations: int = 1
    mentors: int = 3
    businesses: int = 10
    users: int = 20
    products: int = 100
    transactions: int = 500
    journal_entries: int = 500
    journal_lines: int = 1000
    audit_logs: int = 500
    payables: int = 30
    receivables: int = 30
    receipts: int = 100
    recommendations: int = 20
    mentoring_sessions: int = 20


class HasId(Protocol):
    id: UUID


PRODUCT_NAMES = {
    "warung makan": ["Nasi Ayam", "Mie Goreng", "Es Teh", "Soto Ayam", "Kerupuk"],
    "toko kelontong": ["Beras 5kg", "Minyak 1L", "Gula 1kg", "Telur 1kg", "Sabun Cuci"],
    "kopi": ["Kopi Susu", "Americano", "Cappuccino", "Croissant", "Teh Lemon"],
    "laundry": ["Cuci Kering", "Cuci Setrika", "Setrika Saja", "Express", "Bed Cover"],
    "fesyen": ["Kemeja Linen", "Kaos Basic", "Celana Chino", "Rok Plisket", "Tas Kanvas"],
    "kerajinan": ["Keranjang Rotan", "Gantungan Kayu", "Lilin Aroma", "Batik Mini", "Vas Anyam"],
    "jasa digital": ["Logo Usaha", "Paket Konten", "Landing Page", "Edit Video", "Foto Produk"],
    "bengkel": ["Oli Mesin", "Kampas Rem", "Busi", "Jasa Servis", "Ban Motor"],
    "katering": ["Nasi Box", "Tumpeng Mini", "Snack Box", "Es Buah", "Paket Prasmanan"],
    "toko online": ["Pouch Kanvas", "Botol Minum", "Aksesori Meja", "Planner", "Stiker"],
}


def demo_id(kind: str, *parts: object) -> UUID:
    return uuid5(DEMO_NAMESPACE, ":".join((kind, *(str(part) for part in parts))))


def stamp(value: datetime) -> dict[str, datetime]:
    return {"created_at": value, "updated_at": value}


async def add_missing[T: HasId](session: AsyncSession, model: Any, rows: Sequence[T]) -> None:
    if not rows:
        return
    ids = [row.id for row in rows]
    existing = set((await session.scalars(select(model.id).where(model.id.in_(ids)))).all())
    session.add_all([row for row in rows if row.id not in existing])
    await session.flush()


async def ensure_reference(session: AsyncSession) -> None:
    roles = [
        Role(
            id=role_id(code),
            code=code.value,
            name=ROLE_NAMES[code],
            scope=ROLE_SCOPES[code],
            is_system=True,
        )
        for code in RoleCode
    ]
    permissions = [
        Permission(
            id=permission_id(code),
            code=code.value,
            module=code.value.split(".", maxsplit=1)[0],
            description=code.value,
        )
        for code in PermissionCode
    ]
    await add_missing(session, Role, roles)
    await add_missing(session, Permission, permissions)
    role_permissions = [
        RolePermission(
            # Match the IDs used by the authentication migration so running
            # this seed after ``alembic upgrade head`` is conflict-free.
            id=uuid5(AUTH_NAMESPACE, f"role-permission:{role.value}:{permission.value}"),
            role_id=role_id(role),
            permission_id=permission_id(permission),
        )
        for role, granted in ROLE_PERMISSIONS.items()
        for permission in granted
    ]
    await add_missing(session, RolePermission, role_permissions)
    categories = [
        BusinessCategory(
            id=business_category_id(code),
            code=code,
            name=name,
            business_type=business_type,
            display_order=order,
            is_active=True,
        )
        for code, name, business_type, order in BUSINESS_CATEGORY_SEED
    ]
    await add_missing(session, BusinessCategory, categories)


async def seed_demo_data(session: AsyncSession) -> DemoSeedCounts:
    """Create all requested demo entities and return per-table counts."""

    await ensure_reference(session)
    now = datetime.now(UTC).replace(microsecond=0)
    password_manager = PasswordManager()
    # Hash once and reuse the valid Argon2id value for all fictitious accounts.
    demo_password_hash = password_manager.hash(PASSWORD)

    organization = Organization(
        id=demo_id("organization", 1),
        name="Organisasi Pembina UMKM Nusantara",
        status="ACTIVE",
        **stamp(now),
    )
    await add_missing(session, Organization, [organization])
    org_id = organization.id

    role_ids = {code: role_id(code) for code in RoleCode}
    users: list[User] = []
    owner_ids: list[UUID] = []
    staff_ids: list[UUID] = []
    mentor_user_ids: list[UUID] = []
    for index in range(10):
        user_id = demo_id("user", "owner", index)
        owner_ids.append(user_id)
        users.append(
            User(
                id=user_id,
                platform_role_id=role_ids[RoleCode.BUSINESS_OWNER],
                email=f"demo.owner{index + 1:02d}@example.test",
                password_hash=demo_password_hash,
                full_name=f"Pemilik Demo {index + 1}",
                status="ACTIVE",
                email_verified_at=now,
                password_changed_at=now,
                failed_login_attempts=0,
                **stamp(now),
            )
        )
    for index in range(7):
        user_id = demo_id("user", "staff", index)
        staff_ids.append(user_id)
        users.append(
            User(
                id=user_id,
                platform_role_id=role_ids[RoleCode.BUSINESS_STAFF],
                email=f"demo.staff{index + 1:02d}@example.test",
                password_hash=demo_password_hash,
                full_name=f"Kasir Demo {index + 1}",
                status="ACTIVE",
                email_verified_at=now,
                password_changed_at=now,
                failed_login_attempts=0,
                **stamp(now),
            )
        )
    for index in range(3):
        user_id = demo_id("user", "mentor", index)
        mentor_user_ids.append(user_id)
        users.append(
            User(
                id=user_id,
                platform_role_id=role_ids[RoleCode.MENTOR],
                email=f"demo.mentor{index + 1:02d}@example.test",
                password_hash=demo_password_hash,
                full_name=f"Pembina Demo {index + 1}",
                status="ACTIVE",
                email_verified_at=now,
                password_changed_at=now,
                failed_login_attempts=0,
                **stamp(now),
            )
        )
    await add_missing(session, User, users)
    mentors = [
        Mentor(id=demo_id("mentor", i), user_id=user_id, status="ACTIVE", **stamp(now))
        for i, user_id in enumerate(mentor_user_ids)
    ]
    await add_missing(session, Mentor, mentors)
    mentor_ids = [mentor.id for mentor in mentors]

    businesses: list[Business] = []
    profiles: list[BusinessProfile] = []
    completions: list[OnboardingCompletion] = []
    business_members: list[BusinessMember] = []
    organization_members: list[OrganizationMember] = []
    payment_methods: list[BusinessPaymentMethod] = []
    for index, (business_type, business_name) in enumerate(
        zip(BUSINESS_TYPES, BUSINESS_NAMES, strict=True)
    ):
        business_id = demo_id("business", index)
        category_code, profile_type = DEMO_CATEGORIES[business_type]
        business = Business(
            id=business_id,
            organization_id=org_id,
            code=f"DEMO-{index + 1:02d}",
            name=business_name,
            status="ACTIVE",
            **stamp(now),
        )
        businesses.append(business)
        profile = BusinessProfile(
            id=demo_id("profile", index),
            business_id=business_id,
            category_id=business_category_id(category_code),
            business_type=profile_type,
            scale=("MICRO", "SMALL", "MEDIUM")[index % 3],
            established_year=2017 + index % 7,
            address=f"Jl. Contoh Demo No. {index + 1}",
            village="Kelurahan Fiktif",
            district="Kecamatan Fiktif",
            city=("Bandung", "Surabaya", "Yogyakarta", "Semarang", "Malang")[index % 5],
            province="Jawa Barat" if index % 2 == 0 else "Jawa Timur",
            # Reserved-looking fictional number; never use a real contact.
            phone=f"+62000000000{index + 1:02d}",
            email=f"usaha{index + 1:02d}@example.test",
            employee_count=2 + index % 8,
            currency="IDR",
            timezone="Asia/Jakarta",
            recording_method="CASH",
            status="ACTIVE",
            has_products_and_stock=True,
            tutorial_completed_at=now,
            onboarding_completed_at=now,
            **stamp(now),
        )
        profiles.append(profile)
        completions.append(
            OnboardingCompletion(
                id=demo_id("onboarding", index),
                user_id=owner_ids[index],
                business_id=business_id,
                opening_balance=Decimal(2500000 + index * 350000),
                **stamp(now),
            )
        )
        business_members.append(
            BusinessMember(
                id=demo_id("member", index, "owner"),
                business_id=business_id,
                user_id=owner_ids[index],
                role_id=role_ids[RoleCode.BUSINESS_OWNER],
                status="ACTIVE",
                joined_at=now,
                **stamp(now),
            )
        )
        if index < len(staff_ids):
            business_members.append(
                BusinessMember(
                    id=demo_id("member", index, "staff"),
                    business_id=business_id,
                    user_id=staff_ids[index],
                    role_id=role_ids[RoleCode.BUSINESS_STAFF],
                    status="ACTIVE",
                    joined_at=now,
                    **stamp(now),
                )
            )
        organization_members.append(
            OrganizationMember(
                id=demo_id("org-member", index),
                organization_id=org_id,
                user_id=owner_ids[index],
                role_id=role_ids[RoleCode.BUSINESS_OWNER],
                status="ACTIVE",
                **stamp(now),
            )
        )
    for index, user_id in enumerate(mentor_user_ids):
        organization_members.append(
            OrganizationMember(
                id=demo_id("org-member", "mentor", index),
                organization_id=org_id,
                user_id=user_id,
                role_id=role_ids[RoleCode.MENTOR],
                status="ACTIVE",
                **stamp(now),
            )
        )
    await add_missing(session, Business, businesses)
    await add_missing(session, BusinessProfile, profiles)
    await add_missing(session, OnboardingCompletion, completions)
    await add_missing(session, BusinessMember, business_members)
    await add_missing(session, OrganizationMember, organization_members)

    # Accounts are deterministic so payment methods and journal lines remain stable.
    accounts_by_business: dict[UUID, dict[str, Account]] = {}
    account_rows: list[Account] = []
    for index, business in enumerate(businesses):
        by_key: dict[str, Account] = {}
        for template in ACCOUNT_TEMPLATES:
            account_id = demo_id("account", index, template.key.value)
            account = Account(
                id=account_id,
                business_id=business.id,
                code=template.code,
                name=template.name,
                system_key=template.key.value,
                account_type=template.account_type.value,
                normal_balance=template.normal_balance.value,
                is_system=True,
                is_active=True,
                **stamp(now),
            )
            account_rows.append(account)
            by_key[template.key.value] = account
        accounts_by_business[business.id] = by_key
    await add_missing(session, Account, account_rows)
    for index, business in enumerate(businesses):
        by_key = accounts_by_business[business.id]
        payment_methods.extend(
            BusinessPaymentMethod(
                id=demo_id("payment-method", index, code),
                business_id=business.id,
                account_id=by_key[account_key].id,
                code=code,
                name=name,
                is_active=True,
                **stamp(now),
            )
            for code, name, account_key in (
                ("CASH", "Tunai", AccountKey.CASH.value),
                ("BANK_TRANSFER", "Transfer Bank", AccountKey.BANK.value),
                ("QRIS", "QRIS", AccountKey.DIGITAL_WALLET.value),
            )
        )
    await add_missing(session, BusinessPaymentMethod, payment_methods)

    # Ten mentor assignments (each mentor receives multiple businesses).
    accesses = [
        MentorBusinessAccess(
            id=demo_id("mentor-access", index),
            mentor_id=mentor_ids[index % 3],
            business_id=business.id,
            role_id=role_ids[RoleCode.MENTOR],
            requested_by_user_id=mentor_user_ids[index % 3],
            granted_by_user_id=owner_ids[index],
            scope=[
                "SUMMARY",
                "REPORTS",
                "TRANSACTIONS",
                "RECEIPTS",
                "INVENTORY",
                "OBLIGATIONS",
                "EXPORT_REPORTS",
            ],
            status="ACTIVE",
            request_message="Pendampingan demo",
            requested_at=now - timedelta(days=20),
            granted_at=now - timedelta(days=19),
            expires_at=now + timedelta(days=180),
            revision_no=1,
            **stamp(now),
        )
        for index, business in enumerate(businesses)
    ]
    # A few UMKM intentionally have a second pembina to demonstrate the
    # many-to-many access model.
    accesses.extend(
        MentorBusinessAccess(
            id=demo_id("mentor-access", "secondary", index),
            mentor_id=mentor_ids[(index + 1) % 3],
            business_id=businesses[index].id,
            role_id=role_ids[RoleCode.MENTOR],
            requested_by_user_id=mentor_user_ids[(index + 1) % 3],
            granted_by_user_id=owner_ids[index],
            scope=["SUMMARY", "REPORTS"],
            status="ACTIVE",
            request_message="Pendampingan demo kedua",
            requested_at=now - timedelta(days=18),
            granted_at=now - timedelta(days=17),
            expires_at=now + timedelta(days=150),
            revision_no=1,
            **stamp(now),
        )
        for index in range(3)
    )
    await add_missing(session, MentorBusinessAccess, accesses)

    # One hundred products, ten per business.
    products: list[Product] = []
    for business_index, business in enumerate(businesses):
        business_type = BUSINESS_TYPES[business_index]
        names = PRODUCT_NAMES[business_type]
        for product_index in range(10):
            name = (
                f"{names[product_index % len(names)]} {product_index // len(names) + 1}"
                if product_index >= len(names)
                else names[product_index]
            )
            purchase = Decimal(8000 + product_index * 2750 + business_index * 500)
            sale = purchase + Decimal(5000 + business_index * 300)
            stock = Decimal(10 + (product_index * 3 + business_index) % 30)
            products.append(
                Product(
                    id=demo_id("product", business_index, product_index),
                    business_id=business.id,
                    sku=f"{business.code}-SKU-{product_index + 1:03d}",
                    barcode=f"899900{business_index:02d}{product_index:04d}",
                    name=name,
                    category=business_type.title(),
                    unit="pcs",
                    purchase_price=purchase,
                    sale_price=sale,
                    opening_stock=stock,
                    current_stock=stock,
                    minimum_stock=Decimal(5),
                    is_active=True,
                    **stamp(now),
                )
            )
    await add_missing(session, Product, products)

    # Five hundred balanced transactions and corresponding journal entries/lines.
    base_date = DEMO_TODAY - timedelta(days=90)
    tx_specs: list[str] = (
        ["CREDIT_PURCHASE"] * 30
        + ["CREDIT_SALE"] * 30
        + ["PAYABLE_PAYMENT"] * 15
        + ["RECEIVABLE_RECEIPT"] * 15
    )
    generic = [
        "CASH_SALE",
        "NON_CASH_SALE",
        "CASH_PURCHASE",
        "CAPITAL_CONTRIBUTION",
        "OWNER_DRAW",
        "OPERATING_EXPENSE",
    ]
    tx_specs.extend(generic[index % len(generic)] for index in range(410))
    transactions: list[FinancialTransaction] = []
    journals: list[JournalEntry] = []
    lines: list[JournalLine] = []
    revisions: list[TransactionRevision] = []
    audit_logs: list[AuditLog] = []
    tx_by_index: dict[int, FinancialTransaction] = {}
    for tx_index, transaction_type in enumerate(tx_specs):
        business_index = tx_index % 10
        business = businesses[business_index]
        actor_id = owner_ids[business_index]
        amount = Decimal(75000 + ((tx_index * 13750 + business_index * 5000) % 1950000)).quantize(
            Decimal("0.01")
        )
        # Payment transactions mirror the linked obligation so the demo is
        # coherent in both the journal and the utang/piutang screens.
        if 60 <= tx_index < 75:
            obligation_index = tx_index - 50  # 10..24
            source_amount = tx_by_index[obligation_index].amount
            amount = source_amount * (Decimal("0.40") if obligation_index < 20 else Decimal("1.00"))
        elif 75 <= tx_index < 90:
            obligation_index = tx_index - 35  # credit-sale 40..54
            source_amount = tx_by_index[obligation_index].amount
            amount = source_amount * (Decimal("0.40") if obligation_index < 50 else Decimal("1.00"))
        tx_date = base_date + timedelta(days=(tx_index * 7) % 91)
        posted_at = datetime.combine(tx_date, datetime.min.time(), tzinfo=UTC) + timedelta(
            hours=9, minutes=tx_index % 45
        )
        debit_key: str
        credit_key: str
        payment_method = "CASH"
        category_key: str | None = None
        if transaction_type == "CASH_SALE":
            debit_key, credit_key, category_key = (
                AccountKey.CASH.value,
                AccountKey.SALES.value,
                AccountKey.SALES.value,
            )
        elif transaction_type == "NON_CASH_SALE":
            debit_key, credit_key, category_key, payment_method = (
                AccountKey.DIGITAL_WALLET.value,
                AccountKey.SALES.value,
                AccountKey.SALES.value,
                "QRIS",
            )
        elif transaction_type == "CREDIT_SALE":
            debit_key, credit_key, category_key = (
                AccountKey.RECEIVABLE.value,
                AccountKey.SALES.value,
                AccountKey.SALES.value,
            )
        elif transaction_type == "CASH_PURCHASE":
            debit_key, credit_key, category_key = (
                AccountKey.INVENTORY.value,
                AccountKey.CASH.value,
                AccountKey.INVENTORY.value,
            )
        elif transaction_type == "CREDIT_PURCHASE":
            debit_key, credit_key, category_key = (
                AccountKey.INVENTORY.value,
                AccountKey.PAYABLE.value,
                AccountKey.INVENTORY.value,
            )
        elif transaction_type == "PAYABLE_PAYMENT":
            debit_key, credit_key = AccountKey.PAYABLE.value, AccountKey.CASH.value
        elif transaction_type == "RECEIVABLE_RECEIPT":
            debit_key, credit_key = AccountKey.CASH.value, AccountKey.RECEIVABLE.value
        elif transaction_type == "CAPITAL_CONTRIBUTION":
            debit_key, credit_key = AccountKey.CASH.value, AccountKey.OWNER_CAPITAL.value
        elif transaction_type == "OWNER_DRAW":
            debit_key, credit_key = AccountKey.OWNER_DRAW.value, AccountKey.CASH.value
        else:
            expense_key = [
                AccountKey.TRANSPORTATION.value,
                AccountKey.ELECTRICITY.value,
                AccountKey.INTERNET.value,
                AccountKey.PROMOTION.value,
            ][tx_index % 4]
            debit_key, credit_key, category_key = (
                expense_key,
                (AccountKey.BANK.value if tx_index % 3 == 0 else AccountKey.CASH.value),
                expense_key,
            )
            payment_method = "BANK_TRANSFER" if credit_key == AccountKey.BANK.value else "CASH"
        tx_id = demo_id("transaction", tx_index)
        transaction = FinancialTransaction(
            id=tx_id,
            business_id=business.id,
            transaction_number=f"DEMO-{tx_index + 1:04d}",
            transaction_type=transaction_type,
            transaction_date=tx_date,
            amount=amount,
            description=(
                f"Transaksi demo {transaction_type.replace('_', ' ').lower()} #{tx_index + 1:03d}"
            ),
            payment_account_key=debit_key
            if transaction_type
            in {
                "CASH_SALE",
                "NON_CASH_SALE",
                "CREDIT_SALE",
                "RECEIVABLE_RECEIPT",
                "CAPITAL_CONTRIBUTION",
            }
            else credit_key,
            category_account_key=category_key,
            entry_kind=(
                "INCOME"
                if "SALE" in transaction_type or transaction_type == "RECEIVABLE_RECEIPT"
                else (
                    "CAPITAL"
                    if transaction_type == "CAPITAL_CONTRIBUTION"
                    else ("OWNER_DRAW" if transaction_type == "OWNER_DRAW" else "EXPENSE")
                )
            ),
            counterparty_name=(
                f"Pelanggan Demo {business_index + 1}"
                if "SALE" in transaction_type
                else f"Pemasok Demo {business_index + 1}"
            ),
            payment_method_code=payment_method,
            status="POSTED",
            idempotency_key=f"demo:{tx_index}",
            revision_number=1,
            posted_at=posted_at,
            posted_by_user_id=actor_id,
            **stamp(posted_at),
        )
        entry = JournalEntry(
            id=demo_id("journal", tx_index),
            business_id=business.id,
            transaction_id=tx_id,
            entry_number=f"DEMO-J-{business_index + 1:02d}-{tx_index + 1:04d}",
            entry_date=tx_date,
            description=transaction.description,
            source="DEMO_SEED",
            status="POSTED",
            total_debit=amount,
            total_credit=amount,
            posted_at=posted_at,
            posted_by_user_id=actor_id,
            **stamp(posted_at),
        )
        debit_line = JournalLine(
            id=demo_id("journal-line", tx_index, "debit"),
            business_id=business.id,
            journal_entry_id=entry.id,
            account_id=accounts_by_business[business.id][debit_key].id,
            description=transaction.description,
            debit_amount=amount,
            credit_amount=Decimal("0.00"),
            **stamp(posted_at),
        )
        credit_line = JournalLine(
            id=demo_id("journal-line", tx_index, "credit"),
            business_id=business.id,
            journal_entry_id=entry.id,
            account_id=accounts_by_business[business.id][credit_key].id,
            description=transaction.description,
            debit_amount=Decimal("0.00"),
            credit_amount=amount,
            **stamp(posted_at),
        )
        revision = TransactionRevision(
            id=demo_id("transaction-revision", tx_index),
            business_id=business.id,
            transaction_id=tx_id,
            revision_number=1,
            event_sequence=1,
            event_type="POSTED",
            snapshot={"amount": str(amount), "type": transaction_type},
            reason="Seed data demo",
            actor_user_id=actor_id,
            created_at=posted_at,
        )
        transactions.append(transaction)
        journals.append(entry)
        lines.extend((debit_line, credit_line))
        revisions.append(revision)
        audit_logs.append(
            AuditLog(
                id=demo_id("audit", tx_index),
                business_id=business.id,
                actor_user_id=actor_id,
                action="TRANSACTION_POSTED",
                entity_type="FINANCIAL_TRANSACTION",
                entity_id=tx_id,
                before_data=None,
                after_data={"amount": str(amount), "type": transaction_type, "source": "DEMO_SEED"},
                reason="Seed data demo",
                request_id="demo-seed",
                created_at=posted_at,
            )
        )
        tx_by_index[tx_index] = transaction
    await add_missing(session, FinancialTransaction, transactions)
    await add_missing(session, JournalEntry, journals)
    await add_missing(session, JournalLine, lines)
    await add_missing(session, TransactionRevision, revisions)
    await add_missing(session, AuditLog, audit_logs)

    # Counterparties and 30 payables + 30 receivables.
    customers = [
        Customer(
            id=demo_id("customer", i),
            business_id=businesses[i % 10].id,
            name=f"Pelanggan Demo {i + 1:02d}",
            is_active=True,
            **stamp(now),
        )
        for i in range(30)
    ]
    suppliers = [
        Supplier(
            id=demo_id("supplier", i),
            business_id=businesses[i % 10].id,
            name=f"Pemasok Demo {i + 1:02d}",
            is_active=True,
            **stamp(now),
        )
        for i in range(30)
    ]
    await add_missing(session, Customer, customers)
    await add_missing(session, Supplier, suppliers)
    payables: list[Payable] = []
    receivables: list[Receivable] = []
    payable_payments: list[PayablePayment] = []
    receivable_payments: list[ReceivablePayment] = []
    for index in range(30):
        payable_tx = tx_by_index[index]
        receivable_tx = tx_by_index[index + 30]
        partial = payable_tx.amount * Decimal("0.40")
        status = (
            "OPEN"
            if index < 10
            else ("PARTIALLY_PAID" if index < 20 else ("PAID" if index < 25 else "OVERDUE"))
        )
        paid = (
            Decimal("0.00")
            if index < 10 or index >= 25
            else (partial if index < 20 else payable_tx.amount)
        )
        payable = Payable(
            id=demo_id("payable", index),
            business_id=payable_tx.business_id,
            supplier_id=suppliers[index].id,
            initial_transaction_id=payable_tx.id,
            initial_amount=payable_tx.amount,
            paid_amount=paid,
            remaining_amount=payable_tx.amount - paid,
            transaction_date=payable_tx.transaction_date,
            due_date=(
                payable_tx.transaction_date - timedelta(days=10)
                if index >= 25
                else payable_tx.transaction_date + timedelta(days=30)
            ),
            status=status,
            note="Utang demo",
            reminder_enabled=True,
            reminder_days_before=5,
            **stamp(now),
        )
        rstatus = (
            "OPEN"
            if index < 10
            else ("PARTIALLY_PAID" if index < 20 else ("PAID" if index < 25 else "OVERDUE"))
        )
        rpaid = (
            Decimal("0.00")
            if index < 10 or index >= 25
            else (receivable_tx.amount * Decimal("0.40") if index < 20 else receivable_tx.amount)
        )
        receivable = Receivable(
            id=demo_id("receivable", index),
            business_id=receivable_tx.business_id,
            customer_id=customers[index].id,
            initial_transaction_id=receivable_tx.id,
            initial_amount=receivable_tx.amount,
            paid_amount=rpaid,
            remaining_amount=receivable_tx.amount - rpaid,
            transaction_date=receivable_tx.transaction_date,
            due_date=(
                receivable_tx.transaction_date - timedelta(days=10)
                if index >= 25
                else receivable_tx.transaction_date + timedelta(days=30)
            ),
            status=rstatus,
            note="Piutang demo",
            reminder_enabled=True,
            reminder_days_before=5,
            **stamp(now),
        )
        payables.append(payable)
        receivables.append(receivable)
        if 10 <= index < 25:
            payment_tx = tx_by_index[(index - 10) + 60]
            amount = paid
            payable_payments.append(
                PayablePayment(
                    id=demo_id("payable-payment", index),
                    business_id=payable.business_id,
                    payable_id=payable.id,
                    transaction_id=payment_tx.id,
                    amount=amount,
                    payment_date=payment_tx.transaction_date,
                    payment_account_key=AccountKey.CASH.value,
                    note="Pembayaran demo",
                    created_by_user_id=owner_ids[index % 10],
                    created_at=payment_tx.posted_at,
                )
            )
            receipt_tx = tx_by_index[(index - 10) + 75]
            ramount = rpaid
            receivable_payments.append(
                ReceivablePayment(
                    id=demo_id("receivable-payment", index),
                    business_id=receivable.business_id,
                    receivable_id=receivable.id,
                    transaction_id=receipt_tx.id,
                    amount=ramount,
                    payment_date=receipt_tx.transaction_date,
                    payment_account_key=AccountKey.CASH.value,
                    note="Penerimaan demo",
                    created_by_user_id=owner_ids[index % 10],
                    created_at=receipt_tx.posted_at,
                )
            )
    await add_missing(session, Payable, payables)
    await add_missing(session, Receivable, receivables)
    await add_missing(session, PayablePayment, payable_payments)
    await add_missing(session, ReceivablePayment, receivable_payments)

    # One hundred nota, with OCR result and one stored-image metadata row each.
    receipts: list[Receipt] = []
    images: list[ReceiptImage] = []
    ocr_results: list[OcrResult] = []
    ocr_fields: list[OcrField] = []
    for index in range(100):
        transaction = tx_by_index[index + 100]
        receipt_id = demo_id("receipt", index)
        # Set duplicate links only after the complete receipt batch is flushed;
        # ``duplicate_of_receipt_id`` is a self-FK and PostgreSQL checks it
        # immediately.
        duplicate_of = None
        status = "CONFIRMED" if index < 78 else ("NEEDS_REVIEW" if index < 90 else "PROCESSING")
        receipt = Receipt(
            id=receipt_id,
            business_id=transaction.business_id,
            transaction_id=transaction.id,
            status=status,
            perceptual_hash=f"{index % 25:016x}",
            merchant_name=f"Toko Demo {index % 10 + 1:02d}",
            merchant_normalized=f"toko demo {index % 10 + 1:02d}",
            receipt_date=transaction.transaction_date,
            receipt_number=f"NOTA-DEMO-{index + 1:04d}",
            total_amount=transaction.amount,
            duplicate_of_receipt_id=duplicate_of,
            uploaded_by_user_id=owner_ids[index % 10],
            processing_started_at=transaction.posted_at,
            processing_completed_at=(
                transaction.posted_at + timedelta(seconds=2) if status != "PROCESSING" else None
            ),
            processing_duration_ms=(2000 if status != "PROCESSING" else None),
            confirmed_at=(transaction.posted_at if status == "CONFIRMED" else None),
            **stamp(transaction.posted_at),
        )
        result_id = demo_id("ocr-result", index)
        result = OcrResult(
            id=result_id,
            business_id=transaction.business_id,
            receipt_id=receipt_id,
            raw_text=(
                f"TOKO DEMO {index % 10 + 1:02d}\nTOTAL Rp{transaction.amount:,.2f}\nTERIMA KASIH"
            ),
            engine="demo-ml-kit",
            engine_version="1.0",
            mean_confidence=Decimal("0.96" if status == "CONFIRMED" else "0.71"),
            processing_duration_ms=2000,
            created_at=transaction.posted_at,
        )
        for field_name, value in (
            ("merchant_name", receipt.merchant_name or ""),
            ("receipt_date", transaction.transaction_date.isoformat()),
            ("total", str(transaction.amount)),
        ):
            ocr_fields.append(
                OcrField(
                    id=demo_id("ocr-field", index, field_name),
                    business_id=transaction.business_id,
                    receipt_id=receipt_id,
                    ocr_result_id=result_id,
                    field_name=field_name,
                    field_value=value,
                    normalized_value=value,
                    confidence=Decimal("0.96" if status == "CONFIRMED" else "0.71"),
                    source_text=value,
                    is_user_corrected=False,
                    **stamp(transaction.posted_at),
                )
            )
        images.append(
            ReceiptImage(
                id=demo_id("receipt-image", index),
                business_id=transaction.business_id,
                transaction_id=transaction.id,
                receipt_id=receipt_id,
                image_kind="ORIGINAL",
                object_key=f"demo/receipts/{receipt_id}.jpg",
                content_type="image/jpeg",
                size_bytes=145000 + index * 100,
                width=1280,
                height=960,
                perceptual_hash=receipt.perceptual_hash,
                uploaded_by_user_id=receipt.uploaded_by_user_id,
                **stamp(transaction.posted_at),
            )
        )
        receipts.append(receipt)
        ocr_results.append(result)
    await add_missing(session, Receipt, receipts)
    for index, receipt in enumerate(receipts):
        if index and index % 25 == 0:
            # Duplicate candidates share the same tenant, date, total, merchant,
            # number, and perceptual hash so the normal duplicate detector can
            # discover them without relying on the explicit relation.
            reference = receipts[index - 10]
            receipt.duplicate_of_receipt_id = reference.id
            receipt.perceptual_hash = reference.perceptual_hash
            receipt.merchant_name = reference.merchant_name
            receipt.merchant_normalized = reference.merchant_normalized
            receipt.receipt_date = reference.receipt_date
            receipt.receipt_number = reference.receipt_number
            receipt.total_amount = reference.total_amount
    await session.flush()
    await add_missing(session, ReceiptImage, images)
    await add_missing(session, OcrResult, ocr_results)
    await add_missing(session, OcrField, ocr_fields)

    recommendations = [
        Recommendation(
            id=demo_id("recommendation", index),
            business_id=businesses[index % 10].id,
            mentor_id=mentor_ids[index % 3],
            title=("Catat transaksi setiap hari" if index % 2 == 0 else "Pantau stok minimum"),
            description="Gunakan KASTA secara rutin agar kondisi usaha mudah dipantau.",
            priority=("HIGH" if index % 5 == 0 else "MEDIUM"),
            status=("DONE" if index % 5 == 0 else ("IN_PROGRESS" if index % 3 == 0 else "OPEN")),
            due_date=DEMO_TODAY + timedelta(days=14 + index),
            follow_up_note=("Sudah dibahas pada sesi demo" if index % 5 == 0 else None),
            completed_at=(now if index % 5 == 0 else None),
            **stamp(now),
        )
        for index in range(20)
    ]
    sessions = [
        MentoringSession(
            id=demo_id("session", index),
            business_id=businesses[index % 10].id,
            mentor_id=mentor_ids[index % 3],
            scheduled_at=(
                now - timedelta(days=3 + index, hours=2)
                if index < 8
                else now + timedelta(days=3 + index, hours=2)
            ),
            duration_minutes=60,
            mode=("ONLINE" if index % 2 == 0 else "ONSITE"),
            status=("COMPLETED" if index < 8 else "SCHEDULED"),
            topic=(
                "Review laporan bulanan" if index % 2 == 0 else "Pendampingan pencatatan harian"
            ),
            location=("Ruang virtual demo" if index % 2 == 0 else "Lokasi usaha demo"),
            outcome=("Pemilik memahami ringkasan usaha." if index < 8 else None),
            follow_up_date=(DEMO_TODAY + timedelta(days=30) if index < 8 else None),
            completed_at=(now - timedelta(days=1) if index < 8 else None),
            **stamp(now),
        )
        for index in range(20)
    ]
    await add_missing(session, Recommendation, recommendations)
    await add_missing(session, MentoringSession, sessions)
    await session.commit()
    return DemoSeedCounts()


# Backwards-compatible alias for callers that used the shorter name in early
# local scripts.  New code should import ``seed_demo_data``.
seed_demo = seed_demo_data


async def run() -> None:
    parser = argparse.ArgumentParser(description="Seed data demo KASTA yang fiktif dan idempotent")
    parser.parse_args()
    from kasta_api.core.config import get_settings

    settings = get_settings()
    if settings.environment == "production":
        raise SystemExit(
            "Seed demo diblokir pada production. Gunakan environment development/staging."
        )
    try:
        async with AsyncSessionFactory() as session:
            counts = await seed_demo_data(session)
            print("Seed demo selesai:")
            for table, count in asdict(counts).items():
                print(f"  {table}: {count}")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(run())
