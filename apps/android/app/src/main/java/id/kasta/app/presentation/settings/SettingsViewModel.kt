package id.kasta.app.presentation.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.local.AppPreferenceState
import id.kasta.app.data.local.AppPreferences
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel
    @Inject
    constructor(
        private val preferences: AppPreferences,
    ) : ViewModel() {
        val state: StateFlow<AppPreferenceState> =
            preferences.state.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), AppPreferenceState())

        fun setDarkMode(enabled: Boolean) {
            viewModelScope.launch { preferences.setDarkMode(enabled) }
        }

        fun setNotifications(enabled: Boolean) {
            viewModelScope.launch { preferences.setNotifications(enabled) }
        }
    }
