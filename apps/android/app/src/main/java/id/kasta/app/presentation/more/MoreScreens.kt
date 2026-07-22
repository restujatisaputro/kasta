package id.kasta.app.presentation.more

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AccountBalance
import androidx.compose.material.icons.rounded.AccountBalanceWallet
import androidx.compose.material.icons.rounded.Inventory2
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material.icons.rounded.People
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Storefront
import androidx.compose.material.icons.rounded.Sync
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import id.kasta.app.data.local.AppPreferenceState
import id.kasta.app.presentation.theme.KastaTheme
import id.kasta.app.transactions.TransactionUiState
import id.kasta.app.transactions.formatRupiah

data class MoreMenuItem(
    val label: String,
    val icon: ImageVector,
    val route: String,
)

@Composable
fun MoreScreen(onNavigate: (String) -> Unit) {
    val menus =
        listOf(
            MoreMenuItem("Produk", Icons.Rounded.Storefront, "products"),
            MoreMenuItem("Stok", Icons.Rounded.Inventory2, "stock"),
            MoreMenuItem("Utang", Icons.Rounded.AccountBalance, "payables"),
            MoreMenuItem("Piutang", Icons.Rounded.AccountBalanceWallet, "receivables"),
            MoreMenuItem("Pembina", Icons.Rounded.People, "mentor"),
            MoreMenuItem("Profil", Icons.Rounded.Person, "profile"),
            MoreMenuItem("Sinkronisasi", Icons.Rounded.Sync, "sync"),
            MoreMenuItem("Konflik data", Icons.Rounded.Warning, "conflicts"),
            MoreMenuItem("Notifikasi", Icons.Rounded.Notifications, "notifications"),
            MoreMenuItem("Pengaturan", Icons.Rounded.Settings, "settings"),
        )
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("Lainnya", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text("Kelola usaha, tagihan, dan akun.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            modifier = Modifier.fillMaxSize().padding(top = 18.dp),
            contentPadding = PaddingValues(bottom = 90.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(menus, key = { it.route }) { menu ->
                Card(
                    onClick = { onNavigate(menu.route) },
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                ) {
                    Column(Modifier.padding(18.dp)) {
                        Icon(menu.icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Text(menu.label, Modifier.padding(top = 18.dp), fontWeight = FontWeight.ExtraBold)
                    }
                }
            }
        }
    }
}

@Composable
fun ProfileScreen(onBack: () -> Unit) {
    var name by remember { mutableStateOf("Usaha Saya") }
    var phone by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Profil usaha", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text("Informasi ini tampil pada ruang usaha Anda.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            androidx.compose.material3.OutlinedTextField(
                name,
                { name = it },
                label = { Text("Nama usaha") },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        item {
            androidx.compose.material3.OutlinedTextField(phone, {
                phone = it
            }, label = { Text("Nomor telepon usaha") }, modifier = Modifier.fillMaxWidth())
        }
        item {
            androidx.compose.material3.OutlinedTextField("IDR", {
            }, enabled = false, label = { Text("Mata uang") }, modifier = Modifier.fillMaxWidth())
        }
        item { Button(onClick = {}, modifier = Modifier.fillMaxWidth()) { Text("Simpan perubahan") } }
        item { OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Kembali") } }
    }
}

@Composable
fun SettingsScreen(
    state: AppPreferenceState,
    onDarkMode: (Boolean) -> Unit,
    onNotifications: (Boolean) -> Unit,
    onLogout: () -> Unit,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Pengaturan", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text("Sesuaikan pengalaman menggunakan KASTA.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item { PreferenceRow("Mode gelap", "Kurangi cahaya pada layar", state.darkMode, onDarkMode) }
        item { PreferenceRow("Notifikasi", "Pengingat transaksi dan jatuh tempo", state.notificationsEnabled, onNotifications) }
        item { HorizontalDivider() }
        item { OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) { Text("Keluar dari perangkat ini") } }
    }
}

@Composable
private fun PreferenceRow(
    title: String,
    description: String,
    checked: Boolean,
    onChecked: (Boolean) -> Unit,
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold)
                Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(checked, onChecked)
        }
    }
}

@Composable
fun OcrConfirmationScreen(
    onConfirm: () -> Unit,
    onBack: () -> Unit,
) {
    var merchant by remember { mutableStateOf("") }
    var total by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Periksa hasil nota", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text(
                "Koreksi bagian yang belum tepat. Transaksi tidak dibuat sebelum Anda mengonfirmasi.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        item {
            androidx.compose.material3.OutlinedTextField(merchant, {
                merchant = it
            }, label = { Text("Nama toko") }, modifier = Modifier.fillMaxWidth())
        }
        item {
            androidx.compose.material3.OutlinedTextField(total, {
                total = it.filter(Char::isDigit)
            }, label = { Text("Total") }, prefix = { Text("Rp") }, modifier = Modifier.fillMaxWidth())
        }
        item {
            androidx.compose.material3.OutlinedTextField("Pembelian / Uang Keluar", {
            }, label = { Text("Jenis transaksi") }, modifier = Modifier.fillMaxWidth())
        }
        item { Button(onClick = onConfirm, modifier = Modifier.fillMaxWidth()) { Text("Konfirmasi dan lanjutkan") } }
        item { OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Ambil foto lagi") } }
    }
}

@Composable
fun ConflictResolutionScreen(
    state: TransactionUiState,
    onUseServer: (String) -> Unit,
    onUseLocal: (String) -> Unit,
    onBack: () -> Unit,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text("Penyelesaian konflik", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text(
                "Transaksi keuangan tidak ditimpa otomatis. Pilih versi setelah memeriksa datanya.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        if (state.conflicts.isEmpty()) {
            item { Text("Tidak ada konflik yang perlu diselesaikan.", modifier = Modifier.padding(vertical = 32.dp)) }
        } else {
            items(state.conflicts.size, key = { state.conflicts[it].localId }) { index ->
                val item = state.conflicts[index]
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Column(Modifier.padding(16.dp)) {
                        Icon(Icons.Rounded.Warning, contentDescription = null)
                        Text(item.note.ifBlank { "Transaksi ${item.transactionDate}" }, fontWeight = FontWeight.Black)
                        Text(formatRupiah(item.amountRupiah), style = MaterialTheme.typography.titleLarge)
                        Text("Versi lokal ${item.version} · versi server ${item.conflictServerVersion ?: "-"}")
                        Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { onUseServer(item.localId) }, modifier = Modifier.weight(1f)) { Text("Pakai server") }
                            Button(onClick = { onUseLocal(item.localId) }, modifier = Modifier.weight(1f)) { Text("Pakai lokal") }
                        }
                    }
                }
            }
        }
        item { OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Kembali") } }
    }
}

@Preview(showBackground = true)
@Composable
private fun MorePreview() {
    KastaTheme(darkTheme = false) { MoreScreen {} }
}

@Preview(showBackground = true)
@Composable
private fun SettingsPreview() {
    KastaTheme(darkTheme = false) { SettingsScreen(AppPreferenceState(), {}, {}, {}) }
}
