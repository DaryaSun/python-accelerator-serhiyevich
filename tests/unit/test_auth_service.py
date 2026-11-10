from uuid import uuid4

import pytest

from app.core import security
from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.security import DUMMY_HASH, Role, decode_token, hash_password
from app.models.user import User, UserStatus
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from tests.fakes import FakeUserRepository


def make_user(**kw: object) -> User:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "email": "anna@example.com",
        "password_hash": hash_password("pw"),
        "role": Role.TRAINER,
        "status": UserStatus.ACTIVE,
    }
    return User(**{**defaults, **kw})


async def test_login_success(settings: Settings) -> None:
    user = make_user()
    token = await AuthService(FakeUserRepository([user]), settings).login(user.email, "pw")
    assert decode_token(token, settings)["sub"] == str(user.id)


async def test_login_wrong_password(settings: Settings) -> None:
    service = AuthService(FakeUserRepository([make_user()]), settings)
    with pytest.raises(UnauthenticatedError) as exc:
        await service.login("anna@example.com", "bad")
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_login_unknown_email_verifies_dummy_hash(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def spy(password_hash: str, password: str) -> bool:
        calls.append(password_hash)
        return False

    monkeypatch.setattr("app.services.auth_service.verify_password", spy)
    with pytest.raises(UnauthenticatedError) as exc:
        await AuthService(FakeUserRepository([]), settings).login("none@example.com", "pw")
    assert exc.value.code == "INVALID_CREDENTIALS"
    assert calls == [DUMMY_HASH]
    assert security.verify_password(DUMMY_HASH, "pw") is False


async def test_login_inactive_user(settings: Settings) -> None:
    user = make_user(status=UserStatus.INACTIVE)
    with pytest.raises(UnauthenticatedError) as exc:
        await AuthService(FakeUserRepository([user]), settings).login(user.email, "pw")
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_get_active_returns_user() -> None:
    user = make_user()
    assert await UserService(FakeUserRepository([user])).get_active(user.id) is user


@pytest.mark.parametrize("kind", ["inactive", "deleted", "missing"])
async def test_get_active_rejects(kind: str) -> None:
    from datetime import UTC, datetime

    extra: dict[str, object] = {
        "inactive": {"status": UserStatus.INACTIVE},
        "deleted": {"deleted_at": datetime.now(UTC)},
        "missing": {},
    }[kind]  # type: ignore[assignment]
    user = make_user(**extra)
    users = [] if kind == "missing" else [user]
    with pytest.raises(UnauthenticatedError) as exc:
        await UserService(FakeUserRepository(users)).get_active(user.id)
    assert exc.value.code == "UNAUTHENTICATED"
