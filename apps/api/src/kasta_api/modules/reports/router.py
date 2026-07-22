from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from starlette.responses import Response

from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import CurrentPrincipal, require_permission
from kasta_api.modules.reports.constants import ExportFormat, ReportPeriod
from kasta_api.modules.reports.dependencies import ReportServiceDependency
from kasta_api.modules.reports.export import (
    build_report_csv,
    build_report_pdf,
    build_report_xlsx,
)
from kasta_api.modules.reports.schemas import FinancialReportResponse

router = APIRouter(prefix="/businesses/{business_id}/reports")

ReadPrincipal = Annotated[CurrentPrincipal, Depends(require_permission(PermissionCode.REPORT_READ))]
ExportPrincipal = Annotated[
    CurrentPrincipal, Depends(require_permission(PermissionCode.REPORT_EXPORT))
]

CategoryQuery = Annotated[str | None, Query(max_length=50)]
PaymentQuery = Annotated[str | None, Query(max_length=30)]
FormatQuery = Annotated[ExportFormat, Query(alias="format")]


async def _report(
    business_id: UUID,
    service: ReportServiceDependency,
    period: ReportPeriod,
    reference_date: date | None,
    date_from: date | None,
    date_to: date | None,
    category: str | None,
    payment_method: str | None,
    branch_id: UUID | None,
) -> FinancialReportResponse:
    return await service.build(
        business_id,
        period=period,
        reference_date=reference_date or date.today(),
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment_method=payment_method,
        branch_id=branch_id,
    )


@router.get("/financial", response_model=FinancialReportResponse)
async def financial_report(
    business_id: UUID,
    _: ReadPrincipal,
    service: ReportServiceDependency,
    period: ReportPeriod = ReportPeriod.MONTH,
    reference_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: CategoryQuery = None,
    payment_method: PaymentQuery = None,
    branch_id: UUID | None = None,
) -> FinancialReportResponse:
    """Return journal-backed statements, explanations, tables, and chart series."""
    return await _report(
        business_id,
        service,
        period,
        reference_date,
        date_from,
        date_to,
        category,
        payment_method,
        branch_id,
    )


@router.get("/financial/export", response_class=Response)
async def export_financial_report(
    business_id: UUID,
    _: ExportPrincipal,
    service: ReportServiceDependency,
    export_format: FormatQuery,
    period: ReportPeriod = ReportPeriod.MONTH,
    reference_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: CategoryQuery = None,
    payment_method: PaymentQuery = None,
    branch_id: UUID | None = None,
) -> Response:
    report = await _report(
        business_id,
        service,
        period,
        reference_date,
        date_from,
        date_to,
        category,
        payment_method,
        branch_id,
    )
    builders = {
        ExportFormat.PDF: (build_report_pdf, "application/pdf", "pdf"),
        ExportFormat.XLSX: (
            build_report_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        ),
        ExportFormat.CSV: (build_report_csv, "text/csv; charset=utf-8", "csv"),
    }
    builder, media_type, extension = builders[export_format]
    filename = f"laporan-kasta-{report.context.date_from}-{report.context.date_to}.{extension}"
    return Response(
        content=builder(report),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
