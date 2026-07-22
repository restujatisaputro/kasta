from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from starlette.responses import Response

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.ocr.dependencies import (
    ReceiptOcrServiceDependency,
    ReceiptStorageDependency,
)
from kasta_api.modules.ocr.schemas import (
    ReceiptConfirmRequest,
    ReceiptConfirmResponse,
    ReceiptImageUrlResponse,
    ReceiptReviewResponse,
)

router = APIRouter(prefix="/businesses/{business_id}/receipt-scans")

UploadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIPT_UPLOAD))
]
ReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.RECEIPT_READ))
]
CreateTransactionPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.TRANSACTION_CREATE))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.post("", response_model=ReceiptReviewResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_scan(
    business_id: UUID,
    principal: UploadPrincipal,
    service: ReceiptOcrServiceDependency,
    storage: ReceiptStorageDependency,
    original: Annotated[UploadFile, File()],
    processed: Annotated[UploadFile | None, File()] = None,
    raw_ocr: Annotated[str, Form(max_length=100_000)] = "",
    client_fields: Annotated[str | None, Form(max_length=64_000)] = None,
) -> ReceiptReviewResponse:
    return await service.upload_and_process(
        business_id,
        principal.user_id,
        original,
        processed,
        raw_ocr,
        client_fields,
        storage,
    )


@router.get("/{receipt_id}", response_model=ReceiptReviewResponse)
async def receipt_review(
    business_id: UUID,
    receipt_id: UUID,
    _: ReadPrincipal,
    service: ReceiptOcrServiceDependency,
) -> ReceiptReviewResponse:
    return await service.review(business_id, receipt_id)


@router.get("/{receipt_id}/images/{image_kind}", response_class=Response)
async def receipt_scan_image(
    business_id: UUID,
    receipt_id: UUID,
    image_kind: Literal["ORIGINAL", "PROCESSED"],
    _: ReadPrincipal,
    service: ReceiptOcrServiceDependency,
    storage: ReceiptStorageDependency,
) -> Response:
    data, content_type = await service.image_data(business_id, receipt_id, image_kind, storage)
    return Response(content=data, media_type=content_type)


@router.get(
    "/{receipt_id}/images/{image_kind}/url",
    response_model=ReceiptImageUrlResponse,
)
async def receipt_scan_image_url(
    business_id: UUID,
    receipt_id: UUID,
    image_kind: Literal["ORIGINAL", "PROCESSED"],
    _: ReadPrincipal,
    service: ReceiptOcrServiceDependency,
    storage: ReceiptStorageDependency,
) -> ReceiptImageUrlResponse:
    url, expires_in = await service.image_url(business_id, receipt_id, image_kind, storage)
    return ReceiptImageUrlResponse(url=url, expires_in=expires_in)


@router.post("/{receipt_id}/confirm", response_model=ReceiptConfirmResponse)
async def confirm_receipt_scan(
    business_id: UUID,
    receipt_id: UUID,
    payload: ReceiptConfirmRequest,
    request: Request,
    principal: CreateTransactionPrincipal,
    _: UploadPrincipal,
    service: ReceiptOcrServiceDependency,
) -> ReceiptConfirmResponse:
    return await service.confirm(
        business_id,
        receipt_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )
