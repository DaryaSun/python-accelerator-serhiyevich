from uuid import UUID

from app.core.errors import UnauthenticatedError
from app.models.user import User, UserStatus
from app.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get_active(self, user_id: UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise UnauthenticatedError("UNAUTHENTICATED", "Not authenticated")
        return user
