import json
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote

import certifi
from pydantic import Field, PositiveInt, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

BACKEND_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "CyVerse Internal Tools API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(repr=False)
    auth_jwt_secret: SecretStr = SecretStr("development-only-change-this-jwt-secret")
    auth_jwt_issuer: str = "cyverse-backend"
    auth_jwt_audience: str = "cyverse-internal-web"
    auth_access_token_minutes: PositiveInt = 15
    auth_refresh_token_days: PositiveInt = 30
    openrouter_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    research_semantic_scholar_api_key: SecretStr | None = None
    research_openalex_api_key: SecretStr | None = None
    cors_origins: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    cors_origin_regex: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                with suppress(json.JSONDecodeError):
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator("cors_origin_regex", mode="before")
    @classmethod
    def normalize_origin_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if "://" in value:
            scheme, rest = value.split("://", 1)
            if "@" in rest:
                auth, host_part = rest.rsplit("@", 1)
                if ":" in auth and "@" in auth:
                    user, password = auth.split(":", 1)
                    safe_password = quote(unquote(password), safe="")
                    value = f"{scheme}://{user}:{safe_password}@{host_part}"
        try:
            url = make_url(value)
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection URL") from None
        if url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver")
        if not url.host or not url.username or not url.database:
            raise ValueError("DATABASE_URL must include a host, username, and database name")

        query = dict(url.query)
        if url.host.lower().endswith(".pg.tidbcloud.com"):
            query.setdefault("sslmode", "verify-full")
            sslmode = query["sslmode"]
            if not isinstance(sslmode, str) or sslmode not in {"require", "verify-ca", "verify-full"}:
                raise ValueError("DATABASE_URL must require TLS for TiDB Cloud")
            if sslmode == "verify-full":
                query.setdefault("sslrootcert", certifi.where())
        return url.set(drivername="postgresql+psycopg", query=query).render_as_string(
            hide_password=False
        )

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        secret = self.auth_jwt_secret.get_secret_value()
        if len(secret) < 32:
            raise ValueError("AUTH_JWT_SECRET must contain at least 32 characters")
        unsafe_prefixes = ("development-only-", "replace-with-")
        if self.app_env.lower() == "production" and secret.startswith(unsafe_prefixes):
            raise ValueError("AUTH_JWT_SECRET must be changed in production")
        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
