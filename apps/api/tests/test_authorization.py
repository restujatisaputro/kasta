import pytest
from fastapi import HTTPException

from kasta_api.core.config import get_settings
from kasta_api.modules.auth.constants import PermissionCode, RoleCode
from kasta_api.modules.auth.dependencies import require_permission
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


async def test_staff_has_read_but_not_delete_permission(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="staff@example.com")
    read_dependency = require_permission(PermissionCode.TRANSACTION_READ)
    delete_dependency = require_permission(PermissionCode.TRANSACTION_DELETE)
    async with auth_environment.session_factory() as session:
        principal = await read_dependency(
            business_id=auth_environment.business_a_id,
            token=tokens.access_token,
            session=session,
            settings=get_settings(),
        )
        assert principal.role == RoleCode.BUSINESS_STAFF.value
        with pytest.raises(HTTPException) as error:
            await delete_dependency(
                business_id=auth_environment.business_a_id,
                token=tokens.access_token,
                session=session,
                settings=get_settings(),
            )
    assert error.value.status_code == 403
    assert PermissionCode.TRANSACTION_DELETE.value in str(error.value.detail)
