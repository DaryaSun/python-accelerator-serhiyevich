from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import PermissionDeniedError, UnauthenticatedError
from app.core.security import Principal, Role, decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user_repo import SqlUserRepository, UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

bearer = HTTPBearer(auto_error=False)


def get_user_repo(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return SqlUserRepository(session)


def get_auth_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(repo, settings)


def get_user_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> UserService:
    return UserService(repo)


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    if credentials is None:
        raise UnauthenticatedError("UNAUTHENTICATED", "Not authenticated")
    claims = decode_token(credentials.credentials, settings)
    try:
        user_id = UUID(claims["sub"])
    except ValueError as exc:
        raise UnauthenticatedError("UNAUTHENTICATED", "Not authenticated") from exc
    return await service.get_active(user_id)


def current_principal(user: Annotated[User, Depends(current_user)]) -> Principal:
    return Principal(user.id, user.role, None, None)


def require_role(*roles: Role) -> Callable[..., Awaitable[Principal]]:
    async def check(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in roles:
            raise PermissionDeniedError("PERMISSION_DENIED", "Permission denied")
        return principal

    return check
