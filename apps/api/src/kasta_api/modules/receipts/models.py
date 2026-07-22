from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'NEEDS_REVIEW', 'CONFIRMED', 'FAILED')",
            name="receipt_status",
        ),
        Index("ix_receipts_business_status_created", "business_id", "status", "created_at"),
        Index("ix_receipts_duplicate_lookup", "business_id", "receipt_date", "total_amount"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="UPLOADED", server_default="UPLOADED", nullable=False
    )
    perceptual_hash: Mapped[str | None] = mapped_column(String(16), index=True)
    merchant_name: Mapped[str | None] = mapped_column(String(200))
    merchant_normalized: Mapped[str | None] = mapped_column(String(200), index=True)
    receipt_date: Mapped[date | None] = mapped_column(Date)
    receipt_number: Mapped[str | None] = mapped_column(String(100), index=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    duplicate_of_receipt_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT")
    )
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    verified_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(500))


class ReceiptImage(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "receipt_images"
    __table_args__ = (
        CheckConstraint(
            "image_kind IN ('ORIGINAL', 'PROCESSED', 'TRANSACTION_ATTACHMENT')",
            name="ck_receipt_images_image_kind",
        ),
        CheckConstraint(
            "transaction_id IS NOT NULL OR receipt_id IS NOT NULL",
            name="ck_receipt_images_has_parent",
        ),
        Index("ix_receipt_images_business_transaction", "business_id", "transaction_id"),
        Index("ix_receipt_images_receipt_kind", "receipt_id", "image_kind"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), index=True
    )
    receipt_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), index=True
    )
    image_kind: Mapped[str] = mapped_column(
        String(30),
        default="TRANSACTION_ATTACHMENT",
        server_default="TRANSACTION_ATTACHMENT",
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    perceptual_hash: Mapped[str | None] = mapped_column(String(16))
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class OcrResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ocr_results"
    __table_args__ = (Index("ix_ocr_results_business_receipt", "business_id", "receipt_id"),)

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(50))
    mean_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    processing_duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OcrField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ocr_fields"
    __table_args__ = (
        UniqueConstraint("ocr_result_id", "field_name"),
        Index("ix_ocr_fields_business_receipt", "business_id", "receipt_id"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ocr_result_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ocr_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    source_text: Mapped[str | None] = mapped_column(Text)
    is_user_corrected: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    corrected_value: Mapped[str | None] = mapped_column(Text)


class ReceiptItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_items"
    __table_args__ = (UniqueConstraint("receipt_id", "line_number"),)

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ocr_result_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("ocr_results.id", ondelete="RESTRICT"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)


class ReceiptCorrection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "receipt_corrections"
    __table_args__ = (Index("ix_receipt_corrections_receipt_created", "receipt_id", "created_at"),)

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    corrected_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
