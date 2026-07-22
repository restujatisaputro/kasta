package id.kasta.app.di

import android.content.Context
import androidx.room.Room
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import id.kasta.app.BuildConfig
import id.kasta.app.data.local.KastaDatabase
import id.kasta.app.data.local.NotificationDao
import id.kasta.app.data.local.OnboardingDraftDao
import id.kasta.app.data.local.TransactionDao
import id.kasta.app.data.remote.AuthApi
import id.kasta.app.data.remote.InventoryApi
import id.kasta.app.data.remote.MentorAccessApi
import id.kasta.app.data.remote.NotificationApi
import id.kasta.app.data.remote.ObligationApi
import id.kasta.app.data.remote.OnboardingApi
import id.kasta.app.data.remote.ReceiptScanApi
import id.kasta.app.data.remote.ReportApi
import id.kasta.app.data.remote.SyncApi
import id.kasta.app.data.remote.TransactionApi
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    private val migration1To2 =
        object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS transactions (
                        localId TEXT NOT NULL PRIMARY KEY,
                        serverId TEXT,
                        businessId TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        targetServerId TEXT,
                        entryKind TEXT NOT NULL,
                        transactionDate TEXT NOT NULL,
                        amountRupiah INTEGER NOT NULL,
                        categoryAccount TEXT,
                        counterpartyName TEXT,
                        paymentMethod TEXT NOT NULL,
                        note TEXT NOT NULL,
                        receiptUri TEXT,
                        recurrenceFrequency TEXT,
                        recurrenceInterval INTEGER,
                        revisionReason TEXT,
                        syncState TEXT NOT NULL,
                        serverStatus TEXT NOT NULL,
                        errorMessage TEXT,
                        createdAt INTEGER NOT NULL,
                        updatedAt INTEGER NOT NULL
                    )
                    """.trimIndent(),
                )
                database.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_transactions_businessId_syncState " +
                        "ON transactions (businessId, syncState)",
                )
                database.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_transactions_businessId_transactionDate " +
                        "ON transactions (businessId, transactionDate)",
                )
            }
        }

    private val migration2To3 =
        object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL(
                    """
                    CREATE TABLE transactions_v3 (
                        localId TEXT NOT NULL PRIMARY KEY,
                        serverId TEXT,
                        businessId TEXT NOT NULL,
                        deviceId TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        syncStatus TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        entryKind TEXT NOT NULL,
                        transactionDate TEXT NOT NULL,
                        amountRupiah INTEGER NOT NULL,
                        categoryAccount TEXT,
                        counterpartyName TEXT,
                        paymentMethod TEXT NOT NULL,
                        note TEXT NOT NULL,
                        receiptUri TEXT,
                        recurrenceFrequency TEXT,
                        recurrenceInterval INTEGER,
                        revisionReason TEXT,
                        isDraft INTEGER NOT NULL,
                        serverStatus TEXT NOT NULL,
                        errorMessage TEXT,
                        conflictId TEXT,
                        conflictServerVersion INTEGER,
                        conflictServerPayload TEXT,
                        createdAt INTEGER NOT NULL,
                        updatedAt INTEGER NOT NULL,
                        deletedAt INTEGER
                    )
                    """.trimIndent(),
                )
                database.execSQL(
                    """
                    INSERT INTO transactions_v3 (
                        localId, serverId, businessId, deviceId, version, syncStatus,
                        operation, entryKind, transactionDate, amountRupiah,
                        categoryAccount, counterpartyName, paymentMethod, note,
                        receiptUri, recurrenceFrequency, recurrenceInterval,
                        revisionReason, isDraft, serverStatus, errorMessage,
                        createdAt, updatedAt
                    )
                    SELECT localId, serverId, businessId, '',
                        CASE WHEN serverId IS NULL THEN 0 ELSE 1 END,
                        CASE WHEN syncState = 'DRAFT' THEN 'PENDING' ELSE syncState END,
                        operation, entryKind, transactionDate, amountRupiah,
                        categoryAccount, counterpartyName, paymentMethod, note,
                        receiptUri, recurrenceFrequency, recurrenceInterval,
                        revisionReason, CASE WHEN syncState = 'DRAFT' THEN 1 ELSE 0 END,
                        serverStatus, errorMessage, createdAt, updatedAt
                    FROM transactions
                    """.trimIndent(),
                )
                database.execSQL("DROP TABLE transactions")
                database.execSQL("ALTER TABLE transactions_v3 RENAME TO transactions")
                database.execSQL(
                    "CREATE INDEX index_transactions_businessId_syncStatus " +
                        "ON transactions (businessId, syncStatus)",
                )
                database.execSQL(
                    "CREATE INDEX index_transactions_businessId_transactionDate " +
                        "ON transactions (businessId, transactionDate)",
                )
                database.execSQL(
                    "CREATE UNIQUE INDEX index_transactions_businessId_serverId " +
                        "ON transactions (businessId, serverId)",
                )
            }
        }

    private val migration3To4 =
        object : Migration(3, 4) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        localId TEXT NOT NULL PRIMARY KEY,
                        serverId TEXT NOT NULL,
                        businessId TEXT NOT NULL,
                        category TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        entityType TEXT NOT NULL,
                        entityId TEXT NOT NULL,
                        actionPath TEXT,
                        availableAt TEXT,
                        readAt TEXT,
                        createdAt TEXT NOT NULL
                    )
                    """.trimIndent(),
                )
                database.execSQL(
                    "CREATE INDEX IF NOT EXISTS index_notifications_businessId_readAt_createdAt " +
                        "ON notifications (businessId, readAt, createdAt)",
                )
                database.execSQL(
                    "CREATE UNIQUE INDEX IF NOT EXISTS index_notifications_businessId_serverId " +
                        "ON notifications (businessId, serverId)",
                )
            }
        }

    @Provides
    @Singleton
    fun database(
        @ApplicationContext context: Context,
    ): KastaDatabase =
        Room.databaseBuilder(context, KastaDatabase::class.java, "kasta.db")
            .addMigrations(migration1To2, migration2To3, migration3To4)
            .build()

    @Provides
    fun onboardingDraftDao(database: KastaDatabase): OnboardingDraftDao = database.onboardingDraftDao()

    @Provides
    fun transactionDao(database: KastaDatabase): TransactionDao = database.transactionDao()

    @Provides
    fun notificationDao(database: KastaDatabase): NotificationDao = database.notificationDao()

    @Provides
    @Singleton
    fun retrofit(): Retrofit {
        val logging =
            HttpLoggingInterceptor().apply {
                level =
                    if (BuildConfig.DEBUG) {
                        HttpLoggingInterceptor.Level.BASIC
                    } else {
                        HttpLoggingInterceptor.Level.NONE
                    }
            }
        val client = OkHttpClient.Builder().addInterceptor(logging).build()
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    fun onboardingApi(retrofit: Retrofit): OnboardingApi = retrofit.create(OnboardingApi::class.java)

    @Provides
    fun authApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides
    fun transactionApi(retrofit: Retrofit): TransactionApi = retrofit.create(TransactionApi::class.java)

    @Provides
    fun syncApi(retrofit: Retrofit): SyncApi = retrofit.create(SyncApi::class.java)

    @Provides
    fun receiptScanApi(retrofit: Retrofit): ReceiptScanApi = retrofit.create(ReceiptScanApi::class.java)

    @Provides
    fun inventoryApi(retrofit: Retrofit): InventoryApi = retrofit.create(InventoryApi::class.java)

    @Provides
    fun obligationApi(retrofit: Retrofit): ObligationApi = retrofit.create(ObligationApi::class.java)

    @Provides
    fun reportApi(retrofit: Retrofit): ReportApi = retrofit.create(ReportApi::class.java)

    @Provides
    fun mentorAccessApi(retrofit: Retrofit): MentorAccessApi = retrofit.create(MentorAccessApi::class.java)

    @Provides
    fun notificationApi(retrofit: Retrofit): NotificationApi = retrofit.create(NotificationApi::class.java)
}
