from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession, SettingsDependency
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.inventory.repository import InventoryRepository
from kasta_api.modules.receipts.storage import ReceiptStorage
from kasta_api.modules.transactions.repository import TransactionRepository
from kasta_api.modules.transactions.service import SimpleTransactionService


def get_transaction_service(session: DatabaseSession) -> SimpleTransactionService:
    return SimpleTransactionService(
        TransactionRepository(session),
        AccountingRepository(session),
        InventoryRepository(session),
    )


def get_receipt_storage(settings: SettingsDependency) -> ReceiptStorage:
    return ReceiptStorage(settings)


TransactionServiceDependency = Annotated[SimpleTransactionService, Depends(get_transaction_service)]
ReceiptStorageDependency = Annotated[ReceiptStorage, Depends(get_receipt_storage)]
