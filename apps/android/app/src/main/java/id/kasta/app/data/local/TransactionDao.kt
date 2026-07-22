package id.kasta.app.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

data class SyncCountRow(
    val syncStatus: String,
    val total: Int,
)

@Dao
interface TransactionDao {
    @Query(
        "SELECT COUNT(*) FROM transactions WHERE businessId = :businessId " +
            "AND transactionDate = :transactionDate AND deletedAt IS NULL AND isDraft = 0",
    )
    suspend fun countPostedOn(
        businessId: String,
        transactionDate: String,
    ): Int

    @Query(
        """
        SELECT * FROM transactions
        WHERE businessId = :businessId AND deletedAt IS NULL
        ORDER BY transactionDate DESC, updatedAt DESC
        """,
    )
    fun observeAll(businessId: String): Flow<List<TransactionEntity>>

    @Query(
        """
        SELECT * FROM transactions
        WHERE businessId = :businessId
          AND isDraft = 0
          AND syncStatus IN ('PENDING', 'FAILED')
        ORDER BY createdAt
        LIMIT :limit
        """,
    )
    suspend fun pending(
        businessId: String,
        limit: Int = 100,
    ): List<TransactionEntity>

    @Query(
        """
        UPDATE transactions SET syncStatus = 'SYNCING', errorMessage = NULL
        WHERE localId IN (:localIds) AND syncStatus IN ('PENDING', 'FAILED')
        """,
    )
    suspend fun markSyncing(localIds: List<String>)

    @Transaction
    suspend fun claimPending(
        businessId: String,
        limit: Int = 100,
    ): List<TransactionEntity> {
        val rows = pending(businessId, limit)
        if (rows.isNotEmpty()) markSyncing(rows.map { it.localId })
        return rows.map { it.copy(syncStatus = SyncStatus.SYNCING.name) }
    }

    @Query("SELECT * FROM transactions WHERE businessId = :businessId AND serverId = :serverId LIMIT 1")
    suspend fun findByServerId(
        businessId: String,
        serverId: String,
    ): TransactionEntity?

    @Query("SELECT * FROM transactions WHERE localId = :localId LIMIT 1")
    suspend fun findByLocalId(localId: String): TransactionEntity?

    @Query(
        """
        SELECT categoryAccount FROM transactions
        WHERE businessId = :businessId AND entryKind = 'EXPENSE'
          AND categoryAccount IS NOT NULL AND deletedAt IS NULL
        ORDER BY updatedAt DESC LIMIT 1
        """,
    )
    suspend fun lastExpenseCategory(businessId: String): String?

    @Query(
        """
        SELECT syncStatus, COUNT(*) AS total FROM transactions
        WHERE businessId = :businessId AND isDraft = 0
        GROUP BY syncStatus
        """,
    )
    fun observeSyncCounts(businessId: String): Flow<List<SyncCountRow>>

    @Query(
        """
        SELECT * FROM transactions
        WHERE businessId = :businessId AND syncStatus = 'CONFLICT'
        ORDER BY updatedAt DESC
        """,
    )
    fun observeConflicts(businessId: String): Flow<List<TransactionEntity>>

    @Upsert
    suspend fun upsert(transaction: TransactionEntity)

    @Upsert
    suspend fun upsertAll(transactions: List<TransactionEntity>)

    @Query(
        """
        UPDATE transactions SET syncStatus = 'SYNCED', serverId = :serverId,
            version = :version, errorMessage = NULL, conflictId = NULL,
            conflictServerVersion = NULL, conflictServerPayload = NULL,
            updatedAt = :updatedAt, deletedAt = :deletedAt
        WHERE localId = :localId
        """,
    )
    suspend fun markSynced(
        localId: String,
        serverId: String?,
        version: Int,
        deletedAt: Long?,
        updatedAt: Long = System.currentTimeMillis(),
    )

    @Query(
        """
        UPDATE transactions SET syncStatus = 'FAILED', errorMessage = :message
        WHERE localId = :localId
        """,
    )
    suspend fun markFailed(
        localId: String,
        message: String,
    )

    @Query(
        """
        UPDATE transactions SET syncStatus = 'FAILED', errorMessage = :message
        WHERE localId IN (:localIds) AND syncStatus = 'SYNCING'
        """,
    )
    suspend fun releaseForRetry(
        localIds: List<String>,
        message: String,
    )

    @Query(
        """
        UPDATE transactions SET syncStatus = 'CONFLICT', errorMessage = :message,
            serverId = :serverId, conflictId = :conflictId,
            conflictServerVersion = :serverVersion,
            conflictServerPayload = :serverPayload, updatedAt = :updatedAt
        WHERE localId = :localId
        """,
    )
    suspend fun markConflict(
        localId: String,
        serverId: String,
        conflictId: String?,
        serverVersion: Int,
        serverPayload: String,
        message: String,
        updatedAt: Long = System.currentTimeMillis(),
    )

    @Query(
        """
        UPDATE transactions SET syncStatus = 'PENDING', version = :serverVersion,
            operation = 'UPSERT', revisionReason = :reason, conflictId = NULL,
            conflictServerVersion = NULL, conflictServerPayload = NULL,
            errorMessage = NULL, updatedAt = :updatedAt WHERE localId = :localId
        """,
    )
    suspend fun resolveWithLocal(
        localId: String,
        serverVersion: Int,
        reason: String,
        updatedAt: Long = System.currentTimeMillis(),
    )
}
