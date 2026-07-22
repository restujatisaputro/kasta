package id.kasta.app.data.local

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.appDataStore by preferencesDataStore(name = "kasta_preferences")

data class AppPreferenceState(
    val darkMode: Boolean = false,
    val notificationsEnabled: Boolean = true,
    val enabledNotificationCategories: Set<String> = DEFAULT_NOTIFICATION_CATEGORIES,
    val reminderHour: Int = 18,
    val reminderMinute: Int = 0,
    val quietHoursEnabled: Boolean = false,
    val quietStart: String = "21:00",
    val quietEnd: String = "07:00",
)

val DEFAULT_NOTIFICATION_CATEGORIES =
    setOf(
        "NO_TRANSACTION_TODAY",
        "PAYABLE_DUE_SOON",
        "RECEIVABLE_DUE_SOON",
        "LOW_STOCK",
        "OCR_NEEDS_REVIEW",
        "SYNC_FAILED",
        "MENTOR_ACCESS_REQUEST",
        "NEW_RECOMMENDATION",
        "MENTORING_SCHEDULE",
        "MONTHLY_REPORT_AVAILABLE",
    )

@Singleton
class AppPreferences
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        private val darkModeKey = booleanPreferencesKey("dark_mode")
        private val notificationsKey = booleanPreferencesKey("notifications_enabled")
        private val categoriesKey = stringSetPreferencesKey("notification_categories")
        private val reminderHourKey = intPreferencesKey("notification_reminder_hour")
        private val reminderMinuteKey = intPreferencesKey("notification_reminder_minute")
        private val quietEnabledKey = booleanPreferencesKey("notification_quiet_enabled")
        private val quietStartKey = stringPreferencesKey("notification_quiet_start")
        private val quietEndKey = stringPreferencesKey("notification_quiet_end")
        private val lastLocalReminderKey = stringPreferencesKey("last_local_transaction_reminder")

        val state: Flow<AppPreferenceState> =
            context.appDataStore.data.map { values ->
                AppPreferenceState(
                    darkMode = values[darkModeKey] ?: false,
                    notificationsEnabled = values[notificationsKey] ?: true,
                    enabledNotificationCategories =
                        values[categoriesKey] ?: DEFAULT_NOTIFICATION_CATEGORIES,
                    reminderHour = values[reminderHourKey] ?: 18,
                    reminderMinute = values[reminderMinuteKey] ?: 0,
                    quietHoursEnabled = values[quietEnabledKey] ?: false,
                    quietStart = values[quietStartKey] ?: "21:00",
                    quietEnd = values[quietEndKey] ?: "07:00",
                )
            }

        suspend fun setDarkMode(enabled: Boolean) {
            context.appDataStore.edit { it[darkModeKey] = enabled }
        }

        suspend fun setNotifications(enabled: Boolean) {
            context.appDataStore.edit { it[notificationsKey] = enabled }
        }

        suspend fun setCategory(
            category: String,
            enabled: Boolean,
        ) {
            context.appDataStore.edit { values ->
                val categories = (values[categoriesKey] ?: DEFAULT_NOTIFICATION_CATEGORIES).toMutableSet()
                if (enabled) categories.add(category) else categories.remove(category)
                values[categoriesKey] = categories
            }
        }

        suspend fun setReminderTime(
            hour: Int,
            minute: Int,
        ) {
            context.appDataStore.edit {
                it[reminderHourKey] = hour.coerceIn(0, 23)
                it[reminderMinuteKey] = minute.coerceIn(0, 59)
            }
        }

        suspend fun setQuietHours(
            enabled: Boolean,
            start: String,
            end: String,
        ) {
            context.appDataStore.edit {
                it[quietEnabledKey] = enabled
                it[quietStartKey] = start
                it[quietEndKey] = end
            }
        }

        suspend fun lastLocalReminderDate(): String? = context.appDataStore.data.map { it[lastLocalReminderKey] }.first()

        suspend fun setLastLocalReminderDate(value: String) {
            context.appDataStore.edit { it[lastLocalReminderKey] = value }
        }
    }
