package id.kasta.app.domain.usecase

import id.kasta.app.domain.repository.DashboardRepository
import javax.inject.Inject

class ObserveDashboardUseCase
    @Inject
    constructor(
        private val repository: DashboardRepository,
    ) {
        operator fun invoke() = repository.observeDashboard()
    }
