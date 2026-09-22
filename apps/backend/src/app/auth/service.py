from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.auth.errors import (
    AccountInvariantError,
    AuthenticationRequiredError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    PasswordReuseError,
    SelfAdministrationError,
    UsernameConflictError,
    UserNotFoundError,
)
from app.auth.repository import AuthRepository
from app.core.security import (
    TokenType,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import ROLE_ADMIN, User
from app.schemas.auth import CreateUserRequest, UpdateProfileRequest, UpdateUserRequest

DUMMY_PASSWORD_HASH = hash_password("CyVerse-dummy-password-never-valid")


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    user: User


class AuthService:
    """Coordinate authentication and internal account administration."""

    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    async def login(self, username: str, password: str) -> LoginResult:
        normalized_username = username.lower()
        user = await self.repository.get_user_by_username(normalized_username)
        if user is None:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError

        now = utc_now()
        if not user.is_active:
            verify_password(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError

        user.last_login_at = now
        await self.repository.commit()
        return self._issue_token_pair(user, now=now)

    async def authenticate_access_token(self, token: str) -> User:
        return await self._authenticate_token(token, "access")

    async def refresh(self, refresh_token: str) -> LoginResult:
        user = await self._authenticate_token(refresh_token, "refresh")
        return self._issue_token_pair(user)

    async def _authenticate_token(self, token: str, token_type: TokenType) -> User:
        try:
            claims = decode_token(token, token_type)
        except TokenValidationError as error:
            raise AuthenticationRequiredError from error
        user = await self.repository.get_user_by_id(claims.user_id)
        if user is None:
            raise AuthenticationRequiredError
        if not user.is_active or user.token_version != claims.token_version:
            raise AuthenticationRequiredError
        return user

    @staticmethod
    def _issue_token_pair(user: User, *, now: datetime | None = None) -> LoginResult:
        access_token, access_expires_at = create_access_token(user.id, user.token_version, now=now)
        refresh_token, refresh_expires_at = create_refresh_token(
            user.id, user.token_version, now=now
        )
        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            user=user,
        )

    async def list_users(
        self, *, query: str | None, page: int, page_size: int
    ) -> tuple[list[User], int]:
        return await self.repository.list_users(
            query=query, offset=(page - 1) * page_size, limit=page_size
        )

    async def create_user(self, request: CreateUserRequest) -> User:
        if await self.repository.get_user_by_username(request.username) is not None:
            raise UsernameConflictError

        user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            display_name=request.display_name.strip(),
            team=request.team.strip() if request.team else None,
            role=request.role,
        )
        self.repository.add_user(user)
        try:
            await self.repository.commit()
        except IntegrityError as error:
            await self.repository.rollback()
            raise UsernameConflictError from error
        return user

    async def update_user(self, *, actor: User, user_id: UUID, request: UpdateUserRequest) -> User:
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        demoting = request.role is not None and request.role != ROLE_ADMIN
        deactivating = request.is_active is False
        if user.id == actor.id and (demoting or deactivating):
            raise SelfAdministrationError

        removing_active_admin = (
            user.role == ROLE_ADMIN and user.is_active and (demoting or deactivating)
        )
        if removing_active_admin and await self.repository.count_active_admins() <= 1:
            raise AccountInvariantError

        fields = request.model_fields_set
        if "display_name" in fields and request.display_name is not None:
            user.display_name = request.display_name.strip()
        if "team" in fields:
            user.team = request.team.strip() if request.team else None
        if "role" in fields and request.role is not None:
            user.role = request.role
        if "is_active" in fields and request.is_active is not None:
            if user.is_active and not request.is_active:
                user.token_version += 1
            user.is_active = request.is_active

        await self.repository.commit()
        return user

    async def reset_password(self, *, user_id: UUID, password: str) -> User:
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        user.password_hash = hash_password(password)
        user.token_version += 1
        await self.repository.commit()
        return user

    async def update_profile(self, *, user: User, request: UpdateProfileRequest) -> User:
        user.display_name = request.display_name
        user.team = request.team
        await self.repository.commit()
        return user

    async def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> LoginResult:
        if not verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError
        if current_password == new_password:
            raise PasswordReuseError

        user.password_hash = hash_password(new_password)
        user.token_version += 1
        await self.repository.commit()
        return self._issue_token_pair(user)

    async def bootstrap_admin(
        self, *, username: str, password: str, display_name: str, team: str | None
    ) -> User:
        if await self.repository.count_active_admins() > 0:
            raise AccountInvariantError
        request = CreateUserRequest(
            username=username,
            password=password,
            display_name=display_name,
            team=team,
            role=ROLE_ADMIN,
        )
        return await self.create_user(request)
