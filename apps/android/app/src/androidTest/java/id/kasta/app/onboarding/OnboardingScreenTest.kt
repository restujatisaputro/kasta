package id.kasta.app.onboarding

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class OnboardingScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun accountStepUsesSimpleLanguageAndShowsProgress() {
        composeRule.setContent {
            MaterialTheme {
                OnboardingScreen(
                    state = OnboardingUiState(),
                    onChange = {},
                    onCreateAccount = {},
                    onVerify = {},
                    onNext = {},
                    onBack = {},
                    onFinish = {},
                )
            }
        }

        composeRule.onNodeWithText("Buat akun KASTA").assertIsDisplayed()
        composeRule.onNodeWithText("Buat akun").assertIsDisplayed()
        composeRule.onNodeWithTag("progress-label").assertIsDisplayed()
        composeRule.onNodeWithText("Langkah 1 dari 9").assertIsDisplayed()
    }

    @Test
    fun openingBalanceStepAvoidsTechnicalAccountingWords() {
        composeRule.setContent {
            MaterialTheme {
                OnboardingScreen(
                    state = OnboardingUiState(step = 8),
                    onChange = {},
                    onCreateAccount = {},
                    onVerify = {},
                    onNext = {},
                    onBack = {},
                    onFinish = {},
                )
            }
        }

        composeRule.onNodeWithText("Berapa uang usaha yang tersedia?").assertIsDisplayed()
        composeRule.onNodeWithText("Saldo awal").assertIsDisplayed()
    }
}
