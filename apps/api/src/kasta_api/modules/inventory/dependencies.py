from typing import Annotated

from fastapi import Depends

from kasta_api.api.dependencies import DatabaseSession
from kasta_api.modules.inventory.repository import InventoryRepository
from kasta_api.modules.inventory.service import InventoryService


def get_inventory_service(session: DatabaseSession) -> InventoryService:
    return InventoryService(InventoryRepository(session))


InventoryServiceDependency = Annotated[InventoryService, Depends(get_inventory_service)]
