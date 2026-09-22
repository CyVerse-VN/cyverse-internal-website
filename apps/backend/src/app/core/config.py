import re
from functools import lru_cache
from pathlib import Path

from pydantic import PositiveInt, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "CyVerse Internal Tools API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cyverse"
    auth_jwt_secret: SecretStr = SecretStr("development-only-change-this-jwt-secret")
    auth_jwt_issuer: str = "cyverse-backend"
    auth_jwt_audience: str = "cyverse-internal-web"
    auth_access_token_minutes: PositiveInt = 15
    auth_refresh_token_days: PositiveInt = 30
    supabase_pooler_region: str | None = None
    supabase_url: str | None = None
    supabase_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    research_semantic_scholar_api_key: SecretStr | None = None
    research_openalex_api_key: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("supabase_pooler_region", mode="before")
    @classmethod
    def normalize_pooler_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if re.fullmatch(r"[a-z]{2}-[a-z]+-\d", normalized) is None:
            raise ValueError("SUPABASE_POOLER_REGION must be a valid AWS region")
        return normalized

    @model_validator(mode="after")
    def use_supabase_session_pooler(self) -> "Settings":
        if self.supabase_pooler_region is None:
            return self

        url = make_url(self.database_url)
        direct_match = re.fullmatch(r"db\.([a-z0-9]+)\.supabase\.co", url.host or "")
        if direct_match is None:
            if (url.host or "").endswith(".pooler.supabase.com"):
                return self
            raise ValueError("SUPABASE_POOLER_REGION requires a Supabase direct DATABASE_URL")

        project_ref = direct_match.group(1)
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        pooler_url = url.set(
            username=f"postgres.{project_ref}",
            host=f"aws-0-{self.supabase_pooler_region}.pooler.supabase.com",
            port=5432,
            query=query,
        )
        self.database_url = pooler_url.render_as_string(hide_password=False)
        return self

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
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
