package id.kasta.app.reports

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ReportViewModel
    @Inject
    constructor(
        private val repository: ReportRepository,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(ReportUiState())
        val state: StateFlow<ReportUiState> = mutableState.asStateFlow()

        init {
            refresh()
        }

        fun updateFilters(filters: ReportFilters) {
            mutableState.value = mutableState.value.copy(filters = filters, error = null)
        }

        fun refresh() {
            launch("Laporan belum dapat dimuat.") {
                val report = repository.load(mutableState.value.filters)
                mutableState.value = mutableState.value.copy(report = report)
            }
        }

        fun export(
            format: String,
            destination: Uri,
        ) {
            launch("Laporan belum dapat disimpan.") {
                repository.export(mutableState.value.filters, format, destination)
                mutableState.value = mutableState.value.copy(notice = "Laporan $format berhasil disimpan.")
            }
        }

        private fun launch(
            fallbackMessage: String,
            block: suspend () -> Unit,
        ) {
            mutableState.value = mutableState.value.copy(busy = true, error = null, notice = null)
            viewModelScope.launch {
                runCatching { block() }
                    .onSuccess { mutableState.value = mutableState.value.copy(busy = false) }
                    .onFailure { error ->
                        mutableState.value =
                            mutableState.value.copy(
                                busy = false,
                                error = error.message ?: fallbackMessage,
                            )
                    }
            }
        }
    }
