package id.kasta.app.reports

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import id.kasta.app.data.remote.AccountReportLineDto
import id.kasta.app.data.remote.FinancialReportDto
import id.kasta.app.transactions.formatRupiah
import java.math.BigDecimal
import kotlin.math.abs

private val periodChoices =
    listOf(
        "DAY" to "Hari",
        "WEEK" to "Minggu",
        "MONTH" to "Bulan",
        "QUARTER" to "Kuartal",
        "YEAR" to "Tahun",
        "CUSTOM" to "Rentang",
    )
private val categoryChoices =
    listOf(
        "" to "Semua kategori",
        "SALES" to "Penjualan",
        "SERVICE_REVENUE" to "Pendapatan Jasa",
        "PURCHASES" to "Pembelian",
        "RAW_MATERIALS" to "Bahan Baku",
        "TRANSPORTATION" to "Transportasi",
        "SALARY" to "Gaji",
        "RENT" to "Sewa",
        "OTHER_EXPENSE" to "Pengeluaran Lain",
    )
private val paymentChoices =
    listOf(
        "" to "Semua metode",
        "CASH" to "Tunai",
        "BANK_TRANSFER" to "Transfer",
        "QRIS" to "QRIS",
        "E_WALLET" to "Dompet Digital",
        "CARD" to "Kartu",
    )

@Composable
fun ReportScreen(
    state: ReportUiState,
    onBack: () -> Unit,
    onFiltersChange: (ReportFilters) -> Unit,
    onRefresh: () -> Unit,
    onExport: (String, Uri) -> Unit,
) {
    val pdf =
        rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) {
            it?.let { uri -> onExport("PDF", uri) }
        }
    val xlsx =
        rememberLauncherForActivityResult(
            ActivityResultContracts.CreateDocument(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ) { it?.let { uri -> onExport("XLSX", uri) } }
    val csv =
        rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) {
            it?.let { uri -> onExport("CSV", uri) }
        }

    Scaffold { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(
                        "Laporan Keuangan",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                    )
                    Text("Angka dihitung dari jurnal usaha")
                }
                TextButton(onClick = onBack) { Text("Kembali") }
            }
            state.notice?.let { Message(it, false) }
            state.error?.let { Message(it, true) }
            FilterPanel(state.filters, onFiltersChange, onRefresh, state.busy)
            Row(
                Modifier.fillMaxWidth().padding(vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedButton(onClick = { pdf.launch("laporan-kasta.pdf") }, modifier = Modifier.weight(1f)) {
                    Text("PDF")
                }
                OutlinedButton(onClick = { xlsx.launch("laporan-kasta.xlsx") }, modifier = Modifier.weight(1f)) {
                    Text("XLSX")
                }
                OutlinedButton(onClick = { csv.launch("laporan-kasta.csv") }, modifier = Modifier.weight(1f)) {
                    Text("CSV")
                }
            }
            if (state.busy && state.report == null) {
                Text("Menghitung laporan dari jurnal…", modifier = Modifier.padding(vertical = 40.dp))
            }
            state.report?.let { report -> ReportContent(report) }
        }
    }
}

@Composable
private fun FilterPanel(
    filters: ReportFilters,
    onChange: (ReportFilters) -> Unit,
    onRefresh: () -> Unit,
    busy: Boolean,
) {
    SectionCard("Filter laporan") {
        ChipRow(periodChoices, filters.period) { onChange(filters.copy(period = it)) }
        if (filters.period == "CUSTOM") {
            OutlinedTextField(
                value = filters.dateFrom,
                onValueChange = { onChange(filters.copy(dateFrom = it)) },
                label = { Text("Tanggal mulai (YYYY-MM-DD)") },
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = filters.dateTo,
                onValueChange = { onChange(filters.copy(dateTo = it)) },
                label = { Text("Tanggal akhir (YYYY-MM-DD)") },
                modifier = Modifier.fillMaxWidth(),
            )
        } else {
            OutlinedTextField(
                value = filters.referenceDate,
                onValueChange = { onChange(filters.copy(referenceDate = it)) },
                label = { Text("Tanggal acuan (YYYY-MM-DD)") },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Text("Kategori", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
        ChipRow(categoryChoices, filters.category) { onChange(filters.copy(category = it)) }
        Text("Metode pembayaran", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
        ChipRow(paymentChoices, filters.paymentMethod) { onChange(filters.copy(paymentMethod = it)) }
        Text("Cabang: usaha ini", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = onRefresh, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (busy) "Menghitung…" else "Tampilkan laporan")
        }
    }
}

@Composable
private fun ChipRow(
    choices: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        choices.forEach { (value, label) ->
            FilterChip(
                selected = selected == value,
                onClick = { onSelect(value) },
                label = { Text(label) },
            )
        }
    }
}

@Composable
private fun ReportContent(report: FinancialReportDto) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(18.dp)) {
            Text("Ringkasan keuangan", fontWeight = FontWeight.ExtraBold)
            Text(report.explanation, style = MaterialTheme.typography.titleMedium)
            Text("${report.context.dateFrom} sampai ${report.context.dateTo} · Sumber: jurnal double-entry")
        }
    }
    Summary(report)
    ReportCharts(report)
    ProfitLoss(report)
    BalanceSheet(report)
    CashFlow(report)
    SalesAndExpenses(report)
    ObligationsAndInventory(report)
    ProductsAndComparison(report)
}

@Composable
private fun Summary(report: FinancialReportDto) {
    SectionCard("Ringkasan angka") {
        MoneyRow("Pemasukan", report.summary.income)
        MoneyRow("Pengeluaran", report.summary.expense)
        MoneyRow("Perkiraan laba", report.summary.estimatedProfit)
        MoneyRow("Arus kas bersih", report.summary.netCashFlow)
        MoneyRow("Piutang", report.summary.receivables)
        MoneyRow("Utang", report.summary.payables)
        MoneyRow("Nilai persediaan", report.summary.inventoryValue)
    }
}

@Composable
private fun ReportCharts(report: FinancialReportDto) {
    SectionCard("Pemasukan versus pengeluaran") {
        HorizontalBarChart(
            listOf(
                BarData("Pemasukan", report.summary.income.toDouble(), Color(0xFF047857)),
                BarData("Pengeluaran", report.summary.expense.toDouble(), Color(0xFFF59E0B)),
            ),
        )
    }
    SectionCard("Tren laba") {
        HorizontalBarChart(
            report.charts.profitTrend.takeLast(6).map {
                BarData(it.period, it.profit.toDouble(), if (it.profit.toDouble() < 0) Color.Red else Color(0xFF059669))
            },
        )
    }
    SectionCard("Kategori pengeluaran") {
        HorizontalBarChart(
            report.charts.expenseCategories.take(7).map { BarData(it.label, it.amount.toDouble(), Color(0xFFF59E0B)) },
        )
    }
    SectionCard("Penjualan harian") {
        HorizontalBarChart(
            report.charts.dailySales.takeLast(7).map { BarData(it.period.takeLast(5), it.sales.toDouble(), Color(0xFF0F766E)) },
        )
    }
    SectionCard("Produk terlaris") {
        HorizontalBarChart(
            report.charts.bestSellingProducts.take(5).map { BarData(it.name, it.quantitySold.toDouble(), Color(0xFF2563EB), false) },
        )
    }
}

@Composable
private fun ProfitLoss(report: FinancialReportDto) {
    SectionCard("Laporan laba rugi") {
        Text("Pemasukan", fontWeight = FontWeight.Bold)
        AccountLines(report.profitLoss.revenues)
        Text("Pengeluaran", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
        AccountLines(report.profitLoss.expenses)
        MoneyRow("Perkiraan laba", report.profitLoss.profit, true)
        Explanation(report.profitLoss.explanation)
    }
}

@Composable
private fun BalanceSheet(report: FinancialReportDto) {
    SectionCard("Laporan posisi keuangan") {
        Text("Yang dimiliki usaha", fontWeight = FontWeight.Bold)
        AccountLines(report.balanceSheet.assets)
        Text("Kewajiban usaha", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
        AccountLines(report.balanceSheet.liabilities)
        Text("Dana pemilik", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
        AccountLines(report.balanceSheet.equity)
        MoneyRow("Total yang dimiliki", report.balanceSheet.totalAssets, true)
        Explanation(report.balanceSheet.explanation)
    }
}

@Composable
private fun CashFlow(report: FinancialReportDto) {
    SectionCard("Arus kas sederhana") {
        MoneyRow("Uang masuk", report.cashFlow.cashIn)
        MoneyRow("Uang keluar", report.cashFlow.cashOut)
        MoneyRow("Perubahan kas", report.cashFlow.netCashFlow)
        MoneyRow("Saldo kas dan rekening", report.cashFlow.endingCashBalance, true)
        Explanation(report.cashFlow.explanation)
    }
}

@Composable
private fun SalesAndExpenses(report: FinancialReportDto) {
    SectionCard("Penjualan") {
        report.sales.forEach { MoneyRow(it.label, it.amount) }
        if (report.sales.isEmpty()) Text("Belum ada penjualan pada periode ini.")
    }
    SectionCard("Pengeluaran") {
        report.expenditures.forEach { MoneyRow(it.label, it.amount) }
        if (report.expenditures.isEmpty()) Text("Belum ada pengeluaran pada periode ini.")
    }
}

@Composable
private fun ObligationsAndInventory(report: FinancialReportDto) {
    SectionCard("Utang dan piutang") {
        MoneyRow("Piutang menurut jurnal", report.receivables.journalValue)
        MoneyRow("Sisa daftar piutang (${report.receivables.openCount})", report.receivables.totalRemaining)
        MoneyRow("Utang menurut jurnal", report.payables.journalValue)
        MoneyRow("Sisa daftar utang (${report.payables.openCount})", report.payables.totalRemaining)
        Explanation(report.receivables.explanation)
        Explanation(report.payables.explanation)
    }
    SectionCard("Persediaan") {
        Text("${report.inventory.productCount} produk aktif · ${report.inventory.lowStockCount} stok minimum")
        MoneyRow("Nilai stok operasional", report.inventory.operationalValue)
        MoneyRow("Nilai persediaan di jurnal", report.inventory.journalValue)
        Explanation(report.inventory.explanation)
    }
}

@Composable
private fun ProductsAndComparison(report: FinancialReportDto) {
    SectionCard("Produk paling laku") {
        report.bestSellingProducts.forEach {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${it.name} (${it.quantitySold} ${it.unit})", modifier = Modifier.weight(1f))
                Text(money(it.salesValue), fontWeight = FontWeight.Bold)
            }
        }
        if (report.bestSellingProducts.isEmpty()) Text("Belum ada penjualan produk pada periode ini.")
    }
    SectionCard("Perbandingan bulanan") {
        report.monthlyComparison.forEach {
            Text(it.period, fontWeight = FontWeight.ExtraBold)
            MoneyRow("Pemasukan", it.income)
            MoneyRow("Pengeluaran", it.expense)
            MoneyRow("Laba", it.profit)
            HorizontalDivider(Modifier.padding(vertical = 6.dp))
        }
    }
}

@Composable
private fun AccountLines(lines: List<AccountReportLineDto>) {
    lines.forEach { MoneyRow(it.accountName, it.amount) }
    if (lines.isEmpty()) Text("Belum ada nilai pada bagian ini.")
}

private data class BarData(
    val label: String,
    val value: Double,
    val color: Color,
    val isMoney: Boolean = true,
)

@Composable
private fun HorizontalBarChart(items: List<BarData>) {
    if (items.isEmpty()) {
        Text("Belum ada data untuk grafik ini.")
        return
    }
    val maximum = items.maxOfOrNull { abs(it.value) }?.takeIf { it > 0 } ?: 1.0
    items.forEach { item ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(item.label, modifier = Modifier.weight(1f))
            Text(if (item.isMoney) money(item.value.toString()) else item.value.toBigDecimal().stripTrailingZeros().toPlainString())
        }
        Box(
            Modifier
                .fillMaxWidth((abs(item.value) / maximum).toFloat().coerceIn(0.02f, 1f))
                .height(10.dp)
                .background(item.color, RoundedCornerShape(8.dp)),
        )
        Spacer(Modifier.height(8.dp))
    }
}

@Composable
private fun SectionCard(
    title: String,
    content: @Composable () -> Unit,
) {
    Card(Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            content()
        }
    }
}

@Composable
private fun MoneyRow(
    label: String,
    amount: String,
    strong: Boolean = false,
) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, modifier = Modifier.weight(1f), fontWeight = if (strong) FontWeight.Bold else null)
        Spacer(Modifier.width(12.dp))
        Text(money(amount), fontWeight = if (strong) FontWeight.Black else FontWeight.SemiBold)
    }
}

@Composable
private fun Explanation(text: String) {
    Text(
        text,
        modifier = Modifier.fillMaxWidth().background(Color(0xFFECFDF5), RoundedCornerShape(10.dp)).padding(10.dp),
        color = Color(0xFF065F46),
    )
}

@Composable
private fun Message(
    text: String,
    error: Boolean,
) {
    Text(
        text,
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
        color = if (error) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
        fontWeight = FontWeight.Bold,
    )
}

private fun money(value: String): String =
    formatRupiah(value.toBigDecimalOrNull()?.setScale(0, java.math.RoundingMode.HALF_UP)?.toLong() ?: 0L)

private fun String.toDouble(): Double = toBigDecimalOrNull()?.toDouble() ?: BigDecimal.ZERO.toDouble()
