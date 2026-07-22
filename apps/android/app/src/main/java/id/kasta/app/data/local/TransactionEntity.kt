package id.kasta.app.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

enum class SyncStatus {
    PENDING,
    SYNCING,
    SYNCED,
    FAILED,
    CONFLICT,
}

@Entity(
    tableName = "transactions",
    indices = [
        Index(value = ["businessId", "syncStatus"]),
        Index(value = ["businessId", "transactionDate"]),
        Index(value = ["businessId", "serverId"], unique = true),
    ],
)
data class TransactionEntity(
    @PrimaryKey val localId: String,
    val serverId: String? = null,
    val businessId: String,
    val deviceId: String,
    val version: Int = 0,
    val syncStatus: String = SyncStatus.PENDING.name,
    val operation: String = "CREATE",
    val entryKind: String,
    val transactionDate: String,
    val amountRupiah: Long,
    val categoryAccount: String? = null,
    val counterpartyName: String? = null,
    val paymentMethod: String = "CASH",
    val note: String = "",
    val receiptUri: String? = null,
    val recurrenceFrequency: String? = null,
    val recurrenceInterval: Int? = null,
    val revisionReason: String? = null,
    val isDraft: Boolean = false,
    val serverStatus: String = "POSTED",
    val errorMessage: String? = null,
    val conflictId: String? = null,
    val conflictServerVersion: Int? = null,
    val conflictServerPayload: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val deletedAt: Long? = null,
)
