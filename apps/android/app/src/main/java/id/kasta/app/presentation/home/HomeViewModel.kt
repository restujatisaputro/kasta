package id.kasta.app.presentation.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.domain.model.DashboardSummary
import id.kasta.app.domain.usecase.ObserveDashboardUseCase
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class HomeUiState(
    val loading: Boolean = true,
    val summary: DashboardSummary = DashboardSummary(),
)

@HiltViewModel
class HomeViewModel
    @Inject
    constructor(
        observeDashboard: ObserveDashboardUseCase,
    ) : ViewModel() {
        val state: StateFlow<HomeUiState> =
            observeDashboard()
                .map { HomeUiState(loading = false, summary = it) }
                .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), HomeUiState())
    }
