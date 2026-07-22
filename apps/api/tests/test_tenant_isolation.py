import pytest
from fastapi import HTTPException

from kasta_api.core.config import get_settings
from kasta_api.modules.auth.constants import PermissionCode
from kasta_api.modules.auth.dependencies import require_permission
from tests.conftest import AuthTestEnvironment, login_as

pytestmark = pytest.mark.anyio


async def test_access_token_cannot_cross_business_boundary(
    auth_environment: AuthTestEnvironment,
) -> None:
    tokens = await login_as(auth_environment, identifier="owner@example.com")
    http_response = await auth_environment.client.get(
        f"/api/v1/businesses/{auth_environment.business_b_id}/auth/authorization",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert http_response.status_code == 403

    dependency = require_permission(PermissionCode.TRANSACTION_READ)
    async with auth_environment.session_factory() as session:
        with pytest.raises(HTTPException) as error:
            await dependency(
                business_id=auth_environment.business_b_id,
                token=tokens.access_token,
                session=session,
                settings=get_settings(),
            )
    assert error.value.status_code == 403
    assert "usaha" in str(error.value.detail).lower()
