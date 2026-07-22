from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from starlette.responses import Response

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.inventory.dependencies import InventoryServiceDependency
from kasta_api.modules.inventory.schemas import (
    CsvImportResponse,
    InventorySummaryResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    StockHistoryResponse,
    StockMovementRequest,
    StockMovementResponse,
)

router = APIRouter(prefix="/businesses/{business_id}/inventory")

ReadPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PRODUCT_READ))
]
CreatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PRODUCT_CREATE))
]
UpdatePrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.PRODUCT_UPDATE))
]
StockPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.STOCK_MANAGE))
]
ImportPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.INVENTORY_IMPORT))
]
ExportPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.INVENTORY_EXPORT))
]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    business_id: UUID,
    _: ReadPrincipal,
    service: InventoryServiceDependency,
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    active: bool | None = None,
    low_stock: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductListResponse:
    return await service.list_products(
        business_id,
        query=q,
        category=category,
        active=active,
        low_stock=low_stock,
        limit=limit,
        offset=offset,
    )


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    business_id: UUID,
    payload: ProductCreateRequest,
    request: Request,
    principal: CreatePrincipal,
    service: InventoryServiceDependency,
) -> ProductResponse:
    return await service.create_product(
        business_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.get("/products/by-barcode/{barcode}", response_model=ProductResponse)
async def product_by_barcode(
    business_id: UUID,
    barcode: str,
    _: ReadPrincipal,
    service: InventoryServiceDependency,
) -> ProductResponse:
    return await service.product_by_barcode(business_id, barcode)


@router.post("/products/import-csv", response_model=CsvImportResponse)
async def import_products_csv(
    business_id: UUID,
    request: Request,
    principal: ImportPrincipal,
    service: InventoryServiceDependency,
    file: Annotated[UploadFile, File()],
) -> CsvImportResponse:
    return await service.import_csv(
        business_id,
        principal.user_id,
        file,
        request_id=_request_id(request),
    )


@router.get("/products/export.xlsx", response_class=Response)
async def export_products_excel(
    business_id: UUID,
    _: ExportPrincipal,
    service: InventoryServiceDependency,
) -> Response:
    data = await service.export_excel(business_id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="produk-kasta.xlsx"'},
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def product_detail(
    business_id: UUID,
    product_id: UUID,
    _: ReadPrincipal,
    service: InventoryServiceDependency,
) -> ProductResponse:
    return await service.product(business_id, product_id)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    business_id: UUID,
    product_id: UUID,
    payload: ProductUpdateRequest,
    request: Request,
    principal: UpdatePrincipal,
    service: InventoryServiceDependency,
) -> ProductResponse:
    return await service.update_product(
        business_id,
        product_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.post("/products/{product_id}/movements", response_model=StockMovementResponse)
async def move_product_stock(
    business_id: UUID,
    product_id: UUID,
    payload: StockMovementRequest,
    request: Request,
    principal: StockPrincipal,
    service: InventoryServiceDependency,
) -> StockMovementResponse:
    return await service.move_stock(
        business_id,
        product_id,
        principal.user_id,
        payload,
        request_id=_request_id(request),
    )


@router.get("/movements", response_model=StockHistoryResponse)
async def stock_history(
    business_id: UUID,
    _: ReadPrincipal,
    service: InventoryServiceDependency,
    product_id: UUID | None = None,
    movement_type: str | None = Query(default=None, max_length=30),
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StockHistoryResponse:
    return await service.stock_history(
        business_id,
        product_id=product_id,
        movement_type=movement_type,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=InventorySummaryResponse)
async def inventory_summary(
    business_id: UUID,
    _: ReadPrincipal,
    service: InventoryServiceDependency,
) -> InventorySummaryResponse:
    return await service.summary(business_id)
