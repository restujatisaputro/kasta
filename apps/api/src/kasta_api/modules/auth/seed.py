from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.modules.auth.constants import (
    ROLE_NAMES,
    ROLE_PERMISSIONS,
    ROLE_SCOPES,
    PermissionCode,
    RoleCode,
    permission_id,
    role_id,
)
from kasta_api.modules.auth.models import Permission, Role, RolePermission


async def seed_auth_reference_data(session: AsyncSession) -> None:
    session.add_all(
        [
            Role(
                id=role_id(code),
                code=code.value,
                name=ROLE_NAMES[code],
                scope=ROLE_SCOPES[code],
                is_system=True,
            )
            for code in RoleCode
        ]
    )
    session.add_all(
        [
            Permission(
                id=permission_id(code),
                code=code.value,
                module=code.value.split(".", maxsplit=1)[0],
                description=code.value,
            )
            for code in PermissionCode
        ]
    )
    session.add_all(
        [
            RolePermission(role_id=role_id(role), permission_id=permission_id(permission))
            for role, permissions in ROLE_PERMISSIONS.items()
            for permission in permissions
        ]
    )
    await session.commit()
