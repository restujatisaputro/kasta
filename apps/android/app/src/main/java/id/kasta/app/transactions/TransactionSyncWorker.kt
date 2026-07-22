package id.kasta.app.transactions

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class TransactionSyncWorker
    @AssistedInject
    constructor(
        @Assisted context: Context,
        @Assisted parameters: WorkerParameters,
        private val repository: TransactionRepository,
    ) : CoroutineWorker(context, parameters) {
        override suspend fun doWork(): Result =
            when (decideSyncWork(repository.syncPending())) {
                SyncWorkDecision.SUCCESS -> Result.success()
                SyncWorkDecision.RETRY -> Result.retry()
            }
    }
