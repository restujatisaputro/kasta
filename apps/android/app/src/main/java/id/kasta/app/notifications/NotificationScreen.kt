package id.kasta.app.notifications

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Notifications
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import id.kasta.app.data.local.DEFAULT_NOTIFICATION_CATEGORIES
import id.kasta.app.data.local.NotificationEntity
import id.kasta.app.presentation.components.KastaEmptyState
import id.kasta.app.presentation.theme.KastaTheme

private val categoryLabels =
    linkedMapOf(
        "NO_TRANSACTION_TODAY" to "Belum mencatat hari ini",
        "PAYABLE_DUE_SOON" to "Utang mendekati jatuh tempo",
        "RECEIVABLE_DUE_SOON" to "Piutang mendekati jatuh tempo",
        "LOW_STOCK" to "Stok minimum",
        "OCR_NEEDS_REVIEW" to "Hasil foto nota perlu diperiksa",
        "SYNC_FAILED" to "Sinkronisasi gagal",
        "MENTOR_ACCESS_REQUEST" to "Permintaan akses pembina",
        "NEW_RECOMMENDATION" to "Rekomendasi baru",
        "MENTORING_SCHEDULE" to "Jadwal pendampingan",
        "MONTHLY_REPORT_AVAILABLE" to "Laporan bulanan tersedia",
    )

@Composable
fun NotificationScreen(
    state: NotificationUiState,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onOpen: (NotificationEntity) -> Unit,
    onMarkAllRead: () -> Unit,
    onCategory: (String, Boolean) -> Unit,
    onReminderTime: (String) -> Unit,
    onQuietHours: (Boolean, String, String) -> Unit,
) {
    val settings = state.appPreferences
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Notifikasi", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
            Text(
                "Pengingat penting untuk kegiatan dan keuangan usaha.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        state.error?.let { message ->
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(message, color = MaterialTheme.colorScheme.error)
                        OutlinedButton(onClick = onRefresh) { Text("Coba lagi") }
                    }
                }
            }
        }
        if (state.loading) {
            item { CircularProgressIndicator() }
        } else if (state.items.isEmpty()) {
            item { KastaEmptyState("Belum ada notifikasi", "Pengingat baru akan tampil di sini.") }
        } else {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Kotak masuk", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
                    Button(onClick = onMarkAllRead) { Text("Tandai semua dibaca") }
                }
            }
            items(state.items, key = { it.localId }) { item ->
                NotificationCard(item) { onOpen(item) }
            }
        }
        item { HorizontalDivider(Modifier.padding(vertical = 8.dp)) }
        item {
            Text("Atur pengingat", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text("Pilih jenis pesan yang ingin diterima.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        items(categoryLabels.entries.toList(), key = { it.key }) { category ->
            Card(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(category.value, Modifier.weight(1f), fontWeight = FontWeight.Bold)
                    Switch(
                        checked = category.key in settings.enabledNotificationCategories,
                        onCheckedChange = { onCategory(category.key, it) },
                    )
                }
            }
        }
        item {
            OutlinedTextField(
                value = "%02d:%02d".format(settings.reminderHour, settings.reminderMinute),
                onValueChange = onReminderTime,
                label = { Text("Waktu pengingat (JJ:MM)") },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("Jam tenang", fontWeight = FontWeight.Bold)
                            Text("Notifikasi ditunda selama waktu ini.")
                        }
                        Switch(
                            settings.quietHoursEnabled,
                            { onQuietHours(it, settings.quietStart, settings.quietEnd) },
                        )
                    }
                    if (settings.quietHoursEnabled) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                settings.quietStart,
                                { onQuietHours(true, it, settings.quietEnd) },
                                label = { Text("Mulai") },
                                modifier = Modifier.weight(1f),
                            )
                            OutlinedTextField(
                                settings.quietEnd,
                                { onQuietHours(true, settings.quietStart, it) },
                                label = { Text("Selesai") },
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        }
        item { OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Kembali") } }
    }
}

@Composable
private fun NotificationCard(
    item: NotificationEntity,
    onOpen: () -> Unit,
) {
    Card(onClick = onOpen, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.Top) {
            Icon(Icons.Rounded.Notifications, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Column(Modifier.padding(start = 12.dp).weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(item.title, Modifier.weight(1f), fontWeight = FontWeight.Black)
                    if (item.readAt == null) Text("Baru", color = MaterialTheme.colorScheme.primary)
                }
                Text(item.message, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text("Buka detail", Modifier.padding(top = 6.dp), color = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun NotificationPreview() {
    KastaTheme(darkTheme = false) {
        NotificationScreen(
            NotificationUiState(
                loading = false,
                appPreferences =
                    id.kasta.app.data.local.AppPreferenceState(
                        enabledNotificationCategories = DEFAULT_NOTIFICATION_CATEGORIES,
                    ),
                items =
                    listOf(
                        NotificationEntity(
                            "1",
                            "1",
                            "business",
                            "LOW_STOCK",
                            "Stok menipis",
                            "Stok Kopi Arabika tersisa 2 bungkus.",
                            "PRODUCT",
                            "product",
                            "/stok",
                            null,
                            null,
                            "2026-07-22T10:00:00Z",
                        ),
                    ),
            ),
            {},
            {},
            {},
            {},
            { _, _ -> },
            {},
            { _, _, _ -> },
        )
    }
}
