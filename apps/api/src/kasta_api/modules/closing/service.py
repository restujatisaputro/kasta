from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException

from kasta_api.modules.accounting.constants import AccountKey, TransactionType
from kasta_api.modules.accounting.engine import JournalLineDraft
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.accounting.service import JournalService
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.closing.constants import ClosingFrequency
from kasta_api.modules.closing.models import PeriodClosing
from kasta_api.modules.closing.repository import ClosingRepository
from kasta_api.modules.closing.schemas import (
    AccountActivityLine,
    ClosePeriodRequest,
    CurrentPeriodResponse,
    PeriodClosingListResponse,
    PeriodClosingResponse,
)
from kasta_api.modules.reports.repository import LedgerRow, ReportRepository

ZERO = Decimal("0.00")


class ClosingService:
    def __init__(
        self,
        repository: ClosingRepository,
        accounting_repository: AccountingRepository,
        report_repository: ReportRepository,
    ) -> None:
        self.repository = repository
        self.reports = report_repository
        self.journal = JournalService(accounting_repository)

    async def current_period(self, business_id: UUID, as_of: date | None = None) -> CurrentPeriodResponse:
        as_of = as_of or date.today()
        frequency = ClosingFrequency(await self.repository.get_closing_frequency(business_id))
        period_start = await self._next_period_start(business_id)
        suggested_end = suggested_period_end(period_start, frequency)
        rows = await self.reports.ledger_rows(
            business_id,
            date_from=period_start,
            date_to=as_of,
            category=None,
            payment_method=None,
        )
        revenue_lines, expense_lines, total_revenue, total_expense = _activity_lines(rows)
        net_profit = _money(total_revenue - total_expense)
        return CurrentPeriodResponse(
            period_start=period_start,
            period_end_suggested=suggested_end,
            as_of=as_of,
            frequency=frequency,
            revenues=revenue_lines,
            expenses=expense_lines,
            total_revenue=total_revenue,
            total_expense=total_expense,
            net_profit=net_profit,
            is_loss=net_profit < ZERO,
            has_activity=bool(revenue_lines or expense_lines),
            is_overdue=as_of > suggested_end,
            explanation=_explanation(period_start, as_of, total_revenue, total_expense, net_profit),
        )

    async def history(
        self, business_id: UUID, *, limit: int, offset: int
    ) -> PeriodClosingListResponse:
        rows, total = await self.repository.list_closings(business_id, limit=limit, offset=offset)
        return PeriodClosingListResponse(
            items=[PeriodClosingResponse.model_validate(row) for row in rows], total=total
        )

    async def close_period(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: ClosePeriodRequest,
        *,
        request_id: str | None,
    ) -> PeriodClosingResponse:
        if not payload.acknowledge_adjustments:
            raise HTTPException(
                status_code=422,
                detail="Periksa dan sesuaikan transaksi periode ini sebelum menutup.",
            )
        today = date.today()
        if payload.period_end > today:
            raise HTTPException(
                status_code=422, detail="Tidak bisa menutup periode yang belum berlalu."
            )
        period_start = await self._next_period_start(business_id)
        if payload.period_end < period_start:
            raise HTTPException(
                status_code=422,
                detail=f"Tanggal tutup tidak boleh sebelum {period_start.isoformat()}.",
            )
        rows = await self.reports.ledger_rows(
            business_id,
            date_from=period_start,
            date_to=payload.period_end,
            category=None,
            payment_method=None,
        )
        lines, total_revenue, total_expense = _closing_lines(rows)
        net_profit = _money(total_revenue - total_expense)
        if net_profit > ZERO:
            lines.append(JournalLineDraft(account_key=AccountKey.OWNER_CAPITAL, credit_amount=net_profit))
        elif net_profit < ZERO:
            lines.append(
                JournalLineDraft(account_key=AccountKey.OWNER_CAPITAL, debit_amount=-net_profit)
            )
        closing_transaction = None
        try:
            if lines:
                closing_transaction = await self.journal.post_multi_line_transaction(
                    business_id,
                    actor_user_id,
                    transaction_type=TransactionType.PERIOD_CLOSING,
                    transaction_date=payload.period_end,
                    description=(
                        f"Tutup periode {period_start.isoformat()} s.d. "
                        f"{payload.period_end.isoformat()}"
                    ),
                    lines=lines,
                    idempotency_key=f"period-closing:{business_id}:{payload.period_end.isoformat()}",
                    entry_kind=None,
                    request_id=request_id,
                    auto_commit=False,
                )
            record = PeriodClosing(
                id=uuid4(),
                business_id=business_id,
                period_start=period_start,
                period_end=payload.period_end,
                total_revenue=total_revenue,
                total_expense=total_expense,
                net_profit=net_profit,
                closing_transaction_id=(
                    closing_transaction.id if closing_transaction is not None else None
                ),
                closed_by_user_id=actor_user_id,
                note=payload.note or None,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.repository.add(record)
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return PeriodClosingResponse.model_validate(record)

    async def _next_period_start(self, business_id: UUID) -> date:
        last = await self.repository.latest_closing(business_id)
        if last is not None:
            return last.period_end + timedelta(days=1)
        earliest = await self.repository.earliest_transaction_date(business_id)
        return earliest or date.today()


def suggested_period_end(period_start: date, frequency: ClosingFrequency) -> date:
    if frequency == ClosingFrequency.MONTHLY:
        return _month_end(period_start)
    if frequency == ClosingFrequency.SEMIANNUAL:
        boundary_month = 6 if period_start.month <= 6 else 12
        return _month_end(period_start.replace(month=boundary_month))
    # TRIANNUAL: three four-month chunks, Jan-Apr / May-Aug / Sep-Dec.
    boundary_month = ((period_start.month - 1) // 4) * 4 + 4
    return _month_end(period_start.replace(month=boundary_month))


def _month_end(value: date) -> date:
    next_month = value.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


def _normal_amount(row: LedgerRow) -> Decimal:
    return row.debit - row.credit if row.normal_balance == "DEBIT" else row.credit - row.debit


def _activity_lines(
    rows: list[LedgerRow],
) -> tuple[list[AccountActivityLine], list[AccountActivityLine], Decimal, Decimal]:
    revenue: dict[tuple[str, str], Decimal] = {}
    expense: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        if row.account_type == "REVENUE":
            key = (row.account_key, row.account_name)
            revenue[key] = revenue.get(key, ZERO) + _normal_amount(row)
        elif row.account_type == "EXPENSE":
            key = (row.account_key, row.account_name)
            expense[key] = expense.get(key, ZERO) + _normal_amount(row)
    revenue_lines = [
        AccountActivityLine(account_key=key, account_name=name, amount=_money(amount))
        for (key, name), amount in sorted(revenue.items(), key=lambda item: item[0][1])
        if _money(amount) != ZERO
    ]
    expense_lines = [
        AccountActivityLine(account_key=key, account_name=name, amount=_money(amount))
        for (key, name), amount in sorted(expense.items(), key=lambda item: item[0][1])
        if _money(amount) != ZERO
    ]
    total_revenue = _money(sum((line.amount for line in revenue_lines), ZERO))
    total_expense = _money(sum((line.amount for line in expense_lines), ZERO))
    return revenue_lines, expense_lines, total_revenue, total_expense


def _closing_lines(rows: list[LedgerRow]) -> tuple[list[JournalLineDraft], Decimal, Decimal]:
    """Builds one journal line per revenue/expense account that had activity,
    each offsetting that account's net period balance back to zero — the
    standard "close temporary accounts" step, done directly against
    Owner Capital instead of via an Income Summary clearing account.
    """
    totals: dict[str, tuple[Decimal, str]] = {}
    total_revenue = ZERO
    total_expense = ZERO
    for row in rows:
        if row.account_type not in ("REVENUE", "EXPENSE"):
            continue
        amount = _normal_amount(row)
        previous, _ = totals.get(row.account_key, (ZERO, row.normal_balance))
        totals[row.account_key] = (previous + amount, row.normal_balance)
        if row.account_type == "REVENUE":
            total_revenue += amount
        else:
            total_expense += amount
    lines: list[JournalLineDraft] = []
    for account_key, (net_amount, normal_balance) in totals.items():
        net_amount = _money(net_amount)
        if net_amount == ZERO:
            continue
        key = AccountKey(account_key)
        # `net_amount` is normal-balance-signed (positive = the account's usual
        # direction — e.g. a real credit balance for revenue). Closing it means
        # posting the *opposite* side, which depends on which side is "normal"
        # for this particular account, not just the sign of net_amount.
        credit_side_is_normal = normal_balance == "CREDIT"
        if net_amount > ZERO:
            if credit_side_is_normal:
                lines.append(JournalLineDraft(account_key=key, debit_amount=net_amount))
            else:
                lines.append(JournalLineDraft(account_key=key, credit_amount=net_amount))
        else:
            amount = -net_amount
            if credit_side_is_normal:
                lines.append(JournalLineDraft(account_key=key, credit_amount=amount))
            else:
                lines.append(JournalLineDraft(account_key=key, debit_amount=amount))
    return lines, _money(total_revenue), _money(total_expense)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rupiah(value: Decimal) -> str:
    whole = int(_money(value))
    sign = "-" if whole < 0 else ""
    return f"{sign}Rp{abs(whole):,}".replace(",", ".")


def _explanation(
    period_start: date, as_of: date, total_revenue: Decimal, total_expense: Decimal, net_profit: Decimal
) -> str:
    result = "laba" if net_profit >= ZERO else "rugi"
    return (
        f"Sejak {period_start.isoformat()} sampai {as_of.isoformat()}, usaha mencatat pemasukan "
        f"{_rupiah(total_revenue)} dan pengeluaran {_rupiah(total_expense)}, sehingga {result} "
        f"berjalan {_rupiah(abs(net_profit))}. Saat ditutup, jumlah ini akan menambah atau "
        "mengurangi Modal Pemilik."
    )
