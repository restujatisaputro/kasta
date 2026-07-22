package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path

data class MentorAccessDto(
    val id: String,
    @SerializedName("business_id") val businessId: String,
    @SerializedName("mentor_id") val mentorId: String,
    val scope: List<String>,
    val status: String,
    @SerializedName("request_message") val requestMessage: String?,
    @SerializedName("expires_at") val expiresAt: String?,
    @SerializedName("last_accessed_at") val lastAccessedAt: String?,
    @SerializedName("rejection_reason") val rejectionReason: String?,
    @SerializedName("revocation_reason") val revocationReason: String?,
)

data class MentorAccessDecisionDto(
    val decision: String,
    val scope: List<String>,
    @SerializedName("expires_at") val expiresAt: String?,
    val reason: String?,
)

data class MentorAccessRevokeDto(val reason: String)

data class MentorAccessHistoryDto(
    val id: String,
    val action: String,
    @SerializedName("mentor_id") val mentorId: String?,
    val scope: List<String>,
    val reason: String?,
    @SerializedName("accessed_at") val accessedAt: String,
)

interface MentorAccessApi {
    @GET("businesses/{business_id}/mentor-access")
    suspend fun list(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): List<MentorAccessDto>

    @GET("businesses/{business_id}/mentor-access/history")
    suspend fun history(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): List<MentorAccessHistoryDto>

    @PATCH("businesses/{business_id}/mentor-access/{access_id}/decision")
    suspend fun decide(
        @Path("business_id") businessId: String,
        @Path("access_id") accessId: String,
        @Header("Authorization") authorization: String,
        @Body payload: MentorAccessDecisionDto,
    ): MentorAccessDto

    @POST("businesses/{business_id}/mentor-access/{access_id}/revoke")
    suspend fun revoke(
        @Path("business_id") businessId: String,
        @Path("access_id") accessId: String,
        @Header("Authorization") authorization: String,
        @Body payload: MentorAccessRevokeDto,
    ): MentorAccessDto
}
