package id.kasta.app.domain.model

data class DashboardTransaction(
    val id: String,
    val title: String,
    val date: String,
    val amountRupiah: Long,
    val isIncome: Boolean,
    val syncStatus: String,
)

data class DashboardSummary(
    val balanceRupiah: Long = 0,
    val incomeTodayRupiah: Long = 0,
    val expenseTodayRupiah: Long = 0,
    val estimatedMonthlyProfitRupiah: Long = 0,
    val payablesDueRupiah: Long = 0,
    val receivablesDueRupiah: Long = 0,
    val latestTransactions: List<DashboardTransaction> = emptyList(),
)
