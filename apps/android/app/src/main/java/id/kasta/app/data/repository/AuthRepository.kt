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
        fun hasSession(): Boolean = sessionStore.get() != null

        suspend fun login(
            businessId: String,
            identifier: String,
            password: String,
        ) {
            val response =
                authApi.login(
                    LoginRequest(
                        businessId = businessId,
                        identifier = identifier,
                        password = password,
                        deviceId = syncPreferences.deviceId(),
                        deviceName = "${Build.MANUFACTURER} ${Build.MODEL}",
                        appVersion = BuildConfig.VERSION_NAME,
                    ),
                )
            sessionStore.save(
                AppSession(
                    businessId = businessId,
                    accessToken = response.accessToken,
                    refreshToken = response.refreshToken,
                ),
            )
        }

        fun logout() = sessionStore.clear()
    }
