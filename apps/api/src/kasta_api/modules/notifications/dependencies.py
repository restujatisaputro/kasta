from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.notifications.repository import NotificationRepository
from kasta_api.modules.notifications.service import NotificationService


def get_notification_service(session: DatabaseSession) -> NotificationService:
    return NotificationService(NotificationRepository(session))


NotificationServiceDependency = Annotated[NotificationService, Depends(get_notification_service)]
