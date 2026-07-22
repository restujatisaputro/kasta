package id.kasta.app.notifications

import id.kasta.app.data.local.NotificationDao
import id.kasta.app.data.local.NotificationEntity
import id.kasta.app.data.remote.NotificationApi
import id.kasta.app.data.remote.NotificationPreferenceDto
import id.kasta.app.data.remote.NotificationPreferenceUpdateDto
import id.kasta.app.data.remote.NotificationPreferencesUpdateDto
import id.kasta.app.data.session.SessionStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationRepository
    @Inject
    constructor(
        private val dao: NotificationDao,
        private val api: NotificationApi,
        private val sessions: SessionStore,
    ) {
        fun observe(): Flow<List<NotificationEntity>> = sessions.get()?.let { dao.observe(it.businessId) } ?: flowOf(emptyList())

        fun observeUnreadCount(): Flow<Int> = sessions.get()?.let { dao.observeUnreadCount(it.businessId) } ?: flowOf(0)

        suspend fun refresh(): List<NotificationEntity> {
            val session = sessions.get() ?: return emptyList()
            val authorization = "Bearer ${session.accessToken}"
            api.evaluate(session.businessId, authorization)
            val response = api.list(session.businessId, authorization)
            val rows =
                response.map { item ->
                    NotificationEntity(
                        localId = item.id,
                        serverId = item.id,
                        businessId = item.businessId,
                        category = item.category,
                        title = item.title,
                        message = item.message,
                        entityType = item.entityType,
                        entityId = item.entityId,
                        actionPath = item.actionPath,
                        availableAt = item.availableAt,
                        readAt = item.readAt,
                        createdAt = item.createdAt,
                    )
                }
            dao.upsert(rows)
            return rows
        }

        suspend fun unread(): List<NotificationEntity> = sessions.get()?.let { dao.unread(it.businessId) } ?: emptyList()

        suspend fun markRead(item: NotificationEntity) {
            val session = sessions.get() ?: return
            val response =
                api.markRead(
                    session.businessId,
                    item.serverId,
                    "Bearer ${session.accessToken}",
                )
            dao.markRead(item.serverId, response.readAt ?: Instant.now().toString())
        }

        suspend fun markAllRead() {
            val session = sessions.get() ?: return
            api.markAllRead(session.businessId, "Bearer ${session.accessToken}")
            dao.markAllRead(session.businessId, Instant.now().toString())
        }

        suspend fun preferences(): List<NotificationPreferenceDto> {
            val session = requireNotNull(sessions.get()) { "Sesi sudah berakhir." }
            return api.preferences(session.businessId, "Bearer ${session.accessToken}")
        }

        suspend fun updatePreference(item: NotificationPreferenceDto): List<NotificationPreferenceDto> {
            val session = requireNotNull(sessions.get()) { "Sesi sudah berakhir." }
            return api.updatePreferences(
                session.businessId,
                "Bearer ${session.accessToken}",
                NotificationPreferencesUpdateDto(
                    listOf(
                        NotificationPreferenceUpdateDto(
                            category = item.category,
                            enabled = item.enabled,
                            localEnabled = item.localEnabled,
                            pushEnabled = item.pushEnabled,
                            emailEnabled = item.emailEnabled,
                            reminderTime = item.reminderTime,
                            quietHoursStart = item.quietHoursStart,
                            quietHoursEnd = item.quietHoursEnd,
                        ),
                    ),
                ),
            )
        }

        companion object {
            fun temporaryId() = UUID.randomUUID().toString()
        }
    }
