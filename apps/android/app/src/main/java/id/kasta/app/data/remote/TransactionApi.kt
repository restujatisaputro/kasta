package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

data class SimpleTransactionDto(
    @SerializedName("entry_kind") val entryKind: String,
    @SerializedName("transaction_date") val transactionDate: String,
    val amount: String,
    @SerializedName("category_account") val categoryAccount: String?,
    @SerializedName("counterparty_name") val counterpartyName: String?,
    @SerializedName("payment_method") val paymentMethod: String,
    val note: String,
    @SerializedName("recurrence_frequency") val recurrenceFrequency: String? = null,
    @SerializedName("recurrence_interval") val recurrenceInterval: Int? = null,
)

data class SyncOperationDto(
    @SerializedName("client_operation_id") val clientOperationId: String,
    val operation: String,
    @SerializedName("transaction_id") val transactionId: String? = null,
    val payload: SimpleTransactionDto? = null,
    val reason: String? = null,
)

data class TransactionSyncRequest(
    val operations: List<SyncOperationDto>,
    @SerializedName("pull_updated_after") val pullUpdatedAfter: String? = null,
)

data class SyncOperationResultDto(
    @SerializedName("client_operation_id") val clientOperationId: String,
    val status: String,
    @SerializedName("server_transaction_id") val serverTransactionId: String?,
    @SerializedName("draft_id") val draftId: String?,
    val message: String?,
)

data class TransactionListItemDto(
    val id: String,
    @SerializedName("business_id") val businessId: String,
    @SerializedName("transaction_date") val transactionDate: String,
    val amount: String,
    val description: String,
    val status: String,
    @SerializedName("entry_kind") val entryKind: String?,
    @SerializedName("category_account_key") val categoryAccountKey: String?,
    @SerializedName("counterparty_name") val counterpartyName: String?,
    @SerializedName("payment_method_code") val paymentMethodCode: String?,
)

data class TransactionSyncResponse(
    val results: List<SyncOperationResultDto>,
    val changes: List<TransactionListItemDto>,
    @SerializedName("server_time") val serverTime: String,
)

data class RefreshTokenRequest(
    @SerializedName("refresh_token") val refreshToken: String,
)

interface TransactionApi {
    @POST("businesses/{business_id}/sync/transactions")
    suspend fun sync(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Body request: TransactionSyncRequest,
    ): TransactionSyncResponse

    @Multipart
    @POST("businesses/{business_id}/transactions/{transaction_id}/receipts")
    suspend fun uploadReceipt(
        @Path("business_id") businessId: String,
        @Path("transaction_id") transactionId: String,
        @Header("Authorization") authorization: String,
        @Part photo: MultipartBody.Part,
    )

    @POST("auth/refresh")
    suspend fun refresh(
        @Body request: RefreshTokenRequest,
    ): TokenPairDto
}
