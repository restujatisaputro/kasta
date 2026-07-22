package id.kasta.app.transactions

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class TransactionScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun homeShowsFourSimpleTransactionMenus() {
        composeRule.setContent {
            MaterialTheme {
                TransactionScreen(
                    state = TransactionUiState(),
                    onStart = {},
                    onOpenReceipt = {},
                    onOpenInventory = {},
                    onOpenObligations = {},
                    onChange = {},
                    onNext = {},
                    onBack = {},
                    onClose = {},
                    onSave = {},
                    onPostDraft = {},
                    onEdit = {},
                    onCancel = { _, _ -> },
                    onSearch = {},
                    onFilter = {},
                    onSync = {},
                )
            }
        }

        composeRule.onNodeWithText("Uang Masuk").assertIsDisplayed()
        composeRule.onNodeWithText("Uang Keluar").assertIsDisplayed()
        composeRule.onNodeWithText("Tambah Modal").assertIsDisplayed()
        composeRule.onNodeWithText("Ambil Uang Pribadi").assertIsDisplayed()
        composeRule.onNodeWithText("Foto Nota").assertIsDisplayed()
    }

    @Test
    fun entryFlowDeclaresThreeStepsAndFormatsRupiah() {
        composeRule.setContent {
            MaterialTheme {
                TransactionScreen(
                    state =
                        TransactionUiState(
                            step = 1,
                            form = TransactionForm(amountDigits = "125000"),
                        ),
                    onStart = {},
                    onOpenReceipt = {},
                    onOpenInventory = {},
                    onOpenObligations = {},
                    onChange = {},
                    onNext = {},
                    onBack = {},
                    onClose = {},
                    onSave = {},
                    onPostDraft = {},
                    onEdit = {},
                    onCancel = { _, _ -> },
                    onSearch = {},
                    onFilter = {},
                    onSync = {},
                )
            }
        }

        composeRule.onNodeWithText("Langkah 1 dari 3").assertIsDisplayed()
        composeRule.onNodeWithTag("amount-input").assertIsDisplayed()
        composeRule.onNodeWithText("125.000").assertIsDisplayed()
    }
}
