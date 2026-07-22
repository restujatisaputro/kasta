package id.kasta.app.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import id.kasta.app.data.repository.LocalDashboardRepository
import id.kasta.app.domain.repository.DashboardRepository
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindDashboardRepository(repository: LocalDashboardRepository): DashboardRepository
}
