package id.kasta.app.mentoraccess

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.remote.MentorAccessDto
import id.kasta.app.data.remote.MentorAccessHistoryDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MentorAccessUiState(
    val items: List<MentorAccessDto> = emptyList(),
    val history: List<MentorAccessHistoryDto> = emptyList(),
    val busy: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)

@HiltViewModel
class MentorAccessViewModel
    @Inject
    constructor(private val repository: MentorAccessRepository) : ViewModel() {
        private val mutableState = MutableStateFlow(MentorAccessUiState())
        val state = mutableState.asStateFlow()

        init {
            refresh()
        }

        fun refresh() = runAction(null) {}

        fun decide(
            accessId: String,
            approve: Boolean,
            scopes: List<String>,
            expiresAt: String?,
            reason: String?,
        ) = runAction(if (approve) "Izin pembina sudah aktif." else "Permintaan ditolak.") {
            repository.decide(accessId, approve, scopes, expiresAt, reason)
        }

        fun revoke(
            accessId: String,
            reason: String,
        ) = runAction("Izin dicabut. Pembina tidak dapat mengakses data lagi.") {
            repository.revoke(accessId, reason)
        }

        private fun runAction(
            notice: String?,
            action: suspend () -> Unit,
        ) {
            viewModelScope.launch {
                mutableState.update { it.copy(busy = true, error = null, notice = null) }
                try {
                    action()
                    val (items, history) = repository.load()
                    mutableState.value =
                        MentorAccessUiState(items, history, notice = notice)
                } catch (error: Exception) {
                    mutableState.update {
                        it.copy(busy = false, error = error.message ?: "Permintaan gagal diproses.")
                    }
                }
            }
        }
    }
