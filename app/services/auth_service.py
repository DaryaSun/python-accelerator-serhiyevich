from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.security import DUMMY_HASH, encode_token, verify_password
from app.models.user import UserStatus
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, repo: UserRepository, settings: Settings) -> None:
        self._repo = repo
        self._settings = settings

    async def login(self, email: str, password: str) -> str:
        user = await self._repo.get_by_email(email)
        password_hash = user.password_hash if user else DUMMY_HASH
        valid = verify_password(password_hash, password)
        if user is None or not valid or user.status != UserStatus.ACTIVE:
            raise UnauthenticatedError("INVALID_CREDENTIALS", "Invalid email or password")
        return encode_token(user.id, user.role, None, None, self._settings)
