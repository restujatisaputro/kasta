package id.kasta.app.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface NotificationDao {
    @Query(
        "SELECT * FROM notifications WHERE businessId = :businessId " +
            "ORDER BY createdAt DESC",
    )
    fun observe(businessId: String): Flow<List<NotificationEntity>>

    @Query(
        "SELECT COUNT(*) FROM notifications WHERE businessId = :businessId AND readAt IS NULL",
    )
    fun observeUnreadCount(businessId: String): Flow<Int>

    @Query(
        "SELECT * FROM notifications WHERE businessId = :businessId AND readAt IS NULL " +
            "ORDER BY createdAt DESC",
    )
    suspend fun unread(businessId: String): List<NotificationEntity>

    @Upsert
    suspend fun upsert(items: List<NotificationEntity>)

    @Query("UPDATE notifications SET readAt = :readAt WHERE serverId = :serverId")
    suspend fun markRead(
        serverId: String,
        readAt: String,
    )

    @Query("UPDATE notifications SET readAt = :readAt WHERE businessId = :businessId")
    suspend fun markAllRead(
        businessId: String,
        readAt: String,
    )
}
