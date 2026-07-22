package id.kasta.app.reports

import android.content.Context
import android.net.Uri
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.data.remote.ReportApi
import id.kasta.app.data.session.SessionStore
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReportRepository
    @Inject
    constructor(
        private val api: ReportApi,
        private val sessionStore: SessionStore,
        @ApplicationContext private val context: Context,
    ) {
        private fun session() = requireNotNull(sessionStore.get()) { "Sesi sudah berakhir." }

        suspend fun load(filters: ReportFilters) =
            session().let { session ->
                api.financial(
                    businessId = session.businessId,
                    authorization = "Bearer ${session.accessToken}",
                    period = filters.period,
                    referenceDate = filters.referenceDate,
                    dateFrom = filters.dateFrom.takeIf { filters.period == "CUSTOM" },
                    dateTo = filters.dateTo.takeIf { filters.period == "CUSTOM" },
                    category = filters.category.ifBlank { null },
                    paymentMethod = filters.paymentMethod.ifBlank { null },
                    branchId = session.businessId,
                )
            }

        suspend fun export(
            filters: ReportFilters,
            format: String,
            destination: Uri,
        ) {
            val session = session()
            val body =
                api.export(
                    businessId = session.businessId,
                    authorization = "Bearer ${session.accessToken}",
                    period = filters.period,
                    referenceDate = filters.referenceDate,
                    dateFrom = filters.dateFrom.takeIf { filters.period == "CUSTOM" },
                    dateTo = filters.dateTo.takeIf { filters.period == "CUSTOM" },
                    category = filters.category.ifBlank { null },
                    paymentMethod = filters.paymentMethod.ifBlank { null },
                    branchId = session.businessId,
                    format = format,
                )
            val output =
                requireNotNull(context.contentResolver.openOutputStream(destination)) {
                    "Lokasi file tidak dapat dibuka."
                }
            output.use { stream -> body.byteStream().use { it.copyTo(stream) } }
        }
    }
