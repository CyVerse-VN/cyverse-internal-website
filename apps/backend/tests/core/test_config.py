from pathlib import Path

from app.core.config import BACKEND_ENV_FILE, Settings


def test_backend_env_file_is_scoped_to_backend_directory() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    assert BACKEND_ENV_FILE == backend_root / ".env"
    assert Settings.model_config["env_file"] == BACKEND_ENV_FILE


def test_database_default_uses_installed_psycopg_driver() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("postgresql+psycopg://")
