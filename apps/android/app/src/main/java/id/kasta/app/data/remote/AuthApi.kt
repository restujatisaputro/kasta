package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.POST

data class LoginRequest(
    @SerializedName("business_id") val businessId: String,
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

interface AuthApi {
    @POST("auth/login")
    suspend fun login(
        @Body request: LoginRequest,
    ): AuthTokenPairDto
}
