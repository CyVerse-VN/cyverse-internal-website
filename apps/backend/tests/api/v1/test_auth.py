from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.auth.dependencies import get_auth_service, get_current_user
from app.auth.errors import InvalidCredentialsError
from app.auth.service import LoginResult, utc_now
from app.main import create_app
from app.models.user import ROLE_ADMIN, ROLE_MEMBER, User


def make_user(role: str = ROLE_MEMBER) -> User:
    now = utc_now()
    return User(
        id=uuid4(),
        username="nguyen.anh",
        password_hash="not-returned",
        display_name="Nguyen Anh",
        team="Data Team",
        role=role,
        is_active=True,
        token_version=0,
        created_at=now,
        updated_at=now,
    )


class LoginService:
    async def login(self, username: str, password: str) -> LoginResult:
        if username != "nguyen.anh" or password != "correct-password":
            raise InvalidCredentialsError
        return LoginResult(
            access_token="signed-access-token",
            refresh_token="signed-refresh-token",
            access_expires_at=utc_now() + timedelta(minutes=15),
            refresh_expires_at=utc_now() + timedelta(days=30),
            user=make_user(),
        )

    async def refresh(self, refresh_token: str) -> LoginResult:
        if refresh_token != "signed-refresh-token":
            raise InvalidCredentialsError
        return await self.login("nguyen.anh", "correct-password")


class UserListService:
    def __init__(self, users: list[User]) -> None:
        self.users = users

    async def list_users(
        self,
        query: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        return self.users, len(self.users)


class AccountService:
    async def update_profile(self, *, user: User, request: object) -> User:
        user.display_name = "Updated Name"
        user.team = "Platform"
        return user

    async def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> LoginResult:
        return LoginResult(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            access_expires_at=utc_now() + timedelta(minutes=15),
            refresh_expires_at=utc_now() + timedelta(days=30),
            user=user,
        )


def test_login_contract_returns_token_pair_and_safe_user_fields() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = LoginService

    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"username": "nguyen.anh", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "signed-access-token"
    assert response.json()["refresh_token"] == "signed-refresh-token"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["username"] == "nguyen.anh"
    assert "password_hash" not in response.json()["user"]


def test_refresh_contract_returns_a_new_token_pair() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = LoginService

    response = TestClient(app).post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "signed-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "signed-access-token"
    assert response.json()["refresh_token"] == "signed-refresh-token"
    assert "user" not in response.json()


def test_login_failure_does_not_disclose_account_state() -> None:
    app = create_app()
    app.dependency_overrides[get_auth_service] = LoginService

    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"username": "missing.user", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_validation_errors_do_not_echo_password_input() -> None:
    app = create_app()

    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"username": "nguyen.anh", "password": "abc123!"},
    )

    assert response.status_code == 422
    assert "abc123!" not in response.text


def test_member_cannot_access_admin_routes() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: make_user()

    response = TestClient(app).get("/api/v1/admin/users")
    create_response = TestClient(app).post(
        "/api/v1/admin/users",
        json={
            "username": "new.member",
            "password": "a-secure-password",
            "display_name": "New Member",
            "role": "member",
        },
    )

    assert response.status_code == 403
    assert create_response.status_code == 403


def test_admin_user_list_identifies_the_current_user() -> None:
    app = create_app()
    admin = make_user(role=ROLE_ADMIN)
    listed_user = make_user()
    service = UserListService([listed_user])
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_auth_service] = lambda: service

    response = TestClient(app).get("/api/v1/admin/users")

    assert response.status_code == 200
    assert response.json()["current_user_id"] == str(admin.id)
    assert response.json()["items"][0]["id"] == str(listed_user.id)


def test_authenticated_user_can_update_profile_and_change_password() -> None:
    app = create_app()
    user = make_user()
    service = AccountService()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_auth_service] = lambda: service
    client = TestClient(app)

    profile_response = client.patch(
        "/api/v1/auth/me",
        json={"display_name": "Updated Name", "team": "Platform"},
    )
    password_response = client.post(
        "/api/v1/auth/me/change-password",
        json={
            "current_password": "correct-password",
            "new_password": "replacement-password",
        },
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["display_name"] == "Updated Name"
    assert password_response.status_code == 200
    assert password_response.json()["access_token"] == "new-access-token"
