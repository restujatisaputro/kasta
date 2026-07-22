from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.accounting.service import JournalService


def get_journal_service(session: DatabaseSession) -> JournalService:
    return JournalService(AccountingRepository(session))


JournalServiceDependency = Annotated[JournalService, Depends(get_journal_service)]
