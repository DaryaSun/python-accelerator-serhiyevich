from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.api.errors import ErrorResponse
from app.api.v1.auth.schemas import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    summary="Issue access token",
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def login(
    payload: LoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenResponse:
    return TokenResponse(access_token=await service.login(payload.email, payload.password))
