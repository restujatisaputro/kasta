package id.kasta.app.data.session

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

private val Context.syncDataStore by preferencesDataStore(name = "kasta_sync")

data class LocalSyncState(
    val deviceId: String,
    val cursor: Long,
    val lastSyncAt: String?,
)

@Singleton
class SyncPreferences
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        private val deviceIdKey = stringPreferencesKey("device_id")

        suspend fun deviceId(): String {
            context.syncDataStore.data.first()[deviceIdKey]?.let { return it }
            val generated = "android-${UUID.randomUUID()}"
            context.syncDataStore.edit { it[deviceIdKey] = generated }
            return generated
        }

        suspend fun cursor(businessId: String): Long = context.syncDataStore.data.first()[longPreferencesKey("cursor_$businessId")] ?: 0L

        suspend fun saveCursor(
            businessId: String,
            cursor: Long,
            serverTime: String,
        ) {
            context.syncDataStore.edit {
                it[longPreferencesKey("cursor_$businessId")] = cursor
                it[stringPreferencesKey("last_sync_$businessId")] = serverTime
            }
        }

        fun observe(businessId: String): Flow<LocalSyncState> =
            context.syncDataStore.data.map { values ->
                LocalSyncState(
                    deviceId = values[deviceIdKey].orEmpty(),
                    cursor = values[longPreferencesKey("cursor_$businessId")] ?: 0L,
                    lastSyncAt = values[stringPreferencesKey("last_sync_$businessId")],
                )
            }
    }
