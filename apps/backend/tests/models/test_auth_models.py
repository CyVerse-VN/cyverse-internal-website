import pytest
from pydantic import ValidationError
from sqlalchemy import Enum, String

from app.models.user import User
from app.schemas.auth import CreateUserRequest


def test_user_model_supports_soft_delete_and_token_invalidation() -> None:
    assert {"created_at", "updated_at", "deleted_at", "token_version"}.issubset(
        User.__table__.columns.keys()
    )


def test_role_is_stored_as_a_plain_string() -> None:
    role_type = User.__table__.c.role.type

    assert isinstance(role_type, String)
    assert not isinstance(role_type, Enum)


def test_request_schema_rejects_unknown_role_in_backend_code() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            username="new.member",
            password="a-secure-password",
            display_name="New Member",
            role="owner",
        )


def test_password_policy_accepts_eight_characters_and_rejects_seven() -> None:
    request = CreateUserRequest(
        username="new.member",
        password="12345678",
        display_name="New Member",
    )

    assert len(request.password) == 8
    with pytest.raises(ValidationError):
        CreateUserRequest(
            username="other.member",
            password="1234567",
            display_name="Other Member",
        )


def test_username_policy_rejects_whitespace() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            username="new member",
            password="a-secure-password",
            display_name="New Member",
        )
