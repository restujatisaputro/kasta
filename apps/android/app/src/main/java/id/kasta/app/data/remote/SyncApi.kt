package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

data class SyncPushOperationDto(
    @SerializedName("operation_id") val operationId: String,
    @SerializedName("entity_type") val entityType: String = "TRANSACTION",
    val action: String,
    @SerializedName("local_id") val localId: String,
    @SerializedName("server_id") val serverId: String?,
    @SerializedName("base_version") val baseVersion: Int,
    @SerializedName("changed_at") val changedAt: String,
    val payload: Map<String, Any?>,
)

data class SyncPushRequestDto(
    @SerializedName("business_id") val businessId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("batch_id") val batchId: String,
    val operations: List<SyncPushOperationDto>,
)

data class SyncPushResultDto(
    @SerializedName("operation_id") val operationId: String,
    @SerializedName("local_id") val localId: String,
    val status: String,
    @SerializedName("server_id") val serverId: String?,
    @SerializedName("server_version") val serverVersion: Int?,
    @SerializedName("conflict_id") val conflictId: String?,
    @SerializedName("canonical_payload") val canonicalPayload: Map<String, Any?>?,
    @SerializedName("deleted_at") val deletedAt: String?,
    val message: String?,
)

data class SyncPushResponseDto(
    @SerializedName("batch_id") val batchId: String,
    val results: List<SyncPushResultDto>,
    @SerializedName("server_time") val serverTime: String,
)

data class SyncPullRequestDto(
    @SerializedName("business_id") val businessId: String,
    @SerializedName("device_id") val deviceId: String,
    val cursor: Long,
    val limit: Int = 100,
)

data class SyncPullChangeDto(
    val cursor: Long,
    @SerializedName("entity_type") val entityType: String,
    @SerializedName("server_id") val serverId: String,
    val version: Int,
    val action: String,
    val payload: Map<String, Any?>,
    @SerializedName("changed_at") val changedAt: String,
)

data class SyncPullResponseDto(
    val changes: List<SyncPullChangeDto>,
    @SerializedName("next_cursor") val nextCursor: Long,
    @SerializedName("has_more") val hasMore: Boolean,
    @SerializedName("server_time") val serverTime: String,
)

data class RemoteSyncStatusDto(
    @SerializedName("business_id") val businessId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("last_push_at") val lastPushAt: String?,
    @SerializedName("last_pull_at") val lastPullAt: String?,
    @SerializedName("last_cursor") val lastCursor: Long,
    @SerializedName("open_conflicts") val openConflicts: Int,
    @SerializedName("server_time") val serverTime: String,
)

interface SyncApi {
    @POST("sync/push")
    suspend fun push(
        @Header("Authorization") authorization: String,
        @Body request: SyncPushRequestDto,
    ): SyncPushResponseDto

    @POST("sync/pull")
    suspend fun pull(
        @Header("Authorization") authorization: String,
        @Body request: SyncPullRequestDto,
    ): SyncPullResponseDto

    @GET("sync/status")
    suspend fun status(
        @Header("Authorization") authorization: String,
        @Query("business_id") businessId: String,
        @Query("device_id") deviceId: String,
    ): RemoteSyncStatusDto
}
