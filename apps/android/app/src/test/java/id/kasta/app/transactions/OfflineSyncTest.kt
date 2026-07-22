package id.kasta.app.transactions

import id.kasta.app.data.local.SyncStatus
import id.kasta.app.data.local.TransactionEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OfflineSyncTest {
    @Test
    fun `transaksi dapat dibuat offline dan masuk antrean`() {
        val transaction =
            TransactionEntity(
                localId = "local-123",
                serverId = null,
                businessId = "business-123",
                deviceId = "android-device-123",
                entryKind = "INCOME",
                transactionDate = "2026-07-22",
                amountRupiah = 25_000,
            )

        assertNull(transaction.serverId)
        assertEquals(0, transaction.version)
        assertEquals(SyncStatus.PENDING.name, transaction.syncStatus)
    }

    @Test
    fun `jaringan terputus meminta WorkManager retry`() {
        assertEquals(SyncWorkDecision.RETRY, decideSyncWork(completed = false))
    }

    @Test
    fun `sinkronisasi berhasil menyelesaikan worker`() {
        assertEquals(SyncWorkDecision.SUCCESS, decideSyncWork(completed = true))
    }

    @Test
    fun `tombstone mempertahankan identitas data`() {
        val deletedAt = 1_753_158_400_000L
        val transaction =
            TransactionEntity(
                localId = "local-delete",
                serverId = "server-delete",
                businessId = "business-123",
                deviceId = "android-device-123",
                version = 3,
                operation = "DELETE",
                entryKind = "EXPENSE",
                transactionDate = "2026-07-22",
                amountRupiah = 10_000,
                deletedAt = deletedAt,
            )

        assertEquals("server-delete", transaction.serverId)
        assertEquals(deletedAt, transaction.deletedAt)
        assertEquals("DELETE", transaction.operation)
    }
}
