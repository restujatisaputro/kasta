package id.kasta.app.obligations

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import id.kasta.app.data.remote.ObligationDto
import id.kasta.app.transactions.formatRupiah

private val statusChoices =
    listOf(
        "" to "Semua",
        "OPEN" to "Belum Dibayar",
        "PARTIALLY_PAID" to "Dibayar Sebagian",
        "PAID" to "Sudah Lunas",
        "OVERDUE" to "Terlambat",
    )

@Composable
fun ObligationScreen(
    state: ObligationUiState,
    onBack: () -> Unit,
    onSwitchKind: (String) -> Unit,
    onRefresh: () -> Unit,
    onFilters: (String?, String?, String?, Boolean?) -> Unit,
    onOpenCreate: () -> Unit,
    onFormChange: (ObligationForm) -> Unit,
    onSave: () -> Unit,
    onCloseCreate: () -> Unit,
    onOpenPayment: (ObligationDto) -> Unit,
    onPaymentChange: (ObligationPaymentForm) -> Unit,
    onPay: () -> Unit,
    onClosePayment: () -> Unit,
    onHistory: (ObligationDto) -> Unit,
    onCloseHistory: () -> Unit,
    onCancel: (ObligationDto, String) -> Unit,
) {
    var cancelTarget by remember { mutableStateOf<ObligationDto?>(null) }
    var cancelReason by remember { mutableStateOf("") }
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
                        "Utang dan Piutang",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                    )
                    Text("Pantau jatuh tempo dan sisa tagihan")
                }
                TextButton(onClick = onBack) { Text("Kembali") }
            }
            state.notice?.let { Message(it, false) }
            state.error?.let { Message(it, true) }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = state.kind == "RECEIVABLE",
                    onClick = { onSwitchKind("RECEIVABLE") },
                    label = { Text("Piutang pelanggan") },
                    modifier = Modifier.weight(1f),
                )
                FilterChip(
                    selected = state.kind == "PAYABLE",
                    onClick = { onSwitchKind("PAYABLE") },
                    label = { Text("Utang pemasok") },
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(12.dp))
            Card(
                Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            ) {
                Column(Modifier.padding(18.dp)) {
                    Text("Total belum lunas")
                    val total =
                        if (state.kind == "RECEIVABLE") {
                            state.aging?.receivables?.totalOpen
                        } else {
                            state.aging?.payables?.totalOpen
                        }
                    Text(formatMoney(total ?: "0"), fontWeight = FontWeight.Black)
                    Text("${state.reminderCount} tagihan perlu diingatkan")
                }
            }
            Button(onClick = onOpenCreate, modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) {
                Text("Tambah ${if (state.kind == "RECEIVABLE") "piutang" else "utang"}")
            }
            OutlinedTextField(
                value = state.query,
                onValueChange = { onFilters(it, null, null, null) },
                label = { Text("Cari pelanggan, pemasok, atau catatan") },
                trailingIcon = { TextButton(onClick = onRefresh) { Text("Cari") } },
                modifier = Modifier.fillMaxWidth(),
            )
            Text("Filter status", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 12.dp))
            statusChoices.forEach { (value, label) ->
                FilterChip(
                    selected = state.status == value,
                    onClick = {
                        onFilters(null, value, null, null)
                        onRefresh()
                    },
                    label = { Text(label) },
                )
            }
            Row {
                Checkbox(
                    checked = state.overdueOnly,
                    onCheckedChange = {
                        onFilters(null, null, null, it)
                        onRefresh()
                    },
                )
                Text("Hanya yang terlambat", modifier = Modifier.padding(top = 12.dp))
            }
            if (state.items.isEmpty() && !state.busy) {
                Text("Belum ada catatan pada filter ini.", modifier = Modifier.padding(vertical = 24.dp))
            }
            state.items.forEach { item ->
                ObligationCard(
                    item,
                    onOpenPayment,
                    onHistory,
                    onCancel = {
                        cancelTarget = item
                        cancelReason = ""
                    },
                )
            }
        }
    }
    state.form?.let {
        ObligationDialog(it, state.kind, onFormChange, onSave, onCloseCreate, state.busy)
    }
    state.paymentTarget?.let {
        PaymentDialog(
            it,
            state.paymentForm,
            onPaymentChange,
            onPay,
            onClosePayment,
            state.busy,
        )
    }
    state.history?.let { HistoryDialog(it, onCloseHistory) }
    cancelTarget?.let { item ->
        AlertDialog(
            onDismissRequest = { cancelTarget = null },
            title = { Text("Batalkan tagihan") },
            text = {
                Column {
                    Text("Pembatalan akan membuat catatan pembalik.")
                    ObligationField("Alasan", cancelReason) { cancelReason = it }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onCancel(item, cancelReason)
                        cancelTarget = null
                    },
                    enabled = cancelReason.length >= 3,
                ) { Text("Batalkan tagihan") }
            },
            dismissButton = { TextButton(onClick = { cancelTarget = null }) { Text("Kembali") } },
        )
    }
}

@Composable
private fun ObligationCard(
    item: ObligationDto,
    onPay: (ObligationDto) -> Unit,
    onHistory: (ObligationDto) -> Unit,
    onCancel: () -> Unit,
) {
    Card(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(item.party.name, fontWeight = FontWeight.ExtraBold)
                    Text("Jatuh tempo ${item.dueDate}")
                }
                Text(
                    item.statusLabel.ifBlank { obligationStatusLabel(item.status) },
                    color =
                        if (item.status == "OVERDUE") {
                            MaterialTheme.colorScheme.error
                        } else {
                            MaterialTheme.colorScheme.primary
                        },
                    fontWeight = FontWeight.Bold,
                )
            }
            Text("Sisa ${formatMoney(item.remainingAmount)}", fontWeight = FontWeight.Black)
            Text("Nilai awal ${formatMoney(item.initialAmount)}")
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                if (item.status !in listOf("PAID", "CANCELLED")) {
                    Button(onClick = { onPay(item) }) { Text("Catat bayar") }
                }
                TextButton(onClick = { onHistory(item) }) { Text("Riwayat") }
                if (item.paidAmount.toBigDecimalOrNull()?.signum() == 0 && item.status != "CANCELLED") {
                    TextButton(onClick = onCancel) { Text("Batalkan") }
                }
            }
        }
    }
}

@Composable
private fun ObligationDialog(
    form: ObligationForm,
    kind: String,
    onChange: (ObligationForm) -> Unit,
    onSave: () -> Unit,
    onClose: () -> Unit,
    busy: Boolean,
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Tambah ${if (kind == "RECEIVABLE") "piutang" else "utang"}") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                ObligationField(if (kind == "RECEIVABLE") "Nama pelanggan" else "Nama pemasok", form.partyName) {
                    onChange(form.copy(partyName = it))
                }
                ObligationField("Nilai awal", form.initialAmount, true) { onChange(form.copy(initialAmount = it)) }
                ObligationField("Tanggal transaksi", form.transactionDate) { onChange(form.copy(transactionDate = it)) }
                ObligationField("Tanggal jatuh tempo", form.dueDate) { onChange(form.copy(dueDate = it)) }
                ObligationField("Ingatkan berapa hari sebelumnya", form.reminderDaysBefore, true) {
                    onChange(form.copy(reminderDaysBefore = it))
                }
                ObligationField("Catatan", form.note) { onChange(form.copy(note = it)) }
            }
        },
        confirmButton = { Button(onClick = onSave, enabled = !busy) { Text("Simpan") } },
        dismissButton = { TextButton(onClick = onClose) { Text("Kembali") } },
    )
}

@Composable
private fun PaymentDialog(
    item: ObligationDto,
    form: ObligationPaymentForm,
    onChange: (ObligationPaymentForm) -> Unit,
    onSave: () -> Unit,
    onClose: () -> Unit,
    busy: Boolean,
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Catat pembayaran") },
        text = {
            Column {
                Text("${item.party.name} · sisa ${formatMoney(item.remainingAmount)}")
                ObligationField("Jumlah dibayar", form.amount, true) { onChange(form.copy(amount = it)) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = form.paymentAccount == "CASH",
                        onClick = { onChange(form.copy(paymentAccount = "CASH")) },
                        label = { Text("Kas") },
                    )
                    FilterChip(
                        selected = form.paymentAccount == "BANK",
                        onClick = { onChange(form.copy(paymentAccount = "BANK")) },
                        label = { Text("Bank") },
                    )
                }
                ObligationField("Catatan", form.note) { onChange(form.copy(note = it)) }
            }
        },
        confirmButton = { Button(onClick = onSave, enabled = !busy) { Text("Simpan pembayaran") } },
        dismissButton = { TextButton(onClick = onClose) { Text("Kembali") } },
    )
}

@Composable
private fun HistoryDialog(
    item: ObligationDto,
    onClose: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Riwayat pembayaran") },
        text = {
            Column {
                Text(item.party.name, fontWeight = FontWeight.Bold)
                if (item.payments.isNullOrEmpty()) Text("Belum ada pembayaran.")
                item.payments.orEmpty().forEach { payment ->
                    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Column(Modifier.padding(12.dp)) {
                            Text(formatMoney(payment.amount), fontWeight = FontWeight.Black)
                            Text("${payment.paymentDate} · ${if (payment.paymentAccountKey == "CASH") "Kas" else "Bank"}")
                            payment.note?.let { Text(it) }
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("Tutup") } },
    )
}

@Composable
private fun ObligationField(
    label: String,
    value: String,
    numeric: Boolean = false,
    onChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions =
            KeyboardOptions(
                keyboardType = if (numeric) KeyboardType.Decimal else KeyboardType.Text,
            ),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun Message(
    text: String,
    error: Boolean,
) {
    Text(
        text,
        color = if (error) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(vertical = 8.dp),
    )
}

private fun formatMoney(value: String): String = formatRupiah(value.toBigDecimalOrNull()?.toLong() ?: 0L)
