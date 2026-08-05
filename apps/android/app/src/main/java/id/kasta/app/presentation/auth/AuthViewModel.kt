package id.kasta.app.presentation.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.remote.BusinessAccessDto
import id.kasta.app.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val identifier: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val authenticated: Boolean = false,
    val error: String? = null,
    val businessSelected: Boolean = false,
    val businesses: List<BusinessAccessDto> = emptyList(),
    val selectedBusinessId: String? = null,
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

        fun hasPendingBusinessSelection(): Boolean = repository.hasPendingBusinessSelection()

        fun update(transform: (LoginUiState) -> LoginUiState) {
            mutableState.update { transform(it).copy(error = null) }
        }

        fun login() {
            val current = mutableState.value
            if (current.identifier.length < 3 || current.password.isBlank()) {
                mutableState.update { it.copy(error = "Lengkapi email atau nomor telepon dan kata sandi.") }
                return
            }
            viewModelScope.launch {
                mutableState.update { it.copy(loading = true, error = null) }
                runCatching { repository.login(current.identifier.trim(), current.password) }
                    .onSuccess {
                        mutableState.update {
                            it.copy(loading = false, authenticated = true, businessSelected = false, password = "")
                        }
                    }
                    .onFailure { error ->
                        mutableState.update {
                            it.copy(loading = false, error = error.message ?: "Belum dapat masuk. Periksa data Anda.")
                        }
                    }
            }
        }

        fun loadBusinesses() {
            viewModelScope.launch {
                mutableState.update { it.copy(loading = true, error = null) }
                runCatching { repository.businesses() }
                    .onSuccess { businesses -> mutableState.update { it.copy(loading = false, businesses = businesses) } }
                    .onFailure { error ->
                        mutableState.update {
                            it.copy(loading = false, error = error.message ?: "Daftar usaha belum dapat dimuat.")
                        }
                    }
            }
        }

        fun selectBusiness(businessId: String) {
            viewModelScope.launch {
                mutableState.update { it.copy(loading = true, selectedBusinessId = businessId, error = null) }
                runCatching { repository.selectBusiness(businessId) }
                    .onSuccess { mutableState.update { it.copy(loading = false, businessSelected = true, selectedBusinessId = null) } }
                    .onFailure { error ->
                        mutableState.update {
                            it.copy(
                                loading = false,
                                selectedBusinessId = null,
                                error = error.message ?: "Usaha belum dapat dipilih.",
                            )
                        }
                    }
            }
        }

        fun logout() {
            repository.logout()
            mutableState.value = LoginUiState()
        }
    }
