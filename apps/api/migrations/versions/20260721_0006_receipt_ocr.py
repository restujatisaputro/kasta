"""Add receipt OCR, extracted fields, corrections, items, and duplicate detection.

Revision ID: 20260721_0006
Revises: 20260721_0005
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0006"
down_revision: str | None = "20260721_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.Uuid(),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("status", sa.String(20), server_default="UPLOADED", nullable=False),
        sa.Column("perceptual_hash", sa.String(16)),
        sa.Column("merchant_name", sa.String(200)),
        sa.Column("merchant_normalized", sa.String(200)),
        sa.Column("receipt_date", sa.Date()),
        sa.Column("receipt_number", sa.String(100)),
        sa.Column("total_amount", sa.Numeric(18, 2)),
        sa.Column(
            "duplicate_of_receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "verified_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_duration_ms", sa.Integer()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.String(500)),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'NEEDS_REVIEW', 'CONFIRMED', 'FAILED')",
            name="receipt_status",
        ),
    )
    op.create_index("ix_receipts_business_id", "receipts", ["business_id"])
    op.create_index("ix_receipts_transaction_id", "receipts", ["transaction_id"])
    op.create_index("ix_receipts_perceptual_hash", "receipts", ["perceptual_hash"])
    op.create_index("ix_receipts_merchant_normalized", "receipts", ["merchant_normalized"])
    op.create_index("ix_receipts_receipt_number", "receipts", ["receipt_number"])
    op.create_index(
        "ix_receipts_business_status_created", "receipts", ["business_id", "status", "created_at"]
    )
    op.create_index(
        "ix_receipts_duplicate_lookup",
        "receipts",
        ["business_id", "receipt_date", "total_amount"],
    )

    op.alter_column("receipt_images", "transaction_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column(
        "receipt_images",
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
        ),
    )
    op.add_column(
        "receipt_images",
        sa.Column(
            "image_kind",
            sa.String(30),
            server_default="TRANSACTION_ATTACHMENT",
            nullable=False,
        ),
    )
    op.add_column("receipt_images", sa.Column("width", sa.Integer()))
    op.add_column("receipt_images", sa.Column("height", sa.Integer()))
    op.add_column("receipt_images", sa.Column("perceptual_hash", sa.String(16)))
    op.create_index("ix_receipt_images_receipt_id", "receipt_images", ["receipt_id"])
    op.create_index(
        "ix_receipt_images_receipt_kind", "receipt_images", ["receipt_id", "image_kind"]
    )
    op.create_check_constraint(
        "ck_receipt_images_image_kind",
        "receipt_images",
        "image_kind IN ('ORIGINAL', 'PROCESSED', 'TRANSACTION_ATTACHMENT')",
    )
    op.create_check_constraint(
        "ck_receipt_images_has_parent",
        "receipt_images",
        "transaction_id IS NOT NULL OR receipt_id IS NOT NULL",
    )

    op.create_table(
        "ocr_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("engine", sa.String(50), nullable=False),
        sa.Column("engine_version", sa.String(50)),
        sa.Column("mean_confidence", sa.Numeric(5, 4)),
        sa.Column("processing_duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ocr_results_business_id", "ocr_results", ["business_id"])
    op.create_index("ix_ocr_results_receipt_id", "ocr_results", ["receipt_id"])
    op.create_index("ix_ocr_results_business_receipt", "ocr_results", ["business_id", "receipt_id"])

    op.create_table(
        "ocr_fields",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "ocr_result_id",
            sa.Uuid(),
            sa.ForeignKey("ocr_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text()),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("source_text", sa.Text()),
        sa.Column("is_user_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("corrected_value", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("ocr_result_id", "field_name", name="uq_ocr_fields_result_name"),
    )
    op.create_index("ix_ocr_fields_business_id", "ocr_fields", ["business_id"])
    op.create_index("ix_ocr_fields_receipt_id", "ocr_fields", ["receipt_id"])
    op.create_index("ix_ocr_fields_ocr_result_id", "ocr_fields", ["ocr_result_id"])
    op.create_index("ix_ocr_fields_business_receipt", "ocr_fields", ["business_id", "receipt_id"])

    op.create_table(
        "receipt_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "ocr_result_id",
            sa.Uuid(),
            sa.ForeignKey("ocr_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3)),
        sa.Column("unit_price", sa.Numeric(18, 2)),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("receipt_id", "line_number", name="uq_receipt_items_line"),
    )
    op.create_index("ix_receipt_items_business_id", "receipt_items", ["business_id"])
    op.create_index("ix_receipt_items_receipt_id", "receipt_items", ["receipt_id"])

    op.create_table(
        "receipt_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "business_id",
            sa.Uuid(),
            sa.ForeignKey("businesses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "receipt_id",
            sa.Uuid(),
            sa.ForeignKey("receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column(
            "corrected_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_receipt_corrections_business_id", "receipt_corrections", ["business_id"])
    op.create_index("ix_receipt_corrections_receipt_id", "receipt_corrections", ["receipt_id"])
    op.create_index(
        "ix_receipt_corrections_receipt_created",
        "receipt_corrections",
        ["receipt_id", "created_at"],
    )

    for table_name in (
        "receipts",
        "ocr_results",
        "ocr_fields",
        "receipt_items",
        "receipt_corrections",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_delete "
            f"BEFORE DELETE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_financial_delete()"
        )
    for table_name in ("ocr_results", "receipt_items", "receipt_corrections"):
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_no_update "
            f"BEFORE UPDATE ON {table_name} FOR EACH ROW "
            "EXECUTE FUNCTION kasta_reject_immutable_update()"
        )


def downgrade() -> None:
    for table_name in ("ocr_results", "receipt_items", "receipt_corrections"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update ON {table_name}")
    for table_name in (
        "receipts",
        "ocr_results",
        "ocr_fields",
        "receipt_items",
        "receipt_corrections",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete ON {table_name}")
    op.drop_table("receipt_corrections")
    op.drop_table("receipt_items")
    op.drop_table("ocr_fields")
    op.drop_table("ocr_results")
    op.drop_constraint("ck_receipt_images_has_parent", "receipt_images", type_="check")
    op.drop_constraint("ck_receipt_images_image_kind", "receipt_images", type_="check")
    op.drop_index("ix_receipt_images_receipt_kind", table_name="receipt_images")
    op.drop_index("ix_receipt_images_receipt_id", table_name="receipt_images")
    op.drop_column("receipt_images", "perceptual_hash")
    op.drop_column("receipt_images", "height")
    op.drop_column("receipt_images", "width")
    op.drop_column("receipt_images", "image_kind")
    op.drop_column("receipt_images", "receipt_id")
    op.execute("DELETE FROM receipt_images WHERE transaction_id IS NULL")
    op.alter_column("receipt_images", "transaction_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("receipts")
