from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.sync.models import (
    DeviceSyncState,
    SyncChange,
    SyncConflictRevision,
    SyncOperationLog,
    SyncRecord,
)


class SyncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, value: object) -> None:
        self.session.add(value)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def operation(
        self, business_id: UUID, device_id: str, operation_id: str
    ) -> SyncOperationLog | None:
        return (
            await self.session.scalars(
                select(SyncOperationLog).where(
                    SyncOperationLog.business_id == business_id,
                    SyncOperationLog.device_id == device_id,
                    SyncOperationLog.operation_id == operation_id,
                )
            )
        ).one_or_none()

    async def record(
        self, business_id: UUID, entity_type: str, entity_id: UUID, *, lock: bool = False
    ) -> SyncRecord | None:
        statement = select(SyncRecord).where(
            SyncRecord.business_id == business_id,
            SyncRecord.entity_type == entity_type,
            SyncRecord.entity_id == entity_id,
        )
        if lock:
            statement = statement.with_for_update()
        return (await self.session.scalars(statement)).one_or_none()

    async def changes(self, business_id: UUID, cursor: int, limit: int) -> list[SyncChange]:
        return list(
            await self.session.scalars(
                select(SyncChange)
                .where(SyncChange.business_id == business_id, SyncChange.sequence > cursor)
                .order_by(SyncChange.sequence)
                .limit(limit + 1)
            )
        )

    async def device_state(self, business_id: UUID, device_id: str) -> DeviceSyncState | None:
        return (
            await self.session.scalars(
                select(DeviceSyncState).where(
                    DeviceSyncState.business_id == business_id,
                    DeviceSyncState.device_id == device_id,
                )
            )
        ).one_or_none()

    async def open_conflict_count(self, business_id: UUID, device_id: str) -> int:
        return int(
            await self.session.scalar(
                select(func.count(SyncConflictRevision.id)).where(
                    SyncConflictRevision.business_id == business_id,
                    SyncConflictRevision.device_id == device_id,
                    SyncConflictRevision.status == "OPEN",
                )
            )
            or 0
        )
