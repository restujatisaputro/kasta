"""Seed 20 UMKM fiktif dengan pencatatan keuangan lengkap sejak 1 Agustus 2026.

Setiap UMKM mendapat satu pemilik (peran ``business_owner``) yang sudah selesai
onboarding, bagan akun standar, metode pembayaran, saldo awal, lalu transaksi
harian dari 1 Agustus 2026 sampai tanggal akhir (default 30 September 2026):

* penjualan harian (tunai, QRIS, transfer bank),
* belanja bahan/barang dagangan mingguan,
* beban bulanan (sewa, listrik, internet, gaji) dan beban kecil (transport,
  promosi, administrasi),
* prive pemilik di akhir bulan.

Semua ID diturunkan dengan UUID5 dari namespace tersendiri sehingga skrip
idempoten (baris yang sudah ada dilewati) dan mudah dihapus kembali.  Setiap
transaksi punya tepat dua baris jurnal yang seimbang.

Jalankan di container API dengan koneksi peran pemilik skema (bukan peran
runtime yang terkena RLS)::

    docker exec -i -e KASTA_DATABASE_URL=... kasta-production-api-1 \
        python - --izinkan-production < scripts/seed_umkm_agustus.py
"""

from __future__ import annotations

import argparse
import asyncio
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.db import models as _mapped_models  # noqa: F401  (daftarkan semua model)
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
    Organization,
    OrganizationMember,
)
from kasta_api.modules.users.models import User
from kasta_api.seed_demo import PASSWORD, add_missing, demo_id, ensure_reference, stamp

NAMESPACE = UUID("7c1f5a52-3d0e-4f7e-9a51-2b8f0c6d4e21")
START_DATE = date(2026, 8, 1)
DEFAULT_END_DATE = date(2026, 9, 30)
SOURCE = "UMKM_AGUSTUS_SEED"

# (nama usaha, nama pemilik, kode kategori, jenis profil, kota, provinsi)
UMKM = [
    ("Warung Bu Sari", "Sari Wulandari", "food", "CULINARY", "Depok", "Jawa Barat"),
    ("Toko Berkah Abadi", "Ahmad Fauzi", "retail", "TRADE", "Bogor", "Jawa Barat"),
    ("Kopi Tepi Kali", "Dimas Pratama", "beverage", "CULINARY", "Bekasi", "Jawa Barat"),
    ("Laundry Wangi Kilat", "Rina Marlina", "personal_service", "SERVICE", "Depok", "Jawa Barat"),
    ("Batik Kinanti", "Kinanti Rahayu", "fashion", "CREATIVE", "Solo", "Jawa Tengah"),
    ("Rotan Lestari", "Budi Santoso", "craft", "PRODUCTION", "Cirebon", "Jawa Barat"),
    ("Studio Kreasi Digital", "Fajar Nugroho", "professional_service", "SERVICE", "Jakarta Selatan", "DKI Jakarta"),
    ("Bengkel Motor Sejahtera", "Joko Susilo", "personal_service", "SERVICE", "Tangerang", "Banten"),
    ("Katering Dapur Ibu", "Siti Aminah", "food", "CULINARY", "Jakarta Timur", "DKI Jakarta"),
    ("Toko Online Serba Ada", "Nadia Putri", "retail", "TRADE", "Bandung", "Jawa Barat"),
    ("Bakso Mang Ujang", "Ujang Supriatna", "food", "CULINARY", "Bandung", "Jawa Barat"),
    ("Es Teh Segar Jaya", "Rizky Ramadhan", "beverage", "CULINARY", "Semarang", "Jawa Tengah"),
    ("Konveksi Mitra Busana", "Hendra Wijaya", "fashion", "CREATIVE", "Bandung", "Jawa Barat"),
    ("Kerajinan Kayu Jati Asri", "Slamet Riyadi", "craft", "PRODUCTION", "Jepara", "Jawa Tengah"),
    ("Sembako Murah Barokah", "Yusuf Hidayat", "retail", "TRADE", "Yogyakarta", "DI Yogyakarta"),
    ("Salon Cantik Ayu", "Ayu Lestari", "personal_service", "SERVICE", "Malang", "Jawa Timur"),
    ("Pecel Lele Cak Man", "Rohman Hakim", "food", "CULINARY", "Surabaya", "Jawa Timur"),
    ("Jahit Rapi Bu Tini", "Sutini Handayani", "fashion", "CREATIVE", "Klaten", "Jawa Tengah"),
    ("Keripik Singkong Renyah", "Dewi Anggraini", "food", "PRODUCTION", "Garut", "Jawa Barat"),
    ("Percetakan Cepat Kilat", "Agus Setiawan", "professional_service", "SERVICE", "Depok", "Jawa Barat"),
]

# Rentang omzet harian (rupiah) per jenis profil.
DAILY_SALES = {
    "CULINARY": (350_000, 1_200_000),
    "TRADE": (500_000, 2_000_000),
    "SERVICE": (200_000, 900_000),
    "CREATIVE": (250_000, 1_500_000),
    "PRODUCTION": (300_000, 1_300_000),
}


def sid(kind: str, *parts: object) -> UUID:
    return uuid5(NAMESPACE, ":".join((kind, *(str(part) for part in parts))))


def rupiah(value: float, step: int = 500) -> Decimal:
    return Decimal(int(round(value / step)) * step).quantize(Decimal("0.01"))


def month_ends(start: date, end: date) -> set[date]:
    result = set()
    day = start
    while day <= end:
        nxt = day + timedelta(days=1)
        if nxt.month != day.month:
            result.add(day)
        day = nxt
    return result


def plan_transactions(index: int, profile_type: str, end: date) -> list[dict]:
    """Rencana transaksi deterministik: (tanggal, jenis, jumlah, akun, deskripsi)."""

    rng = random.Random(f"umkm:{index}")
    low, high = DAILY_SALES[profile_type]
    is_service = profile_type == "SERVICE"
    revenue_key = AccountKey.SERVICE_REVENUE if is_service else AccountKey.SALES
    purchase_key = (
        AccountKey.RAW_MATERIALS
        if profile_type in {"CULINARY", "PRODUCTION", "CREATIVE"}
        else (AccountKey.PURCHASES if not is_service else AccountKey.RAW_MATERIALS)
    )
    rent = rupiah(rng.uniform(800_000, 2_500_000), 50_000)
    salary = rupiah(rng.uniform(1_500_000, 3_500_000), 50_000)
    closed_weekday = rng.randrange(7)
    plan: list[dict] = []
    ends = month_ends(START_DATE, end)
    day = START_DATE
    while day <= end:
        weekend = day.weekday() >= 5
        if day.weekday() != closed_weekday:
            # 1-3 penjualan per hari, lebih ramai di akhir pekan.
            for n in range(rng.randint(2, 3) if weekend else rng.randint(1, 2)):
                amount = rupiah(rng.uniform(low, high) * (1.25 if weekend else 1.0) / (n + 1))
                roll = rng.random()
                if roll < 0.55:
                    kind, debit, method = "CASH_SALE", AccountKey.CASH, "CASH"
                elif roll < 0.85:
                    kind, debit, method = "NON_CASH_SALE", AccountKey.DIGITAL_WALLET, "QRIS"
                else:
                    kind, debit, method = "NON_CASH_SALE", AccountKey.BANK, "BANK_TRANSFER"
                plan.append(
                    dict(
                        date=day,
                        type=kind,
                        amount=amount,
                        debit=debit,
                        credit=revenue_key,
                        category=revenue_key,
                        method=method,
                        entry_kind="INCOME",
                        description=("Pendapatan jasa" if is_service else "Penjualan harian")
                        + (" (tunai)" if method == "CASH" else f" via {method.replace('_', ' ').title()}"),
                        counterparty="Pelanggan umum",
                    )
                )
        # Belanja bahan/barang tiap Senin dan Kamis (~35-45% omzet).
        if day.weekday() in (0, 3):
            amount = rupiah(rng.uniform(low, high) * rng.uniform(1.0, 1.6), 1000)
            plan.append(
                dict(
                    date=day,
                    type="CASH_PURCHASE",
                    amount=amount,
                    debit=purchase_key,
                    credit=AccountKey.CASH,
                    category=purchase_key,
                    method="CASH",
                    entry_kind="EXPENSE",
                    description="Belanja bahan baku"
                    if purchase_key == AccountKey.RAW_MATERIALS
                    else "Belanja barang dagangan",
                    counterparty="Pemasok langganan",
                )
            )
        # Transport mingguan (Rabu) dan promosi dua mingguan.
        if day.weekday() == 2:
            plan.append(
                _expense(day, AccountKey.TRANSPORTATION, rupiah(rng.uniform(50_000, 200_000)),
                         "Bensin dan ongkos antar", AccountKey.CASH)
            )
        if day.day in (10, 24):
            plan.append(
                _expense(day, AccountKey.PROMOTION, rupiah(rng.uniform(100_000, 350_000), 1000),
                         "Iklan media sosial", AccountKey.BANK)
            )
        # Beban bulanan.
        if day.day == 1:
            plan.append(_expense(day, AccountKey.RENT, rent, "Sewa tempat usaha", AccountKey.BANK))
        if day.day == 5:
            plan.append(
                _expense(day, AccountKey.ELECTRICITY, rupiah(rng.uniform(250_000, 750_000), 1000),
                         "Token/tagihan listrik", AccountKey.CASH)
            )
            plan.append(
                _expense(day, AccountKey.INTERNET, rupiah(rng.uniform(150_000, 400_000), 1000),
                         "Paket internet", AccountKey.BANK)
            )
        if day.day == 15:
            plan.append(
                _expense(day, AccountKey.ADMINISTRATION, rupiah(rng.uniform(15_000, 60_000)),
                         "Biaya administrasi bank", AccountKey.BANK)
            )
        if day.day == 25:
            plan.append(_expense(day, AccountKey.SALARY, salary, "Gaji karyawan", AccountKey.CASH))
        if day in ends:
            plan.append(
                dict(
                    date=day,
                    type="OWNER_DRAW",
                    amount=rupiah(rng.uniform(500_000, 1_500_000), 50_000),
                    debit=AccountKey.OWNER_DRAW,
                    credit=AccountKey.CASH,
                    category=None,
                    method="CASH",
                    entry_kind="OWNER_DRAW",
                    description="Prive pemilik akhir bulan",
                    counterparty=None,
                )
            )
        day += timedelta(days=1)
    return plan


def keep_solvent(plan: list[dict], opening_cash: Decimal) -> list[dict]:
    """Jaga saldo kas dan bank tidak pernah minus.

    Pembayaran pindah ke rekening lain (kas <-> bank) bila saldo sumber kurang;
    bila keduanya kurang, pemilik menyetor modal tambahan tunai lebih dulu.
    Prive dilewati bila kas tidak cukup.
    """

    balance = {AccountKey.CASH: opening_cash, AccountKey.BANK: Decimal("0.00")}
    other = {AccountKey.CASH: AccountKey.BANK, AccountKey.BANK: AccountKey.CASH}
    result: list[dict] = []
    for item in plan:
        pay = item["credit"]
        if pay in balance and balance[pay] < item["amount"]:
            if item["type"] == "OWNER_DRAW":
                continue
            if balance[other[pay]] >= item["amount"]:
                pay = other[pay]
                item = {
                    **item,
                    "credit": pay,
                    "method": "BANK_TRANSFER" if pay == AccountKey.BANK else "CASH",
                }
            else:
                top_up = rupiah(float(item["amount"] - balance[pay]) + 500_000, 100_000)
                result.append(
                    dict(
                        date=item["date"],
                        type="CAPITAL_CONTRIBUTION",
                        amount=top_up,
                        debit=pay,
                        credit=AccountKey.OWNER_CAPITAL,
                        category=None,
                        method="BANK_TRANSFER" if pay == AccountKey.BANK else "CASH",
                        entry_kind="CAPITAL",
                        description="Setoran modal tambahan pemilik",
                        counterparty=None,
                    )
                )
                balance[pay] += top_up
        if item["debit"] in balance:
            balance[item["debit"]] += item["amount"]
        if item["credit"] in balance:
            balance[item["credit"]] -= item["amount"]
        result.append(item)
    return result


def _expense(day: date, key: AccountKey, amount: Decimal, description: str, pay: AccountKey) -> dict:
    return dict(
        date=day,
        type="OPERATING_EXPENSE",
        amount=amount,
        debit=key,
        credit=pay,
        category=key,
        method="BANK_TRANSFER" if pay == AccountKey.BANK else "CASH",
        entry_kind="EXPENSE",
        description=description,
        counterparty=None,
    )


async def seed(session: AsyncSession, end: date) -> dict[str, int]:
    await ensure_reference(session)
    now = datetime.now(UTC).replace(microsecond=0)
    onboard_at = datetime.combine(START_DATE, datetime.min.time(), tzinfo=UTC) + timedelta(hours=1)
    password_hash = PasswordManager().hash(PASSWORD)
    owner_role = role_id(RoleCode.BUSINESS_OWNER)

    # Organisasi pembina yang sama dengan seed demo.
    organization = Organization(
        id=demo_id("organization", 1),
        name="Organisasi Pembina UMKM Nusantara",
        status="ACTIVE",
        **stamp(now),
    )
    await add_missing(session, Organization, [organization])

    users, businesses, profiles, completions, members, org_members = [], [], [], [], [], []
    for i, (biz_name, owner_name, category, profile_type, city, province) in enumerate(UMKM):
        n = i + 1
        user_id, business_id = sid("user", i), sid("business", i)
        users.append(
            User(
                id=user_id,
                platform_role_id=owner_role,
                email=f"umkm{n:02d}@example.test",
                password_hash=password_hash,
                full_name=owner_name,
                status="ACTIVE",
                email_verified_at=onboard_at,
                password_changed_at=onboard_at,
                failed_login_attempts=0,
                **stamp(onboard_at),
            )
        )
        businesses.append(
            Business(
                id=business_id,
                organization_id=organization.id,
                code=f"UMKM-{n:02d}",
                name=biz_name,
                status="ACTIVE",
                **stamp(onboard_at),
            )
        )
        profiles.append(
            BusinessProfile(
                id=sid("profile", i),
                business_id=business_id,
                category_id=business_category_id(category),
                business_type=profile_type,
                scale="MICRO" if i % 4 else "SMALL",
                established_year=2015 + i % 10,
                address=f"Jl. Contoh UMKM No. {n}",
                village="Kelurahan Fiktif",
                district="Kecamatan Fiktif",
                city=city,
                province=province,
                phone=f"+62000000001{n:02d}",
                email=f"usaha.umkm{n:02d}@example.test",
                employee_count=1 + i % 5,
                currency="IDR",
                timezone="Asia/Jakarta",
                recording_method="CASH",
                status="ACTIVE",
                has_products_and_stock=False,
                tutorial_completed_at=onboard_at,
                onboarding_completed_at=onboard_at,
                **stamp(onboard_at),
            )
        )
        completions.append(
            OnboardingCompletion(
                id=sid("onboarding", i),
                user_id=user_id,
                business_id=business_id,
                opening_balance=Decimal(3_000_000 + i * 250_000),
                **stamp(onboard_at),
            )
        )
        members.append(
            BusinessMember(
                id=sid("member", i),
                business_id=business_id,
                user_id=user_id,
                role_id=owner_role,
                status="ACTIVE",
                joined_at=onboard_at,
                **stamp(onboard_at),
            )
        )
        org_members.append(
            OrganizationMember(
                id=sid("org-member", i),
                organization_id=organization.id,
                user_id=user_id,
                role_id=owner_role,
                status="ACTIVE",
                **stamp(onboard_at),
            )
        )
    # Urutan tulis mengikuti onboarding: usaha + keanggotaan sebelum tabel bertenant.
    await add_missing(session, User, users)
    await add_missing(session, Business, businesses)
    await add_missing(session, BusinessMember, members)
    await add_missing(session, BusinessProfile, profiles)
    await add_missing(session, OnboardingCompletion, completions)
    await add_missing(session, OrganizationMember, org_members)

    accounts: dict[int, dict[str, Account]] = {}
    account_rows: list[Account] = []
    for i, business in enumerate(businesses):
        accounts[i] = {}
        for template in ACCOUNT_TEMPLATES:
            account = Account(
                id=sid("account", i, template.key.value),
                business_id=business.id,
                code=template.code,
                name=template.name,
                system_key=template.key.value,
                account_type=template.account_type.value,
                normal_balance=template.normal_balance.value,
                is_system=True,
                is_active=True,
                **stamp(onboard_at),
            )
            account_rows.append(account)
            accounts[i][template.key.value] = account
    await add_missing(session, Account, account_rows)
    await add_missing(
        session,
        BusinessPaymentMethod,
        [
            BusinessPaymentMethod(
                id=sid("payment-method", i, code),
                business_id=business.id,
                account_id=accounts[i][key].id,
                code=code,
                name=name,
                is_active=True,
                **stamp(onboard_at),
            )
            for i, business in enumerate(businesses)
            for code, name, key in (
                ("CASH", "Tunai", AccountKey.CASH.value),
                ("BANK_TRANSFER", "Transfer Bank", AccountKey.BANK.value),
                ("QRIS", "QRIS", AccountKey.DIGITAL_WALLET.value),
            )
        ],
    )

    journals: list[JournalEntry] = []
    lines: list[JournalLine] = []
    transactions: list[FinancialTransaction] = []
    revisions: list[TransactionRevision] = []
    audits: list[AuditLog] = []
    for i, business in enumerate(businesses):
        actor = users[i].id
        acc = accounts[i]
        # Saldo awal: jurnal tanpa transaksi, sama seperti layanan onboarding.
        opening = completions[i].opening_balance
        opening_entry = JournalEntry(
            id=sid("opening-journal", i),
            business_id=business.id,
            entry_number="OPENING-0001",
            entry_date=START_DATE,
            description="Saldo awal usaha",
            source="ONBOARDING",
            status="POSTED",
            total_debit=opening,
            total_credit=opening,
            posted_at=onboard_at,
            posted_by_user_id=actor,
            **stamp(onboard_at),
        )
        journals.append(opening_entry)
        lines.extend(
            (
                JournalLine(
                    id=sid("opening-line", i, "debit"),
                    business_id=business.id,
                    journal_entry_id=opening_entry.id,
                    account_id=acc[AccountKey.CASH.value].id,
                    description="Saldo awal yang tersedia",
                    debit_amount=opening,
                    credit_amount=Decimal("0.00"),
                    **stamp(onboard_at),
                ),
                JournalLine(
                    id=sid("opening-line", i, "credit"),
                    business_id=business.id,
                    journal_entry_id=opening_entry.id,
                    account_id=acc[AccountKey.OWNER_CAPITAL.value].id,
                    description="Modal awal pemilik",
                    debit_amount=Decimal("0.00"),
                    credit_amount=opening,
                    **stamp(onboard_at),
                ),
            )
        )
        plan = keep_solvent(plan_transactions(i, UMKM[i][3], end), opening)
        for seq, item in enumerate(plan, start=1):
            posted_at = datetime.combine(item["date"], datetime.min.time(), tzinfo=UTC) + timedelta(
                hours=1 + seq % 10, minutes=(seq * 7) % 60
            )
            tx_id = sid("transaction", i, seq)
            number = f"UMKM{i + 1:02d}-{seq:04d}"
            debit, credit = item["debit"].value, item["credit"].value
            payment_key = debit if item["entry_kind"] == "INCOME" else credit
            transaction = FinancialTransaction(
                id=tx_id,
                business_id=business.id,
                transaction_number=number,
                transaction_type=item["type"],
                transaction_date=item["date"],
                amount=item["amount"],
                description=item["description"],
                payment_account_key=payment_key,
                category_account_key=item["category"].value if item["category"] else None,
                entry_kind=item["entry_kind"],
                counterparty_name=item["counterparty"],
                payment_method_code=item["method"],
                status="POSTED",
                idempotency_key=f"umkm-agustus:{i}:{seq}",
                revision_number=1,
                posted_at=posted_at,
                posted_by_user_id=actor,
                **stamp(posted_at),
            )
            entry = JournalEntry(
                id=sid("journal", i, seq),
                business_id=business.id,
                transaction_id=tx_id,
                entry_number=f"JU-{number}",
                entry_date=item["date"],
                description=item["description"],
                source="TRANSACTION",
                status="POSTED",
                total_debit=item["amount"],
                total_credit=item["amount"],
                posted_at=posted_at,
                posted_by_user_id=actor,
                **stamp(posted_at),
            )
            lines.extend(
                (
                    JournalLine(
                        id=sid("journal-line", i, seq, "debit"),
                        business_id=business.id,
                        journal_entry_id=entry.id,
                        account_id=acc[debit].id,
                        description=item["description"],
                        debit_amount=item["amount"],
                        credit_amount=Decimal("0.00"),
                        **stamp(posted_at),
                    ),
                    JournalLine(
                        id=sid("journal-line", i, seq, "credit"),
                        business_id=business.id,
                        journal_entry_id=entry.id,
                        account_id=acc[credit].id,
                        description=item["description"],
                        debit_amount=Decimal("0.00"),
                        credit_amount=item["amount"],
                        **stamp(posted_at),
                    ),
                )
            )
            transactions.append(transaction)
            journals.append(entry)
            revisions.append(
                TransactionRevision(
                    id=sid("transaction-revision", i, seq),
                    business_id=business.id,
                    transaction_id=tx_id,
                    revision_number=1,
                    event_sequence=1,
                    event_type="POSTED",
                    snapshot={"amount": str(item["amount"]), "type": item["type"]},
                    reason="Pencatatan transaksi",
                    actor_user_id=actor,
                    created_at=posted_at,
                )
            )
            audits.append(
                AuditLog(
                    id=sid("audit", i, seq),
                    business_id=business.id,
                    actor_user_id=actor,
                    action="TRANSACTION_POSTED",
                    entity_type="FINANCIAL_TRANSACTION",
                    entity_id=tx_id,
                    before_data=None,
                    after_data={"amount": str(item["amount"]), "type": item["type"], "source": SOURCE},
                    reason="Pencatatan transaksi",
                    request_id=SOURCE.lower(),
                    created_at=posted_at,
                )
            )
    await add_missing(session, FinancialTransaction, transactions)
    await add_missing(session, JournalEntry, journals)
    await add_missing(session, JournalLine, lines)
    await add_missing(session, TransactionRevision, revisions)
    await add_missing(session, AuditLog, audits)
    await session.commit()
    return {
        "users": len(users),
        "businesses": len(businesses),
        "transactions": len(transactions),
        "journal_entries": len(journals),
        "journal_lines": len(lines),
    }


async def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sampai", type=date.fromisoformat, default=DEFAULT_END_DATE)
    parser.add_argument("--izinkan-production", action="store_true")
    args = parser.parse_args()
    from kasta_api.core.config import get_settings

    if get_settings().environment == "production" and not args.izinkan_production:
        raise SystemExit("Environment production: tambahkan --izinkan-production untuk melanjutkan.")
    try:
        async with AsyncSessionFactory() as session:
            counts = await seed(session, args.sampai)
        print("Seed UMKM Agustus selesai:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(run())
