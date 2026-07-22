package id.kasta.app.mentoraccess

import id.kasta.app.data.remote.MentorAccessApi
import id.kasta.app.data.remote.MentorAccessDecisionDto
import id.kasta.app.data.remote.MentorAccessRevokeDto
import id.kasta.app.data.session.SessionStore
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MentorAccessRepository
    @Inject
    constructor(
        private val api: MentorAccessApi,
        private val sessionStore: SessionStore,
    ) {
        private fun session() = requireNotNull(sessionStore.get()) { "Sesi sudah berakhir." }

        suspend fun load() =
            session().let { session ->
                val authorization = "Bearer ${session.accessToken}"
                api.list(session.businessId, authorization) to
                    api.history(session.businessId, authorization)
            }

        suspend fun decide(
            accessId: String,
            approve: Boolean,
            scopes: List<String>,
            expiresAt: String?,
            reason: String?,
        ) {
            val session = session()
            api.decide(
                session.businessId,
                accessId,
                "Bearer ${session.accessToken}",
                MentorAccessDecisionDto(
                    if (approve) "APPROVE" else "REJECT",
                    if (approve) scopes else emptyList(),
                    if (approve) expiresAt else null,
                    reason,
                ),
            )
        }

        suspend fun revoke(
            accessId: String,
            reason: String,
        ) {
            val session = session()
            api.revoke(
                session.businessId,
                accessId,
                "Bearer ${session.accessToken}",
                MentorAccessRevokeDto(reason),
            )
        }
    }
