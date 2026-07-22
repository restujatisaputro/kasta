package id.kasta.app.receiptscan

import id.kasta.app.data.remote.DuplicateReceiptDto
import id.kasta.app.data.remote.ReceiptItemDto

enum class ReceiptScanStage {
    CLOSED,
    CAMERA,
    PROCESSING,
    REVIEW,
    CONFIRMED,
    FAILED,
}

data class DocumentQuad(
    val topLeftX: Float = 0.08f,
    val topLeftY: Float = 0.08f,
    val topRightX: Float = 0.92f,
    val topRightY: Float = 0.08f,
    val bottomRightX: Float = 0.92f,
    val bottomRightY: Float = 0.92f,
    val bottomLeftX: Float = 0.08f,
    val bottomLeftY: Float = 0.92f,
) {
    fun isUsable(): Boolean = (topRightX - topLeftX) > 0.35f && (bottomLeftY - topLeftY) > 0.35f
}

data class ReceiptFieldValue(
    val value: String,
    val confidence: Float,
    val sourceText: String? = null,
)

data class ReceiptScanUiState(
    val stage: ReceiptScanStage = ReceiptScanStage.CLOSED,
    val quad: DocumentQuad = DocumentQuad(),
    val documentDetected: Boolean = false,
    val receiptId: String? = null,
    val originalPath: String? = null,
    val processedPath: String? = null,
    val rawOcr: String = "",
    val fields: Map<String, ReceiptFieldValue> = emptyMap(),
    val originalValues: Map<String, String> = emptyMap(),
    val items: List<ReceiptItemDto> = emptyList(),
    val duplicates: List<DuplicateReceiptDto> = emptyList(),
    val entryKind: String = "EXPENSE",
    val categoryAccount: String = "PURCHASES",
    val paymentMethod: String = "CASH",
    val acknowledgeDuplicate: Boolean = false,
    val transactionId: String? = null,
    val busy: Boolean = false,
    val message: String? = null,
    val error: String? = null,
)

data class LocalReceiptItem(
    val description: String,
    val lineTotal: String,
    val confidence: Float,
)

data class LocalParsedReceipt(
    val fields: Map<String, ReceiptFieldValue>,
    val items: List<LocalReceiptItem>,
)
