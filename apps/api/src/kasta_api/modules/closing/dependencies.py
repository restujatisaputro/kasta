from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.closing.repository import ClosingRepository
from kasta_api.modules.closing.service import ClosingService
from kasta_api.modules.reports.repository import ReportRepository


def get_closing_service(session: DatabaseSession) -> ClosingService:
    return ClosingService(
        ClosingRepository(session),
        AccountingRepository(session),
        ReportRepository(session),
    )


ClosingServiceDependency = Annotated[ClosingService, Depends(get_closing_service)]
