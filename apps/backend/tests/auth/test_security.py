from datetime import timedelta
from uuid import uuid4

import pytest

from app.auth.service import utc_now
from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_passwords_are_hashed_with_argon2_and_verified() -> None:
    password = "a-secure-password"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash)
    assert not verify_password("another-password", password_hash)


def test_signed_tokens_preserve_type_user_and_version() -> None:
    user_id = uuid4()
    access_token, _ = create_access_token(user_id, 3)
    refresh_token, _ = create_refresh_token(user_id, 3)

    access_claims = decode_token(access_token, "access")
    refresh_claims = decode_token(refresh_token, "refresh")

    assert access_claims.user_id == user_id
    assert access_claims.token_version == 3
    assert refresh_claims.user_id == user_id
    assert refresh_claims.expires_at > access_claims.expires_at


def test_expired_or_wrong_type_tokens_are_rejected() -> None:
    expired_token, _ = create_access_token(uuid4(), 0, now=utc_now() - timedelta(days=1))
    refresh_token, _ = create_refresh_token(uuid4(), 0)

    with pytest.raises(TokenValidationError):
        decode_token(expired_token, "access")
    with pytest.raises(TokenValidationError):
        decode_token(refresh_token, "access")
