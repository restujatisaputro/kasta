package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import okhttp3.ResponseBody
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

data class ReportContextDto(
    @SerializedName("business_name") val businessName: String,
    @SerializedName("date_from") val dateFrom: String,
    @SerializedName("date_to") val dateTo: String,
    @SerializedName("branch_name") val branchName: String,
    val source: String,
)

data class ReportSummaryDto(
    val income: String,
    val expense: String,
    @SerializedName("estimated_profit") val estimatedProfit: String,
    @SerializedName("cash_in") val cashIn: String,
    @SerializedName("cash_out") val cashOut: String,
    @SerializedName("net_cash_flow") val netCashFlow: String,
    val receivables: String,
    val payables: String,
    @SerializedName("inventory_value") val inventoryValue: String,
)

data class AccountReportLineDto(
    @SerializedName("account_key") val accountKey: String,
    @SerializedName("account_name") val accountName: String,
    val amount: String,
)

data class ProfitLossReportDto(
    val revenues: List<AccountReportLineDto>,
    val expenses: List<AccountReportLineDto>,
    @SerializedName("total_revenue") val totalRevenue: String,
    @SerializedName("total_expense") val totalExpense: String,
    val profit: String,
    val explanation: String,
)

data class BalanceSheetReportDto(
    val assets: List<AccountReportLineDto>,
    val liabilities: List<AccountReportLineDto>,
    val equity: List<AccountReportLineDto>,
    @SerializedName("total_assets") val totalAssets: String,
    @SerializedName("total_liabilities") val totalLiabilities: String,
    @SerializedName("total_equity") val totalEquity: String,
    val difference: String,
    val explanation: String,
)

data class CashFlowReportDto(
    @SerializedName("cash_in") val cashIn: String,
    @SerializedName("cash_out") val cashOut: String,
    @SerializedName("net_cash_flow") val netCashFlow: String,
    @SerializedName("ending_cash_balance") val endingCashBalance: String,
    val explanation: String,
)

data class CategoryTotalDto(
    val key: String,
    val label: String,
    val amount: String,
    val percentage: String,
)

data class ObligationReportDto(
    @SerializedName("open_count") val openCount: Int,
    @SerializedName("overdue_count") val overdueCount: Int,
    @SerializedName("total_remaining") val totalRemaining: String,
    @SerializedName("journal_value") val journalValue: String,
    val explanation: String,
)

data class InventoryReportDto(
    @SerializedName("product_count") val productCount: Int,
    @SerializedName("low_stock_count") val lowStockCount: Int,
    @SerializedName("operational_value") val operationalValue: String,
    @SerializedName("journal_value") val journalValue: String,
    val explanation: String,
)

data class ReportTimePointDto(
    val period: String,
    val income: String,
    val expense: String,
    val profit: String,
    val sales: String,
)

data class ProductPerformanceDto(
    @SerializedName("product_id") val productId: String,
    val sku: String,
    val name: String,
    val unit: String,
    @SerializedName("quantity_sold") val quantitySold: String,
    @SerializedName("sales_value") val salesValue: String,
)

data class ReportChartsDto(
    @SerializedName("income_vs_expense") val incomeVsExpense: List<ReportTimePointDto>,
    @SerializedName("profit_trend") val profitTrend: List<ReportTimePointDto>,
    @SerializedName("expense_categories") val expenseCategories: List<CategoryTotalDto>,
    @SerializedName("daily_sales") val dailySales: List<ReportTimePointDto>,
    @SerializedName("best_selling_products") val bestSellingProducts: List<ProductPerformanceDto>,
)

data class FinancialReportDto(
    val context: ReportContextDto,
    val summary: ReportSummaryDto,
    @SerializedName("profit_loss") val profitLoss: ProfitLossReportDto,
    @SerializedName("balance_sheet") val balanceSheet: BalanceSheetReportDto,
    @SerializedName("cash_flow") val cashFlow: CashFlowReportDto,
    val sales: List<CategoryTotalDto>,
    val expenditures: List<CategoryTotalDto>,
    val receivables: ObligationReportDto,
    val payables: ObligationReportDto,
    val inventory: InventoryReportDto,
    @SerializedName("best_selling_products") val bestSellingProducts: List<ProductPerformanceDto>,
    @SerializedName("monthly_comparison") val monthlyComparison: List<ReportTimePointDto>,
    val charts: ReportChartsDto,
    val explanation: String,
)

interface ReportApi {
    @GET("businesses/{business_id}/reports/financial")
    suspend fun financial(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Query("period") period: String,
        @Query("reference_date") referenceDate: String,
        @Query("date_from") dateFrom: String?,
        @Query("date_to") dateTo: String?,
        @Query("category") category: String?,
        @Query("payment_method") paymentMethod: String?,
        @Query("branch_id") branchId: String,
    ): FinancialReportDto

    @Streaming
    @GET("businesses/{business_id}/reports/financial/export")
    suspend fun export(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Query("period") period: String,
        @Query("reference_date") referenceDate: String,
        @Query("date_from") dateFrom: String?,
        @Query("date_to") dateTo: String?,
        @Query("category") category: String?,
        @Query("payment_method") paymentMethod: String?,
        @Query("branch_id") branchId: String,
        @Query("format") format: String,
    ): ResponseBody
}
