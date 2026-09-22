from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleValue = Literal["admin", "member"]

USERNAME_PATTERN = r"^[A-Za-z0-9._-]+$"


class UsernameMixin(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=USERNAME_PATTERN)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class PasswordMixin(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str
    team: str | None
    role: RoleValue
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(UsernameMixin, PasswordMixin):
    pass


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class CreateUserRequest(UsernameMixin, PasswordMixin):
    display_name: str = Field(min_length=1, max_length=100)
    team: str | None = Field(default=None, min_length=1, max_length=100)
    role: RoleValue = "member"

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Display name cannot be blank")
        return stripped

    @field_validator("team")
    @classmethod
    def validate_team(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Team cannot be blank")
        return stripped


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    team: str | None = Field(default=None, min_length=1, max_length=100)
    role: RoleValue | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Display name cannot be blank")
        return stripped

    @field_validator("team")
    @classmethod
    def validate_team(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Team cannot be blank")
        return stripped


class ResetPasswordRequest(PasswordMixin):
    pass


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    team: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Display name cannot be blank")
        return stripped

    @field_validator("team")
    @classmethod
    def validate_team(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Team cannot be blank")
        return stripped


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserListResponse(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int
    current_user_id: UUID
