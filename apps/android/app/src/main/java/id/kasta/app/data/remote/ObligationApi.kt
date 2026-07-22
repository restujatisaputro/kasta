package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class ObligationPartyDto(
    val id: String,
    val name: String,
)

data class ObligationPaymentDto(
    val id: String,
    val amount: String,
    @SerializedName("payment_date") val paymentDate: String,
    @SerializedName("payment_account_key") val paymentAccountKey: String,
    val note: String?,
)

data class ObligationDto(
    val id: String,
    val kind: String,
    val party: ObligationPartyDto,
    @SerializedName("initial_amount") val initialAmount: String,
    @SerializedName("paid_amount") val paidAmount: String,
    @SerializedName("remaining_amount") val remainingAmount: String,
    @SerializedName("transaction_date") val transactionDate: String,
    @SerializedName("due_date") val dueDate: String,
    val status: String,
    @SerializedName("status_label") val statusLabel: String,
    val note: String?,
    @SerializedName("days_until_due") val daysUntilDue: Int,
    val payments: List<ObligationPaymentDto>? = null,
)

data class ObligationListDto(
    val items: List<ObligationDto>,
    val total: Int,
)

data class ObligationCreateDto(
    @SerializedName("party_name") val partyName: String,
    @SerializedName("initial_amount") val initialAmount: String,
    @SerializedName("transaction_date") val transactionDate: String,
    @SerializedName("due_date") val dueDate: String,
    val note: String,
    @SerializedName("reminder_enabled") val reminderEnabled: Boolean,
    @SerializedName("reminder_days_before") val reminderDaysBefore: Int,
)

data class ObligationPaymentCreateDto(
    val amount: String,
    @SerializedName("payment_date") val paymentDate: String,
    @SerializedName("payment_account") val paymentAccount: String,
    val note: String,
)

data class ObligationCancellationDto(
    val reason: String,
    @SerializedName("cancellation_date") val cancellationDate: String,
)

data class AgingSectionDto(
    @SerializedName("total_open") val totalOpen: String,
)

data class ObligationAgingDto(
    val receivables: AgingSectionDto,
    val payables: AgingSectionDto,
)

data class ObligationReminderListDto(
    val items: List<ObligationReminderDto>,
)

data class ObligationReminderDto(
    @SerializedName("obligation_id") val obligationId: String,
    val kind: String,
    val message: String,
)

interface ObligationApi {
    @GET("businesses/{business_id}/{resource}")
    suspend fun list(
        @Path("business_id") businessId: String,
        @Path("resource") resource: String,
        @Header("Authorization") authorization: String,
        @Query("q") query: String? = null,
        @Query("status") status: String? = null,
        @Query("due_to") dueTo: String? = null,
        @Query("overdue_only") overdueOnly: Boolean = false,
    ): ObligationListDto

    @POST("businesses/{business_id}/{resource}")
    suspend fun create(
        @Path("business_id") businessId: String,
        @Path("resource") resource: String,
        @Header("Authorization") authorization: String,
        @Body payload: ObligationCreateDto,
    ): ObligationDto

    @GET("businesses/{business_id}/{resource}/{id}")
    suspend fun detail(
        @Path("business_id") businessId: String,
        @Path("resource") resource: String,
        @Path("id") id: String,
        @Header("Authorization") authorization: String,
    ): ObligationDto

    @POST("businesses/{business_id}/{resource}/{id}/payments")
    suspend fun pay(
        @Path("business_id") businessId: String,
        @Path("resource") resource: String,
        @Path("id") id: String,
        @Header("Authorization") authorization: String,
        @Body payload: ObligationPaymentCreateDto,
    ): ObligationDto

    @POST("businesses/{business_id}/{resource}/{id}/cancellation")
    suspend fun cancel(
        @Path("business_id") businessId: String,
        @Path("resource") resource: String,
        @Path("id") id: String,
        @Header("Authorization") authorization: String,
        @Body payload: ObligationCancellationDto,
    ): ObligationDto

    @GET("businesses/{business_id}/obligations/aging")
    suspend fun aging(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): ObligationAgingDto

    @GET("businesses/{business_id}/obligations/reminders")
    suspend fun reminders(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): ObligationReminderListDto
}
