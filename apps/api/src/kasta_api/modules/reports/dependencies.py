from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.reports.repository import ReportRepository
from kasta_api.modules.reports.service import ReportService


def get_report_service(session: DatabaseSession) -> ReportService:
    return ReportService(ReportRepository(session))


ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]
