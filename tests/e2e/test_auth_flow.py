from datetime import timedelta
from typing import cast
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from httpx import AsyncClient

from app.api.deps import require_role
from app.core.config import Settings
from app.core.security import Role, encode_token
from app.models.user import User
from tests.conftest import PASSWORD


async def login(client: AsyncClient, email: str = "anna@example.com") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200
    return str(resp.json()["access_token"])


async def test_login_then_me(client: AsyncClient, users: list[User]) -> None:
    token = await login(client)
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {
        "id": str(users[0].id),
        "email": "anna@example.com",
        "role": "trainer",
        "status": "active",
    }


async def test_bad_password_matches_unknown_email(client: AsyncClient) -> None:
    bad = await client.post(
        "/api/v1/auth/login", json={"email": "anna@example.com", "password": "nope"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "none@example.com", "password": "nope"}
    )
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_me_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_me_with_expired_token(
    client: AsyncClient, users: list[User], settings: Settings
) -> None:
    expired = settings.model_copy(update={"access_token_ttl": timedelta(seconds=-1)})
    token = encode_token(users[0].id, Role.TRAINER, None, None, expired)
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_login_validation_errors(client: AsyncClient) -> None:
    for body in (
        {"email": "not-an-email", "password": "x"},
        {"email": "anna@example.com", "password": "x", "extra": 1},
    ):
        resp = await client.post("/api/v1/auth/login", json=body)
        assert resp.status_code == 422
        error = resp.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert all({"field", "message"} <= d.keys() for d in error["details"])


async def test_require_role_mismatch(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/admin-only", dependencies=[Depends(require_role(Role.SUPER_ADMIN))])
    async def admin_only() -> None:
        return None

    token = await login(client)
    resp = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def _tamper(token: str) -> str:
    return token[:-5] + ("A" if token[-5] != "A" else "B") + token[-4:]


@pytest.mark.parametrize("case", ["inactive_user", "tampered", "non_uuid_sub"])
async def test_me_rejects_invalid_token(
    client: AsyncClient, users: list[User], settings: Settings, case: str
) -> None:
    if case == "inactive_user":
        token = encode_token(users[1].id, Role.PLAYER, None, None, settings)
    elif case == "tampered":
        token = _tamper(encode_token(users[0].id, Role.TRAINER, None, None, settings))
    else:
        token = encode_token(cast(UUID, "not-a-uuid"), Role.TRAINER, None, None, settings)
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHENTICATED"
    assert resp.headers["WWW-Authenticate"] == "Bearer"


async def test_me_without_token_has_www_authenticate(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.headers["WWW-Authenticate"] == "Bearer"


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/nope")
    assert resp.status_code == 404
    assert set(resp.json()) == {"error"}
    assert {"code", "message"} <= resp.json()["error"].keys()
