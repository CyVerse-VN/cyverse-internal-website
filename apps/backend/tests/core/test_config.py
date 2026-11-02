from pathlib import Path

import certifi
import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.core.config import BACKEND_ENV_FILE, Settings


def test_backend_env_file_is_scoped_to_backend_directory() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    assert BACKEND_ENV_FILE == backend_root / ".env"
    assert Settings.model_config["env_file"] == BACKEND_ENV_FILE


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_production_requires_a_non_default_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_JWT_SECRET must be changed"):
        Settings(app_env="production", _env_file=None)


def test_jwt_secret_requires_at_least_32_characters() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(auth_jwt_secret="too-short", _env_file=None)


@pytest.mark.parametrize("scheme", ["postgresql", "postgresql+psycopg"])
def test_tidb_url_uses_psycopg_and_verified_tls(scheme: str) -> None:
    settings = Settings(
        database_url=(
            f"{scheme}://example.postgres:database-secret@"
            "example.gateway01.us-east-1.prod.aws.pg.tidbcloud.com:5432/cyverse_internal"
        ),
        _env_file=None,
    )
    url = make_url(settings.database_url)

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "example.postgres"
    assert url.password == "database-secret"
    assert url.host == "example.gateway01.us-east-1.prod.aws.pg.tidbcloud.com"
    assert url.port == 5432
    assert url.database == "cyverse_internal"
    assert url.query["sslmode"] == "verify-full"
    assert url.query["sslrootcert"] == certifi.where()


@pytest.mark.parametrize("password", ["example@password", "example%40password"])
def test_database_url_preserves_password_with_at_sign(password: str) -> None:
    settings = Settings(
        database_url=f"postgresql://user:{password}@localhost:5432/cyverse_internal_test",
        _env_file=None,
    )

    assert make_url(settings.database_url).password == "example@password"


def test_database_url_preserves_custom_tls_and_connection_options() -> None:
    settings = Settings(
        database_url=(
            "postgresql://example.postgres:secret@example.pg.tidbcloud.com:5432/"
            "cyverse_internal?sslmode=verify-full&sslrootcert=%2Fcerts%2Fca.pem&connect_timeout=10"
        ),
        _env_file=None,
    )

    assert dict(make_url(settings.database_url).query) == {
        "sslmode": "verify-full",
        "sslrootcert": "/certs/ca.pem",
        "connect_timeout": "10",
    }


@pytest.mark.parametrize("sslmode", ["disable", "allow", "prefer", "require&sslmode=disable"])
def test_tidb_url_rejects_connections_without_required_tls(sslmode: str) -> None:
    with pytest.raises(ValidationError, match="must require TLS"):
        Settings(
            database_url=(
                "postgresql://example.postgres:secret@example.pg.tidbcloud.com:5432/"
                f"cyverse_internal?sslmode={sslmode}"
            ),
            _env_file=None,
        )


@pytest.mark.parametrize(
    "url",
    [
        "invalid-url",
        "mysql://user:secret@localhost:3306/cyverse_internal_test",
        "postgresql+asyncpg://user:secret@localhost:5432/cyverse_internal_test",
        "postgresql://user:secret@localhost:invalid/cyverse_internal_test",
        "postgresql://user:secret@localhost:5432",
    ],
)
def test_invalid_database_url_is_rejected_without_disclosing_credentials(url: str) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(database_url=url, _env_file=None)

    assert "secret" not in str(error.value)


def test_database_credentials_are_excluded_from_settings_representation() -> None:
    settings = Settings(
        database_url="postgresql://user:database-secret@localhost:5432/cyverse_internal_test",
        _env_file=None,
    )

    assert "database-secret" not in repr(settings)


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
