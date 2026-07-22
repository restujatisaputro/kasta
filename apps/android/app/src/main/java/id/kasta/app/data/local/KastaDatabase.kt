package id.kasta.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [OnboardingDraftEntity::class, TransactionEntity::class, NotificationEntity::class],
    version = 4,
    exportSchema = true,
)
abstract class KastaDatabase : RoomDatabase() {
    abstract fun onboardingDraftDao(): OnboardingDraftDao

    abstract fun transactionDao(): TransactionDao

    abstract fun notificationDao(): NotificationDao
}
