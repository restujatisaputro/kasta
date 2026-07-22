from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from kasta_api.db import models as mapped_models  # noqa: F401
from kasta_api.db.base import Base
from kasta_api.db.session import get_db_session
from kasta_api.main import app
from kasta_api.modules.auth.constants import RoleCode, role_id
from kasta_api.modules.auth.dependencies import get_password_manager
from kasta_api.modules.auth.schemas import TokenPairResponse
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.auth.seed import seed_auth_reference_data
from kasta_api.modules.businesses.models import Business, BusinessMember
from kasta_api.modules.businesses.seed import seed_business_categories
from kasta_api.modules.users.models import User


@dataclass(frozen=True, slots=True)
class AuthTestEnvironment:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    business_a_id: UUID
    business_b_id: UUID
    owner_id: UUID
    staff_id: UUID
    phone_user_id: UUID
    unverified_user_id: UUID
    password: str


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def auth_environment() -> AsyncIterator[AuthTestEnvironment]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_auth_reference_data(session)
        await seed_business_categories(session)
        environment = await _seed_tenants(session, session_factory)

    async def override_database() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_database
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield AuthTestEnvironment(
            client=client,
            session_factory=environment.session_factory,
            business_a_id=environment.business_a_id,
            business_b_id=environment.business_b_id,
            owner_id=environment.owner_id,
            staff_id=environment.staff_id,
            phone_user_id=environment.phone_user_id,
            unverified_user_id=environment.unverified_user_id,
            password=environment.password,
        )
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_tenants(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> AuthTestEnvironment:
    now = utc_now()
    password = "Kasta-password-aman-2026"
    password_hash = get_password_manager().hash(password)
    business_a_id = uuid4()
    business_b_id = uuid4()
    owner_id = uuid4()
    staff_id = uuid4()
    phone_user_id = uuid4()
    unverified_user_id = uuid4()
    business_b_owner_id = uuid4()
    session.add_all(
        [
            Business(id=business_a_id, code="TOKO-A", name="Toko A", status="ACTIVE"),
            Business(id=business_b_id, code="TOKO-B", name="Toko B", status="ACTIVE"),
            User(
                id=owner_id,
                email="owner@example.com",
                password_hash=password_hash,
                full_name="Pemilik A",
                email_verified_at=now,
            ),
            User(
                id=staff_id,
                email="staff@example.com",
                password_hash=password_hash,
                full_name="Staf A",
                email_verified_at=now,
            ),
            User(
                id=phone_user_id,
                phone="+6281234567890",
                password_hash=password_hash,
                full_name="Kasir Telepon",
                phone_verified_at=now,
            ),
            User(
                id=unverified_user_id,
                email="unverified@example.com",
                password_hash=password_hash,
                full_name="Pengguna Baru",
            ),
            User(
                id=business_b_owner_id,
                email="owner-b@example.com",
                password_hash=password_hash,
                full_name="Pemilik B",
                email_verified_at=now,
            ),
        ]
    )
    await session.flush()
    members = [
        (business_a_id, owner_id, RoleCode.BUSINESS_OWNER),
        (business_a_id, staff_id, RoleCode.BUSINESS_STAFF),
        (business_a_id, phone_user_id, RoleCode.BUSINESS_STAFF),
        (business_a_id, unverified_user_id, RoleCode.BUSINESS_STAFF),
        (business_b_id, business_b_owner_id, RoleCode.BUSINESS_OWNER),
    ]
    session.add_all(
        [
            BusinessMember(
                business_id=business_id,
                user_id=user_id,
                role_id=role_id(role),
                status="ACTIVE",
                joined_at=now - timedelta(days=1),
            )
            for business_id, user_id, role in members
        ]
    )
    await session.commit()
    return AuthTestEnvironment(
        client=None,  # type: ignore[arg-type]
        session_factory=session_factory,
        business_a_id=business_a_id,
        business_b_id=business_b_id,
        owner_id=owner_id,
        staff_id=staff_id,
        phone_user_id=phone_user_id,
        unverified_user_id=unverified_user_id,
        password=password,
    )


async def login_as(
    environment: AuthTestEnvironment,
    *,
    identifier: str,
    business_id: UUID | None = None,
    password: str | None = None,
) -> TokenPairResponse:
    response = await environment.client.post(
        "/api/v1/auth/login",
        json={
            "business_id": str(business_id or environment.business_a_id),
            "identifier": identifier,
            "password": password or environment.password,
            "device_id": f"test-device-{uuid4()}",
            "platform": "WEB",
            "device_name": "Pytest",
            "app_version": "test",
        },
    )
    assert response.status_code == 200, response.text
    return TokenPairResponse.model_validate(response.json())
