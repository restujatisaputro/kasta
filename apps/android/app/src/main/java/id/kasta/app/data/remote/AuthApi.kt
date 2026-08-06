package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

data class LoginRequest(
    @SerializedName("business_id") val businessId: String? = null,
    val identifier: String,
    val password: String,
    @SerializedName("device_id") val deviceId: String,
    val platform: String = "ANDROID",
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("app_version") val appVersion: String,
)

data class AuthTokenPairDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Int,
)

data class BusinessAccessDto(
    @SerializedName("business_id") val businessId: String,
    val code: String,
    val name: String,
    val role: String,
)

data class AccessTokenDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Int,
)

interface AuthApi {
    @POST("auth/login")
    suspend fun login(
        @Body request: LoginRequest,
    ): AuthTokenPairDto

    @GET("auth/businesses")
    suspend fun businesses(
        @Header("Authorization") authorization: String,
    ): List<BusinessAccessDto>

    @POST("auth/businesses/{business_id}/select")
    suspend fun selectBusiness(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): AccessTokenDto
}
