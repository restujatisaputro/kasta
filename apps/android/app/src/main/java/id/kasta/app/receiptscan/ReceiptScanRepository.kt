package id.kasta.app.receiptscan

import com.google.gson.Gson
import id.kasta.app.data.remote.ReceiptConfirmRequest
import id.kasta.app.data.remote.ReceiptConfirmResponse
import id.kasta.app.data.remote.ReceiptReviewDto
import id.kasta.app.data.remote.ReceiptScanApi
import id.kasta.app.data.session.SessionStore
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReceiptScanRepository
    @Inject
    constructor(
        private val api: ReceiptScanApi,
        private val sessionStore: SessionStore,
    ) {
        suspend fun upload(
            images: ProcessedReceiptImages,
            rawOcr: String,
            parsed: LocalParsedReceipt,
        ): ReceiptReviewDto {
            val session = requireNotNull(sessionStore.get()) { "Sesi tidak tersedia" }
            val clientFields =
                parsed.fields.mapValues { (_, field) ->
                    mapOf("value" to field.value, "confidence" to field.confidence)
                }
            return api.upload(
                businessId = session.businessId,
                authorization = "Bearer ${session.accessToken}",
                original = images.original.toPart("original", "nota-asli.jpg"),
                processed = images.processed.toPart("processed", "nota-crop.jpg"),
                rawOcr = rawOcr.toRequestBody("text/plain".toMediaType()),
                clientFields =
                    Gson().toJson(clientFields).toRequestBody("application/json".toMediaType()),
            )
        }

        suspend fun review(receiptId: String): ReceiptReviewDto {
            val session = requireNotNull(sessionStore.get()) { "Sesi tidak tersedia" }
            return api.review(
                session.businessId,
                receiptId,
                "Bearer ${session.accessToken}",
            )
        }

        suspend fun confirm(
            receiptId: String,
            fields: Map<String, ReceiptFieldValue>,
            entryKind: String,
            categoryAccount: String,
            paymentMethod: String,
            acknowledgeDuplicate: Boolean,
        ): ReceiptConfirmResponse {
            val session = requireNotNull(sessionStore.get()) { "Sesi tidak tersedia" }
            return api.confirm(
                businessId = session.businessId,
                receiptId = receiptId,
                authorization = "Bearer ${session.accessToken}",
                request =
                    ReceiptConfirmRequest(
                        corrections = fields.mapValues { it.value.value.ifBlank { null } },
                        entryKind = entryKind,
                        categoryAccount = categoryAccount,
                        paymentMethod = paymentMethod,
                        note =
                            fields["merchant_name"]?.value?.let { "Foto nota $it" }
                                ?: "Foto nota usaha",
                        acknowledgeDuplicate = acknowledgeDuplicate,
                    ),
            )
        }

        private fun File.toPart(
            name: String,
            filename: String,
        ): MultipartBody.Part =
            MultipartBody.Part.createFormData(
                name,
                filename,
                asRequestBody("image/jpeg".toMediaType()),
            )
    }
