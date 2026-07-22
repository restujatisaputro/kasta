from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.notifications.dependencies import NotificationServiceDependency
from kasta_api.modules.notifications.schemas import (
    NotificationEvaluationResponse,
    NotificationPreferenceResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    PushSubscriptionRequest,
    PushSubscriptionResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/businesses/{business_id}/notifications", tags=["notifications"])

NotificationRead = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.NOTIFICATION_READ))
]
NotificationPreferenceManage = Annotated[
    CurrentPrincipal,
    Depends(require_permission(PermissionCode.NOTIFICATION_PREFERENCE_MANAGE)),
]
NotificationGenerate = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.NOTIFICATION_GENERATE))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    business_id: UUID,
    principal: NotificationRead,
    service: NotificationServiceDependency,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NotificationResponse]:
    result = await service.list_notifications(
        business_id,
        principal.user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return result.items


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    business_id: UUID,
    principal: NotificationRead,
    service: NotificationServiceDependency,
) -> UnreadCountResponse:
    result = await service.list_notifications(
        business_id, principal.user_id, unread_only=True, limit=1, offset=0
    )
    return UnreadCountResponse(unread_count=result.unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    business_id: UUID,
    notification_id: UUID,
    principal: NotificationRead,
    service: NotificationServiceDependency,
) -> NotificationResponse:
    return await service.mark_read(business_id, principal.user_id, notification_id)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_notifications_read(
    business_id: UUID,
    principal: NotificationRead,
    service: NotificationServiceDependency,
) -> UnreadCountResponse:
    await service.mark_all_read(business_id, principal.user_id)
    return UnreadCountResponse(unread_count=0)


@router.get("/preferences", response_model=list[NotificationPreferenceResponse])
async def get_preferences(
    business_id: UUID,
    principal: NotificationPreferenceManage,
    service: NotificationServiceDependency,
) -> list[NotificationPreferenceResponse]:
    return await service.preferences(business_id, principal.user_id)


@router.put("/preferences", response_model=list[NotificationPreferenceResponse])
async def update_preferences(
    business_id: UUID,
    payload: NotificationPreferencesUpdate,
    request: Request,
    principal: NotificationPreferenceManage,
    service: NotificationServiceDependency,
) -> list[NotificationPreferenceResponse]:
    return await service.update_preferences(
        business_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.put(
    "/push-subscription",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def register_push_subscription(
    business_id: UUID,
    payload: PushSubscriptionRequest,
    principal: NotificationPreferenceManage,
    service: NotificationServiceDependency,
) -> PushSubscriptionResponse:
    await service.register_push(business_id, principal.user_id, principal.session_id, payload)
    return PushSubscriptionResponse()


@router.post("/evaluate", response_model=NotificationEvaluationResponse)
async def evaluate_notifications(
    business_id: UUID,
    principal: NotificationGenerate,
    service: NotificationServiceDependency,
    as_of: date | None = None,
) -> NotificationEvaluationResponse:
    return await service.evaluate(business_id, principal.user_id, as_of or date.today())
