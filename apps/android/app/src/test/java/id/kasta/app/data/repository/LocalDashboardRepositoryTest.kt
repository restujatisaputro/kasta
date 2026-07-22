package id.kasta.app.data.repository

import id.kasta.app.data.local.TransactionEntity
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.LocalDate

class LocalDashboardRepositoryTest {
    @Test
    fun `ringkasan menghitung saldo dan laba dari transaksi Room`() {
        val rows =
            listOf(
                transaction("income", "INCOME", 750_000),
                transaction("expense", "EXPENSE", 225_000),
                transaction("capital", "CAPITAL", 1_000_000),
                transaction("draft", "INCOME", 9_000_000, isDraft = true),
                transaction("reversed", "EXPENSE", 8_000_000, status = "REVERSED"),
            )

        val result = summarizeDashboard(rows, LocalDate.of(2026, 7, 22))

        assertEquals(1_525_000, result.balanceRupiah)
        assertEquals(750_000, result.incomeTodayRupiah)
        assertEquals(225_000, result.expenseTodayRupiah)
        assertEquals(525_000, result.estimatedMonthlyProfitRupiah)
        assertEquals(3, result.latestTransactions.size)
    }

    private fun transaction(
        id: String,
        kind: String,
        amount: Long,
        isDraft: Boolean = false,
        status: String = "POSTED",
    ) = TransactionEntity(
        localId = id,
        businessId = "business-1",
        deviceId = "device-1",
        entryKind = kind,
        transactionDate = "2026-07-22",
        amountRupiah = amount,
        isDraft = isDraft,
        serverStatus = status,
    )
}
