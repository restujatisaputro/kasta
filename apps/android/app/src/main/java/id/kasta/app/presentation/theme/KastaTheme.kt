package id.kasta.app.presentation.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val KastaTeal = Color(0xFF31574F)
private val KastaSage = Color(0xFFE5EEE8)
private val KastaGold = Color(0xFFC5A476)
private val LightColors =
    lightColorScheme(
        primary = KastaTeal,
        onPrimary = Color.White,
        primaryContainer = KastaSage,
        onPrimaryContainer = Color(0xFF1D3835),
        secondary = Color(0xFF64877B),
        tertiary = KastaGold,
        background = Color(0xFFF8F8F4),
        surface = Color(0xFFFFFEFA),
        surfaceVariant = Color(0xFFEEF2ED),
    )

private val DarkColors =
    darkColorScheme(
        primary = Color(0xFFB2C9BD),
        onPrimary = Color(0xFF1D3835),
        primaryContainer = Color(0xFF24423C),
        secondary = Color(0xFF8FB0A3),
        tertiary = Color(0xFFD4B887),
        background = Color(0xFF101B18),
        surface = Color(0xFF172622),
        surfaceVariant = Color(0xFF223630),
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
