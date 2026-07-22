package id.kasta.app.obligations

import id.kasta.app.data.remote.ObligationApi
import id.kasta.app.data.remote.ObligationCancellationDto
import id.kasta.app.data.remote.ObligationCreateDto
import id.kasta.app.data.remote.ObligationPaymentCreateDto
import id.kasta.app.data.session.SessionStore
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ObligationRepository
    @Inject
    constructor(
        private val api: ObligationApi,
        private val sessionStore: SessionStore,
    ) {
        private fun session() = requireNotNull(sessionStore.get()) { "Sesi sudah berakhir." }

        private fun resource(kind: String) = if (kind == "RECEIVABLE") "receivables" else "payables"

        suspend fun load(state: ObligationUiState) =
            session().let { session ->
                val authorization = "Bearer ${session.accessToken}"
                api.list(
                    session.businessId,
                    resource(state.kind),
                    authorization,
                    state.query.ifBlank { null },
                    state.status.ifBlank { null },
                    state.dueTo.ifBlank { null },
                    state.overdueOnly,
                ) to (
                    api.aging(session.businessId, authorization) to
                        api.reminders(session.businessId, authorization).items.size
                )
            }

        suspend fun create(
            kind: String,
            form: ObligationForm,
        ) {
            val session = session()
            api.create(
                session.businessId,
                resource(kind),
                "Bearer ${session.accessToken}",
                ObligationCreateDto(
                    form.partyName,
                    form.initialAmount,
                    form.transactionDate,
                    form.dueDate,
                    form.note,
                    true,
                    form.reminderDaysBefore.toIntOrNull() ?: 3,
                ),
            )
        }

        suspend fun pay(
            kind: String,
            id: String,
            form: ObligationPaymentForm,
        ) {
            val session = session()
            api.pay(
                session.businessId,
                resource(kind),
                id,
                "Bearer ${session.accessToken}",
                ObligationPaymentCreateDto(
                    form.amount,
                    LocalDate.now().toString(),
                    form.paymentAccount,
                    form.note,
                ),
            )
        }

        suspend fun detail(
            kind: String,
            id: String,
        ) = session().let { session ->
            api.detail(
                session.businessId,
                resource(kind),
                id,
                "Bearer ${session.accessToken}",
            )
        }

        suspend fun cancel(
            kind: String,
            id: String,
            reason: String,
        ) {
            val session = session()
            api.cancel(
                session.businessId,
                resource(kind),
                id,
                "Bearer ${session.accessToken}",
                ObligationCancellationDto(reason, LocalDate.now().toString()),
            )
        }
    }
