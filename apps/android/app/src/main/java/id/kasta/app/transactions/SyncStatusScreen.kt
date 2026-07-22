package id.kasta.app.transactions

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import id.kasta.app.data.local.TransactionEntity

@Composable
fun SyncStatusScreen(
    state: TransactionUiState,
    onBack: () -> Unit,
    onSync: () -> Unit,
    onUseServer: (TransactionEntity) -> Unit,
    onUseLocal: (TransactionEntity) -> Unit,
) {
    Scaffold { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
        ) {
            TextButton(onClick = onBack) { Text("Kembali") }
            Text(
                "Status Sinkronisasi",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Black,
            )
            Text("Data di layar selalu berasal dari penyimpanan perangkat (Room).")
            Text(
                "Terakhir berhasil: ${state.lastSyncAt ?: "Belum pernah"}",
                modifier = Modifier.padding(top = 8.dp),
            )
            Text("Cursor: ${state.syncCursor}", style = MaterialTheme.typography.bodySmall)
            Row(
                Modifier.fillMaxWidth().padding(vertical = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                SyncCount("Menunggu", state.syncCounts["PENDING"] ?: 0, Modifier.weight(1f))
                SyncCount("Gagal", state.syncCounts["FAILED"] ?: 0, Modifier.weight(1f))
                SyncCount("Konflik", state.syncCounts["CONFLICT"] ?: 0, Modifier.weight(1f))
            }
            Button(
                onClick = onSync,
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth().testTag("sync-now"),
            ) { Text("Coba sinkronkan sekarang") }
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            Text(
                "Perlu diselesaikan",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 24.dp),
            )
            if (state.conflicts.isEmpty()) {
                Text("Tidak ada konflik transaksi.", modifier = Modifier.padding(top = 10.dp))
            }
            state.conflicts.forEach { item ->
                Card(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp)
                        .testTag("sync-conflict"),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(item.note.ifBlank { "Transaksi ${item.transactionDate}" }, fontWeight = FontWeight.Bold)
                        Text("Versi perangkat: ${item.version}; versi server: ${item.conflictServerVersion ?: "-"}")
                        Text("Transaksi keuangan tidak pernah ditimpa otomatis.")
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { onUseServer(item) }) { Text("Gunakan server") }
                            Button(onClick = { onUseLocal(item) }) { Text("Buat revisi saya") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SyncCount(
    label: String,
    value: Int,
    modifier: Modifier = Modifier,
) {
    Card(modifier) {
        Column(Modifier.padding(12.dp)) {
            Text(value.toString(), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text(label, style = MaterialTheme.typography.bodySmall)
        }
    }
}
