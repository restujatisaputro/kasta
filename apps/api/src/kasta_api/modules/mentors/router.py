from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from starlette.responses import Response

from kasta_api.modules.mentors.dependencies import (
    MentorExportDependency,
    MentorNoteDependency,
    MentorReadDependency,
    MentorRecommendationDependency,
    MentorServiceDependency,
    MentorSessionDependency,
)
from kasta_api.modules.mentors.export import (
    build_mentor_csv,
    build_mentor_pdf,
    build_mentor_xlsx,
)
from kasta_api.modules.mentors.schemas import (
    MentorAggregateReport,
    MentorAuditResponse,
    MentorBusinessDetail,
    MentorBusinessSummary,
    MentorDashboard,
    MentoringSessionCreate,
    MentoringSessionResponse,
    MentoringSessionUpdate,
    MentorNoteCreate,
    MentorNoteResponse,
    RecommendationCreate,
    RecommendationResponse,
    RecommendationUpdate,
)
from kasta_api.modules.reports.constants import ExportFormat

router = APIRouter(prefix="/mentors/me", tags=["mentors"])
FormatQuery = Annotated[ExportFormat, Query(alias="format")]


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value is not None else None


@router.get("/dashboard", response_model=MentorDashboard)
async def dashboard(
    mentor: MentorReadDependency, service: MentorServiceDependency
) -> MentorDashboard:
    return await service.dashboard(mentor)


@router.get("/businesses", response_model=list[MentorBusinessSummary])
async def businesses(
    mentor: MentorReadDependency, service: MentorServiceDependency
) -> list[MentorBusinessSummary]:
    return await service.businesses(mentor)


@router.get("/businesses/{business_id}", response_model=MentorBusinessDetail)
async def business_detail(
    business_id: UUID,
    mentor: MentorReadDependency,
    service: MentorServiceDependency,
) -> MentorBusinessDetail:
    return await service.detail(mentor, business_id)


@router.post(
    "/businesses/{business_id}/notes",
    response_model=MentorNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    business_id: UUID,
    payload: MentorNoteCreate,
    request: Request,
    mentor: MentorNoteDependency,
    service: MentorServiceDependency,
) -> MentorNoteResponse:
    return await service.create_note(mentor, business_id, payload, request_id=_request_id(request))


@router.post(
    "/businesses/{business_id}/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recommendation(
    business_id: UUID,
    payload: RecommendationCreate,
    request: Request,
    mentor: MentorRecommendationDependency,
    service: MentorServiceDependency,
) -> RecommendationResponse:
    return await service.create_recommendation(
        mentor, business_id, payload, request_id=_request_id(request)
    )


@router.patch(
    "/businesses/{business_id}/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
)
async def update_recommendation(
    business_id: UUID,
    recommendation_id: UUID,
    payload: RecommendationUpdate,
    request: Request,
    mentor: MentorRecommendationDependency,
    service: MentorServiceDependency,
) -> RecommendationResponse:
    return await service.update_recommendation(
        mentor,
        business_id,
        recommendation_id,
        payload,
        request_id=_request_id(request),
    )


@router.post(
    "/businesses/{business_id}/sessions",
    response_model=MentoringSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    business_id: UUID,
    payload: MentoringSessionCreate,
    request: Request,
    mentor: MentorSessionDependency,
    service: MentorServiceDependency,
) -> MentoringSessionResponse:
    return await service.create_session(
        mentor, business_id, payload, request_id=_request_id(request)
    )


@router.patch(
    "/businesses/{business_id}/sessions/{session_id}",
    response_model=MentoringSessionResponse,
)
async def update_session(
    business_id: UUID,
    session_id: UUID,
    payload: MentoringSessionUpdate,
    request: Request,
    mentor: MentorSessionDependency,
    service: MentorServiceDependency,
) -> MentoringSessionResponse:
    return await service.update_session(
        mentor, business_id, session_id, payload, request_id=_request_id(request)
    )


@router.get("/report", response_model=MentorAggregateReport)
async def aggregate_report(
    mentor: MentorReadDependency, service: MentorServiceDependency
) -> MentorAggregateReport:
    return await service.aggregate_report(mentor)


@router.get("/report/export", response_class=Response)
async def export_report(
    export_format: FormatQuery,
    mentor: MentorExportDependency,
    service: MentorServiceDependency,
) -> Response:
    report = await service.aggregate_report(mentor, require_export_scope=True)
    builders = {
        ExportFormat.PDF: (build_mentor_pdf, "application/pdf", "pdf"),
        ExportFormat.XLSX: (
            build_mentor_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        ),
        ExportFormat.CSV: (build_mentor_csv, "text/csv; charset=utf-8", "csv"),
    }
    builder, media_type, extension = builders[export_format]
    filename = f"laporan-pembinaan-kasta-{date.today().isoformat()}.{extension}"
    return Response(
        content=builder(report),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit", response_model=list[MentorAuditResponse])
async def audit_activity(
    mentor: MentorReadDependency, service: MentorServiceDependency
) -> list[MentorAuditResponse]:
    return await service.audits(mentor)
