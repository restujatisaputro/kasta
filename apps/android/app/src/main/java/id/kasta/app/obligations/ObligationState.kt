package id.kasta.app.obligations

import id.kasta.app.data.remote.ObligationAgingDto
import id.kasta.app.data.remote.ObligationDto
import java.time.LocalDate

data class ObligationForm(
    val partyName: String = "",
    val initialAmount: String = "",
    val transactionDate: String = LocalDate.now().toString(),
    val dueDate: String = LocalDate.now().toString(),
    val note: String = "",
    val reminderDaysBefore: String = "3",
)

data class ObligationPaymentForm(
    val amount: String = "",
    val paymentAccount: String = "CASH",
    val note: String = "",
)

data class ObligationUiState(
    val kind: String = "RECEIVABLE",
    val items: List<ObligationDto> = emptyList(),
    val aging: ObligationAgingDto? = null,
    val reminderCount: Int = 0,
    val query: String = "",
    val status: String = "",
    val dueTo: String = "",
    val overdueOnly: Boolean = false,
    val form: ObligationForm? = null,
    val paymentTarget: ObligationDto? = null,
    val paymentForm: ObligationPaymentForm = ObligationPaymentForm(),
    val history: ObligationDto? = null,
    val busy: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)

fun obligationStatusLabel(status: String): String =
    when (status) {
        "OPEN" -> "Belum Dibayar"
        "PARTIALLY_PAID" -> "Dibayar Sebagian"
        "PAID" -> "Sudah Lunas"
        "OVERDUE" -> "Terlambat"
        "CANCELLED" -> "Dibatalkan"
        else -> status
    }
