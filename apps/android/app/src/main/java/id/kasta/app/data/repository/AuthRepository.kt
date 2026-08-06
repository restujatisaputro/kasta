package id.kasta.app.data.repository

import android.os.Build
import id.kasta.app.BuildConfig
import id.kasta.app.data.remote.AuthApi
import id.kasta.app.data.remote.LoginRequest
import id.kasta.app.data.session.AppSession
import id.kasta.app.data.session.SessionStore
import id.kasta.app.data.session.SyncPreferences
import javax.inject.Inject

class AuthRepository
    @Inject
    constructor(
        private val authApi: AuthApi,
        private val sessionStore: SessionStore,
        private val syncPreferences: SyncPreferences,
    ) {
        fun hasSession(): Boolean = sessionStore.get()?.businessId?.isNotBlank() == true

        suspend fun login(
            identifier: String,
            password: String,
        ) {
            val response =
                authApi.login(
                    LoginRequest(
                        identifier = identifier,
                        password = password,
                        deviceId = syncPreferences.deviceId(),
                        deviceName = "${Build.MANUFACTURER} ${Build.MODEL}",
                        appVersion = BuildConfig.VERSION_NAME,
                    ),
                )
            sessionStore.save(
                AppSession(
                    businessId = "",
                    accessToken = response.accessToken,
                    refreshToken = response.refreshToken,
                ),
            )
        }

        fun hasPendingBusinessSelection(): Boolean = sessionStore.get()?.businessId?.isBlank() == true

        suspend fun businesses() =
            sessionStore.get()?.let { session ->
                authApi.businesses("Bearer ${session.accessToken}")
            } ?: emptyList()

        suspend fun selectBusiness(businessId: String) {
            val session = sessionStore.get() ?: error("Sesi tidak ditemukan.")
            val response = authApi.selectBusiness(businessId, "Bearer ${session.accessToken}")
            sessionStore.save(session.copy(businessId = businessId, accessToken = response.accessToken))
        }

        fun logout() = sessionStore.clear()
    }
