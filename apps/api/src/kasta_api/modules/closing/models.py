from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from kasta_api.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PeriodClosing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A closed accounting period: an immutable record of a completed close-the-books action.

    There is no "open period" row — the current, still-open period is always
    computed on the fly as "the day after the latest closing's period_end,
    through today" (see ClosingService.current_period).
    """

    __tablename__ = "period_closings"
    __table_args__ = (
        UniqueConstraint("business_id", "period_end", name="uq_period_closings_business_end"),
        CheckConstraint("period_end >= period_start", name="period_closing_valid_range"),
        CheckConstraint(
            "total_revenue >= 0 AND total_expense >= 0", name="period_closing_non_negative"
        ),
        Index("ix_period_closings_business_end", "business_id", "period_end"),
    )

    business_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_expense: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    closing_transaction_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True
    )
    closed_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(500))
