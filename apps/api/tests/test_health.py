import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID

from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from kasta_api.db.session import get_db_session
from kasta_api.main import app


def database_override(
    session: AsyncSession,
) -> Callable[[], AsyncIterator[AsyncSession]]:
    async def override() -> AsyncIterator[AsyncSession]:
        yield session

    return override


def api_request(method: str, path: str, *, headers: dict[str, str] | None = None) -> Response:
    async def send() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return await client.request(method, path, headers=headers)

    return asyncio.run(send())


def test_liveness_returns_service_identity() -> None:
    response = api_request("GET", "/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "kasta-api"
    assert UUID(response.headers["X-Request-ID"])


def test_readiness_returns_timestamp() -> None:
    session_mock = AsyncMock(spec=AsyncSession)
    session = cast(AsyncSession, session_mock)
    app.dependency_overrides[get_db_session] = database_override(session)
    try:
        response = api_request(
            "GET",
            "/api/v1/health/ready",
            headers={"X-Request-ID": "test-ready-001"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.headers["X-Request-ID"] == "test-ready-001"
    timestamp = response.json()["timestamp"].replace("Z", "+00:00")
    assert datetime.fromisoformat(timestamp).tzinfo is not None
    session_mock.execute.assert_awaited_once()


def test_readiness_returns_structured_error_when_database_is_unavailable() -> None:
    session_mock = AsyncMock(spec=AsyncSession)
    session_mock.execute.side_effect = SQLAlchemyError("database unavailable")
    session = cast(AsyncSession, session_mock)
    app.dependency_overrides[get_db_session] = database_override(session)
    try:
        response = api_request("GET", "/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert body["status"] == 503
    assert body["detail"] == "Database belum siap."
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_unknown_route_uses_structured_error_response() -> None:
    response = api_request("GET", "/api/v1/not-found")

    body = response.json()
    assert response.status_code == 404
    assert body["title"] == "Not Found"
    assert body["instance"] == "/api/v1/not-found"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_cors_preflight_allows_local_web_origin() -> None:
    response = api_request(
        "OPTIONS",
        "/api/v1/health/live",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "X-Request-ID" in response.headers
