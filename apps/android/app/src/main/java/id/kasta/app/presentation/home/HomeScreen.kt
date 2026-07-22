package id.kasta.app.presentation.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ReceiptLong
import androidx.compose.material.icons.automirrored.rounded.TrendingUp
import androidx.compose.material.icons.rounded.AccountBalanceWallet
import androidx.compose.material.icons.rounded.AddCircle
import androidx.compose.material.icons.rounded.CameraAlt
import androidx.compose.material.icons.rounded.MoneyOff
import androidx.compose.material.icons.rounded.Payments
import androidx.compose.material.icons.rounded.RemoveCircle
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import id.kasta.app.domain.model.DashboardSummary
import id.kasta.app.domain.model.DashboardTransaction
import id.kasta.app.presentation.components.KastaActionButton
import id.kasta.app.presentation.components.KastaEmptyState
import id.kasta.app.presentation.components.KastaMetricCard
import id.kasta.app.presentation.theme.KastaTheme
import id.kasta.app.transactions.formatRupiah

@Composable
fun HomeScreen(
    state: HomeUiState,
    onIncome: () -> Unit,
    onExpense: () -> Unit,
    onReceipt: () -> Unit,
    onTransactions: () -> Unit,
) {
    if (state.loading) {
        Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
            CircularProgressIndicator()
            Text("Menyiapkan beranda…", Modifier.padding(top = 12.dp))
        }
        return
    }
    val summary = state.summary
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text("Selamat datang", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            Text("Keuangan usaha Anda", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text("Ringkasan dari catatan yang tersimpan di perangkat.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            KastaMetricCard(
                label = "Saldo",
                value = formatRupiah(summary.balanceRupiah),
                icon = Icons.Rounded.AccountBalanceWallet,
                modifier = Modifier.fillMaxWidth(),
                supportingText = "Uang usaha saat ini",
            )
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                KastaMetricCard(
                    "Uang masuk hari ini",
                    formatRupiah(summary.incomeTodayRupiah),
                    Icons.Rounded.AddCircle,
                    Modifier.weight(1f),
                )
                KastaMetricCard(
                    "Uang keluar hari ini",
                    formatRupiah(summary.expenseTodayRupiah),
                    Icons.Rounded.RemoveCircle,
                    Modifier.weight(1f),
                )
            }
        }
        item {
            KastaMetricCard(
                "Perkiraan laba bulan ini",
                formatRupiah(summary.estimatedMonthlyProfitRupiah),
                Icons.AutoMirrored.Rounded.TrendingUp,
                Modifier.fillMaxWidth(),
                "Uang masuk dikurangi uang keluar",
            )
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                KastaMetricCard("Utang jatuh tempo", formatRupiah(summary.payablesDueRupiah), Icons.Rounded.MoneyOff, Modifier.weight(1f))
                KastaMetricCard(
                    "Piutang jatuh tempo",
                    formatRupiah(summary.receivablesDueRupiah),
                    Icons.Rounded.Payments,
                    Modifier.weight(1f),
                )
            }
        }
        item {
            Text(
                "Catat sekarang",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Black,
                modifier = Modifier.padding(top = 6.dp),
            )
            Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                KastaActionButton("Uang Masuk", Icons.Rounded.AddCircle, onIncome, Modifier.weight(1f))
                KastaActionButton("Uang Keluar", Icons.Rounded.RemoveCircle, onExpense, Modifier.weight(1f))
            }
            KastaActionButton("Foto Nota", Icons.Rounded.CameraAlt, onReceipt, Modifier.fillMaxWidth().padding(top = 10.dp))
        }
        item {
            Row(
                Modifier.fillMaxWidth().padding(top = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Transaksi terbaru", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
                Text("Lihat semua", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
        if (summary.latestTransactions.isEmpty()) {
            item { KastaEmptyState("Belum ada transaksi", "Tekan Uang Masuk atau Uang Keluar untuk mulai mencatat.") }
        } else {
            items(summary.latestTransactions, key = { it.id }) { transaction ->
                TransactionItem(transaction, onTransactions)
            }
        }
    }
}

@Composable
private fun TransactionItem(
    transaction: DashboardTransaction,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                Icons.AutoMirrored.Rounded.ReceiptLong,
                contentDescription = null,
                tint = if (transaction.isIncome) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.tertiary,
            )
            Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                Text(transaction.title, fontWeight = FontWeight.Bold)
                Text(
                    "${transaction.date} · ${syncLabel(transaction.syncStatus)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                "${if (transaction.isIncome) "+" else "−"}${formatRupiah(transaction.amountRupiah)}",
                fontWeight = FontWeight.Black,
                color = if (transaction.isIncome) MaterialTheme.colorScheme.primary else Color.Unspecified,
            )
        }
    }
}

private fun syncLabel(status: String): String =
    when (status) {
        "SYNCED" -> "Tersinkron"
        "CONFLICT" -> "Perlu diperiksa"
        "FAILED" -> "Gagal sinkron"
        else -> "Menunggu sinkron"
    }

@Preview(showBackground = true, backgroundColor = 0xFFF7F9F6, heightDp = 1100)
@Composable
private fun HomeScreenPreview() {
    KastaTheme(darkTheme = false) {
        HomeScreen(
            state =
                HomeUiState(
                    loading = false,
                    summary =
                        DashboardSummary(
                            balanceRupiah = 4_850_000,
                            incomeTodayRupiah = 750_000,
                            expenseTodayRupiah = 225_000,
                            estimatedMonthlyProfitRupiah = 3_400_000,
                            payablesDueRupiah = 500_000,
                            receivablesDueRupiah = 850_000,
                            latestTransactions =
                                listOf(
                                    DashboardTransaction("1", "Penjualan makan siang", "2026-07-22", 350_000, true, "SYNCED"),
                                    DashboardTransaction("2", "Belanja bahan", "2026-07-22", 175_000, false, "PENDING"),
                                ),
                        ),
                ),
            onIncome = {},
            onExpense = {},
            onReceipt = {},
            onTransactions = {},
        )
    }
}
