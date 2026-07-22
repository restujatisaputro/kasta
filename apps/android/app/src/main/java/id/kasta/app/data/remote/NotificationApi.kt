package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

data class NotificationDto(
    val id: String,
    @SerializedName("business_id") val businessId: String,
    @SerializedName("notification_type") val category: String,
    val title: String,
    val message: String,
    @SerializedName("entity_type") val entityType: String,
    @SerializedName("entity_id") val entityId: String,
    @SerializedName("action_path") val actionPath: String?,
    @SerializedName("available_at") val availableAt: String?,
    @SerializedName("read_at") val readAt: String?,
    @SerializedName("created_at") val createdAt: String,
)

data class NotificationPreferenceDto(
    val category: String,
    val label: String,
    val enabled: Boolean,
    @SerializedName("local_enabled") val localEnabled: Boolean,
    @SerializedName("push_enabled") val pushEnabled: Boolean,
    @SerializedName("email_enabled") val emailEnabled: Boolean,
    @SerializedName("reminder_time") val reminderTime: String,
    @SerializedName("quiet_hours_start") val quietHoursStart: String?,
    @SerializedName("quiet_hours_end") val quietHoursEnd: String?,
    val timezone: String,
)

data class NotificationPreferenceUpdateDto(
    val category: String,
    val enabled: Boolean,
    @SerializedName("local_enabled") val localEnabled: Boolean,
    @SerializedName("push_enabled") val pushEnabled: Boolean,
    @SerializedName("email_enabled") val emailEnabled: Boolean,
    @SerializedName("reminder_time") val reminderTime: String,
    @SerializedName("quiet_hours_start") val quietHoursStart: String?,
    @SerializedName("quiet_hours_end") val quietHoursEnd: String?,
    val timezone: String = "Asia/Jakarta",
)

data class NotificationPreferencesUpdateDto(
    val items: List<NotificationPreferenceUpdateDto>,
)

interface NotificationApi {
    @POST("businesses/{business_id}/notifications/evaluate")
    suspend fun evaluate(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    )

    @GET("businesses/{business_id}/notifications")
    suspend fun list(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): List<NotificationDto>

    @POST("businesses/{business_id}/notifications/{notification_id}/read")
    suspend fun markRead(
        @Path("business_id") businessId: String,
        @Path("notification_id") notificationId: String,
        @Header("Authorization") authorization: String,
    ): NotificationDto

    @POST("businesses/{business_id}/notifications/read-all")
    suspend fun markAllRead(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    )

    @GET("businesses/{business_id}/notifications/preferences")
    suspend fun preferences(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): List<NotificationPreferenceDto>

    @PUT("businesses/{business_id}/notifications/preferences")
    suspend fun updatePreferences(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Body payload: NotificationPreferencesUpdateDto,
    ): List<NotificationPreferenceDto>
}
