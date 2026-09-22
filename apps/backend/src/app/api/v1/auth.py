from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.service import AuthService
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenPairResponse,
    UpdateProfileRequest,
    UserPublic,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    result = await service.login(request.username, request.password)
    return LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        access_expires_at=result.access_expires_at,
        refresh_expires_at=result.refresh_expires_at,
        user=UserPublic.model_validate(result.user),
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    request: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    result = await service.refresh(request.refresh_token)
    return TokenPairResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        access_expires_at=result.access_expires_at,
        refresh_expires_at=result.refresh_expires_at,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    return user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    request: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.update_profile(user=user, request=request)


@router.post("/me/change-password", response_model=TokenPairResponse)
async def change_password(
    request: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPairResponse:
    result = await service.change_password(
        user=user,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return TokenPairResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        access_expires_at=result.access_expires_at,
        refresh_expires_at=result.refresh_expires_at,
    )
