package id.kasta.app.mentoraccess

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import id.kasta.app.data.remote.MentorAccessDto

private val scopeLabels =
    linkedMapOf(
        "SUMMARY" to "Melihat ringkasan",
        "REPORTS" to "Melihat laporan",
        "TRANSACTIONS" to "Melihat transaksi",
        "RECEIPTS" to "Melihat nota",
        "INVENTORY" to "Melihat stok",
        "OBLIGATIONS" to "Melihat utang dan piutang",
        "EXPORT_REPORTS" to "Mengunduh laporan",
    )

@Composable
fun MentorAccessScreen(
    state: MentorAccessUiState,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onDecide: (String, Boolean, List<String>, String?, String?) -> Unit,
    onRevoke: (String, String) -> Unit,
) {
    var decisionTarget by remember { mutableStateOf<MentorAccessDto?>(null) }
    var revokeTarget by remember { mutableStateOf<MentorAccessDto?>(null) }
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
                    Text("Akses Pembina", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                    Text("Anda menentukan data yang boleh dilihat")
                }
                TextButton(onClick = onBack) { Text("Kembali") }
            }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            state.notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
            OutlinedButton(onClick = onRefresh, enabled = !state.busy) { Text("Muat ulang") }
            Spacer(Modifier.height(12.dp))
            if (state.items.isEmpty() && !state.busy) Text("Belum ada permintaan akses pembina.")
            state.items.forEach { access ->
                Card(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Column(Modifier.padding(16.dp)) {
                        Text("Pembina ${access.mentorId.take(8)}", fontWeight = FontWeight.Bold)
                        Text("Status: ${access.status}")
                        access.requestMessage?.let { Text("“$it”") }
                        Text(access.scope.mapNotNull(scopeLabels::get).joinToString(" · "))
                        access.lastAccessedAt?.let { Text("Terakhir melihat: $it") }
                        if (access.status == "REQUESTED") {
                            Button(onClick = { decisionTarget = access }, enabled = !state.busy) {
                                Text("Periksa permintaan")
                            }
                        } else if (access.status == "ACTIVE") {
                            OutlinedButton(onClick = { revokeTarget = access }, enabled = !state.busy) {
                                Text("Cabut izin")
                            }
                        }
                    }
                }
            }
            Spacer(Modifier.height(20.dp))
            Text("Riwayat akses", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            state.history.forEach { item ->
                Text("${item.action} · ${item.accessedAt}", modifier = Modifier.padding(vertical = 5.dp))
            }
        }
    }
    decisionTarget?.let { access ->
        DecisionDialog(
            access = access,
            onDismiss = { decisionTarget = null },
            onSubmit = { approve, scopes, expiry, reason ->
                decisionTarget = null
                onDecide(access.id, approve, scopes, expiry, reason)
            },
        )
    }
    revokeTarget?.let { access ->
        RevokeDialog(
            onDismiss = { revokeTarget = null },
            onSubmit = { reason ->
                revokeTarget = null
                onRevoke(access.id, reason)
            },
        )
    }
}

@Composable
private fun DecisionDialog(
    access: MentorAccessDto,
    onDismiss: () -> Unit,
    onSubmit: (Boolean, List<String>, String?, String?) -> Unit,
) {
    var selected by remember { mutableStateOf(access.scope.toSet()) }
    var expiry by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Pilih izin pembina") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                scopeLabels.forEach { (scope, label) ->
                    Row {
                        Checkbox(
                            checked = scope in selected,
                            onCheckedChange = {
                                selected = if (it) selected + scope else selected - scope
                            },
                        )
                        Text(label, modifier = Modifier.padding(top = 12.dp))
                    }
                }
                OutlinedTextField(
                    value = expiry,
                    onValueChange = { expiry = it },
                    label = { Text("Berlaku sampai (YYYY-MM-DD)") },
                )
                OutlinedTextField(value = reason, onValueChange = { reason = it }, label = { Text("Alasan penolakan") })
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val instant = expiry.takeIf(String::isNotBlank)?.plus("T23:59:59+07:00")
                    onSubmit(true, selected.toList(), instant, null)
                },
                enabled = selected.isNotEmpty() && expiry.isNotBlank(),
            ) { Text("Setujui") }
        },
        dismissButton = {
            TextButton(onClick = { onSubmit(false, emptyList(), null, reason) }, enabled = reason.length >= 3) {
                Text("Tolak")
            }
        },
    )
}

@Composable
private fun RevokeDialog(
    onDismiss: () -> Unit,
    onSubmit: (String) -> Unit,
) {
    var reason by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Cabut izin pembina?") },
        text = {
            OutlinedTextField(value = reason, onValueChange = { reason = it }, label = { Text("Alasan pencabutan") })
        },
        confirmButton = {
            Button(onClick = { onSubmit(reason) }, enabled = reason.length >= 3) { Text("Cabut izin") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Batal") } },
    )
}
