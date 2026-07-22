package id.kasta.app

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.hilt.navigation.compose.hiltViewModel
import dagger.hilt.android.AndroidEntryPoint
import id.kasta.app.notifications.NOTIFICATION_ACTION_PATH
import id.kasta.app.presentation.navigation.KastaNavigation
import id.kasta.app.presentation.settings.SettingsViewModel
import id.kasta.app.presentation.theme.KastaTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var notificationActionPath by mutableStateOf<String?>(null)
    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        notificationActionPath = intent.getStringExtra(NOTIFICATION_ACTION_PATH)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        setContent {
            KastaApp(
                initialActionPath = notificationActionPath,
                onActionConsumed = { notificationActionPath = null },
            )
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        notificationActionPath = intent.getStringExtra(NOTIFICATION_ACTION_PATH)
    }
}

@Composable
fun KastaApp(
    initialActionPath: String? = null,
    onActionConsumed: () -> Unit = {},
    settingsViewModel: SettingsViewModel = hiltViewModel(),
) {
    val preferences by settingsViewModel.state.collectAsState()
    KastaTheme(darkTheme = preferences.darkMode) {
        KastaNavigation(
            settingsViewModel = settingsViewModel,
            initialActionPath = initialActionPath,
            onActionConsumed = onActionConsumed,
        )
    }
}
