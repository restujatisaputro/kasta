package id.kasta.app.data.session

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import dagger.hilt.android.qualifiers.ApplicationContext
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.inject.Inject
import javax.inject.Singleton

data class AppSession(
    val businessId: String,
    val accessToken: String,
    val refreshToken: String,
)

@Singleton
class SessionStore
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) {
        private val preferences =
            context.getSharedPreferences("kasta_session", Context.MODE_PRIVATE)
        private val cipher = SessionCipher()

        init {
            migrateLegacySession()
        }

        @Synchronized
        fun get(): AppSession? {
            val encrypted = preferences.getString(ENCRYPTED_SESSION, null) ?: return null
            return runCatching {
                val payload = JSONObject(cipher.decrypt(encrypted))
                AppSession(
                    businessId = payload.getString("business_id"),
                    accessToken = payload.getString("access_token"),
                    refreshToken = payload.getString("refresh_token"),
                )
            }.getOrElse {
                clear()
                null
            }
        }

        @Synchronized
        fun save(session: AppSession) {
            val payload =
                JSONObject()
                    .put("business_id", session.businessId)
                    .put("access_token", session.accessToken)
                    .put("refresh_token", session.refreshToken)
            preferences.edit()
                .putString(ENCRYPTED_SESSION, cipher.encrypt(payload.toString()))
                .remove(LEGACY_BUSINESS_ID)
                .remove(LEGACY_ACCESS_TOKEN)
                .remove(LEGACY_REFRESH_TOKEN)
                .apply()
        }

        @Synchronized
        fun clear() =
            preferences.edit()
                .remove(ENCRYPTED_SESSION)
                .remove(LEGACY_BUSINESS_ID)
                .remove(LEGACY_ACCESS_TOKEN)
                .remove(LEGACY_REFRESH_TOKEN)
                .apply()

        fun lastSync(): String? = preferences.getString("last_transaction_sync", null)

        fun saveLastSync(value: String) = preferences.edit().putString("last_transaction_sync", value).apply()

        private fun migrateLegacySession() {
            if (preferences.contains(ENCRYPTED_SESSION)) return
            val businessId = preferences.getString(LEGACY_BUSINESS_ID, null) ?: return
            val accessToken = preferences.getString(LEGACY_ACCESS_TOKEN, null) ?: return
            val refreshToken = preferences.getString(LEGACY_REFRESH_TOKEN, null) ?: return
            save(AppSession(businessId, accessToken, refreshToken))
        }

        private companion object {
            const val ENCRYPTED_SESSION = "encrypted_session_v1"
            const val LEGACY_BUSINESS_ID = "business_id"
            const val LEGACY_ACCESS_TOKEN = "access_token"
            const val LEGACY_REFRESH_TOKEN = "refresh_token"
        }
    }

private class SessionCipher {
    private val keyStore =
        KeyStore.getInstance(KEY_STORE).apply {
            load(null)
        }

    fun encrypt(plaintext: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val iv = Base64.encodeToString(cipher.iv, Base64.NO_WRAP)
        val ciphertext =
            Base64.encodeToString(cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        return "$VERSION.$iv.$ciphertext"
    }

    fun decrypt(encoded: String): String {
        val parts = encoded.split('.', limit = 3)
        require(parts.size == 3 && parts[0] == VERSION) { "Format session terenkripsi tidak valid" }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            secretKey(),
            GCMParameterSpec(GCM_TAG_BITS, Base64.decode(parts[1], Base64.NO_WRAP)),
        )
        return String(cipher.doFinal(Base64.decode(parts[2], Base64.NO_WRAP)), Charsets.UTF_8)
    }

    private fun secretKey(): SecretKey {
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEY_STORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build(),
            )
            generateKey()
        }
    }

    private companion object {
        const val KEY_STORE = "AndroidKeyStore"
        const val KEY_ALIAS = "kasta_session_aes_v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
        const val VERSION = "v1"
    }
}
