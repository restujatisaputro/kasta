package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path

data class CreateAccountRequest(
    @SerializedName("full_name") val fullName: String,
    val email: String? = null,
    val phone: String? = null,
    val password: String,
)

data class VerifyRequest(val token: String)

data class VerifyResponse(
    @SerializedName("onboarding_token") val onboardingToken: String,
)

data class BusinessCategoryDto(
    val id: String,
    val code: String,
    val name: String,
    @SerializedName("business_type") val businessType: String,
)

data class DeviceDto(
    @SerializedName("device_id") val deviceId: String,
    val platform: String = "ANDROID",
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("app_version") val appVersion: String,
)

data class CompleteOnboardingRequest(
    @SerializedName("role_selection") val roleSelection: String = "BUSINESS_OWNER",
    @SerializedName("business_name") val businessName: String,
    @SerializedName("business_type") val businessType: String,
    @SerializedName("category_id") val categoryId: String,
    val scale: String,
    @SerializedName("established_year") val establishedYear: Int?,
    val address: String?,
    val village: String?,
    val district: String?,
    val city: String,
    val province: String,
    val phone: String?,
    val email: String?,
    @SerializedName("employee_count") val employeeCount: Int,
    val currency: String,
    val timezone: String,
    @SerializedName("recording_method") val recordingMethod: String,
    @SerializedName("payment_methods") val paymentMethods: List<String>,
    @SerializedName("opening_balance") val openingBalance: String,
    @SerializedName("has_products_and_stock") val hasProductsAndStock: Boolean,
    @SerializedName("tutorial_completed") val tutorialCompleted: Boolean = true,
    val device: DeviceDto,
)

data class TokenPairDto(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String,
)

data class BusinessProfileDto(
    @SerializedName("business_id") val businessId: String,
    val name: String,
    @SerializedName("logo_path") val logoPath: String?,
    @SerializedName("business_type") val businessType: String,
    @SerializedName("category_id") val categoryId: String,
    @SerializedName("category_name") val categoryName: String,
    val scale: String,
    @SerializedName("established_year") val establishedYear: Int?,
    val address: String?,
    val village: String?,
    val district: String?,
    val city: String,
    val province: String,
    val phone: String?,
    val email: String?,
    @SerializedName("employee_count") val employeeCount: Int,
    val currency: String,
    val timezone: String,
    @SerializedName("recording_method") val recordingMethod: String,
    val status: String,
    @SerializedName("payment_methods") val paymentMethods: List<String>,
    @SerializedName("opening_balance") val openingBalance: String,
    @SerializedName("has_products_and_stock") val hasProductsAndStock: Boolean,
    @SerializedName("tutorial_completed_at") val tutorialCompletedAt: String?,
    @SerializedName("onboarding_completed_at") val onboardingCompletedAt: String,
)

data class CompleteOnboardingResponse(
    @SerializedName("business_id") val businessId: String,
    val profile: BusinessProfileDto,
    val tokens: TokenPairDto,
)

interface OnboardingApi {
    @POST("onboarding/account")
    suspend fun createAccount(
        @Body request: CreateAccountRequest,
    )

    @POST("onboarding/verify")
    suspend fun verify(
        @Body request: VerifyRequest,
    ): VerifyResponse

    @GET("onboarding/categories")
    suspend fun categories(): List<BusinessCategoryDto>

    @POST("onboarding/complete")
    suspend fun complete(
        @Header("Authorization") authorization: String,
        @Body request: CompleteOnboardingRequest,
    ): CompleteOnboardingResponse

    @Multipart
    @PUT("businesses/{business_id}/profile/logo")
    suspend fun uploadLogo(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Part logo: MultipartBody.Part,
    ): BusinessProfileDto
}
