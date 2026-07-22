package id.kasta.app.data.repository

import id.kasta.app.data.local.TransactionDao
import id.kasta.app.data.local.TransactionEntity
import id.kasta.app.data.session.SessionStore
import id.kasta.app.domain.model.DashboardSummary
import id.kasta.app.domain.model.DashboardTransaction
import id.kasta.app.domain.repository.DashboardRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.time.LocalDate
import javax.inject.Inject

class LocalDashboardRepository
    @Inject
    constructor(
        private val transactionDao: TransactionDao,
        sessionStore: SessionStore,
    ) : DashboardRepository {
        private val businessId = sessionStore.get()?.businessId.orEmpty()

        override fun observeDashboard(): Flow<DashboardSummary> = transactionDao.observeAll(businessId).map(::summarizeDashboard)
    }

internal fun summarizeDashboard(
    source: List<TransactionEntity>,
    today: LocalDate = LocalDate.now(),
): DashboardSummary {
    val transactions = source.filter { !it.isDraft && it.deletedAt == null && it.serverStatus != "REVERSED" }
    val todayText = today.toString()
    val month = todayText.take(7)

    fun signed(item: TransactionEntity): Long =
        when (item.entryKind) {
            "INCOME", "CAPITAL" -> item.amountRupiah
            else -> -item.amountRupiah
        }
    val monthlyIncome = transactions.filter { it.transactionDate.startsWith(month) && it.entryKind == "INCOME" }.sumOf { it.amountRupiah }
    val monthlyExpense = transactions.filter { it.transactionDate.startsWith(month) && it.entryKind == "EXPENSE" }.sumOf { it.amountRupiah }
    return DashboardSummary(
        balanceRupiah = transactions.sumOf(::signed),
        incomeTodayRupiah = transactions.filter { it.transactionDate == todayText && it.entryKind == "INCOME" }.sumOf { it.amountRupiah },
        expenseTodayRupiah = transactions.filter { it.transactionDate == todayText && it.entryKind == "EXPENSE" }.sumOf { it.amountRupiah },
        estimatedMonthlyProfitRupiah = monthlyIncome - monthlyExpense,
        latestTransactions =
            transactions.take(5).map { item ->
                DashboardTransaction(
                    id = item.localId,
                    title = item.note.ifBlank { entryLabel(item.entryKind) },
                    date = item.transactionDate,
                    amountRupiah = item.amountRupiah,
                    isIncome = item.entryKind in setOf("INCOME", "CAPITAL"),
                    syncStatus = item.syncStatus,
                )
            },
    )
}

private fun entryLabel(kind: String): String =
    when (kind) {
        "INCOME" -> "Uang Masuk"
        "EXPENSE" -> "Uang Keluar"
        "CAPITAL" -> "Tambah Modal"
        else -> "Ambil Uang Pribadi"
    }
