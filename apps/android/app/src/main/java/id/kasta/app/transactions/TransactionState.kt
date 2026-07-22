package id.kasta.app.transactions

import id.kasta.app.data.local.TransactionEntity
import java.text.NumberFormat
import java.time.LocalDate
import java.util.Locale

data class TransactionForm(
    val entryKind: String = "INCOME",
    val transactionDate: String = LocalDate.now().toString(),
    val amountDigits: String = "",
    val categoryAccount: String = "SALES",
    val counterpartyName: String = "",
    val paymentMethod: String = "CASH",
    val note: String = "",
    val receiptUri: String? = null,
    val recurring: Boolean = false,
    val recurrenceFrequency: String = "MONTHLY",
    val recurrenceInterval: Int = 1,
    val revisionReason: String = "",
)

data class TransactionUiState(
    val step: Int = 0,
    val form: TransactionForm = TransactionForm(),
    val transactions: List<TransactionEntity> = emptyList(),
    val visibleTransactions: List<TransactionEntity> = emptyList(),
    val expenseCategories: List<Pair<String, String>> = DEFAULT_EXPENSE_CATEGORIES,
    val search: String = "",
    val kindFilter: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
    val editTargetServerId: String? = null,
    val syncCounts: Map<String, Int> = emptyMap(),
    val conflicts: List<TransactionEntity> = emptyList(),
    val syncDeviceId: String = "",
    val syncCursor: Long = 0,
    val lastSyncAt: String? = null,
)

val INCOME_SOURCES =
    listOf(
        "SALES" to "Penjualan",
        "SERVICE_REVENUE" to "Pendapatan jasa",
        "OTHER_REVENUE" to "Pendapatan lain",
    )

val DEFAULT_EXPENSE_CATEGORIES =
    listOf(
        "PURCHASES" to "Pembelian",
        "RAW_MATERIALS" to "Bahan baku",
        "TRANSPORTATION" to "Transportasi",
        "ELECTRICITY" to "Listrik",
        "INTERNET" to "Internet",
        "SALARY" to "Gaji",
        "RENT" to "Sewa",
        "PROMOTION" to "Promosi",
        "ADMINISTRATION" to "Administrasi",
        "OTHER_EXPENSE" to "Beban lain",
    )

val PAYMENT_METHODS =
    listOf(
        "CASH" to "Tunai",
        "BANK_TRANSFER" to "Transfer bank",
        "QRIS" to "QRIS",
        "E_WALLET" to "Dompet digital",
        "CARD" to "Kartu",
    )

fun formatRupiah(value: Long): String =
    NumberFormat.getCurrencyInstance(Locale.forLanguageTag("id-ID")).apply {
        maximumFractionDigits = 0
    }.format(value)

fun formatRupiahDigits(value: String): String =
    value.toLongOrNull()?.let {
        NumberFormat.getIntegerInstance(Locale.forLanguageTag("id-ID")).format(it)
    } ?: ""
