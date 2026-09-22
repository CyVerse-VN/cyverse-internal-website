from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import BACKEND_ENV_FILE, Settings


def test_backend_env_file_is_scoped_to_backend_directory() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    assert BACKEND_ENV_FILE == backend_root / ".env"
    assert Settings.model_config["env_file"] == BACKEND_ENV_FILE


def test_database_default_uses_installed_psycopg_driver() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_requires_a_non_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_JWT_SECRET must be changed"):
        Settings(app_env="production", _env_file=None)


def test_jwt_secret_requires_at_least_32_characters() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(auth_jwt_secret="too-short", _env_file=None)


def test_supabase_direct_url_can_use_the_ipv4_session_pooler() -> None:
    settings = Settings(
        database_url=(
            "postgresql://postgres:database-secret@"
            "db.abcdefghijklmnopqrst.supabase.co:5432/postgres"
        ),
        supabase_pooler_region="AP-SOUTHEAST-2",
        _env_file=None,
    )
    url = make_url(settings.database_url)

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "postgres.abcdefghijklmnopqrst"
    assert url.password == "database-secret"
    assert url.host == "aws-0-ap-southeast-2.pooler.supabase.com"
    assert url.port == 5432
    assert url.query["sslmode"] == "require"


def test_cors_origins_can_be_parsed_from_comma_separated_string() -> None:
    settings = Settings(
        cors_origins="https://app.example.com, https://cyverse.vercel.app ",
        _env_file=None,
    )
    assert settings.cors_origins == ["https://app.example.com", "https://cyverse.vercel.app"]


def test_cors_origins_can_be_parsed_from_json_string() -> None:
    settings = Settings(
        cors_origins='["https://app.example.com", "https://cyverse.vercel.app"]',
        _env_file=None,
    )
    assert settings.cors_origins == ["https://app.example.com", "https://cyverse.vercel.app"]


def test_cors_origin_regex_normalization() -> None:
    settings = Settings(
        cors_origin_regex="  ^https://.*\\.vercel\\.app$  ",
        _env_file=None,
    )
    assert settings.cors_origin_regex == "^https://.*\\.vercel\\.app$"
