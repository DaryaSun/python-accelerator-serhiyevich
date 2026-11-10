from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from uuid6 import uuid7

from app.api.deps import get_user_repo
from app.core.config import Settings, get_settings
from app.core.security import Role, hash_password
from app.main import create_app
from app.models.user import User, UserStatus
from tests.fakes import FakeUserRepository

PASSWORD = "s3cret-pass"


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="postgresql+asyncpg://x/x", jwt_secret="k" * 32)


@pytest.fixture
def users() -> list[User]:
    password_hash = hash_password(PASSWORD)
    return [
        User(
            id=uuid7(),
            email="anna@example.com",
            password_hash=password_hash,
            role=Role.TRAINER,
            status=UserStatus.ACTIVE,
        ),
        User(
            id=uuid7(),
            email="off@example.com",
            password_hash=password_hash,
            role=Role.PLAYER,
            status=UserStatus.INACTIVE,
        ),
    ]


@pytest.fixture
def app(users: list[User], settings: Settings) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_user_repo] = lambda: FakeUserRepository(users)
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
