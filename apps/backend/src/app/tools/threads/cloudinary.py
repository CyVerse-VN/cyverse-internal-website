"""Server-only cleanup for previously stored authenticated archives."""

import hashlib
import logging
import time
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BACKEND_ENV_FILE
from app.tools.threads.errors import ThreadsError

logger = logging.getLogger(__name__)


class CloudinaryConfig(BaseSettings):
    cloud_name: str = Field(default="", pattern=r"^[A-Za-z0-9_-]*$")
    api_key: SecretStr = SecretStr("")
    api_secret: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(
        env_prefix="CLOUDINARY_",
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    @property
    def ready(self) -> bool:
        return bool(
            self.cloud_name
            and self.api_key.get_secret_value().strip()
            and self.api_secret.get_secret_value().strip()
        )


class DestroyResponse(BaseModel):
    result: Literal["ok", "not found"]


class TextStore(Protocol):
    @property
    def available(self) -> bool: ...
    async def delete(self, public_id: str) -> None: ...


class CloudinaryTextStore:
    def __init__(self, config: CloudinaryConfig, client: httpx.AsyncClient) -> None:
        self.config = config
        self.client = client

    @property
    def available(self) -> bool:
        return self.config.ready

    def _parameters(self, public_id: str) -> dict[str, str]:
        if not self.config.ready:
            raise ThreadsError("CLOUDINARY_NOT_CONFIGURED", "Configure Cloudinary storage.", 503)
        parameters = {
            "public_id": public_id,
            "type": "authenticated",
            "invalidate": "true",
            "timestamp": str(int(time.time())),
        }
        signing_input = "&".join(f"{key}={value}" for key, value in sorted(parameters.items()))
        parameters["signature"] = hashlib.sha256(
            (signing_input + self.config.api_secret.get_secret_value()).encode()
        ).hexdigest()
        parameters["api_key"] = self.config.api_key.get_secret_value()
        return parameters

    async def delete(self, public_id: str) -> None:
        parameters = self._parameters(public_id)
        try:
            response = await self.client.post(
                f"https://api.cloudinary.com/v1_1/{self.config.cloud_name}/raw/destroy",
                data=parameters,
                timeout=60,
            )
            response.raise_for_status()
            DestroyResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            logger.error(
                "Cloudinary delete failed for %s: %s (%s)",
                public_id,
                type(exc).__name__,
                exc,
            )
            raise ThreadsError(
                "CLOUDINARY_DELETE_FAILED", "Cloudinary cleanup failed and will be retried.", 502
            ) from exc


cloudinary_config = CloudinaryConfig()
