"""Add UMKM onboarding, business profiles, and opening journal.

Revision ID: 20260721_0003
Revises: 20260721_0002
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_NAMESPACE = UUID("8d9b0b88-5a22-4d79-b4de-7f475fb74e74")
CATEGORY_NAMESPACE = UUID("30e46f66-2958-42ef-84cb-196ca15d9c2f")
CATEGORIES = (
    ("retail", "Toko dan Eceran", "TRADE", 10),
    ("wholesale", "Grosir dan Distributor", "TRADE", 20),
    ("food", "Makanan", "CULINARY", 30),
    ("beverage", "Minuman", "CULINARY", 40),
    ("personal_service", "Jasa Perorangan", "SERVICE", 50),
    ("professional_service", "Jasa Profesional", "SERVICE", 60),
    ("craft", "Kerajinan", "PRODUCTION", 70),
    ("manufacturing", "Produksi dan Pengolahan", "PRODUCTION", 80),
    ("fashion", "Pakaian dan Aksesori", "CREATIVE", 90),
    ("creative", "Desain, Foto, dan Karya Kreatif", "CREATIVE", 100),
    ("agriculture", "Pertanian dan Perkebunan", "AGRICULTURE", 110),
    ("fishery", "Perikanan dan Peternakan", "AGRICULTURE", 120),
    ("other", "Usaha Lainnya", "OTHER", 999),
)
NEW_ROLE_PERMISSIONS = {
    "business_owner": ("business.profile.read", "business.profile.update"),
    "business_staff": ("business.profile.read",),
    "mentor": ("business.profile.read",),
    "organization_admin": ("business.profile.read", "business.profile.update"),
    "super_admin": ("business.profile.read", "business.profile.update"),
}


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "business_categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("business_type", sa.String(20), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "business_type IN ('TRADE', 'SERVICE', 'PRODUCTION', 'CULINARY', "
            "'AGRICULTURE', 'CREATIVE', 'OTHER')",
            name="business_category_type",
        ),
        sa.UniqueConstraint("code", name="uq_business_categories_code"),
    )
    op.create_index(
        "ix_business_categories_business_type", "business_categories", ["business_type"]
    )
    op.create_table(
        "business_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Uuid(),
            sa.ForeignKey("business_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("logo_object_key", sa.String(500)),
        sa.Column("business_type", sa.String(20), nullable=False),
        sa.Column("scale", sa.String(20), nullable=False),
        sa.Column("established_year", sa.Integer()),
        sa.Column("address", sa.String(500)),
        sa.Column("village", sa.String(100)),
        sa.Column("district", sa.String(100)),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("province", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(16)),
        sa.Column("email", sa.String(320)),
        sa.Column("employee_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(3), server_default="IDR", nullable=False),
        sa.Column("timezone", sa.String(50), server_default="Asia/Jakarta", nullable=False),
        sa.Column("recording_method", sa.String(20), server_default="CASH", nullable=False),
        sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False),
        sa.Column(
            "has_products_and_stock", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("tutorial_completed_at", sa.DateTime(timezone=True)),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "business_type IN ('TRADE', 'SERVICE', 'PRODUCTION', 'CULINARY', "
            "'AGRICULTURE', 'CREATIVE', 'OTHER')",
            name="business_profile_type",
        ),
        sa.CheckConstraint("scale IN ('MICRO', 'SMALL', 'MEDIUM')", name="business_profile_scale"),
        sa.CheckConstraint("employee_count >= 0", name="business_profile_employee_count"),
        sa.CheckConstraint(
            "established_year IS NULL OR established_year BETWEEN 1800 AND 9999",
            name="business_profile_established_year",
        ),
        sa.CheckConstraint("currency IN ('IDR', 'USD', 'SGD', 'MYR')", name="business_currency"),
        sa.CheckConstraint(
            "timezone IN ('Asia/Jakarta', 'Asia/Makassar', 'Asia/Jayapura')",
            name="business_timezone",
        ),
        sa.CheckConstraint(
            "recording_method IN ('CASH', 'ACCRUAL')", name="business_recording_method"
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="business_profile_status"),
        sa.UniqueConstraint("business_id", name="uq_business_profiles_business_id"),
    )
    op.create_index("ix_business_profiles_category_id", "business_profiles", ["category_id"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("account_type IN ('ASSET', 'EQUITY')", name="account_type"),
        sa.UniqueConstraint("business_id", "code", name="uq_accounts_business_id"),
    )
    op.create_index("ix_accounts_business_id", "accounts", ["business_id"])
    op.create_table(
        "business_payment_methods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "code IN ('CASH', 'BANK_TRANSFER', 'QRIS', 'E_WALLET', 'CARD')",
            name="business_payment_method_code",
        ),
        sa.UniqueConstraint("business_id", "code", name="uq_business_payment_methods_business_id"),
    )
    op.create_index(
        "ix_business_payment_methods_business_id", "business_payment_methods", ["business_id"]
    )
    op.create_index(
        "ix_business_payment_methods_account_id", "business_payment_methods", ["account_id"]
    )
    op.create_table(
        "onboarding_completions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("opening_balance", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        *_timestamps(),
        sa.CheckConstraint("opening_balance >= 0", name="onboarding_opening_balance"),
        sa.UniqueConstraint("user_id", name="uq_onboarding_completions_user_id"),
        sa.UniqueConstraint("business_id", name="uq_onboarding_completions_business_id"),
    )
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("entry_number", sa.String(50), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="POSTED", nullable=False),
        sa.Column("total_debit", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_credit", sa.Numeric(18, 2), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("status IN ('POSTED', 'REVERSED')", name="journal_entry_status"),
        sa.CheckConstraint("total_debit = total_credit", name="journal_entry_balanced"),
        sa.UniqueConstraint("business_id", "entry_number", name="uq_journal_entries_business_id"),
    )
    op.create_index("ix_journal_entries_business_id", "journal_entries", ["business_id"])
    op.create_index(
        "ix_journal_entries_business_date", "journal_entries", ["business_id", "entry_date"]
    )
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "journal_entry_id",
            sa.Uuid(),
            sa.ForeignKey("journal_entries.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("debit_amount", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("credit_amount", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "debit_amount >= 0 AND credit_amount >= 0", name="journal_line_non_negative"
        ),
        sa.CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="journal_line_one_side",
        ),
    )
    op.create_index("ix_journal_lines_business_id", "journal_lines", ["business_id"])
    op.create_index("ix_journal_lines_journal_entry_id", "journal_lines", ["journal_entry_id"])
    op.create_index("ix_journal_lines_account_id", "journal_lines", ["account_id"])
    op.create_index(
        "ix_journal_lines_business_entry",
        "journal_lines",
        ["business_id", "journal_entry_id"],
    )

    categories_table = sa.table(
        "business_categories",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("business_type", sa.String()),
        sa.column("display_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("module", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid5(CATEGORY_NAMESPACE, code),
                "code": code,
                "name": name,
                "business_type": business_type,
                "display_order": display_order,
                "is_active": True,
            }
            for code, name, business_type, display_order in CATEGORIES
        ],
    )
    new_permissions = ("business.profile.read", "business.profile.update")
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": uuid5(AUTH_NAMESPACE, f"permission:{code}"),
                "code": code,
                "module": "business",
                "description": code,
            }
            for code in new_permissions
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "id": uuid5(AUTH_NAMESPACE, f"role-permission:{role}:{permission}"),
                "role_id": uuid5(AUTH_NAMESPACE, f"role:{role}"),
                "permission_id": uuid5(AUTH_NAMESPACE, f"permission:{permission}"),
            }
            for role, permissions in NEW_ROLE_PERMISSIONS.items()
            for permission in permissions
        ],
    )


def downgrade() -> None:
    for table_name in [
        "journal_lines",
        "journal_entries",
        "onboarding_completions",
        "business_payment_methods",
        "accounts",
        "business_profiles",
        "business_categories",
    ]:
        op.drop_table(table_name)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN "
            "('business.profile.read', 'business.profile.update'))"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('business.profile.read', 'business.profile.update')"
        )
    )
