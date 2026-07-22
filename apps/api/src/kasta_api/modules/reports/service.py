from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException

from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.reports.constants import ReportPeriod
from kasta_api.modules.reports.repository import (
    LedgerRow,
    ObligationSnapshot,
    ProductSaleRow,
    ProductSnapshot,
    ReportRepository,
)
from kasta_api.modules.reports.schemas import (
    AccountReportLine,
    BalanceSheetReport,
    CashFlowReport,
    CategoryTotal,
    ChartData,
    FinancialReportResponse,
    FinancialSummary,
    InventoryReport,
    ObligationReport,
    ProductPerformance,
    ProfitLossReport,
    ReportContext,
    TimeSeriesPoint,
)

ZERO = Decimal("0.00")
MONEY = Decimal("0.01")
CASH_KEYS = {"CASH", "BANK", "DIGITAL_WALLET"}


class ReportService:
    def __init__(self, repository: ReportRepository) -> None:
        self.repository = repository

    async def build(
        self,
        business_id: UUID,
        *,
        period: ReportPeriod,
        reference_date: date,
        date_from: date | None,
        date_to: date | None,
        category: str | None,
        payment_method: str | None,
        branch_id: UUID | None,
    ) -> FinancialReportResponse:
        business = await self.repository.business(business_id)
        if business is None:
            raise HTTPException(status_code=404, detail="Usaha tidak ditemukan.")
        if branch_id is not None and branch_id != business_id:
            raise HTTPException(
                status_code=422,
                detail="Cabang yang dipilih tidak termasuk dalam usaha ini.",
            )
        start, end = self.resolve_dates(period, reference_date, date_from, date_to)
        category = category.strip().upper() if category else None
        payment_method = payment_method.strip().upper() if payment_method else None

        period_rows = await self.repository.ledger_rows(
            business_id,
            date_from=start,
            date_to=end,
            category=category,
            payment_method=payment_method,
        )
        cumulative_rows = await self.repository.ledger_rows(
            business_id,
            date_from=None,
            date_to=end,
            category=category,
            payment_method=payment_method,
        )
        comparison_start = self._shift_month(self._month_start(end), -5)
        comparison_rows = await self.repository.ledger_rows(
            business_id,
            date_from=comparison_start,
            date_to=end,
            category=category,
            payment_method=payment_method,
        )
        products = await self.repository.products(business_id)
        product_sales = await self.repository.product_sales(
            business_id,
            date_from=start,
            date_to=end,
            category=category,
            payment_method=payment_method,
        )
        receivables = await self.repository.receivables(business_id)
        payables = await self.repository.payables(business_id)

        revenues = self._account_lines(period_rows, "REVENUE")
        expenses = self._account_lines(period_rows, "EXPENSE")
        total_revenue = self._sum_lines(revenues)
        total_expense = self._sum_lines(expenses)
        profit = self._money(total_revenue - total_expense)
        cash_in, cash_out = self._cash_movement(period_rows)
        ending_cash = self._ending_cash(cumulative_rows)
        receivable_journal = self._account_balance(cumulative_rows, {"RECEIVABLE"})
        payable_journal = self._account_balance(cumulative_rows, {"PAYABLE", "OTHER_PAYABLE"})
        receivable_report = self._obligations(receivables, end, "piutang", receivable_journal)
        payable_report = self._obligations(payables, end, "utang", payable_journal)
        inventory_report = self._inventory(products, cumulative_rows)
        best_sellers = self._best_sellers(product_sales)
        daily = self._time_series(period_rows, monthly=False)
        monthly = self._time_series(comparison_rows, monthly=True)
        sales = self._categories(revenues)
        expenditures = self._categories(expenses)
        profit_loss = ProfitLossReport(
            revenues=revenues,
            expenses=expenses,
            total_revenue=total_revenue,
            total_expense=total_expense,
            profit=profit,
            explanation=self._profit_explanation(total_revenue, total_expense, profit),
        )
        balance_sheet = self._balance_sheet(cumulative_rows, end, bool(category or payment_method))
        net_cash = self._money(cash_in - cash_out)
        cash_flow = CashFlowReport(
            cash_in=cash_in,
            cash_out=cash_out,
            net_cash_flow=net_cash,
            ending_cash_balance=ending_cash,
            explanation=(
                f"Kas dan rekening usaha bertambah {self._rupiah(cash_in)} dan berkurang "
                f"{self._rupiah(cash_out)} selama periode ini. Perubahan bersihnya "
                f"{self._rupiah(net_cash)}."
            ),
        )
        summary = FinancialSummary(
            income=total_revenue,
            expense=total_expense,
            estimated_profit=profit,
            cash_in=cash_in,
            cash_out=cash_out,
            net_cash_flow=net_cash,
            receivables=receivable_report.journal_value,
            payables=payable_report.journal_value,
            inventory_value=inventory_report.journal_value,
        )
        explanation = self._main_explanation(summary)
        return FinancialReportResponse(
            context=ReportContext(
                business_id=business_id,
                business_name=business.name,
                period=period,
                date_from=start,
                date_to=end,
                category=category,
                payment_method=payment_method,
                branch_id=business_id,
                branch_name=business.name,
                generated_at=utc_now(),
            ),
            summary=summary,
            profit_loss=profit_loss,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            sales=sales,
            expenditures=expenditures,
            receivables=receivable_report,
            payables=payable_report,
            inventory=inventory_report,
            best_selling_products=best_sellers,
            monthly_comparison=monthly,
            charts=ChartData(
                income_vs_expense=daily,
                profit_trend=monthly,
                expense_categories=expenditures,
                daily_sales=daily,
                best_selling_products=best_sellers,
            ),
            explanation=explanation,
        )

    @staticmethod
    def resolve_dates(
        period: ReportPeriod,
        reference: date,
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[date, date]:
        if period == ReportPeriod.CUSTOM:
            if date_from is None or date_to is None:
                raise HTTPException(
                    status_code=422,
                    detail="Isi tanggal mulai dan tanggal akhir untuk rentang tanggal.",
                )
            start, end = date_from, date_to
        elif period == ReportPeriod.DAY:
            start = end = reference
        elif period == ReportPeriod.WEEK:
            start = reference - timedelta(days=reference.weekday())
            end = start + timedelta(days=6)
        elif period == ReportPeriod.MONTH:
            start = reference.replace(day=1)
            end = ReportService._shift_month(start, 1) - timedelta(days=1)
        elif period == ReportPeriod.QUARTER:
            month = ((reference.month - 1) // 3) * 3 + 1
            start = reference.replace(month=month, day=1)
            end = ReportService._shift_month(start, 3) - timedelta(days=1)
        else:
            start = reference.replace(month=1, day=1)
            end = reference.replace(month=12, day=31)
        if start > end:
            raise HTTPException(status_code=422, detail="Tanggal mulai melewati tanggal akhir.")
        if (end - start).days > 3660:
            raise HTTPException(status_code=422, detail="Rentang laporan maksimal 10 tahun.")
        return start, end

    def _balance_sheet(
        self, rows: list[LedgerRow], as_of: date, filtered: bool
    ) -> BalanceSheetReport:
        assets = self._position_lines(rows, "ASSET")
        liabilities = self._position_lines(rows, "LIABILITY")
        equity = self._position_lines(rows, "EQUITY")
        cumulative_revenue = self._sum_lines(self._account_lines(rows, "REVENUE"))
        cumulative_expense = self._sum_lines(self._account_lines(rows, "EXPENSE"))
        running_profit = self._money(cumulative_revenue - cumulative_expense)
        if running_profit != ZERO:
            equity.append(
                AccountReportLine(
                    account_key="CURRENT_EARNINGS",
                    account_name="Laba berjalan",
                    amount=running_profit,
                )
            )
        total_assets = self._sum_lines(assets)
        total_liabilities = self._sum_lines(liabilities)
        total_equity = self._sum_lines(equity)
        difference = self._money(total_assets - total_liabilities - total_equity)
        qualification = " dengan filter yang dipilih" if filtered else ""
        return BalanceSheetReport(
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            total_equity=total_equity,
            difference=difference,
            explanation=(
                f"Pada {as_of.isoformat()}{qualification}, usaha memiliki aset "
                f"{self._rupiah(total_assets)}, utang {self._rupiah(total_liabilities)}, "
                f"dan modal beserta laba {self._rupiah(total_equity)}."
            ),
        )

    def _account_lines(self, rows: list[LedgerRow], account_type: str) -> list[AccountReportLine]:
        values: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
        for row in rows:
            if row.account_type == account_type:
                values[(row.account_key, row.account_name)] += self._normal_amount(row)
        return [
            AccountReportLine(account_key=key, account_name=name, amount=self._money(amount))
            for (key, name), amount in sorted(values.items(), key=lambda item: item[0][1])
            if self._money(amount) != ZERO
        ]

    def _position_lines(self, rows: list[LedgerRow], account_type: str) -> list[AccountReportLine]:
        values: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: ZERO)
        for row in rows:
            if row.account_type != account_type:
                continue
            amount = self._normal_amount(row)
            if account_type == "EQUITY" and row.normal_balance == "DEBIT":
                amount = -amount
            values[(row.account_key, row.account_name, row.normal_balance)] += amount
        return [
            AccountReportLine(account_key=key, account_name=name, amount=self._money(amount))
            for (key, name, _), amount in sorted(values.items(), key=lambda item: item[0][1])
            if self._money(amount) != ZERO
        ]

    def _time_series(self, rows: list[LedgerRow], *, monthly: bool) -> list[TimeSeriesPoint]:
        values: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"income": ZERO, "expense": ZERO, "sales": ZERO}
        )
        for row in rows:
            key = row.entry_date.strftime("%Y-%m" if monthly else "%Y-%m-%d")
            if row.account_type == "REVENUE":
                amount = self._normal_amount(row)
                values[key]["income"] += amount
                if row.account_key == "SALES":
                    values[key]["sales"] += amount
            elif row.account_type == "EXPENSE":
                values[key]["expense"] += self._normal_amount(row)
        return [
            TimeSeriesPoint(
                period=key,
                income=self._money(value["income"]),
                expense=self._money(value["expense"]),
                profit=self._money(value["income"] - value["expense"]),
                sales=self._money(value["sales"]),
            )
            for key, value in sorted(values.items())
        ]

    def _categories(self, lines: list[AccountReportLine]) -> list[CategoryTotal]:
        total = self._sum_lines(lines)
        return [
            CategoryTotal(
                key=line.account_key,
                label=line.account_name,
                amount=line.amount,
                percentage=(
                    (line.amount / total * Decimal("100")).quantize(MONEY)
                    if total != ZERO
                    else ZERO
                ),
            )
            for line in sorted(lines, key=lambda item: item.amount, reverse=True)
        ]

    def _best_sellers(self, rows: list[ProductSaleRow]) -> list[ProductPerformance]:
        values: dict[tuple[UUID, str, str, str], tuple[Decimal, Decimal]] = {}
        for row in rows:
            quantity, amount = values.get(
                (row.product_id, row.sku, row.name, row.unit), (ZERO, ZERO)
            )
            sign = Decimal("-1") if row.transaction_type == "REVERSAL" else Decimal("1")
            values[(row.product_id, row.sku, row.name, row.unit)] = (
                quantity + (sign * row.quantity),
                amount + (sign * row.line_total),
            )
        result = [
            ProductPerformance(
                product_id=product_id,
                sku=sku,
                name=name,
                unit=unit,
                quantity_sold=max(quantity, Decimal("0")),
                sales_value=self._money(max(amount, ZERO)),
            )
            for (product_id, sku, name, unit), (quantity, amount) in values.items()
            if quantity > 0
        ]
        return sorted(
            result, key=lambda item: (item.quantity_sold, item.sales_value), reverse=True
        )[:10]

    def _obligations(
        self,
        rows: list[ObligationSnapshot],
        as_of: date,
        label: str,
        journal_value: Decimal,
    ) -> ObligationReport:
        active = [
            row
            for row in rows
            if row.transaction_date <= as_of
            and row.status != "CANCELLED"
            and row.remaining_amount > ZERO
        ]
        initial = self._money(sum((row.initial_amount for row in active), ZERO))
        paid = self._money(sum((row.paid_amount for row in active), ZERO))
        remaining = self._money(sum((row.remaining_amount for row in active), ZERO))
        overdue = sum(1 for row in active if row.due_date < as_of)
        return ObligationReport(
            open_count=len(active),
            overdue_count=overdue,
            total_initial=initial,
            total_paid=paid,
            total_remaining=remaining,
            journal_value=journal_value,
            explanation=(
                f"Saat laporan dibuat, terdapat {len(active)} {label} belum lunas senilai "
                f"{self._rupiah(remaining)} menurut daftar tagihan; saldo jurnal pada tanggal "
                f"laporan adalah {self._rupiah(journal_value)}. {overdue} di antaranya "
                "melewati jatuh tempo."
            ),
        )

    def _inventory(self, products: list[ProductSnapshot], rows: list[LedgerRow]) -> InventoryReport:
        active = [product for product in products if product.is_active]
        quantity = sum((product.current_stock for product in active), Decimal("0.000"))
        operational = self._money(
            sum((product.current_stock * product.purchase_price for product in active), ZERO)
        )
        journal = self._money(
            sum(
                (self._normal_amount(row) for row in rows if row.account_key == "INVENTORY"),
                ZERO,
            )
        )
        low_stock = sum(1 for product in active if product.current_stock <= product.minimum_stock)
        return InventoryReport(
            product_count=len(active),
            low_stock_count=low_stock,
            total_quantity=quantity,
            operational_value=operational,
            journal_value=journal,
            explanation=(
                f"Terdapat {len(active)} produk aktif dengan perkiraan nilai stok "
                f"{self._rupiah(operational)}. Nilai akun Persediaan di jurnal adalah "
                f"{self._rupiah(journal)}; selisih perlu ditinjau bila pembelian "
                "dicatat sebagai biaya."
            ),
        )

    @staticmethod
    def _cash_movement(rows: list[LedgerRow]) -> tuple[Decimal, Decimal]:
        cash_in = sum((row.debit for row in rows if row.account_key in CASH_KEYS), ZERO)
        cash_out = sum((row.credit for row in rows if row.account_key in CASH_KEYS), ZERO)
        return ReportService._money(cash_in), ReportService._money(cash_out)

    @staticmethod
    def _ending_cash(rows: list[LedgerRow]) -> Decimal:
        return ReportService._money(
            sum(
                (row.debit - row.credit for row in rows if row.account_key in CASH_KEYS),
                ZERO,
            )
        )

    @staticmethod
    def _normal_amount(row: LedgerRow) -> Decimal:
        return row.debit - row.credit if row.normal_balance == "DEBIT" else row.credit - row.debit

    @staticmethod
    def _account_balance(rows: list[LedgerRow], account_keys: set[str]) -> Decimal:
        return ReportService._money(
            sum(
                (
                    ReportService._normal_amount(row)
                    for row in rows
                    if row.account_key in account_keys
                ),
                ZERO,
            )
        )

    @staticmethod
    def _sum_lines(lines: list[AccountReportLine]) -> Decimal:
        return ReportService._money(sum((line.amount for line in lines), ZERO))

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)

    @staticmethod
    def _rupiah(value: Decimal) -> str:
        whole = int(ReportService._money(value))
        sign = "-" if whole < 0 else ""
        return f"{sign}Rp{abs(whole):,}".replace(",", ".")

    @classmethod
    def _profit_explanation(cls, income: Decimal, expense: Decimal, profit: Decimal) -> str:
        result = "perkiraan laba" if profit >= ZERO else "perkiraan rugi"
        return (
            f"Usaha memperoleh pemasukan {cls._rupiah(income)} dan mengeluarkan "
            f"{cls._rupiah(expense)}. {result.capitalize()} periode ini adalah "
            f"{cls._rupiah(abs(profit))}."
        )

    @classmethod
    def _main_explanation(cls, summary: FinancialSummary) -> str:
        return cls._profit_explanation(
            summary.income,
            summary.expense,
            summary.estimated_profit,
        )

    @staticmethod
    def _month_start(value: date) -> date:
        return value.replace(day=1)

    @staticmethod
    def _shift_month(value: date, count: int) -> date:
        index = value.year * 12 + value.month - 1 + count
        return value.replace(year=index // 12, month=index % 12 + 1, day=1)
