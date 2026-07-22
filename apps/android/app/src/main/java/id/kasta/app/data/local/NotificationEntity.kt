package id.kasta.app.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "notifications",
    indices = [
        Index(value = ["businessId", "readAt", "createdAt"]),
        Index(value = ["businessId", "serverId"], unique = true),
    ],
)
data class NotificationEntity(
    @PrimaryKey val localId: String,
    val serverId: String,
    val businessId: String,
    val category: String,
    val title: String,
    val message: String,
    val entityType: String,
    val entityId: String,
    val actionPath: String?,
    val availableAt: String?,
    val readAt: String?,
    val createdAt: String,
)
