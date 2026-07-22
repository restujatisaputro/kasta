package id.kasta.app.transactions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.local.TransactionEntity
import id.kasta.app.data.session.SessionStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class TransactionViewModel
    @Inject
    constructor(
        private val repository: TransactionRepository,
        sessionStore: SessionStore,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(TransactionUiState())
        val state: StateFlow<TransactionUiState> = mutableState.asStateFlow()
        private val businessId = sessionStore.get()?.businessId.orEmpty()

        init {
            if (businessId.isNotBlank()) {
                viewModelScope.launch {
                    val last = repository.lastExpenseCategory(businessId)
                    val categories =
                        if (last == null) {
                            DEFAULT_EXPENSE_CATEGORIES
                        } else {
                            DEFAULT_EXPENSE_CATEGORIES.sortedBy { if (it.first == last) 0 else 1 }
                        }
                    mutableState.value = mutableState.value.copy(expenseCategories = categories)
                    repository.observe(businessId).collectLatest { values ->
                        setTransactions(values)
                    }
                }
                viewModelScope.launch {
                    repository.observeSyncCounts(businessId).collectLatest { rows ->
                        mutableState.value =
                            mutableState.value.copy(
                                syncCounts = rows.associate { it.syncStatus to it.total },
                            )
                    }
                }
                viewModelScope.launch {
                    repository.observeConflicts(businessId).collectLatest { rows ->
                        mutableState.value = mutableState.value.copy(conflicts = rows)
                    }
                }
                viewModelScope.launch {
                    repository.observeSyncMetadata(businessId).collectLatest { metadata ->
                        mutableState.value =
                            mutableState.value.copy(
                                syncDeviceId = metadata.deviceId,
                                syncCursor = metadata.cursor,
                                lastSyncAt = metadata.lastSyncAt,
                            )
                    }
                }
                repository.enqueueSync()
            }
        }

        fun start(entryKind: String) {
            val category =
                when (entryKind) {
                    "INCOME" -> INCOME_SOURCES.first().first
                    "EXPENSE" -> mutableState.value.expenseCategories.first().first
                    else -> ""
                }
            mutableState.value =
                mutableState.value.copy(
                    step = 1,
                    form = TransactionForm(entryKind = entryKind, categoryAccount = category),
                    editTargetServerId = null,
                    error = null,
                    notice = null,
                )
        }

        fun update(form: TransactionForm) {
            mutableState.value = mutableState.value.copy(form = form, error = null)
        }

        fun next() {
            val current = mutableState.value
            if (current.step == 1) {
                val amount = current.form.amountDigits.toLongOrNull() ?: 0
                if (amount <= 0 || current.form.transactionDate.isBlank()) {
                    mutableState.value = current.copy(error = "Isi tanggal dan nominal transaksi.")
                    return
                }
                if (
                    current.form.entryKind in setOf("INCOME", "EXPENSE") &&
                    current.form.categoryAccount.isBlank()
                ) {
                    mutableState.value = current.copy(error = "Pilih sumber atau kategori transaksi.")
                    return
                }
            }
            mutableState.value = current.copy(step = (current.step + 1).coerceAtMost(3), error = null)
        }

        fun back() {
            val current = mutableState.value
            mutableState.value = current.copy(step = (current.step - 1).coerceAtLeast(0))
        }

        fun close() {
            mutableState.value = mutableState.value.copy(step = 0, error = null)
        }

        fun save(asDraft: Boolean) {
            val current = mutableState.value
            if (
                current.editTargetServerId != null &&
                current.form.revisionReason.trim().length < 3
            ) {
                mutableState.value = current.copy(error = "Isi alasan perubahan minimal 3 karakter.")
                return
            }
            launchRequest {
                repository.save(
                    current.form,
                    asDraft = asDraft,
                    targetServerId = current.editTargetServerId,
                    operation = if (current.editTargetServerId == null) "CREATE" else "REVISE",
                )
                mutableState.value =
                    current.copy(
                        step = 0,
                        form = TransactionForm(),
                        editTargetServerId = null,
                        notice =
                            if (asDraft) {
                                "Draft tersimpan di perangkat."
                            } else {
                                "Transaksi tersimpan dan akan disinkronkan."
                            },
                    )
            }
        }

        fun postDraft(entity: TransactionEntity) {
            launchRequest {
                repository.postDraft(entity)
                mutableState.value = mutableState.value.copy(notice = "Draft masuk antrean sinkronisasi.")
            }
        }

        fun edit(entity: TransactionEntity) {
            if (entity.serverId == null) return
            mutableState.value =
                mutableState.value.copy(
                    step = 1,
                    form =
                        TransactionForm(
                            entryKind = entity.entryKind,
                            transactionDate = entity.transactionDate,
                            amountDigits = entity.amountRupiah.toString(),
                            categoryAccount = entity.categoryAccount.orEmpty(),
                            counterpartyName = entity.counterpartyName.orEmpty(),
                            paymentMethod = entity.paymentMethod,
                            note = entity.note,
                        ),
                    editTargetServerId = entity.serverId,
                    error = null,
                )
        }

        fun cancel(
            entity: TransactionEntity,
            reason: String,
        ) {
            if (entity.serverId == null || reason.trim().length < 3) {
                mutableState.value = mutableState.value.copy(error = "Isi alasan pembatalan.")
                return
            }
            launchRequest {
                repository.save(
                    TransactionForm(
                        entryKind = entity.entryKind,
                        transactionDate = entity.transactionDate,
                        amountDigits = entity.amountRupiah.toString(),
                        categoryAccount = entity.categoryAccount.orEmpty(),
                        paymentMethod = entity.paymentMethod,
                        note = entity.note,
                        revisionReason = reason,
                    ),
                    asDraft = false,
                    targetServerId = entity.serverId,
                    operation = "REVERSE",
                )
                mutableState.value = mutableState.value.copy(notice = "Pembatalan masuk antrean sinkronisasi.")
            }
        }

        fun search(value: String) {
            mutableState.value = mutableState.value.copy(search = value)
            applyFilter()
        }

        fun filter(kind: String) {
            mutableState.value = mutableState.value.copy(kindFilter = kind)
            applyFilter()
        }

        fun syncNow() {
            launchRequest {
                val success = repository.syncPending()
                mutableState.value =
                    mutableState.value.copy(
                        notice = if (success) "Sinkronisasi selesai." else null,
                        error = if (success) null else "Belum dapat terhubung ke server.",
                    )
            }
        }

        fun resolveWithServer(entity: TransactionEntity) {
            launchRequest {
                repository.resolveConflictWithServer(entity)
                mutableState.value = mutableState.value.copy(notice = "Versi server digunakan.")
            }
        }

        fun resolveWithLocal(entity: TransactionEntity) {
            launchRequest {
                repository.resolveConflictWithLocal(entity)
                mutableState.value =
                    mutableState.value.copy(
                        notice = "Versi perangkat akan dibuat sebagai revisi terkontrol.",
                    )
            }
        }

        private fun setTransactions(values: List<TransactionEntity>) {
            mutableState.value = mutableState.value.copy(transactions = values)
            applyFilter()
        }

        private fun applyFilter() {
            val current = mutableState.value
            val query = current.search.trim().lowercase()
            val filtered =
                current.transactions.filter { item ->
                    item.operation != "REVERSE" &&
                        (current.kindFilter.isBlank() || item.entryKind == current.kindFilter) &&
                        (
                            query.isBlank() ||
                                item.note.lowercase().contains(query) ||
                                item.counterpartyName.orEmpty().lowercase().contains(query)
                        )
                }
            mutableState.value = current.copy(visibleTransactions = filtered)
        }

        private fun launchRequest(block: suspend () -> Unit) {
            mutableState.value = mutableState.value.copy(busy = true, error = null)
            viewModelScope.launch {
                try {
                    block()
                } catch (error: Exception) {
                    mutableState.value =
                        mutableState.value.copy(
                            error = error.message ?: "Data belum dapat disimpan.",
                        )
                } finally {
                    mutableState.value = mutableState.value.copy(busy = false)
                }
            }
        }
    }
