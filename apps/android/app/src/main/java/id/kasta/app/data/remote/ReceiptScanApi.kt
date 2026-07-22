package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

data class OcrFieldDto(
    val name: String,
    val value: String,
    val confidence: String,
    @SerializedName("source_text") val sourceText: String?,
    @SerializedName("corrected_value") val correctedValue: String?,
)

data class ReceiptItemDto(
    @SerializedName("line_number") val lineNumber: Int,
    val description: String,
    val quantity: String?,
    @SerializedName("unit_price") val unitPrice: String?,
    @SerializedName("line_total") val lineTotal: String,
    val confidence: String,
)

data class DuplicateReceiptDto(
    val id: String,
    @SerializedName("merchant_name") val merchantName: String?,
    @SerializedName("receipt_date") val receiptDate: String?,
    @SerializedName("receipt_number") val receiptNumber: String?,
    @SerializedName("total_amount") val totalAmount: String?,
    @SerializedName("hash_distance") val hashDistance: Int?,
    @SerializedName("match_reasons") val matchReasons: List<String>,
)

data class ReceiptReviewDto(
    val id: String,
    @SerializedName("business_id") val businessId: String,
    val status: String,
    @SerializedName("transaction_id") val transactionId: String?,
    val fields: List<OcrFieldDto>,
    val items: List<ReceiptItemDto>,
    @SerializedName("duplicate_candidates") val duplicateCandidates: List<DuplicateReceiptDto>,
    @SerializedName("processing_duration_ms") val processingDurationMs: Int?,
    @SerializedName("failure_reason") val failureReason: String?,
)

data class ReceiptConfirmRequest(
    val corrections: Map<String, String?>,
    @SerializedName("entry_kind") val entryKind: String,
    @SerializedName("category_account") val categoryAccount: String,
    @SerializedName("payment_method") val paymentMethod: String,
    val note: String,
    @SerializedName("acknowledge_duplicate") val acknowledgeDuplicate: Boolean,
)

data class ReceiptConfirmResponse(
    val receipt: ReceiptReviewDto,
    @SerializedName("transaction_id") val transactionId: String,
)

interface ReceiptScanApi {
    @Multipart
    @POST("businesses/{business_id}/receipt-scans")
    suspend fun upload(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Part original: MultipartBody.Part,
        @Part processed: MultipartBody.Part,
        @Part("raw_ocr") rawOcr: RequestBody,
        @Part("client_fields") clientFields: RequestBody,
    ): ReceiptReviewDto

    @GET("businesses/{business_id}/receipt-scans/{receipt_id}")
    suspend fun review(
        @Path("business_id") businessId: String,
        @Path("receipt_id") receiptId: String,
        @Header("Authorization") authorization: String,
    ): ReceiptReviewDto

    @POST("businesses/{business_id}/receipt-scans/{receipt_id}/confirm")
    suspend fun confirm(
        @Path("business_id") businessId: String,
        @Path("receipt_id") receiptId: String,
        @Header("Authorization") authorization: String,
        @Body request: ReceiptConfirmRequest,
    ): ReceiptConfirmResponse
}
