from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from kasta_api.modules.reports.constants import ReportPeriod


class ReportContext(BaseModel):
    business_id: UUID
    business_name: str
    period: ReportPeriod
    date_from: date
    date_to: date
    category: str | None
    payment_method: str | None
    branch_id: UUID
    branch_name: str
    generated_at: datetime
    source: Literal["JOURNAL"] = "JOURNAL"


class FinancialSummary(BaseModel):
    income: Decimal
    expense: Decimal
    estimated_profit: Decimal
    cash_in: Decimal
    cash_out: Decimal
    net_cash_flow: Decimal
    receivables: Decimal
    payables: Decimal
    inventory_value: Decimal


class AccountReportLine(BaseModel):
    account_key: str
    account_name: str
    amount: Decimal


class ProfitLossReport(BaseModel):
    revenues: list[AccountReportLine]
    expenses: list[AccountReportLine]
    total_revenue: Decimal
    total_expense: Decimal
    profit: Decimal
    explanation: str


class BalanceSheetReport(BaseModel):
    assets: list[AccountReportLine]
    liabilities: list[AccountReportLine]
    equity: list[AccountReportLine]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    difference: Decimal
    explanation: str


class CashFlowReport(BaseModel):
    cash_in: Decimal
    cash_out: Decimal
    net_cash_flow: Decimal
    ending_cash_balance: Decimal
    explanation: str


class CategoryTotal(BaseModel):
    key: str
    label: str
    amount: Decimal
    percentage: Decimal


class TimeSeriesPoint(BaseModel):
    period: str
    income: Decimal
    expense: Decimal
    profit: Decimal
    sales: Decimal


class ProductPerformance(BaseModel):
    product_id: UUID
    sku: str
    name: str
    unit: str
    quantity_sold: Decimal
    sales_value: Decimal


class ObligationReport(BaseModel):
    open_count: int
    overdue_count: int
    total_initial: Decimal
    total_paid: Decimal
    total_remaining: Decimal
    journal_value: Decimal
    explanation: str


class InventoryReport(BaseModel):
    product_count: int
    low_stock_count: int
    total_quantity: Decimal
    operational_value: Decimal
    journal_value: Decimal
    explanation: str


class ChartData(BaseModel):
    income_vs_expense: list[TimeSeriesPoint]
    profit_trend: list[TimeSeriesPoint]
    expense_categories: list[CategoryTotal]
    daily_sales: list[TimeSeriesPoint]
    best_selling_products: list[ProductPerformance]


class FinancialReportResponse(BaseModel):
    context: ReportContext
    summary: FinancialSummary
    profit_loss: ProfitLossReport
    balance_sheet: BalanceSheetReport
    cash_flow: CashFlowReport
    sales: list[CategoryTotal]
    expenditures: list[CategoryTotal]
    receivables: ObligationReport
    payables: ObligationReport
    inventory: InventoryReport
    best_selling_products: list[ProductPerformance]
    monthly_comparison: list[TimeSeriesPoint]
    charts: ChartData
    explanation: str
