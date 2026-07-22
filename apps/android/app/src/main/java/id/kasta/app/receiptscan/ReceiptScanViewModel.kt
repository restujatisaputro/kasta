package id.kasta.app.receiptscan

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.tasks.Task
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import id.kasta.app.data.remote.ReceiptReviewDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.io.File
import javax.inject.Inject
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

@HiltViewModel
class ReceiptScanViewModel
    @Inject
    constructor(
        private val repository: ReceiptScanRepository,
        @ApplicationContext private val context: Context,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(ReceiptScanUiState())
        val state: StateFlow<ReceiptScanUiState> = mutableState.asStateFlow()
        private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

        fun open() {
            mutableState.value = ReceiptScanUiState(stage = ReceiptScanStage.CAMERA)
        }

        fun close() {
            cleanupFiles()
            mutableState.value = ReceiptScanUiState()
        }

        fun documentDetected(
            quad: DocumentQuad,
            detected: Boolean,
        ) {
            val current = mutableState.value
            if (current.stage == ReceiptScanStage.CAMERA) {
                mutableState.value = current.copy(quad = quad, documentDetected = detected)
            }
        }

        fun photoCaptured(file: File) {
            val quad = mutableState.value.quad
            mutableState.value =
                mutableState.value.copy(
                    stage = ReceiptScanStage.PROCESSING,
                    originalPath = file.absolutePath,
                    busy = true,
                    error = null,
                )
            viewModelScope.launch {
                try {
                    val images =
                        withContext(Dispatchers.Default) {
                            ReceiptImageProcessor.process(file, context.cacheDir, quad)
                        }
                    val rawText = recognize(images.processed)
                    val parsed = IndonesianReceiptParser.parse(rawText)
                    mutableState.value =
                        mutableState.value.copy(
                            processedPath = images.processed.absolutePath,
                            rawOcr = rawText,
                            fields = parsed.fields,
                            originalValues = parsed.fields.mapValues { it.value.value },
                        )
                    val review =
                        withContext(Dispatchers.IO) {
                            repository.upload(images, rawText, parsed)
                        }
                    applyReview(review)
                } catch (error: Exception) {
                    mutableState.value =
                        mutableState.value.copy(
                            stage = ReceiptScanStage.FAILED,
                            busy = false,
                            error =
                                error.message
                                    ?: "Foto belum dapat diproses. Periksa koneksi lalu coba lagi.",
                        )
                }
            }
        }

        fun retryUpload() {
            val current = mutableState.value
            val original = current.originalPath?.let(::File)
            val processed = current.processedPath?.let(::File)
            if (original == null || processed == null || !original.exists() || !processed.exists()) {
                mutableState.value = ReceiptScanUiState(stage = ReceiptScanStage.CAMERA)
                return
            }
            mutableState.value = current.copy(stage = ReceiptScanStage.PROCESSING, busy = true, error = null)
            viewModelScope.launch {
                try {
                    val parsed = IndonesianReceiptParser.parse(current.rawOcr)
                    val review =
                        withContext(Dispatchers.IO) {
                            repository.upload(
                                ProcessedReceiptImages(original, processed),
                                current.rawOcr,
                                parsed.copy(fields = current.fields),
                            )
                        }
                    applyReview(review)
                } catch (error: Exception) {
                    mutableState.value =
                        mutableState.value.copy(
                            stage = ReceiptScanStage.FAILED,
                            busy = false,
                            error = error.message ?: "Nota belum dapat dikirim.",
                        )
                }
            }
        }

        fun updateField(
            name: String,
            value: String,
        ) {
            val current = mutableState.value
            val old = current.fields[name] ?: ReceiptFieldValue("", 0f)
            val fields = current.fields.toMutableMap().apply { put(name, old.copy(value = value)) }
            mutableState.value =
                current.copy(
                    fields = fields,
                    entryKind = if (name == "transaction_kind") value else current.entryKind,
                    categoryAccount =
                        if (name == "category_account") value else current.categoryAccount,
                    paymentMethod = if (name == "payment_method") value else current.paymentMethod,
                    error = null,
                )
        }

        fun updateChoices(
            entryKind: String? = null,
            category: String? = null,
            payment: String? = null,
            acknowledgeDuplicate: Boolean? = null,
        ) {
            val current = mutableState.value
            val fields = current.fields.toMutableMap()
            entryKind?.let {
                fields["transaction_kind"] =
                    (fields["transaction_kind"] ?: ReceiptFieldValue("", 0f)).copy(value = it)
            }
            category?.let {
                fields["category_account"] =
                    (fields["category_account"] ?: ReceiptFieldValue("", 0f)).copy(value = it)
            }
            payment?.let {
                fields["payment_method"] =
                    (fields["payment_method"] ?: ReceiptFieldValue("", 0f)).copy(value = it)
            }
            mutableState.value =
                current.copy(
                    fields = fields,
                    entryKind = entryKind ?: current.entryKind,
                    categoryAccount = category ?: current.categoryAccount,
                    paymentMethod = payment ?: current.paymentMethod,
                    acknowledgeDuplicate = acknowledgeDuplicate ?: current.acknowledgeDuplicate,
                    error = null,
                )
        }

        fun confirm() {
            val current = mutableState.value
            val receiptId = current.receiptId ?: return
            val required = listOf("merchant_name", "receipt_date", "total")
            if (required.any { current.fields[it]?.value.isNullOrBlank() }) {
                mutableState.value = current.copy(error = "Periksa nama toko, tanggal, dan total nota.")
                return
            }
            if (current.duplicates.isNotEmpty() && !current.acknowledgeDuplicate) {
                mutableState.value = current.copy(error = "Periksa peringatan nota mirip terlebih dahulu.")
                return
            }
            mutableState.value = current.copy(busy = true, error = null)
            viewModelScope.launch {
                try {
                    val response =
                        withContext(Dispatchers.IO) {
                            repository.confirm(
                                receiptId,
                                current.fields,
                                current.entryKind,
                                current.categoryAccount,
                                current.paymentMethod,
                                current.acknowledgeDuplicate,
                            )
                        }
                    mutableState.value =
                        mutableState.value.copy(
                            stage = ReceiptScanStage.CONFIRMED,
                            transactionId = response.transactionId,
                            busy = false,
                            message = "Transaksi sudah dibuat dari nota yang Anda periksa.",
                        )
                } catch (error: Exception) {
                    mutableState.value =
                        mutableState.value.copy(
                            busy = false,
                            error = error.message ?: "Konfirmasi nota belum berhasil.",
                        )
                }
            }
        }

        private suspend fun recognize(file: File): String {
            val image = InputImage.fromFilePath(context, Uri.fromFile(file))
            return recognizer.process(image).awaitResult().text
        }

        private fun applyReview(review: ReceiptReviewDto) {
            val fields =
                review.fields.associate { field ->
                    field.name to
                        ReceiptFieldValue(
                            value = field.correctedValue ?: field.value,
                            confidence = field.confidence.toFloatOrNull() ?: 0f,
                            sourceText = field.sourceText,
                        )
                }
            val entryKind = fields["transaction_kind"]?.value ?: "EXPENSE"
            val proposedCategory = fields["category_account"]?.value ?: "PURCHASES"
            val category =
                if (entryKind == "INCOME" && proposedCategory !in setOf("SALES", "SERVICE_REVENUE", "OTHER_REVENUE")) {
                    "SALES"
                } else {
                    proposedCategory
                }
            mutableState.value =
                mutableState.value.copy(
                    stage =
                        if (review.status == "FAILED") {
                            ReceiptScanStage.FAILED
                        } else {
                            ReceiptScanStage.REVIEW
                        },
                    receiptId = review.id,
                    fields = fields,
                    originalValues = fields.mapValues { it.value.value },
                    items = review.items,
                    duplicates = review.duplicateCandidates,
                    entryKind = entryKind,
                    categoryAccount = category,
                    paymentMethod = fields["payment_method"]?.value ?: "CASH",
                    busy = false,
                    error = review.failureReason,
                )
        }

        private fun cleanupFiles() {
            listOfNotNull(mutableState.value.originalPath, mutableState.value.processedPath)
                .distinct()
                .forEach { path -> runCatching { File(path).delete() } }
        }

        override fun onCleared() {
            recognizer.close()
            super.onCleared()
        }
    }

private suspend fun <T> Task<T>.awaitResult(): T =
    suspendCancellableCoroutine { continuation ->
        addOnSuccessListener { result ->
            if (continuation.isActive) continuation.resume(result)
        }
        addOnFailureListener { error ->
            if (continuation.isActive) continuation.resumeWithException(error)
        }
    }
