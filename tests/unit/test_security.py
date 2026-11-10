from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.security import (
    Role,
    decode_token,
    encode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip() -> None:
    hashed = hash_password("pw")
    assert verify_password(hashed, "pw")
    assert not verify_password(hashed, "other")


def test_token_round_trip(settings: Settings) -> None:
    user_id, trainer_id = uuid4(), uuid4()
    claims = decode_token(encode_token(user_id, Role.PLAYER, trainer_id, None, settings), settings)
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "player"
    assert claims["trainer_id"] == str(trainer_id)
    assert claims["act"] is None
    assert claims["jti"]


def test_expired_token_raises(settings: Settings) -> None:
    expired = settings.model_copy(update={"access_token_ttl": timedelta(seconds=-1)})
    token = encode_token(uuid4(), Role.PLAYER, None, None, expired)
    with pytest.raises(UnauthenticatedError):
        decode_token(token, settings)
