package id.kasta.app.onboarding

import android.content.Context
import android.os.Build
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.BuildConfig
import id.kasta.app.data.local.OnboardingDraftDao
import id.kasta.app.data.remote.CompleteOnboardingRequest
import id.kasta.app.data.remote.CompleteOnboardingResponse
import id.kasta.app.data.remote.CreateAccountRequest
import id.kasta.app.data.remote.DeviceDto
import id.kasta.app.data.remote.OnboardingApi
import id.kasta.app.data.remote.VerifyRequest
import id.kasta.app.data.session.AppSession
import id.kasta.app.data.session.SessionStore
import id.kasta.app.data.session.SyncPreferences
import kotlinx.coroutines.flow.first
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import javax.inject.Inject
import javax.inject.Singleton

private const val MAX_LOGO_BYTES = 2 * 1024 * 1024

class OnboardingInputException(message: String) : IllegalArgumentException(message)

@Singleton
class OnboardingRepository
    @Inject
    constructor(
        private val api: OnboardingApi,
        private val drafts: OnboardingDraftDao,
        @ApplicationContext private val context: Context,
        private val sessionStore: SessionStore,
        private val syncPreferences: SyncPreferences,
    ) {
        suspend fun restoreDraft() = drafts.observe().first()

        suspend fun saveDraft(state: OnboardingUiState) = drafts.save(state.toDraft())

        suspend fun clearDraft() = drafts.clear()

        fun session() = sessionStore.get()

        suspend fun categories() = api.categories()

        suspend fun createAccount(state: OnboardingUiState) {
            api.createAccount(
                CreateAccountRequest(
                    fullName = state.fullName.trim(),
                    email = state.identifier.trim().takeIf { state.accountUsesEmail },
                    phone = state.identifier.trim().takeIf { !state.accountUsesEmail },
                    password = state.password,
                ),
            )
        }

        suspend fun verify(token: String) = api.verify(VerifyRequest(token.trim())).onboardingToken

        suspend fun complete(state: OnboardingUiState): CompleteOnboardingResponse {
            val deviceId = syncPreferences.deviceId()
            val result =
                api.complete(
                    authorization = "Bearer ${state.onboardingToken}",
                    request =
                        CompleteOnboardingRequest(
                            businessName = state.businessName.trim(),
                            businessType = state.businessType,
                            categoryId = state.categoryId,
                            scale = state.scale,
                            establishedYear = state.establishedYear.toIntOrNull(),
                            address = state.address.trim().ifBlank { null },
                            village = state.village.trim().ifBlank { null },
                            district = state.district.trim().ifBlank { null },
                            city = state.city.trim(),
                            province = state.province.trim(),
                            phone = state.businessPhone.trim().ifBlank { null },
                            email = state.businessEmail.trim().ifBlank { null },
                            employeeCount = state.employeeCount.toIntOrNull() ?: 0,
                            currency = state.currency,
                            timezone = state.timezone,
                            recordingMethod = state.recordingMethod,
                            paymentMethods = state.paymentMethods.toList(),
                            openingBalance = state.openingBalance.ifBlank { "0" },
                            hasProductsAndStock = state.hasProducts,
                            device =
                                DeviceDto(
                                    deviceId = deviceId,
                                    deviceName = Build.MODEL.take(100),
                                    appVersion = BuildConfig.VERSION_NAME,
                                ),
                        ),
                )
            sessionStore.save(
                AppSession(
                    businessId = result.businessId,
                    accessToken = result.tokens.accessToken,
                    refreshToken = result.tokens.refreshToken,
                ),
            )
            state.logoUri?.let { value ->
                val uri = android.net.Uri.parse(value)
                val bytes =
                    context.contentResolver.openInputStream(uri)?.use(InputStream::readLogoBytes)
                        ?: throw IOException("Logo tidak dapat dibaca")
                val contentType = context.contentResolver.getType(uri) ?: "image/jpeg"
                val body = bytes.toRequestBody(contentType.toMediaTypeOrNull())
                api.uploadLogo(
                    businessId = result.businessId,
                    authorization = "Bearer ${result.tokens.accessToken}",
                    logo = MultipartBody.Part.createFormData("logo", "logo-usaha", body),
                )
            }
            return result
        }
    }

private fun InputStream.readLogoBytes(): ByteArray {
    val output = ByteArrayOutputStream()
    val buffer = ByteArray(8 * 1024)
    var total = 0
    while (true) {
        val count = read(buffer)
        if (count < 0) break
        total += count
        if (total > MAX_LOGO_BYTES) {
            throw OnboardingInputException("Ukuran logo paling besar 2 MB.")
        }
        output.write(buffer, 0, count)
    }
    return output.toByteArray()
}
