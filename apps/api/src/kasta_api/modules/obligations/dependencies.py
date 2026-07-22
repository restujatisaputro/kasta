from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.obligations.repository import ObligationRepository
from kasta_api.modules.obligations.service import ObligationService


def get_obligation_service(session: DatabaseSession) -> ObligationService:
    return ObligationService(ObligationRepository(session), AccountingRepository(session))


ObligationServiceDependency = Annotated[ObligationService, Depends(get_obligation_service)]
