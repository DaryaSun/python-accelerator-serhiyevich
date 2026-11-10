import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings
from app.core.errors import UnauthenticatedError


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    TRAINER = "trainer"
    COACH = "coach"
    PLAYER = "player"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: uuid.UUID
    role: Role
    trainer_id: uuid.UUID | None
    act: uuid.UUID | None


_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


DUMMY_HASH = hash_password("dummy-password")


def encode_token(
    user_id: uuid.UUID,
    role: Role,
    trainer_id: uuid.UUID | None,
    act: uuid.UUID | None,
    settings: Settings,
) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "role": role.value,
        "trainer_id": str(trainer_id) if trainer_id else None,
        "act": str(act) if act else None,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + settings.access_token_ttl,
    }
    return jwt.encode(
        claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthenticatedError("UNAUTHENTICATED", "Not authenticated") from exc
