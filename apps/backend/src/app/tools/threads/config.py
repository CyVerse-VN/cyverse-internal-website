from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BACKEND_ENV_FILE, BACKEND_ROOT


class ThreadsAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    username: SecretStr | None = None
    password: SecretStr | None = None
    totp_secret: SecretStr | None = None
    proxy: SecretStr | None = None
    enabled: bool = True


class ThreadsConfig(BaseSettings):
    enabled: bool = False
    embedded_worker: bool = True
    txt_archive_enabled: bool = False
    accounts: list[ThreadsAccount] = Field(default_factory=list, max_length=10, repr=False)
    anonymous: bool = False
    sessions_dir: Path = BACKEND_ROOT / ".local" / "threads" / "sessions"
    groq_model: str = "qwen/qwen3.8-27b"
    keywords_per_query: int = Field(default=3, ge=1, le=5)
    min_delay_seconds: float = Field(default=2, ge=0, le=60)
    max_delay_seconds: float = Field(default=4, ge=0, le=60)
    run_timeout_seconds: int = Field(default=1800, ge=30, le=7200)
    search_timeout_seconds: int = Field(default=120, ge=15, le=600)
    worker_poll_seconds: float = Field(default=2, ge=0.1, le=60)
    worker_restart_seconds: float = Field(default=5, ge=1, le=60)
    worker_advisory_lock_id: int = 73193604

    @model_validator(mode="after")
    def validate_configuration(self) -> "ThreadsConfig":
        ids = [account.id.lower() for account in self.accounts]
        if len(ids) != len(set(ids)):
            raise ValueError("Threads account IDs must be unique")
        if self.min_delay_seconds > self.max_delay_seconds:
            raise ValueError("Threads minimum delay must not exceed maximum delay")
        if not self.sessions_dir.is_absolute():
            self.sessions_dir = (BACKEND_ROOT / self.sessions_dir).resolve()
        return self

    def session_path(self, account: ThreadsAccount) -> Path:
        return self.sessions_dir / f"{account.id}.json"

    model_config = SettingsConfigDict(
        env_prefix="THREADS_",
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


threads_config = ThreadsConfig()
