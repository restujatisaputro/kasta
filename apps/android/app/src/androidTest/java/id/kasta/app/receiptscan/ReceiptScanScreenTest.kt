package id.kasta.app.receiptscan

import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class ReceiptScanScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun reviewExplainsThatConfirmationIsRequired() {
        composeRule.setContent {
            MaterialTheme {
                ReceiptScanScreen(
                    state =
                        ReceiptScanUiState(
                            stage = ReceiptScanStage.REVIEW,
                            receiptId = "receipt-1",
                            fields =
                                mapOf(
                                    "merchant_name" to ReceiptFieldValue("Toko Maju", 0.92f),
                                    "receipt_date" to ReceiptFieldValue("2026-07-21", 0.95f),
                                    "total" to ReceiptFieldValue("25000.00", 0.99f),
                                ),
                        ),
                    onClose = {},
                    onDetected = { _, _ -> },
                    onCaptured = {},
                    onRetry = {},
                    onFieldChange = { _, _ -> },
                    onChoicesChange = { _, _, _, _ -> },
                    onConfirm = {},
                    onDone = {},
                )
            }
        }

        composeRule.onNodeWithText("Transaksi belum dibuat").assertIsDisplayed()
        composeRule.onNodeWithText("KASTA hanya membuat transaksi setelah Anda menekan tombol konfirmasi.")
            .assertIsDisplayed()
        composeRule.onNodeWithTag("receipt-confirm").assertIsDisplayed()
    }
}
