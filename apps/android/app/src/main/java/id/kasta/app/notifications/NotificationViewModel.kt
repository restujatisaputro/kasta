package id.kasta.app.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.local.AppPreferenceState
import id.kasta.app.data.local.AppPreferences
import id.kasta.app.data.local.NotificationEntity
import id.kasta.app.data.remote.NotificationPreferenceDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import javax.inject.Inject

data class NotificationUiState(
    val items: List<NotificationEntity> = emptyList(),
    val appPreferences: AppPreferenceState = AppPreferenceState(),
    val serverPreferences: List<NotificationPreferenceDto> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class NotificationViewModel
    @Inject
    constructor(
        private val repository: NotificationRepository,
        private val preferences: AppPreferences,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(NotificationUiState())
        val state: StateFlow<NotificationUiState> = mutableState.asStateFlow()

        init {
            viewModelScope.launch {
                combine(repository.observe(), preferences.state) { items, settings -> items to settings }
                    .collect { (items, settings) ->
                        mutableState.value =
                            mutableState.value.copy(
                                items = items,
                                appPreferences = settings,
                                loading = false,
                            )
                    }
            }
            refresh()
        }

        fun refresh() {
            viewModelScope.launch {
                runCatching {
                    repository.refresh()
                    repository.preferences()
                }.onSuccess { serverPreferences ->
                    mutableState.value =
                        mutableState.value.copy(
                            serverPreferences = serverPreferences,
                            loading = false,
                            error = null,
                        )
                }.onFailure { error ->
                    mutableState.value =
                        mutableState.value.copy(
                            loading = false,
                            error = error.message ?: "Notifikasi belum dapat diperbarui.",
                        )
                }
            }
        }

        fun markRead(item: NotificationEntity) {
            viewModelScope.launch {
                runCatching { repository.markRead(item) }
                    .onFailure { mutableState.value = mutableState.value.copy(error = it.message) }
            }
        }

        fun markAllRead() {
            viewModelScope.launch {
                runCatching { repository.markAllRead() }
                    .onFailure { mutableState.value = mutableState.value.copy(error = it.message) }
            }
        }

        fun setCategory(
            category: String,
            enabled: Boolean,
        ) {
            viewModelScope.launch {
                preferences.setCategory(category, enabled)
                mutableState.value.serverPreferences.firstOrNull { it.category == category }?.let { current ->
                    runCatching {
                        repository.updatePreference(
                            current.copy(enabled = enabled, localEnabled = enabled),
                        )
                    }.onSuccess {
                        mutableState.value = mutableState.value.copy(serverPreferences = it)
                    }
                }
            }
        }

        fun setReminderTime(value: String) {
            val parts = value.split(":")
            val hour = parts.getOrNull(0)?.toIntOrNull() ?: return
            val minute = parts.getOrNull(1)?.toIntOrNull() ?: return
            viewModelScope.launch { preferences.setReminderTime(hour, minute) }
        }

        fun setQuietHours(
            enabled: Boolean,
            start: String,
            end: String,
        ) {
            viewModelScope.launch { preferences.setQuietHours(enabled, start, end) }
        }
    }
