package id.kasta.app.presentation.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowForward
import androidx.compose.material.icons.rounded.AccountBalanceWallet
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import id.kasta.app.presentation.theme.KastaTheme
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(onFinished: () -> Unit) {
    LaunchedEffect(Unit) {
        delay(850)
        onFinished()
    }
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Surface(color = MaterialTheme.colorScheme.primary, shape = RoundedCornerShape(24.dp)) {
            Icon(
                Icons.Rounded.AccountBalanceWallet,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.padding(22.dp),
            )
        }
        Spacer(Modifier.height(18.dp))
        Text("KASTA", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black)
        Text("Keuangan dan Asistensi UMKM", color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
fun LoginScreen(
    state: LoginUiState,
    onChange: ((LoginUiState) -> LoginUiState) -> Unit,
    onLogin: () -> Unit,
    onRegister: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Masuk ke KASTA", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text("Lanjutkan pencatatan usaha Anda.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = state.businessId,
            onValueChange = { value -> onChange { it.copy(businessId = value) } },
            label = { Text("ID usaha") },
            supportingText = { Text("Diperoleh setelah profil usaha selesai dibuat") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().testTag("login-business-id"),
        )
        OutlinedTextField(
            value = state.identifier,
            onValueChange = { value -> onChange { it.copy(identifier = value) } },
            label = { Text("Email atau nomor telepon") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp).testTag("login-identifier"),
        )
        OutlinedTextField(
            value = state.password,
            onValueChange = { value -> onChange { it.copy(password = value) } },
            label = { Text("Kata sandi") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp).testTag("login-password"),
        )
        state.error?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 10.dp),
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Button(
            onClick = onLogin,
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth().height(56.dp).padding(top = 12.dp).testTag("login-submit"),
        ) {
            if (state.loading) CircularProgressIndicator(modifier = Modifier.height(22.dp)) else Text("Masuk", fontWeight = FontWeight.Bold)
        }
        OutlinedButton(onClick = onRegister, modifier = Modifier.fillMaxWidth().height(52.dp).padding(top = 8.dp)) {
            Text("Buat akun baru")
        }
    }
}

@Composable
fun RegistrationScreen(
    onContinue: () -> Unit,
    onLogin: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Buat akun KASTA", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text("Pendaftaran dan pembuatan profil usaha dipandu langkah demi langkah.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        listOf(
            "Daftar dengan email atau nomor telepon",
            "Verifikasi akun Anda",
            "Isi profil dan saldo awal usaha",
        ).forEach { label ->
            androidx.compose.foundation.layout.Row(Modifier.padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(label, Modifier.padding(start = 10.dp), fontWeight = FontWeight.Medium)
            }
        }
        Button(onClick = onContinue, modifier = Modifier.fillMaxWidth().height(56.dp).padding(top = 20.dp)) {
            Text("Mulai pendaftaran", fontWeight = FontWeight.Bold)
            Icon(Icons.AutoMirrored.Rounded.ArrowForward, contentDescription = null, modifier = Modifier.padding(start = 8.dp))
        }
        OutlinedButton(
            onClick = onLogin,
            modifier = Modifier.fillMaxWidth().height(52.dp).padding(top = 8.dp),
        ) { Text("Saya sudah punya akun") }
    }
}

@Preview(showBackground = true)
@Composable
private fun LoginPreview() {
    KastaTheme(darkTheme = false) {
        LoginScreen(LoginUiState(), {}, {}, {})
    }
}

@Preview(showBackground = true)
@Composable
private fun RegistrationPreview() {
    KastaTheme(darkTheme = false) { RegistrationScreen({}, {}) }
}
