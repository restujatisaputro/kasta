package id.kasta.app.notifications

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.data.local.AppPreferences
import id.kasta.app.data.local.NotificationEntity
import id.kasta.app.data.local.TransactionDao
import id.kasta.app.data.session.SessionStore
import kotlinx.coroutines.flow.first
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@HiltWorker
class NotificationPullWorker
    @AssistedInject
    constructor(
        @Assisted context: Context,
        @Assisted parameters: WorkerParameters,
        private val repository: NotificationRepository,
        private val preferences: AppPreferences,
        private val notifications: KastaNotificationManager,
    ) : CoroutineWorker(context, parameters) {
        override suspend fun doWork(): Result =
            try {
                repository.refresh()
                val settings = preferences.state.first()
                if (settings.notificationsEnabled) {
                    repository.unread()
                        .filter { it.category in settings.enabledNotificationCategories }
                        .filter { it.availableAt == null || Instant.parse(it.availableAt) <= Instant.now() }
                        .forEach(notifications::show)
                }
                Result.success()
            } catch (_: Exception) {
                Result.retry()
            }
    }

@HiltWorker
class LocalTransactionReminderWorker
    @AssistedInject
    constructor(
        @Assisted context: Context,
        @Assisted parameters: WorkerParameters,
        private val sessions: SessionStore,
        private val transactions: TransactionDao,
        private val preferences: AppPreferences,
        private val notifications: KastaNotificationManager,
    ) : CoroutineWorker(context, parameters) {
        override suspend fun doWork(): Result {
            val session = sessions.get() ?: return Result.success()
            val settings = preferences.state.first()
            val today = LocalDate.now().toString()
            val now = LocalTime.now()
            val due = LocalTime.of(settings.reminderHour, settings.reminderMinute)
            if (
                !settings.notificationsEnabled ||
                "NO_TRANSACTION_TODAY" !in settings.enabledNotificationCategories ||
                now < due ||
                isQuiet(now, settings.quietHoursEnabled, settings.quietStart, settings.quietEnd) ||
                preferences.lastLocalReminderDate() == today ||
                transactions.countPostedOn(session.businessId, today) > 0
            ) {
                return Result.success()
            }
            notifications.show(
                NotificationEntity(
                    localId = "local-no-transaction-$today",
                    serverId = "local-no-transaction-$today",
                    businessId = session.businessId,
                    category = "NO_TRANSACTION_TODAY",
                    title = "Belum ada catatan hari ini",
                    message = "Catat uang masuk atau uang keluar agar laporan tetap lengkap.",
                    entityType = "BUSINESS",
                    entityId = session.businessId,
                    actionPath = "/transaksi",
                    availableAt = null,
                    readAt = null,
                    createdAt = Instant.now().toString(),
                ),
            )
            preferences.setLastLocalReminderDate(today)
            return Result.success()
        }
    }

fun isQuiet(
    now: LocalTime,
    enabled: Boolean,
    startValue: String,
    endValue: String,
): Boolean {
    if (!enabled) return false
    val start = LocalTime.parse(startValue)
    val end = LocalTime.parse(endValue)
    return if (start < end) now >= start && now < end else now >= start || now < end
}

@Singleton
class NotificationScheduler
    @Inject
    constructor(
        @ApplicationContext private val context: Context,
    ) {
        fun schedule() {
            val networkRequest =
                PeriodicWorkRequestBuilder<NotificationPullWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(
                        Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build(),
                    ).build()
            val localRequest =
                PeriodicWorkRequestBuilder<LocalTransactionReminderWorker>(15, TimeUnit.MINUTES)
                    .build()
            val manager = WorkManager.getInstance(context)
            manager.enqueueUniquePeriodicWork(
                "kasta-notification-pull",
                ExistingPeriodicWorkPolicy.UPDATE,
                networkRequest,
            )
            manager.enqueueUniquePeriodicWork(
                "kasta-local-reminders",
                ExistingPeriodicWorkPolicy.UPDATE,
                localRequest,
            )
        }
    }
