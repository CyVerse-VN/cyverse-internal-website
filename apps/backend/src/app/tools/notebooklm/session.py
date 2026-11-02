from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.tools.notebooklm.errors import NotebookImportError


def _cipher() -> Fernet:
    secret = settings.auth_jwt_secret.get_secret_value().encode("utf-8")
    key = hashlib.sha256(b"cyverse-notebooklm-job-session-v1\x00" + secret).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_session(storage_json: str) -> str:
    return _cipher().encrypt(storage_json.encode("utf-8")).decode("ascii")


def decrypt_session(ciphertext: str | None) -> str:
    if not ciphertext:
        raise NotebookImportError("NOTEBOOKLM_SESSION_REQUIRED", "Reconnect NotebookLM and retry.")
    try:
        return _cipher().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise NotebookImportError("NOTEBOOKLM_SESSION_REQUIRED", "Reconnect NotebookLM and retry.") from exc
