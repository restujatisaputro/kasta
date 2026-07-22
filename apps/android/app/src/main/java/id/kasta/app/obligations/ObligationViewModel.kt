package id.kasta.app.obligations

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.remote.ObligationDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ObligationViewModel
    @Inject
    constructor(
        private val repository: ObligationRepository,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(ObligationUiState())
        val state: StateFlow<ObligationUiState> = mutableState.asStateFlow()

        init {
            refresh()
        }

        fun refresh() =
            launch {
                val (list, summary) = repository.load(mutableState.value)
                val (aging, reminderCount) = summary
                mutableState.value =
                    mutableState.value.copy(
                        items = list.items,
                        aging = aging,
                        reminderCount = reminderCount,
                    )
            }

        fun switchKind(kind: String) {
            mutableState.value = mutableState.value.copy(kind = kind, status = "", history = null)
            refresh()
        }

        fun filters(
            query: String? = null,
            status: String? = null,
            dueTo: String? = null,
            overdueOnly: Boolean? = null,
        ) {
            val current = mutableState.value
            mutableState.value =
                current.copy(
                    query = query ?: current.query,
                    status = status ?: current.status,
                    dueTo = dueTo ?: current.dueTo,
                    overdueOnly = overdueOnly ?: current.overdueOnly,
                )
        }

        fun openCreate() {
            mutableState.value = mutableState.value.copy(form = ObligationForm(), error = null)
        }

        fun updateForm(form: ObligationForm) {
            mutableState.value = mutableState.value.copy(form = form, error = null)
        }

        fun closeCreate() {
            mutableState.value = mutableState.value.copy(form = null)
        }

        fun save() {
            val current = mutableState.value
            val form = current.form ?: return
            if (form.partyName.isBlank() || (form.initialAmount.toBigDecimalOrNull()?.signum() ?: 0) <= 0) {
                mutableState.value = current.copy(error = "Isi nama dan nilai tagihan.")
                return
            }
            launch {
                repository.create(current.kind, form)
                mutableState.value = mutableState.value.copy(form = null, notice = "Tagihan berhasil dicatat.")
                refresh()
            }
        }

        fun openPayment(item: ObligationDto) {
            mutableState.value =
                mutableState.value.copy(
                    paymentTarget = item,
                    paymentForm = ObligationPaymentForm(amount = item.remainingAmount),
                )
        }

        fun updatePayment(form: ObligationPaymentForm) {
            mutableState.value = mutableState.value.copy(paymentForm = form, error = null)
        }

        fun closePayment() {
            mutableState.value = mutableState.value.copy(paymentTarget = null)
        }

        fun pay() {
            val current = mutableState.value
            val item = current.paymentTarget ?: return
            val amount = current.paymentForm.amount.toBigDecimalOrNull()
            if (amount == null || amount.signum() <= 0 || amount > item.remainingAmount.toBigDecimal()) {
                mutableState.value = current.copy(error = "Jumlah bayar tidak boleh melebihi sisa tagihan.")
                return
            }
            launch {
                repository.pay(current.kind, item.id, current.paymentForm)
                mutableState.value =
                    mutableState.value.copy(
                        paymentTarget = null,
                        notice = "Pembayaran berhasil dicatat.",
                    )
                refresh()
            }
        }

        fun history(item: ObligationDto) =
            launch {
                mutableState.value = mutableState.value.copy(history = repository.detail(mutableState.value.kind, item.id))
            }

        fun closeHistory() {
            mutableState.value = mutableState.value.copy(history = null)
        }

        fun cancel(
            item: ObligationDto,
            reason: String,
        ) {
            if (reason.length < 3) return
            launch {
                repository.cancel(mutableState.value.kind, item.id, reason)
                mutableState.value = mutableState.value.copy(notice = "Tagihan berhasil dibatalkan.")
                refresh()
            }
        }

        private fun launch(block: suspend () -> Unit) {
            mutableState.value = mutableState.value.copy(busy = true, error = null)
            viewModelScope.launch {
                runCatching { block() }
                    .onSuccess { mutableState.value = mutableState.value.copy(busy = false) }
                    .onFailure { error ->
                        mutableState.value =
                            mutableState.value.copy(
                                busy = false,
                                error = error.message ?: "Tagihan belum dapat diproses.",
                            )
                    }
            }
        }
    }
