package id.kasta.app.transactions

import android.content.Context
import android.net.Uri
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.google.gson.Gson
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.data.local.SyncCountRow
import id.kasta.app.data.local.SyncStatus
import id.kasta.app.data.local.TransactionDao
import id.kasta.app.data.local.TransactionEntity
import id.kasta.app.data.remote.RefreshTokenRequest
import id.kasta.app.data.remote.SyncApi
import id.kasta.app.data.remote.SyncPullChangeDto
import id.kasta.app.data.remote.SyncPullRequestDto
import id.kasta.app.data.remote.SyncPushOperationDto
import id.kasta.app.data.remote.SyncPushRequestDto
import id.kasta.app.data.remote.SyncPushResponseDto
import id.kasta.app.data.remote.TransactionApi
import id.kasta.app.data.session.AppSession
import id.kasta.app.data.session.SessionStore
import id.kasta.app.data.session.SyncPreferences
import kotlinx.coroutines.flow.Flow
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import java.io.ByteArrayOutputStream
import java.time.Instant
import java.util.UUID
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

private const val MAX_RECEIPT_BYTES = 8 * 1024 * 1024

@Singleton
class TransactionRepository
    @Inject
    constructor(
        private val dao: TransactionDao,
        private val syncApi: SyncApi,
        private val transactionApi: TransactionApi,
        private val sessionStore: SessionStore,
        private val syncPreferences: SyncPreferences,
        @ApplicationContext private val context: Context,
    ) {
        private val gson = Gson()

        fun observe(businessId: String): Flow<List<TransactionEntity>> = dao.observeAll(businessId)

        fun observeSyncCounts(businessId: String): Flow<List<SyncCountRow>> = dao.observeSyncCounts(businessId)

        fun observeConflicts(businessId: String): Flow<List<TransactionEntity>> = dao.observeConflicts(businessId)

        fun observeSyncMetadata(businessId: String) = syncPreferences.observe(businessId)

        suspend fun lastExpenseCategory(businessId: String): String? = dao.lastExpenseCategory(businessId)

        suspend fun save(
            input: TransactionForm,
            asDraft: Boolean,
            targetServerId: String? = null,
            operation: String = "CREATE",
        ): TransactionEntity {
            val session = sessionStore.get() ?: throw IllegalStateException("Sesi tidak tersedia")
            val deviceId = syncPreferences.deviceId()
            val now = System.currentTimeMillis()
            val existing = targetServerId?.let { dao.findByServerId(session.businessId, it) }
            val action =
                when (operation) {
                    "REVISE" -> "UPSERT"
                    "REVERSE" -> "DELETE"
                    else -> "CREATE"
                }
            val entity =
                TransactionEntity(
                    localId = existing?.localId ?: UUID.randomUUID().toString(),
                    serverId = existing?.serverId ?: targetServerId,
                    businessId = session.businessId,
                    deviceId = deviceId,
                    version = existing?.version ?: 0,
                    syncStatus = SyncStatus.PENDING.name,
                    operation = action,
                    entryKind = input.entryKind,
                    transactionDate = input.transactionDate,
                    amountRupiah = input.amountDigits.toLongOrNull() ?: 0,
                    categoryAccount = input.categoryAccount.ifBlank { null },
                    counterpartyName = input.counterpartyName.trim().ifBlank { null },
                    paymentMethod = input.paymentMethod,
                    note = input.note.trim(),
                    receiptUri = input.receiptUri ?: existing?.receiptUri,
                    recurrenceFrequency = input.recurrenceFrequency.takeIf { input.recurring },
                    recurrenceInterval = input.recurrenceInterval.takeIf { input.recurring },
                    revisionReason = input.revisionReason.trim().ifBlank { null },
                    isDraft = asDraft,
                    serverStatus = existing?.serverStatus ?: "POSTED",
                    createdAt = existing?.createdAt ?: now,
                    updatedAt = now,
                    deletedAt = if (action == "DELETE") now else null,
                )
            dao.upsert(entity)
            if (!asDraft) enqueueSync()
            return entity
        }

        suspend fun postDraft(entity: TransactionEntity) {
            dao.upsert(
                entity.copy(
                    operation = "CREATE",
                    isDraft = false,
                    syncStatus = SyncStatus.PENDING.name,
                    updatedAt = System.currentTimeMillis(),
                ),
            )
            enqueueSync()
        }

        suspend fun syncPending(): Boolean {
            val originalSession = sessionStore.get() ?: return false
            val claimed = dao.claimPending(originalSession.businessId)
            return try {
                var session = originalSession
                if (claimed.isNotEmpty()) {
                    val response =
                        try {
                            push(session, claimed)
                        } catch (error: HttpException) {
                            if (error.code() != 401) throw error
                            session = refresh(session)
                            push(session, claimed)
                        }
                    applyPushResults(session, claimed, response)
                }
                try {
                    pullAll(session)
                } catch (error: HttpException) {
                    if (error.code() != 401) throw error
                    session = refresh(session)
                    pullAll(session)
                }
                true
            } catch (error: Exception) {
                if (claimed.isNotEmpty()) {
                    dao.releaseForRetry(
                        claimed.map { it.localId },
                        error.message ?: "Jaringan terputus. Akan dicoba lagi.",
                    )
                }
                false
            }
        }

        suspend fun resolveConflictWithServer(entity: TransactionEntity) {
            val payload = entity.conflictServerPayload ?: return

            @Suppress("UNCHECKED_CAST")
            val values = gson.fromJson(payload, Map::class.java) as Map<String, Any?>
            dao.upsert(
                entity.fromCanonicalPayload(values).copy(
                    syncStatus = SyncStatus.SYNCED.name,
                    version = entity.conflictServerVersion ?: entity.version,
                    conflictId = null,
                    conflictServerVersion = null,
                    conflictServerPayload = null,
                    errorMessage = null,
                    deletedAt = null,
                    updatedAt = System.currentTimeMillis(),
                ),
            )
        }

        suspend fun resolveConflictWithLocal(entity: TransactionEntity) {
            dao.resolveWithLocal(
                entity.localId,
                entity.conflictServerVersion ?: entity.version,
                "Pengguna memilih data dari perangkat ini",
            )
            enqueueSync()
        }

        fun enqueueSync() {
            val request =
                OneTimeWorkRequestBuilder<TransactionSyncWorker>()
                    .setConstraints(
                        Constraints.Builder()
                            .setRequiredNetworkType(NetworkType.CONNECTED)
                            .build(),
                    ).setBackoffCriteria(
                        BackoffPolicy.EXPONENTIAL,
                        30,
                        TimeUnit.SECONDS,
                    ).build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                "kasta-offline-sync",
                ExistingWorkPolicy.KEEP,
                request,
            )
        }

        private suspend fun push(
            session: AppSession,
            rows: List<TransactionEntity>,
        ): SyncPushResponseDto {
            val request =
                SyncPushRequestDto(
                    businessId = session.businessId,
                    deviceId = syncPreferences.deviceId(),
                    batchId = "batch-${UUID.randomUUID()}",
                    operations = rows.map(TransactionEntity::toPushOperation),
                )
            return syncApi.push("Bearer ${session.accessToken}", request)
        }

        private suspend fun applyPushResults(
            session: AppSession,
            claimed: List<TransactionEntity>,
            response: SyncPushResponseDto,
        ) {
            response.results.forEach { result ->
                val local = claimed.firstOrNull { it.localId == result.localId } ?: return@forEach
                when (result.status) {
                    SyncStatus.SYNCED.name -> {
                        if (local.receiptUri != null && result.serverId != null) {
                            uploadReceipt(session, result.serverId, local.receiptUri)
                        }
                        dao.markSynced(
                            local.localId,
                            result.serverId,
                            result.serverVersion ?: local.version,
                            result.deletedAt?.let(::parseEpoch),
                        )
                    }
                    SyncStatus.CONFLICT.name ->
                        dao.markConflict(
                            localId = local.localId,
                            serverId = result.serverId ?: local.serverId.orEmpty(),
                            conflictId = result.conflictId,
                            serverVersion = result.serverVersion ?: local.version,
                            serverPayload = gson.toJson(result.canonicalPayload.orEmpty()),
                            message = result.message ?: "Perlu memilih versi transaksi.",
                        )
                    else ->
                        dao.markFailed(
                            local.localId,
                            result.message ?: "Transaksi ditolak server.",
                        )
                }
            }
        }

        private suspend fun pullAll(session: AppSession) {
            val deviceId = syncPreferences.deviceId()
            var cursor = syncPreferences.cursor(session.businessId)
            var hasMore: Boolean
            do {
                val response =
                    syncApi.pull(
                        "Bearer ${session.accessToken}",
                        SyncPullRequestDto(session.businessId, deviceId, cursor),
                    )
                response.changes
                    .filter { it.entityType == "TRANSACTION" }
                    .forEach { applyChange(session.businessId, deviceId, it) }
                cursor = response.nextCursor
                syncPreferences.saveCursor(session.businessId, cursor, response.serverTime)
                hasMore = response.hasMore
            } while (hasMore)
        }

        private suspend fun applyChange(
            businessId: String,
            deviceId: String,
            change: SyncPullChangeDto,
        ) {
            val existing = dao.findByServerId(businessId, change.serverId)
            if (
                existing != null &&
                existing.syncStatus in setOf(SyncStatus.PENDING.name, SyncStatus.SYNCING.name) &&
                change.version > existing.version
            ) {
                dao.markConflict(
                    localId = existing.localId,
                    serverId = change.serverId,
                    conflictId = null,
                    serverVersion = change.version,
                    serverPayload = gson.toJson(change.payload),
                    message = "Data berubah di perangkat lain.",
                )
                return
            }
            val base =
                existing ?: TransactionEntity(
                    localId = "server:${change.serverId}",
                    serverId = change.serverId,
                    businessId = businessId,
                    deviceId = deviceId,
                    entryKind = "INCOME",
                    transactionDate = "",
                    amountRupiah = 0,
                )
            dao.upsert(
                base.fromCanonicalPayload(change.payload).copy(
                    serverId = change.serverId,
                    version = change.version,
                    syncStatus = SyncStatus.SYNCED.name,
                    serverStatus =
                        if (change.action == "DELETE") {
                            "REVERSED"
                        } else {
                            change.payload["server_status"]?.toString() ?: "POSTED"
                        },
                    deletedAt = if (change.action == "DELETE") parseEpoch(change.changedAt) else null,
                    updatedAt = parseEpoch(change.changedAt),
                ),
            )
        }

        private suspend fun refresh(session: AppSession): AppSession {
            val tokens = transactionApi.refresh(RefreshTokenRequest(session.refreshToken))
            return AppSession(session.businessId, tokens.accessToken, tokens.refreshToken).also {
                sessionStore.save(it)
            }
        }

        private suspend fun uploadReceipt(
            session: AppSession,
            transactionId: String,
            uriValue: String,
        ) {
            val uri = Uri.parse(uriValue)
            val bytes =
                context.contentResolver.openInputStream(uri)?.use { stream ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(8 * 1024)
                    var total = 0
                    while (true) {
                        val read = stream.read(buffer)
                        if (read < 0) break
                        total += read
                        require(total <= MAX_RECEIPT_BYTES) { "Foto bukti paling besar 8 MB." }
                        output.write(buffer, 0, read)
                    }
                    output.toByteArray()
                } ?: return
            val contentType = context.contentResolver.getType(uri) ?: "image/jpeg"
            transactionApi.uploadReceipt(
                businessId = session.businessId,
                transactionId = transactionId,
                authorization = "Bearer ${session.accessToken}",
                photo =
                    MultipartBody.Part.createFormData(
                        "photo",
                        "bukti-${UUID.randomUUID()}.jpg",
                        bytes.toRequestBody(contentType.toMediaTypeOrNull()),
                    ),
            )
        }

        private fun parseEpoch(value: String): Long =
            runCatching { Instant.parse(value).toEpochMilli() }.getOrDefault(System.currentTimeMillis())
    }

private fun TransactionEntity.toPushOperation(): SyncPushOperationDto =
    SyncPushOperationDto(
        operationId = "$localId:$updatedAt",
        action = operation,
        localId = localId,
        serverId = serverId,
        baseVersion = version,
        changedAt = Instant.ofEpochMilli(updatedAt).toString(),
        payload =
            if (operation == "DELETE") {
                mapOf("reason" to (revisionReason ?: "Dibatalkan dari perangkat"))
            } else {
                mapOf(
                    "entry_kind" to entryKind,
                    "transaction_date" to transactionDate,
                    "amount" to "$amountRupiah.00",
                    "category_account" to categoryAccount,
                    "counterparty_name" to counterpartyName,
                    "payment_method" to paymentMethod,
                    "note" to note,
                    "recurrence_frequency" to recurrenceFrequency,
                    "recurrence_interval" to recurrenceInterval,
                    "revision_reason" to revisionReason,
                )
            },
    )

private fun TransactionEntity.fromCanonicalPayload(payload: Map<String, Any?>): TransactionEntity =
    copy(
        entryKind = payload["entry_kind"]?.toString() ?: entryKind,
        transactionDate = payload["transaction_date"]?.toString() ?: transactionDate,
        amountRupiah =
            payload["amount"]?.toString()?.substringBefore('.')?.toLongOrNull() ?: amountRupiah,
        categoryAccount = payload["category_account"]?.toString()?.takeUnless { it == "null" },
        counterpartyName = payload["counterparty_name"]?.toString()?.takeUnless { it == "null" },
        paymentMethod = payload["payment_method"]?.toString() ?: paymentMethod,
        note = payload["note"]?.toString() ?: note,
        recurrenceFrequency =
            payload["recurrence_frequency"]?.toString()?.takeUnless { it == "null" },
        recurrenceInterval = (payload["recurrence_interval"] as? Number)?.toInt(),
    )
