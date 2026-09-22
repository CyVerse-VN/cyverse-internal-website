from typing import cast
from uuid import UUID, uuid4

import pytest

from app.auth.errors import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    SelfAdministrationError,
)
from app.auth.repository import AuthRepository
from app.auth.service import AuthService, utc_now
from app.core.security import decode_token, hash_password, verify_password
from app.models.user import ROLE_ADMIN, ROLE_MEMBER, User
from app.schemas.auth import (
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateUserRequest,
)


class FakeAuthRepository:
    def __init__(self, users: list[User]) -> None:
        self.users = {user.id: user for user in users}
        self.commits = 0

    async def get_user_by_username(self, username: str) -> User | None:
        return next(
            (
                user
                for user in self.users.values()
                if user.username == username and user.deleted_at is None
            ),
            None,
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        user = self.users.get(user_id)
        return user if user is not None and user.deleted_at is None else None

    async def count_active_admins(self) -> int:
        return sum(
            user.role == ROLE_ADMIN and user.is_active and user.deleted_at is None
            for user in self.users.values()
        )

    def add_user(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.token_version is None:
            user.token_version = 0
        self.users[user.id] = user

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass


def make_user(*, role: str = ROLE_MEMBER, active: bool = True) -> User:
    now = utc_now()
    return User(
        id=uuid4(),
        username="nguyen.anh",
        password_hash=hash_password("correct-password"),
        display_name="Nguyen Anh",
        team="Data Team",
        role=role,
        is_active=active,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_login_issues_separate_access_and_refresh_tokens() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))

    result = await service.login("NGUYEN.ANH", "correct-password")

    assert result.user is user
    assert result.access_token != result.refresh_token
    assert decode_token(result.access_token, "access").user_id == user.id
    assert decode_token(result.refresh_token, "refresh").user_id == user.id
    assert result.access_expires_at < result.refresh_expires_at


@pytest.mark.asyncio
async def test_refresh_token_issues_a_new_token_pair() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))
    login = await service.login(user.username, "correct-password")

    refreshed = await service.refresh(login.refresh_token)

    assert refreshed.access_token != login.access_token
    assert refreshed.refresh_token != login.refresh_token
    assert decode_token(refreshed.access_token, "access").user_id == user.id
    assert decode_token(refreshed.refresh_token, "refresh").user_id == user.id


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_an_access_token() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))
    login = await service.login(user.username, "correct-password")

    with pytest.raises(AuthenticationRequiredError):
        await service.authenticate_access_token(login.refresh_token)


@pytest.mark.asyncio
async def test_failed_logins_do_not_lock_the_account() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))

    for _ in range(10):
        with pytest.raises(InvalidCredentialsError):
            await service.login(user.username, "incorrect-password")

    assert (await service.login(user.username, "correct-password")).user is user


@pytest.mark.asyncio
async def test_inactive_and_unknown_accounts_use_the_same_error() -> None:
    service = AuthService(cast(AuthRepository, FakeAuthRepository([make_user(active=False)])))

    with pytest.raises(InvalidCredentialsError) as inactive_error:
        await service.login("nguyen.anh", "correct-password")
    with pytest.raises(InvalidCredentialsError) as unknown_error:
        await service.login("unknown.user", "correct-password")

    assert inactive_error.value.detail == unknown_error.value.detail


@pytest.mark.asyncio
async def test_soft_deleted_account_cannot_sign_in() -> None:
    user = make_user()
    user.deleted_at = utc_now()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))

    with pytest.raises(InvalidCredentialsError):
        await service.login(user.username, "correct-password")


@pytest.mark.asyncio
async def test_admin_cannot_demote_own_account() -> None:
    admin = make_user(role=ROLE_ADMIN)
    service = AuthService(cast(AuthRepository, FakeAuthRepository([admin])))

    with pytest.raises(SelfAdministrationError):
        await service.update_user(
            actor=admin,
            user_id=admin.id,
            request=UpdateUserRequest(role=ROLE_MEMBER),
        )


@pytest.mark.asyncio
async def test_deactivating_an_account_invalidates_its_existing_tokens() -> None:
    admin = make_user(role=ROLE_ADMIN)
    admin.username = "admin"
    member = make_user()
    repository = FakeAuthRepository([admin, member])
    service = AuthService(cast(AuthRepository, repository))
    login = await service.login(member.username, "correct-password")

    await service.update_user(
        actor=admin,
        user_id=member.id,
        request=UpdateUserRequest(is_active=False),
    )

    assert member.token_version == 1
    with pytest.raises(AuthenticationRequiredError):
        await service.authenticate_access_token(login.access_token)


@pytest.mark.asyncio
async def test_create_user_stores_an_argon2_password_hash() -> None:
    repository = FakeAuthRepository([])
    service = AuthService(cast(AuthRepository, repository))

    user = await service.create_user(
        CreateUserRequest(
            username="new.member",
            password="a-secure-password",
            display_name="New Member",
        )
    )

    assert user.password_hash != "a-secure-password"
    assert user.password_hash.startswith("$argon2")
    assert verify_password("a-secure-password", user.password_hash)


@pytest.mark.asyncio
async def test_reset_password_hashes_password_and_invalidates_existing_tokens() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))
    login = await service.login(user.username, "correct-password")

    await service.reset_password(
        user_id=user.id,
        password=ResetPasswordRequest(password="replacement-password").password,
    )

    assert verify_password("replacement-password", user.password_hash)
    assert user.token_version == 1
    with pytest.raises(AuthenticationRequiredError):
        await service.authenticate_access_token(login.access_token)
    with pytest.raises(AuthenticationRequiredError):
        await service.refresh(login.refresh_token)


@pytest.mark.asyncio
async def test_user_can_update_own_profile_without_changing_access_fields() -> None:
    user = make_user(role=ROLE_ADMIN)
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))

    updated = await service.update_profile(
        user=user,
        request=UpdateProfileRequest(display_name="Updated Name", team="Platform"),
    )

    assert updated.display_name == "Updated Name"
    assert updated.team == "Platform"
    assert updated.role == ROLE_ADMIN
    assert updated.is_active is True


@pytest.mark.asyncio
async def test_change_password_verifies_current_password_and_rotates_tokens() -> None:
    user = make_user()
    service = AuthService(cast(AuthRepository, FakeAuthRepository([user])))
    login = await service.login(user.username, "correct-password")

    with pytest.raises(InvalidCurrentPasswordError):
        await service.change_password(
            user=user,
            current_password="incorrect-password",
            new_password="replacement-password",
        )

    changed = await service.change_password(
        user=user,
        current_password="correct-password",
        new_password="replacement-password",
    )

    assert verify_password("replacement-password", user.password_hash)
    assert user.token_version == 1
    assert changed.access_token != login.access_token
    with pytest.raises(AuthenticationRequiredError):
        await service.refresh(login.refresh_token)
