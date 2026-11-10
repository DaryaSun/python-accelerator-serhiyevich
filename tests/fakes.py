from uuid import UUID

from app.models.user import User


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    async def get_by_email(self, email: str) -> User | None:
        return next(
            (u for u in self._users if u.email.lower() == email.lower() and u.deleted_at is None),
            None,
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        return next((u for u in self._users if u.id == user_id and u.deleted_at is None), None)
