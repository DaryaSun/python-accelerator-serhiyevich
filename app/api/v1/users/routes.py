from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.api.errors import ErrorResponse
from app.api.v1.users.schemas import MeResponse
from app.models.user import User

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    summary="Current caller's account",
    responses={401: {"model": ErrorResponse}},
)
async def me(user: Annotated[User, Depends(current_user)]) -> MeResponse:
    return MeResponse.model_validate(user)
