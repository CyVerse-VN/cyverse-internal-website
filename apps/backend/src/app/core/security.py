"""Authentication and cryptographic helpers."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

PASSWORD_HASHER = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


class TokenValidationError(ValueError):
    """Raised when a signed authentication token cannot be trusted."""


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    token_type: TokenType
    token_version: int
    expires_at: datetime


def hash_password(password: str) -> str:
    """Hash a password with the configured Argon2id policy."""

    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing hash-library errors to callers."""

    return PASSWORD_HASHER.verify(password, password_hash)


def _create_token(
    *,
    user_id: UUID,
    token_version: int,
    token_type: TokenType,
    lifetime: timedelta,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + lifetime
    token = jwt.encode(
        {
            "iss": settings.auth_jwt_issuer,
            "aud": settings.auth_jwt_audience,
            "sub": str(user_id),
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expires_at,
            "type": token_type,
            "ver": token_version,
            "jti": str(uuid4()),
        },
        settings.auth_jwt_secret.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )
    return token, expires_at


def create_access_token(
    user_id: UUID, token_version: int, *, now: datetime | None = None
) -> tuple[str, datetime]:
    """Create a short-lived signed access token."""

    return _create_token(
        user_id=user_id,
        token_version=token_version,
        token_type="access",
        lifetime=timedelta(minutes=settings.auth_access_token_minutes),
        now=now,
    )


def create_refresh_token(
    user_id: UUID, token_version: int, *, now: datetime | None = None
) -> tuple[str, datetime]:
    """Create a longer-lived signed refresh token."""

    return _create_token(
        user_id=user_id,
        token_version=token_version,
        token_type="refresh",
        lifetime=timedelta(days=settings.auth_refresh_token_days),
        now=now,
    )


def decode_token(token: str, expected_type: TokenType) -> TokenClaims:
    """Validate a JWT and return the claims used by authorization."""

    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={
                "require": [
                    "iss",
                    "aud",
                    "sub",
                    "iat",
                    "nbf",
                    "exp",
                    "type",
                    "ver",
                    "jti",
                ]
            },
        )
        token_type = payload["type"]
        token_version = payload["ver"]
        if token_type != expected_type:
            raise TokenValidationError("Unexpected token type")
        if isinstance(token_version, bool) or not isinstance(token_version, int):
            raise TokenValidationError("Invalid token version")
        if token_version < 0:
            raise TokenValidationError("Invalid token version")
        return TokenClaims(
            user_id=UUID(payload["sub"]),
            token_type=expected_type,
            token_version=token_version,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, TokenValidationError):
            raise
        raise TokenValidationError("Invalid authentication token") from error
