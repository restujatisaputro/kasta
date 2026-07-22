package id.kasta.app.presentation.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val KastaGreen = Color(0xFF166534)
private val KastaGreenLight = Color(0xFFDCFCE7)
private val LightColors =
    lightColorScheme(
        primary = KastaGreen,
        onPrimary = Color.White,
        primaryContainer = KastaGreenLight,
        onPrimaryContainer = Color(0xFF052E16),
        secondary = Color(0xFF0F766E),
        tertiary = Color(0xFFD97706),
        background = Color(0xFFF7F9F6),
        surface = Color.White,
        surfaceVariant = Color(0xFFEEF2EC),
    )

private val DarkColors =
    darkColorScheme(
        primary = Color(0xFF86EFAC),
        onPrimary = Color(0xFF052E16),
        primaryContainer = Color(0xFF14532D),
        secondary = Color(0xFF5EEAD4),
        tertiary = Color(0xFFFCD34D),
        background = Color(0xFF0C1410),
        surface = Color(0xFF121C16),
        surfaceVariant = Color(0xFF1E2A22),
    )

@Composable
fun KastaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
