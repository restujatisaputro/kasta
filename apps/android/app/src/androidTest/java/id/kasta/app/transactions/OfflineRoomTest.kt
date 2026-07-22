package id.kasta.app.transactions

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import id.kasta.app.data.local.KastaDatabase
import id.kasta.app.data.local.SyncStatus
import id.kasta.app.data.local.TransactionEntity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class OfflineRoomTest {
    private lateinit var database: KastaDatabase

    @Before
    fun createDatabase() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database =
            Room.inMemoryDatabaseBuilder(context, KastaDatabase::class.java)
                .allowMainThreadQueries()
                .build()
    }

    @After
    fun closeDatabase() = database.close()

    @Test
    fun transaksiOfflineDisimpanDanDiklaimWorker() =
        runBlocking {
            val entity =
                TransactionEntity(
                    localId = "offline-room-1",
                    businessId = "business-room",
                    deviceId = "android-room-device",
                    entryKind = "INCOME",
                    transactionDate = "2026-07-22",
                    amountRupiah = 42_000,
                )

            database.transactionDao().upsert(entity)

            val visible = database.transactionDao().observeAll("business-room").first()
            assertEquals(1, visible.size)
            assertEquals(SyncStatus.PENDING.name, visible.single().syncStatus)

            val claimed = database.transactionDao().claimPending("business-room")
            assertEquals(1, claimed.size)
            assertEquals(SyncStatus.SYNCING.name, claimed.single().syncStatus)
        }
}
