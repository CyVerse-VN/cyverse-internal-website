from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import get_auth_service
from app.auth.permissions import require_admin
from app.auth.service import AuthService
from app.models.user import User
from app.schemas.auth import (
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
    UserListResponse,
    UserPublic,
)

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    query: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListResponse:
    users, total = await service.list_users(query=query, page=page, page_size=page_size)
    return UserListResponse(
        items=[UserPublic.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        current_user_id=admin.id,
    )


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.create_user(request)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.update_user(actor=admin, user_id=user_id, request=request)


@router.post("/users/{user_id}/reset-password", response_model=UserPublic)
async def reset_password(
    user_id: UUID,
    request: ResetPasswordRequest,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.reset_password(user_id=user_id, password=request.password)
