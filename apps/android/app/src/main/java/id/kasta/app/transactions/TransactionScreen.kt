package id.kasta.app.transactions

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import id.kasta.app.data.local.TransactionEntity

private val KIND_LABELS =
    mapOf(
        "INCOME" to "Uang Masuk",
        "EXPENSE" to "Uang Keluar",
        "CAPITAL" to "Tambah Modal",
        "OWNER_DRAW" to "Ambil Uang Pribadi",
    )

@Composable
fun TransactionScreen(
    state: TransactionUiState,
    onStart: (String) -> Unit,
    onOpenReceipt: () -> Unit,
    onOpenInventory: () -> Unit,
    onOpenObligations: () -> Unit,
    onChange: (TransactionForm) -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit,
    onClose: () -> Unit,
    onSave: (Boolean) -> Unit,
    onPostDraft: (TransactionEntity) -> Unit,
    onEdit: (TransactionEntity) -> Unit,
    onCancel: (TransactionEntity, String) -> Unit,
    onSearch: (String) -> Unit,
    onFilter: (String) -> Unit,
    onSync: () -> Unit,
    onOpenReports: () -> Unit = {},
    onOpenMentorAccess: () -> Unit = {},
    onOpenSyncStatus: () -> Unit = {},
) {
    if (state.step == 0) {
        TransactionHome(
            state = state,
            onStart = onStart,
            onOpenReceipt = onOpenReceipt,
            onOpenInventory = onOpenInventory,
            onOpenObligations = onOpenObligations,
            onPostDraft = onPostDraft,
            onEdit = onEdit,
            onCancel = onCancel,
            onSearch = onSearch,
            onFilter = onFilter,
            onSync = onSync,
            onOpenReports = onOpenReports,
            onOpenMentorAccess = onOpenMentorAccess,
            onOpenSyncStatus = onOpenSyncStatus,
        )
    } else {
        TransactionFormScreen(state, onChange, onNext, onBack, onClose, onSave)
    }
}

@Composable
private fun TransactionHome(
    state: TransactionUiState,
    onStart: (String) -> Unit,
    onOpenReceipt: () -> Unit,
    onOpenInventory: () -> Unit,
    onOpenObligations: () -> Unit,
    onPostDraft: (TransactionEntity) -> Unit,
    onEdit: (TransactionEntity) -> Unit,
    onCancel: (TransactionEntity, String) -> Unit,
    onSearch: (String) -> Unit,
    onFilter: (String) -> Unit,
    onSync: () -> Unit,
    onOpenReports: () -> Unit,
    onOpenMentorAccess: () -> Unit,
    onOpenSyncStatus: () -> Unit,
) {
    var cancelTarget by remember { mutableStateOf<TransactionEntity?>(null) }
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
                    Text("KASTA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
                    Text("Catatan usaha sehari-hari", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                OutlinedButton(onClick = onSync, enabled = !state.busy) { Text("Sinkronkan") }
            }
            state.notice?.let { Message(it, false) }
            state.error?.let { Message(it, true) }
            Spacer(Modifier.height(26.dp))
            Text("Keuangan usaha hari ini", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Spacer(Modifier.height(16.dp))
            listOf(
                "INCOME" to "Penjualan atau pendapatan usaha",
                "EXPENSE" to "Belanja dan biaya usaha",
                "CAPITAL" to "Masukkan uang pemilik ke usaha",
                "OWNER_DRAW" to "Ambil uang usaha untuk pemilik",
            ).chunked(2).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    row.forEach { (kind, hint) ->
                        Card(
                            onClick = { onStart(kind) },
                            modifier = Modifier.weight(1f).testTag("menu-${kind.lowercase()}"),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
                        ) {
                            Column(Modifier.padding(16.dp)) {
                                Text(KIND_LABELS.getValue(kind), fontWeight = FontWeight.ExtraBold)
                                Text(hint, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
            }
            Card(
                onClick = onOpenReceipt,
                modifier = Modifier.fillMaxWidth().testTag("menu-foto-nota"),
                colors =
                    CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer,
                    ),
            ) {
                Column(Modifier.padding(18.dp)) {
                    Text("Foto Nota", fontWeight = FontWeight.ExtraBold)
                    Text("Potret nota, periksa hasil bacaan, lalu buat transaksi")
                }
            }
            Spacer(Modifier.height(12.dp))
            OutlinedButton(
                onClick = onOpenInventory,
                modifier = Modifier.fillMaxWidth().testTag("menu-inventory"),
            ) {
                Text("Produk dan Stok")
            }
            OutlinedButton(
                onClick = onOpenObligations,
                modifier = Modifier.fillMaxWidth().testTag("menu-obligations"),
            ) {
                Text("Utang dan Piutang")
            }
            OutlinedButton(
                onClick = onOpenReports,
                modifier = Modifier.fillMaxWidth().testTag("menu-reports"),
            ) {
                Text("Laporan Keuangan")
            }
            OutlinedButton(
                onClick = onOpenMentorAccess,
                modifier = Modifier.fillMaxWidth().testTag("menu-mentor-access"),
            ) {
                Text("Akses Pembina")
            }
            OutlinedButton(
                onClick = onOpenSyncStatus,
                modifier = Modifier.fillMaxWidth().testTag("menu-sync-status"),
            ) {
                Text("Status Sinkronisasi")
            }

            val drafts = state.transactions.filter { it.isDraft }
            if (drafts.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                Text("Draft transaksi", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
                drafts.forEach { item ->
                    TransactionRow(item, onPostDraft = { onPostDraft(item) })
                }
            }

            Spacer(Modifier.height(24.dp))
            Text("Transaksi terakhir", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            OutlinedTextField(
                value = state.search,
                onValueChange = onSearch,
                label = { Text("Cari catatan atau nama") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("" to "Semua", "INCOME" to "Masuk", "EXPENSE" to "Keluar").forEach { (value, label) ->
                    FilterChip(
                        selected = state.kindFilter == value,
                        onClick = { onFilter(value) },
                        label = { Text(label) },
                    )
                }
            }
            state.visibleTransactions.filter { !it.isDraft }.forEach { item ->
                TransactionRow(
                    item = item,
                    onEdit =
                        if (item.serverId != null && item.serverStatus == "POSTED") {
                            ({ onEdit(item) })
                        } else {
                            null
                        },
                    onCancel =
                        if (item.serverId != null && item.serverStatus == "POSTED") {
                            ({ cancelTarget = item })
                        } else {
                            null
                        },
                )
            }
        }
    }
    cancelTarget?.let { item ->
        AlertDialog(
            onDismissRequest = { cancelTarget = null },
            title = { Text("Batalkan transaksi?") },
            text = {
                Column {
                    Text("Catatan lama tetap tersimpan. KASTA akan membuat catatan pembatalan.")
                    OutlinedTextField(
                        value = cancelReason,
                        onValueChange = { cancelReason = it },
                        label = { Text("Alasan pembatalan") },
                    )
                }
            },
            confirmButton = {
                Button(onClick = {
                    onCancel(item, cancelReason)
                    cancelTarget = null
                }) {
                    Text("Ya, batalkan")
                }
            },
            dismissButton = { TextButton(onClick = { cancelTarget = null }) { Text("Kembali") } },
        )
    }
}

@Composable
private fun TransactionFormScreen(
    state: TransactionUiState,
    onChange: (TransactionForm) -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit,
    onClose: () -> Unit,
    onSave: (Boolean) -> Unit,
) {
    val form = state.form
    val context = LocalContext.current
    val photoPicker =
        rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
            uri?.let {
                runCatching {
                    context.contentResolver.takePersistableUriPermission(
                        it,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION,
                    )
                }
                onChange(form.copy(receiptUri = it.toString()))
            }
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
                        text = KIND_LABELS.getValue(form.entryKind),
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "Langkah ${state.step} dari 3",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Black,
                        modifier = Modifier.testTag("transaction-progress"),
                    )
                }
                TextButton(onClick = onClose) { Text("Tutup") }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                repeat(3) { index ->
                    Card(
                        modifier = Modifier.weight(1f).height(8.dp),
                        colors =
                            CardDefaults.cardColors(
                                containerColor =
                                    if (index < state.step) {
                                        MaterialTheme.colorScheme.primary
                                    } else {
                                        MaterialTheme.colorScheme.surfaceVariant
                                    },
                            ),
                    ) {}
                }
            }
            state.error?.let { Message(it, true) }
            Spacer(Modifier.height(26.dp))
            when (state.step) {
                1 -> AmountStep(form, state.expenseCategories, onChange)
                2 -> DetailsStep(form, onChange, onPhoto = { photoPicker.launch(arrayOf("image/*")) })
                3 -> ReviewStep(form, state.editTargetServerId != null, onChange)
            }
            Spacer(Modifier.height(26.dp))
            HorizontalDivider()
            Spacer(Modifier.height(16.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                TextButton(onClick = onBack) { Text("Kembali") }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (state.step == 3 && state.editTargetServerId == null) {
                        OutlinedButton(onClick = { onSave(true) }, enabled = !state.busy) { Text("Simpan draft") }
                    }
                    Button(
                        onClick = if (state.step == 3) ({ onSave(false) }) else onNext,
                        enabled = !state.busy,
                        modifier = Modifier.testTag("transaction-next"),
                    ) {
                        Text(if (state.step == 3) "Catat transaksi" else "Lanjut")
                    }
                }
            }
        }
    }
}

@Composable
private fun AmountStep(
    form: TransactionForm,
    expenseCategories: List<Pair<String, String>>,
    onChange: (TransactionForm) -> Unit,
) {
    Text("Jumlah dan tanggal", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
    OutlinedTextField(
        value = form.transactionDate,
        onValueChange = { onChange(form.copy(transactionDate = it)) },
        label = { Text("Tanggal (YYYY-MM-DD)") },
        singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    )
    OutlinedTextField(
        value = formatRupiahDigits(form.amountDigits),
        onValueChange = { value -> onChange(form.copy(amountDigits = value.filter(Char::isDigit))) },
        label = { Text("Nominal Rupiah") },
        prefix = { Text("Rp ") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp).testTag("amount-input"),
    )
    val categories = if (form.entryKind == "INCOME") INCOME_SOURCES else expenseCategories
    if (form.entryKind in setOf("INCOME", "EXPENSE")) {
        Text(
            if (form.entryKind == "INCOME") "Sumber pemasukan" else "Kategori pengeluaran",
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 18.dp),
        )
        categories.forEach { (value, label) ->
            FilterChip(selected = form.categoryAccount == value, onClick = {
                onChange(form.copy(categoryAccount = value))
            }, label = { Text(label) }, modifier = Modifier.padding(end = 6.dp))
        }
    }
    Text(
        if (form.entryKind == "INCOME") "Metode penerimaan" else "Metode pembayaran",
        fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(top = 14.dp),
    )
    PAYMENT_METHODS.filter { (value, _) ->
        form.entryKind == "INCOME" || value in setOf("CASH", "BANK_TRANSFER", "CARD")
    }.forEach { (value, label) ->
        FilterChip(selected = form.paymentMethod == value, onClick = {
            onChange(form.copy(paymentMethod = value))
        }, label = { Text(label) }, modifier = Modifier.padding(end = 6.dp))
    }
}

@Composable
private fun DetailsStep(
    form: TransactionForm,
    onChange: (TransactionForm) -> Unit,
    onPhoto: () -> Unit,
) {
    Text("Tambahan (boleh dilewati)", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
    if (form.entryKind in setOf("INCOME", "EXPENSE")) {
        OutlinedTextField(value = form.counterpartyName, onValueChange = {
            onChange(form.copy(counterpartyName = it))
        }, label = {
            Text(
                if (form.entryKind == "INCOME") "Pelanggan" else "Pemasok",
            )
        }, modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
    }
    OutlinedTextField(value = form.note, onValueChange = {
        onChange(form.copy(note = it))
    }, label = { Text("Catatan") }, minLines = 3, modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
    OutlinedButton(onClick = onPhoto, modifier = Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Text(if (form.receiptUri == null) "Pilih foto bukti" else "Foto bukti dipilih")
    }
    Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text("Jadikan transaksi berulang", fontWeight = FontWeight.Bold)
        Checkbox(checked = form.recurring, onCheckedChange = { onChange(form.copy(recurring = it)) })
    }
    if (form.recurring) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = form.recurrenceFrequency == "WEEKLY", onClick = {
                onChange(form.copy(recurrenceFrequency = "WEEKLY"))
            }, label = { Text("Mingguan") })
            FilterChip(selected = form.recurrenceFrequency == "MONTHLY", onClick = {
                onChange(form.copy(recurrenceFrequency = "MONTHLY"))
            }, label = { Text("Bulanan") })
        }
    }
}

@Composable
private fun ReviewStep(
    form: TransactionForm,
    editing: Boolean,
    onChange: (TransactionForm) -> Unit,
) {
    Text("Periksa sebelum menyimpan", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
    ) {
        Column(Modifier.padding(18.dp)) {
            Text(KIND_LABELS.getValue(form.entryKind), fontWeight = FontWeight.Bold)
            Text(
                formatRupiah(form.amountDigits.toLongOrNull() ?: 0),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Black,
            )
            Text("${form.transactionDate} · ${PAYMENT_METHODS.firstOrNull { it.first == form.paymentMethod }?.second}")
            Text(form.note.ifBlank { "Tidak ada catatan" })
        }
    }
    if (editing) {
        OutlinedTextField(value = form.revisionReason, onValueChange = {
            onChange(form.copy(revisionReason = it))
        }, label = { Text("Alasan perubahan") }, minLines = 2, modifier = Modifier.fillMaxWidth().padding(top = 12.dp))
    }
    Message("KASTA membuat catatan keuangan berpasangan secara otomatis. Anda tidak perlu mengisi debit atau kredit.", false)
}

@Composable
private fun TransactionRow(
    item: TransactionEntity,
    onPostDraft: (() -> Unit)? = null,
    onEdit: (() -> Unit)? = null,
    onCancel: (() -> Unit)? = null,
) {
    Card(modifier = Modifier.fillMaxWidth().padding(top = 10.dp)) {
        Column(Modifier.padding(15.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text(item.note.ifBlank { KIND_LABELS[item.entryKind].orEmpty() }, fontWeight = FontWeight.Bold)
                    Text(
                        "${item.transactionDate} · ${item.statusLabel()}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(formatRupiah(item.amountRupiah), fontWeight = FontWeight.ExtraBold)
            }
            if (onPostDraft != null || onEdit != null || onCancel != null) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    onPostDraft?.let { TextButton(onClick = it) { Text("Posting") } }
                    onEdit?.let { TextButton(onClick = it) { Text("Ubah") } }
                    onCancel?.let { TextButton(onClick = it) { Text("Batalkan") } }
                }
            }
        }
    }
}

private fun TransactionEntity.statusLabel(): String =
    when {
        isDraft -> "Draft"
        syncStatus == "PENDING" -> "Menunggu sinkronisasi"
        syncStatus == "SYNCING" -> "Sedang disinkronkan"
        syncStatus == "FAILED" -> "Perlu dicoba lagi"
        syncStatus == "CONFLICT" -> "Perlu memilih versi"
        serverStatus == "REVERSED" -> "Dibatalkan"
        else -> "Tercatat"
    }

@Composable
private fun Message(
    text: String,
    error: Boolean,
) {
    Card(
        colors =
            CardDefaults.cardColors(
                containerColor = if (error) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
            ),
        modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
    ) { Text(text, modifier = Modifier.padding(14.dp)) }
}
