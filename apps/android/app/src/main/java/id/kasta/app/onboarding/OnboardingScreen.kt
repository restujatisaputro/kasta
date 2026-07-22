package id.kasta.app.onboarding

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import id.kasta.app.data.remote.BusinessCategoryDto
import id.kasta.app.data.remote.BusinessProfileDto

private const val TOTAL_STEPS = 9

private val businessTypes =
    listOf(
        "TRADE" to "Jual beli",
        "CULINARY" to "Makanan & minuman",
        "SERVICE" to "Jasa",
        "PRODUCTION" to "Produksi",
        "CREATIVE" to "Kreatif",
        "AGRICULTURE" to "Tani & ternak",
        "OTHER" to "Lainnya",
    )

private val paymentOptions =
    listOf(
        "CASH" to "Tunai",
        "BANK_TRANSFER" to "Transfer bank",
        "QRIS" to "QRIS",
        "E_WALLET" to "Dompet digital",
        "CARD" to "Kartu debit/kredit",
    )

@Composable
fun OnboardingScreen(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
    onCreateAccount: () -> Unit,
    onVerify: () -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit,
    onFinish: () -> Unit,
    onOpenTransactions: () -> Unit = {},
) {
    if (state.screen == OnboardingScreen.PROFILE && state.profile != null) {
        BusinessProfileScreen(state.profile, onOpenTransactions)
        return
    }
    Scaffold { contentPadding ->
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .padding(contentPadding)
                    .navigationBarsPadding()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 22.dp, vertical = 24.dp),
        ) {
            Text("KASTA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
            Spacer(Modifier.height(22.dp))
            Text(
                "Langkah ${state.step} dari $TOTAL_STEPS",
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier.testTag("progress-label"),
            )
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { state.step / TOTAL_STEPS.toFloat() },
                modifier = Modifier.fillMaxWidth(),
            )
            state.notice?.let {
                Spacer(Modifier.height(16.dp))
                MessageCard(it, false)
            }
            state.error?.let {
                Spacer(Modifier.height(16.dp))
                MessageCard(it, true)
            }
            Spacer(Modifier.height(28.dp))
            when (state.step) {
                1 -> AccountStep(state, onChange, onCreateAccount)
                2 -> VerificationStep(state, onChange, onVerify)
                3 -> OwnerStep { onChange(state.copy(step = 4)) }
                4 -> BusinessStep(state, onChange)
                5 -> ScaleStep(state, onChange)
                6 -> AddressStep(state, onChange)
                7 -> PreferencesStep(state, onChange)
                8 -> OpeningStep(state, onChange)
                9 -> TutorialStep(state, onChange)
            }
            if (state.step >= 4) {
                Spacer(Modifier.height(28.dp))
                HorizontalDivider()
                Spacer(Modifier.height(18.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = onBack) { Text("Kembali") }
                    Button(
                        onClick = if (state.step == TOTAL_STEPS) onFinish else onNext,
                        enabled = !state.busy,
                    ) {
                        Text(
                            if (state.busy) {
                                "Menyimpan…"
                            } else if (state.step == TOTAL_STEPS) {
                                "Selesaikan"
                            } else {
                                "Lanjut"
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AccountStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
    onSubmit: () -> Unit,
) {
    StepHeading("Selamat datang", "Buat akun KASTA", "Gunakan email atau nomor telepon yang aktif.")
    ChoiceRow(
        options = listOf(true to "Email", false to "Nomor telepon"),
        selected = state.accountUsesEmail,
    ) { onChange(state.copy(accountUsesEmail = it, identifier = "")) }
    SimpleField("Nama lengkap", state.fullName) { onChange(state.copy(fullName = it)) }
    SimpleField(
        if (state.accountUsesEmail) "Email" else "Nomor telepon",
        state.identifier,
        keyboardType = if (state.accountUsesEmail) KeyboardType.Email else KeyboardType.Phone,
    ) { onChange(state.copy(identifier = it)) }
    OutlinedTextField(
        value = state.password,
        onValueChange = { onChange(state.copy(password = it)) },
        label = { Text("Password (minimal 12 karakter)") },
        visualTransformation = PasswordVisualTransformation(),
        singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    )
    Button(
        onClick = onSubmit,
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth().padding(top = 22.dp),
    ) { Text(if (state.busy) "Membuat akun…" else "Buat akun") }
}

@Composable
private fun VerificationStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
    onSubmit: () -> Unit,
) {
    StepHeading(
        "Periksa pesan Anda",
        "Verifikasi akun",
        "Tempel kode verifikasi dari email atau SMS.",
    )
    OutlinedTextField(
        value = state.verificationToken,
        onValueChange = { onChange(state.copy(verificationToken = it)) },
        label = { Text("Kode verifikasi") },
        minLines = 3,
        modifier = Modifier.fillMaxWidth().padding(top = 18.dp),
    )
    Button(
        onClick = onSubmit,
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth().padding(top = 22.dp),
    ) { Text(if (state.busy) "Memeriksa…" else "Verifikasi akun") }
}

@Composable
private fun OwnerStep(onChoose: () -> Unit) {
    StepHeading("Peran Anda", "Bagaimana Anda menggunakan KASTA?", null)
    Card(
        onClick = onChoose,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
    ) {
        Column(Modifier.padding(20.dp)) {
            Text("🏪  Saya Pemilik UMKM", fontWeight = FontWeight.Bold)
            Text("Saya ingin mencatat dan melihat perkembangan usaha.", Modifier.padding(top = 6.dp))
        }
    }
}

@Composable
private fun BusinessStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    StepHeading("Tentang usaha", "Ceritakan usaha Anda", null)
    SimpleField("Nama usaha", state.businessName) { onChange(state.copy(businessName = it)) }
    Text("Jenis usaha", Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    ChoiceColumn(businessTypes, state.businessType) {
        onChange(state.copy(businessType = it, categoryId = ""))
    }
    Text("Kategori usaha", Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    CategoryChoices(state.categories.filter { it.businessType == state.businessType }, state.categoryId) {
        onChange(state.copy(categoryId = it))
    }
}

@Composable
private fun ScaleStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    val logoPicker =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            onChange(state.copy(logoUri = uri?.toString()))
        }
    StepHeading("Ukuran usaha", "Seperti apa usaha Anda sekarang?", null)
    ChoiceColumn(listOf("MICRO" to "Mikro", "SMALL" to "Kecil", "MEDIUM" to "Menengah"), state.scale) {
        onChange(state.copy(scale = it))
    }
    SimpleField("Tahun berdiri (boleh kosong)", state.establishedYear, KeyboardType.Number) {
        onChange(state.copy(establishedYear = it.filter(Char::isDigit)))
    }
    SimpleField("Jumlah pegawai", state.employeeCount, KeyboardType.Number) {
        onChange(state.copy(employeeCount = it.filter(Char::isDigit)))
    }
    Text("Logo usaha (boleh nanti)", Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    Text(
        if (state.logoUri == null) "PNG, JPG, atau WebP; paling besar 2 MB." else "Logo sudah dipilih.",
        Modifier.padding(top = 5.dp),
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Button(onClick = { logoPicker.launch("image/*") }, modifier = Modifier.padding(top = 10.dp)) {
        Text(if (state.logoUri == null) "Pilih logo" else "Ganti logo")
    }
}

@Composable
private fun AddressStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    StepHeading("Lokasi usaha", "Di mana usaha Anda berjalan?", "Alamat umum sudah cukup.")
    SimpleField("Alamat", state.address) { onChange(state.copy(address = it)) }
    SimpleField("Kelurahan/desa", state.village) { onChange(state.copy(village = it)) }
    SimpleField("Kecamatan", state.district) { onChange(state.copy(district = it)) }
    SimpleField("Kota/kabupaten", state.city) { onChange(state.copy(city = it)) }
    SimpleField("Provinsi", state.province) { onChange(state.copy(province = it)) }
    SimpleField("Telepon usaha (boleh kosong)", state.businessPhone, KeyboardType.Phone) {
        onChange(state.copy(businessPhone = it))
    }
    SimpleField("Email usaha (boleh kosong)", state.businessEmail, KeyboardType.Email) {
        onChange(state.copy(businessEmail = it))
    }
}

@Composable
private fun PreferencesStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    StepHeading("Pengaturan harian", "Sesuaikan dengan cara usaha Anda", null)
    Text("Mata uang", fontWeight = FontWeight.Bold)
    ChoiceColumn(listOf("IDR" to "Rupiah", "USD" to "Dolar AS", "SGD" to "Dolar Singapura", "MYR" to "Ringgit"), state.currency) {
        onChange(state.copy(currency = it))
    }
    Text("Zona waktu", Modifier.padding(top = 16.dp), fontWeight = FontWeight.Bold)
    ChoiceColumn(listOf("Asia/Jakarta" to "WIB", "Asia/Makassar" to "WITA", "Asia/Jayapura" to "WIT"), state.timezone) {
        onChange(state.copy(timezone = it))
    }
    Text("Kapan catatan dibuat?", Modifier.padding(top = 16.dp), fontWeight = FontWeight.Bold)
    ChoiceColumn(listOf("CASH" to "Saat uang diterima atau dibayar", "ACCRUAL" to "Saat jual beli terjadi"), state.recordingMethod) {
        onChange(state.copy(recordingMethod = it))
    }
    Text("Cara menerima pembayaran", Modifier.padding(top = 16.dp), fontWeight = FontWeight.Bold)
    paymentOptions.forEach { (value, label) ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, Modifier.padding(top = 12.dp))
            Checkbox(
                checked = value in state.paymentMethods,
                onCheckedChange = {
                    val methods = if (it) state.paymentMethods + value else state.paymentMethods - value
                    onChange(state.copy(paymentMethods = methods))
                },
            )
        }
    }
}

@Composable
private fun OpeningStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    StepHeading(
        "Titik awal",
        "Berapa uang usaha yang tersedia?",
        "Isi uang yang benar-benar menjadi milik usaha saat ini. Boleh 0.",
    )
    SimpleField("Saldo awal", state.openingBalance, KeyboardType.Decimal) {
        onChange(state.copy(openingBalance = it.filter { char -> char.isDigit() || char == '.' }))
    }
    Text("Apakah usaha memiliki produk dan stok?", Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    ChoiceRow(listOf(true to "Ya, ada", false to "Belum/tidak"), state.hasProducts) {
        onChange(state.copy(hasProducts = it))
    }
}

@Composable
private fun TutorialStep(
    state: OnboardingUiState,
    onChange: (OnboardingUiState) -> Unit,
) {
    StepHeading("Hampir selesai", "Tiga hal penting di KASTA", null)
    TutorialCard("1", "Catat uang setiap hari", "Gunakan Uang Masuk dan Uang Keluar.")
    TutorialCard("2", "Foto nota bila ada", "Nota membantu mengecek kembali catatan.")
    TutorialCard("3", "Lihat ringkasan rutin", "Kenali keadaan usaha dengan lebih mudah.")
    Row(Modifier.fillMaxWidth().padding(top = 14.dp)) {
        Checkbox(
            checked = state.tutorialDone,
            onCheckedChange = { onChange(state.copy(tutorialDone = it)) },
        )
        Text("Saya sudah memahami tutorial singkat ini.", Modifier.padding(top = 12.dp))
    }
}

@Composable
private fun BusinessProfileScreen(
    profile: BusinessProfileDto,
    onOpenTransactions: () -> Unit,
) {
    val location =
        listOfNotNull(
            profile.address,
            profile.village,
            profile.district,
            profile.city,
            profile.province,
        ).filter(String::isNotBlank).joinToString(", ")
    val contact = listOfNotNull(profile.phone, profile.email).filter(String::isNotBlank).joinToString(" · ")
    val paymentMethods =
        profile.paymentMethods.joinToString(", ") {
            when (it) {
                "CASH" -> "Tunai"
                "BANK_TRANSFER" -> "Transfer bank"
                "E_WALLET" -> "Dompet digital"
                "CARD" -> "Kartu"
                else -> it
            }
        }
    Scaffold { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(24.dp),
        ) {
            Text("KASTA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
            Spacer(Modifier.height(28.dp))
            Text("Profil Usaha", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            Text(profile.name, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black)
            Text("${profile.categoryName} · ${profile.city}, ${profile.province}")
            Spacer(Modifier.height(24.dp))
            Button(
                onClick = onOpenTransactions,
                modifier = Modifier.fillMaxWidth().testTag("open-transactions"),
            ) {
                Text("Catat transaksi")
            }
            Spacer(Modifier.height(16.dp))
            ProfileValue("Status", if (profile.status == "ACTIVE") "Aktif" else "Tidak aktif")
            ProfileValue(
                "Skala usaha",
                when (profile.scale) {
                    "MICRO" -> "Mikro"
                    "SMALL" -> "Kecil"
                    else -> "Menengah"
                },
            )
            ProfileValue("Tahun berdiri", profile.establishedYear?.toString() ?: "Belum diisi")
            ProfileValue("Lokasi", location)
            ProfileValue("Kontak", contact.ifBlank { "Belum diisi" })
            ProfileValue("Jumlah pegawai", "${profile.employeeCount} orang")
            ProfileValue("Mata uang", profile.currency)
            ProfileValue(
                "Waktu usaha",
                when (profile.timezone) {
                    "Asia/Jakarta" -> "WIB"
                    "Asia/Makassar" -> "WITA"
                    else -> "WIT"
                },
            )
            ProfileValue(
                "Cara mencatat",
                if (profile.recordingMethod == "CASH") "Saat uang berpindah" else "Saat jual beli terjadi",
            )
            ProfileValue("Cara pembayaran", paymentMethods)
            ProfileValue("Saldo awal", "${profile.currency} ${profile.openingBalance}")
            ProfileValue("Produk dan stok", if (profile.hasProductsAndStock) "Digunakan" else "Belum digunakan")
        }
    }
}

@Composable
private fun StepHeading(
    eyebrow: String,
    title: String,
    subtitle: String?,
) {
    Text(
        eyebrow.uppercase(),
        color = MaterialTheme.colorScheme.primary,
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
    )
    Text(
        title,
        style = MaterialTheme.typography.headlineMedium,
        fontWeight = FontWeight.Black,
        modifier = Modifier.padding(top = 5.dp).testTag("step-title"),
    )
    subtitle?.let { Text(it, Modifier.padding(top = 8.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }
}

@Composable
private fun SimpleField(
    label: String,
    value: String,
    keyboardType: KeyboardType = KeyboardType.Text,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value,
        onValueChange,
        label = {
            Text(label)
        },
        singleLine = true,
        keyboardOptions =
            KeyboardOptions(
                keyboardType = keyboardType,
            ),
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    )
}

@Composable
private fun <T> ChoiceRow(
    options: List<Pair<T, String>>,
    selected: T,
    onSelect: (T) -> Unit,
) {
    Row(Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach {
                (value, label) ->
            FilterChip(selected = selected == value, onClick = { onSelect(value) }, label = { Text(label) })
        }
    }
}

@Composable
private fun ChoiceColumn(
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        options.forEach {
                (value, label) ->
            FilterChip(selected = selected == value, onClick = { onSelect(value) }, label = { Text(label) })
        }
    }
}

@Composable
private fun CategoryChoices(
    categories: List<BusinessCategoryDto>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    if (categories.isEmpty()) Text("Kategori sedang dimuat…", color = MaterialTheme.colorScheme.onSurfaceVariant)
    categories.forEach {
            category ->
        FilterChip(selected = selected == category.id, onClick = { onSelect(category.id) }, label = { Text(category.name) })
    }
}

@Composable
private fun TutorialCard(
    number: String,
    title: String,
    description: String,
) {
    Card(Modifier.fillMaxWidth().padding(top = 10.dp)) {
        Row(Modifier.padding(16.dp)) {
            Text(number, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Black)
            Column(Modifier.padding(start = 14.dp)) {
                Text(title, fontWeight = FontWeight.Bold)
                Text(description, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun MessageCard(
    message: String,
    error: Boolean,
) {
    Surface(
        color = if (error) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
        shape = MaterialTheme.shapes.medium,
    ) {
        Text(message, Modifier.padding(14.dp))
    }
}

@Composable
private fun ProfileValue(
    label: String,
    value: String,
) {
    Card(Modifier.fillMaxWidth().padding(bottom = 10.dp)) {
        Column(Modifier.padding(16.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            Text(value, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))
        }
    }
}
