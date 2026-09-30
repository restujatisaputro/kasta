"""Create fictitious UMKM owner accounts with complete daily bookkeeping for a period.

Unlike :mod:`kasta_api.seed_demo`, this command may run on production, but only
with ``--izinkan-production``: it adds new tenants and never touches existing
rows.  Records use stable UUID5 values, so a second run with the same arguments
is a no-op.  Passwords are generated per run and printed once; they are not
stored anywhere except as Argon2id hashes.

Run inside the API container with an owner (bypass-RLS) database URL::

    python -m kasta_api.seed_umkm_periode --jumlah 5 --mulai 2026-08-01 --sampai 2026-09-30
"""

from __future__ import annotations

import argparse
import asyncio
import random
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

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
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.security import PasswordManager
from kasta_api.modules.businesses.categories import business_category_id
from kasta_api.modules.businesses.models import (
    Business,
    BusinessMember,
    BusinessPaymentMethod,
    BusinessProfile,
    OnboardingCompletion,
)
from kasta_api.modules.users.models import User
from kasta_api.seed_demo import DEMO_CATEGORIES, add_missing, ensure_reference, stamp

NAMESPACE = UUID("8f0d6c52-2d7e-4c55-9a3b-6f1e4b7a2c90")
JAKARTA = ZoneInfo("Asia/Jakarta")
USAHA = [
    ("warung makan", "Warung Makan Bu Sari", Decimal(900_000)),
    ("kopi", "Kedai Kopi Lintang", Decimal(750_000)),
    ("laundry", "Laundry Wangi Kilat", Decimal(450_000)),
    ("toko kelontong", "Toko Kelontong Berkah", Decimal(1_200_000)),
    ("katering", "Katering Dapur Ibu", Decimal(1_500_000)),
    ("fesyen", "Butik Kain Nusa", Decimal(800_000)),
    ("kerajinan", "Kriya Bambu Asri", Decimal(600_000)),
    ("bengkel", "Bengkel Motor Sinar", Decimal(700_000)),
    ("jasa digital", "Studio Desain Rupa", Decimal(650_000)),
    ("toko online", "Lapak Online Ceria", Decimal(1_000_000)),
]
BULAN = (
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)
INCOME_TYPES = {"CASH_SALE", "NON_CASH_SALE", "CAPITAL_CONTRIBUTION"}


def seed_id(kind: str, *parts: object) -> UUID:
    return uuid5(NAMESPACE, ":".join((kind, *(str(part) for part in parts))))


def rupiah(value: Decimal | float) -> Decimal:
    """Round to a realistic Rp500 multiple, never below Rp1.000."""
    rounded = (Decimal(value) / 500).quantize(Decimal(1)) * 500
    return max(rounded, Decimal(1000)).quantize(Decimal("0.01"))


def daily_plan(
    rng: random.Random, day: date, start: date, daily_sales: Decimal
) -> list[tuple[str, str, str, Decimal, str]]:
    """Return (type, debit key, credit key, amount, description) rows for one day."""

    rows: list[tuple[str, str, str, Decimal, str]] = []
    if day == start:
        rows.append(
            (
                "CAPITAL_CONTRIBUTION",
                AccountKey.CASH.value,
                AccountKey.OWNER_CAPITAL.value,
                rupiah(daily_sales * 10),
                "Setoran modal awal periode",
            )
        )
    weekend = day.weekday() >= 5
    factor = Decimal(str(rng.uniform(0.75, 1.3))) * (Decimal("1.2") if weekend else 1)
    total_sales = daily_sales * factor
    qris_share = Decimal(str(rng.uniform(0.15, 0.25)))
    rows.append(
        (
            "CASH_SALE",
            AccountKey.CASH.value,
            AccountKey.SALES.value,
            rupiah(total_sales * (1 - qris_share)),
            "Penjualan tunai harian",
        )
    )
    rows.append(
        (
            "NON_CASH_SALE",
            AccountKey.DIGITAL_WALLET.value,
            AccountKey.SALES.value,
            rupiah(total_sales * qris_share),
            "Penjualan QRIS harian",
        )
    )
    if (day - start).days % 3 == 0:
        rows.append(
            (
                "OPERATING_EXPENSE",
                AccountKey.PURCHASES.value,
                AccountKey.CASH.value,
                rupiah(daily_sales * Decimal(str(rng.uniform(1.4, 1.8)))),
                "Belanja bahan/stok",
            )
        )
    if day.weekday() == 0:
        rows.append(
            (
                "OPERATING_EXPENSE",
                AccountKey.TRANSPORTATION.value,
                AccountKey.CASH.value,
                rupiah(Decimal(rng.randint(60, 150)) * 1000),
                "Biaya transportasi mingguan",
            )
        )
    monthly = {
        1: (AccountKey.RENT, AccountKey.CASH, Decimal("3.0"), "Sewa tempat usaha"),
        5: (AccountKey.ELECTRICITY, AccountKey.CASH, Decimal("0.45"), "Tagihan listrik"),
        10: (AccountKey.INTERNET, AccountKey.CASH, Decimal("0.3"), "Tagihan internet"),
        15: (AccountKey.PROMOTION, AccountKey.CASH, Decimal("0.4"), "Biaya promosi"),
        25: (AccountKey.SALARY, AccountKey.CASH, Decimal("4.0"), "Gaji karyawan"),
    }
    if day.day in monthly:
        expense_key, paid_from, ratio, description = monthly[day.day]
        rows.append(
            (
                "OPERATING_EXPENSE",
                expense_key.value,
                paid_from.value,
                rupiah(daily_sales * ratio),
                f"{description} {BULAN[day.month]} {day.year}",
            )
        )
    if (day + timedelta(days=1)).month != day.month:
        rows.append(
            (
                "OWNER_DRAW",
                AccountKey.OWNER_DRAW.value,
                AccountKey.CASH.value,
                rupiah(daily_sales * Decimal("2.5")),
                f"Prive pemilik {BULAN[day.month]} {day.year}",
            )
        )
    return rows


async def seed(
    jumlah: int, start: date, end: date, email_domain: str
) -> list[tuple[str, str, str]]:
    now = datetime.now(UTC).replace(microsecond=0)
    password_manager = PasswordManager()
    credentials: list[tuple[str, str, str]] = []
    owner_role = role_id(RoleCode.BUSINESS_OWNER)
    async with AsyncSessionFactory() as session:
        await ensure_reference(session)
        for index in range(jumlah):
            business_type, business_name, daily_sales = USAHA[index % len(USAHA)]
            number = index + 1
            code = f"UMKM-{start:%Y%m}-{number:02d}"
            email = f"umkm{start:%Y%m}.{number:02d}@{email_domain}"
            user_id = seed_id("user", code)
            business_id = seed_id("business", code)
            existing_user = await session.get(User, user_id)
            password = None
            if existing_user is None:
                password = secrets.token_urlsafe(12)
                await add_missing(
                    session,
                    User,
                    [
                        User(
                            id=user_id,
                            platform_role_id=owner_role,
                            email=email,
                            password_hash=password_manager.hash(password),
                            full_name=f"Pemilik {business_name}",
                            status="ACTIVE",
                            email_verified_at=now,
                            password_changed_at=now,
                            failed_login_attempts=0,
                            **stamp(now),
                        )
                    ],
                )
            credentials.append((email, password or "(sudah ada, tidak diubah)", business_name))

            category_code, profile_type = DEMO_CATEGORIES[business_type]
            await add_missing(
                session,
                Business,
                [
                    Business(
                        id=business_id, code=code, name=business_name, status="ACTIVE", **stamp(now)
                    )
                ],
            )
            await add_missing(
                session,
                BusinessProfile,
                [
                    BusinessProfile(
                        id=seed_id("profile", code),
                        business_id=business_id,
                        category_id=business_category_id(category_code),
                        business_type=profile_type,
                        scale="MICRO",
                        established_year=2019 + index % 5,
                        address=f"Jl. Contoh UMKM No. {number}",
                        village="Kelurahan Fiktif",
                        district="Kecamatan Fiktif",
                        city="Depok",
                        province="Jawa Barat",
                        email=f"usaha.{code.lower()}@{email_domain}",
                        employee_count=1 + index % 4,
                        currency="IDR",
                        timezone="Asia/Jakarta",
                        recording_method="CASH",
                        status="ACTIVE",
                        has_products_and_stock=False,
                        tutorial_completed_at=now,
                        onboarding_completed_at=now,
                        **stamp(now),
                    )
                ],
            )
            await add_missing(
                session,
                OnboardingCompletion,
                [
                    OnboardingCompletion(
                        id=seed_id("onboarding", code),
                        user_id=user_id,
                        business_id=business_id,
                        opening_balance=Decimal(0),
                        **stamp(now),
                    )
                ],
            )
            await add_missing(
                session,
                BusinessMember,
                [
                    BusinessMember(
                        id=seed_id("member", code),
                        business_id=business_id,
                        user_id=user_id,
                        role_id=owner_role,
                        status="ACTIVE",
                        joined_at=now,
                        **stamp(now),
                    )
                ],
            )
            accounts = {
                template.key.value: Account(
                    id=seed_id("account", code, template.key.value),
                    business_id=business_id,
                    code=template.code,
                    name=template.name,
                    system_key=template.key.value,
                    account_type=template.account_type.value,
                    normal_balance=template.normal_balance.value,
                    is_system=True,
                    is_active=True,
                    **stamp(now),
                )
                for template in ACCOUNT_TEMPLATES
            }
            await add_missing(session, Account, list(accounts.values()))
            await add_missing(
                session,
                BusinessPaymentMethod,
                [
                    BusinessPaymentMethod(
                        id=seed_id("payment-method", code, method),
                        business_id=business_id,
                        account_id=accounts[account_key].id,
                        code=method,
                        name=name,
                        is_active=True,
                        **stamp(now),
                    )
                    for method, name, account_key in (
                        ("CASH", "Tunai", AccountKey.CASH.value),
                        ("BANK_TRANSFER", "Transfer Bank", AccountKey.BANK.value),
                        ("QRIS", "QRIS", AccountKey.DIGITAL_WALLET.value),
                    )
                ],
            )

            rng = random.Random(f"{code}:{start}:{end}")
            transactions: list[FinancialTransaction] = []
            journals: list[JournalEntry] = []
            lines: list[JournalLine] = []
            revisions: list[TransactionRevision] = []
            audits: list[AuditLog] = []
            sequence = 0
            day = start
            while day <= end:
                for tx_type, debit_key, credit_key, amount, description in daily_plan(
                    rng, day, start, daily_sales
                ):
                    sequence += 1
                    local_time = datetime.combine(day, datetime.min.time(), tzinfo=JAKARTA)
                    posted_at = (
                        local_time + timedelta(hours=8, minutes=sequence * 7 % 600)
                    ).astimezone(UTC)
                    tx_id = seed_id("transaction", code, sequence)
                    payment_key = debit_key if tx_type in INCOME_TYPES else credit_key
                    method = {
                        AccountKey.DIGITAL_WALLET.value: "QRIS",
                        AccountKey.BANK.value: "BANK_TRANSFER",
                    }.get(payment_key, "CASH")
                    is_sale = "SALE" in tx_type
                    transactions.append(
                        FinancialTransaction(
                            id=tx_id,
                            business_id=business_id,
                            transaction_number=f"{code}-{sequence:05d}",
                            transaction_type=tx_type,
                            transaction_date=day,
                            amount=amount,
                            description=description,
                            payment_account_key=payment_key,
                            category_account_key=(
                                None
                                if tx_type in {"CAPITAL_CONTRIBUTION", "OWNER_DRAW"}
                                else (AccountKey.SALES.value if is_sale else debit_key)
                            ),
                            entry_kind=(
                                "INCOME"
                                if is_sale
                                else {
                                    "CAPITAL_CONTRIBUTION": "CAPITAL",
                                    "OWNER_DRAW": "OWNER_DRAW",
                                }.get(tx_type, "EXPENSE")
                            ),
                            counterparty_name="Pelanggan umum" if is_sale else None,
                            payment_method_code=method,
                            status="POSTED",
                            idempotency_key=f"seed-umkm:{code}:{sequence}",
                            revision_number=1,
                            posted_at=posted_at,
                            posted_by_user_id=user_id,
                            **stamp(posted_at),
                        )
                    )
                    entry_id = seed_id("journal", code, sequence)
                    journals.append(
                        JournalEntry(
                            id=entry_id,
                            business_id=business_id,
                            transaction_id=tx_id,
                            entry_number=f"J-{code}-{sequence:05d}",
                            entry_date=day,
                            description=description,
                            source="SEED_UMKM",
                            status="POSTED",
                            total_debit=amount,
                            total_credit=amount,
                            posted_at=posted_at,
                            posted_by_user_id=user_id,
                            **stamp(posted_at),
                        )
                    )
                    for side, account_key in (("debit", debit_key), ("credit", credit_key)):
                        lines.append(
                            JournalLine(
                                id=seed_id("journal-line", code, sequence, side),
                                business_id=business_id,
                                journal_entry_id=entry_id,
                                account_id=accounts[account_key].id,
                                description=description,
                                debit_amount=amount if side == "debit" else Decimal("0.00"),
                                credit_amount=amount if side == "credit" else Decimal("0.00"),
                                **stamp(posted_at),
                            )
                        )
                    snapshot = {"amount": str(amount), "type": tx_type}
                    revisions.append(
                        TransactionRevision(
                            id=seed_id("revision", code, sequence),
                            business_id=business_id,
                            transaction_id=tx_id,
                            revision_number=1,
                            event_sequence=1,
                            event_type="POSTED",
                            snapshot=snapshot,
                            reason="Seed data UMKM",
                            actor_user_id=user_id,
                            created_at=posted_at,
                        )
                    )
                    audits.append(
                        AuditLog(
                            id=seed_id("audit", code, sequence),
                            business_id=business_id,
                            actor_user_id=user_id,
                            action="TRANSACTION_POSTED",
                            entity_type="FINANCIAL_TRANSACTION",
                            entity_id=tx_id,
                            before_data=None,
                            after_data={**snapshot, "source": "SEED_UMKM"},
                            reason="Seed data UMKM",
                            request_id="seed-umkm",
                            created_at=posted_at,
                        )
                    )
                day += timedelta(days=1)
            await add_missing(session, FinancialTransaction, transactions)
            await add_missing(session, JournalEntry, journals)
            await add_missing(session, JournalLine, lines)
            await add_missing(session, TransactionRevision, revisions)
            await add_missing(session, AuditLog, audits)
            print(f"{code} {business_name}: {len(transactions)} transaksi {start}..{end}")
        await session.commit()
    return credentials


async def run() -> None:
    parser = argparse.ArgumentParser(description="Buat akun UMKM fiktif + transaksi harian lengkap")
    parser.add_argument("--jumlah", type=int, default=5)
    parser.add_argument("--mulai", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--sampai", type=date.fromisoformat, default=date(2026, 9, 30))
    parser.add_argument("--domain-email", default="example.test")
    parser.add_argument("--izinkan-production", action="store_true")
    args = parser.parse_args()
    from kasta_api.core.config import get_settings

    if get_settings().environment == "production" and not args.izinkan_production:
        raise SystemExit("Environment production: tambahkan --izinkan-production bila disengaja.")
    if not 1 <= args.jumlah <= len(USAHA) or args.sampai < args.mulai:
        raise SystemExit(f"--jumlah harus 1..{len(USAHA)} dan --sampai >= --mulai.")
    try:
        credentials = await seed(args.jumlah, args.mulai, args.sampai, args.domain_email)
    finally:
        await dispose_engine()
    print("\nAkun UMKM (simpan password ini, tidak ditampilkan lagi):")
    for email, password, name in credentials:
        print(f"  {email}  {password}  {name}")


if __name__ == "__main__":
    asyncio.run(run())
