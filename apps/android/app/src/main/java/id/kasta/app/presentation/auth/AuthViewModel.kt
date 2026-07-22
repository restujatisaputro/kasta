package id.kasta.app.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class LoginUiState(
    val businessId: String = "",
    val identifier: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val authenticated: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class AuthViewModel
    @Inject
    constructor(
        private val repository: AuthRepository,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(LoginUiState())
        val state: StateFlow<LoginUiState> = mutableState.asStateFlow()

        fun hasSession(): Boolean = repository.hasSession()

        fun update(transform: (LoginUiState) -> LoginUiState) {
            mutableState.update { transform(it).copy(error = null) }
        }

        fun login() {
            val current = mutableState.value
            val validBusinessId = runCatching { UUID.fromString(current.businessId) }.isSuccess
            if (!validBusinessId || current.identifier.length < 3 || current.password.isBlank()) {
                mutableState.update { it.copy(error = "Lengkapi ID usaha, email atau nomor telepon, dan kata sandi.") }
                return
            }
            viewModelScope.launch {
                mutableState.update { it.copy(loading = true, error = null) }
                runCatching { repository.login(current.businessId, current.identifier.trim(), current.password) }
                    .onSuccess { mutableState.update { it.copy(loading = false, authenticated = true, password = "") } }
                    .onFailure { error ->
                        mutableState.update {
                            it.copy(loading = false, error = error.message ?: "Belum dapat masuk. Periksa data Anda.")
                        }
                    }
            }
        }

        fun logout() {
            repository.logout()
            mutableState.value = LoginUiState()
        }
    }
