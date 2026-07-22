from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")


class Business(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="business_status"),)

    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")


class BusinessMember(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "business_members"
    __table_args__ = (
        UniqueConstraint("business_id", "user_id"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="business_member_status"),
        Index("ix_business_members_access", "user_id", "business_id", "status", "deleted_at"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationMember(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="organization_member_status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")


class BusinessCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_categories"
    __table_args__ = (
        CheckConstraint(
            "business_type IN ('TRADE', 'SERVICE', 'PRODUCTION', 'CULINARY', "
            "'AGRICULTURE', 'CREATIVE', 'OTHER')",
            name="business_category_type",
        ),
    )

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    business_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class BusinessProfile(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "business_profiles"
    __table_args__ = (
        CheckConstraint(
            "business_type IN ('TRADE', 'SERVICE', 'PRODUCTION', 'CULINARY', "
            "'AGRICULTURE', 'CREATIVE', 'OTHER')",
            name="business_profile_type",
        ),
        CheckConstraint("scale IN ('MICRO', 'SMALL', 'MEDIUM')", name="business_profile_scale"),
        CheckConstraint("employee_count >= 0", name="business_profile_employee_count"),
        CheckConstraint(
            "established_year IS NULL OR established_year BETWEEN 1800 AND 9999",
            name="business_profile_established_year",
        ),
        CheckConstraint("currency IN ('IDR', 'USD', 'SGD', 'MYR')", name="business_currency"),
        CheckConstraint(
            "timezone IN ('Asia/Jakarta', 'Asia/Makassar', 'Asia/Jayapura')",
            name="business_timezone",
        ),
        CheckConstraint(
            "recording_method IN ('CASH', 'ACCRUAL')", name="business_recording_method"
        ),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="business_profile_status"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("business_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    logo_object_key: Mapped[str | None] = mapped_column(String(500))
    business_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scale: Mapped[str] = mapped_column(String(20), nullable=False)
    established_year: Mapped[int | None] = mapped_column(Integer)
    address: Mapped[str | None] = mapped_column(String(500))
    village: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(16))
    email: Mapped[str | None] = mapped_column(String(320))
    employee_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="IDR", server_default="IDR")
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Jakarta", server_default="Asia/Jakarta"
    )
    recording_method: Mapped[str] = mapped_column(String(20), default="CASH", server_default="CASH")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", server_default="ACTIVE")
    has_products_and_stock: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    tutorial_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class BusinessPaymentMethod(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "business_payment_methods"
    __table_args__ = (
        UniqueConstraint("business_id", "code"),
        CheckConstraint(
            "code IN ('CASH', 'BANK_TRANSFER', 'QRIS', 'E_WALLET', 'CARD')",
            name="business_payment_method_code",
        ),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class OnboardingCompletion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_completions"
    __table_args__ = (CheckConstraint("opening_balance >= 0", name="onboarding_opening_balance"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default="0.00", nullable=False
    )
