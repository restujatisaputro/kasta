package id.kasta.app.reports

import id.kasta.app.data.remote.FinancialReportDto
import java.time.LocalDate

data class ReportFilters(
    val period: String = "MONTH",
    val referenceDate: String = LocalDate.now().toString(),
    val dateFrom: String = LocalDate.now().withDayOfMonth(1).toString(),
    val dateTo: String = LocalDate.now().toString(),
    val category: String = "",
    val paymentMethod: String = "",
)

data class ReportUiState(
    val report: FinancialReportDto? = null,
    val filters: ReportFilters = ReportFilters(),
    val busy: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)
