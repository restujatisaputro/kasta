package id.kasta.app.domain.repository

import id.kasta.app.domain.model.DashboardSummary
import kotlinx.coroutines.flow.Flow

interface DashboardRepository {
    fun observeDashboard(): Flow<DashboardSummary>
}
