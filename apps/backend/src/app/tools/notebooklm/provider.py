from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

import httpx
from notebooklm import AuthError, AuthExtractionError, NotebookLMClient, NotebookLMError
from notebooklm.auth import build_cookie_jar, enumerate_accounts, extract_cookies_with_domains

from app.tools.notebooklm.config import notebook_import_config
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.schemas import BrowserCookie, NotebookAccount, NotebookItem


class NotebookProvider(Protocol):
    async def discover(self, cookies: list[BrowserCookie]) -> list[NotebookAccount]: ...

    async def list_notebooks(self, storage_json: str) -> list[NotebookItem]: ...

    async def add_file(self, storage_json: str, notebook_id: str, path: Path) -> str: ...

    async def wait_ready(self, storage_json: str, notebook_id: str, source_id: str) -> None: ...


def storage_json(cookies: list[BrowserCookie], account: NotebookAccount) -> str:
    return json.dumps({
        "cookies": [cookie.model_dump() for cookie in cookies],
        "origins": [],
        "notebooklm": {"version": 1, "account": account.model_dump()},
    }, separators=(",", ":"))


@contextmanager
def temporary_storage(content: str) -> Iterator[Path]:
    descriptor, filename = tempfile.mkstemp(prefix="cyverse-nlm-", suffix=".json")
    path = Path(filename)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
        yield path
    finally:
        path.unlink(missing_ok=True)


class NotebookLMPyProvider:
    """Use a verified browser session for one operation, without global SDK state."""

    async def discover(self, cookies: list[BrowserCookie]) -> list[NotebookAccount]:
        try:
            state = {"cookies": [cookie.model_dump() for cookie in cookies]}
            jar = build_cookie_jar(extract_cookies_with_domains(state))
            accounts = await enumerate_accounts(jar)
            return [NotebookAccount(email=item.email.lower(), authuser=item.authuser) for item in accounts]
        except (AuthError, AuthExtractionError, ValueError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_AUTH_EXPIRED", "Sign in to NotebookLM in this browser and reconnect.", 401
            ) from exc
        except (NotebookLMError, httpx.HTTPError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_UNAVAILABLE", "NotebookLM is temporarily unavailable.", 503
            ) from exc

    async def list_notebooks(self, content: str) -> list[NotebookItem]:
        try:
            with temporary_storage(content) as path:
                async with NotebookLMClient.from_storage(path=str(path)) as client:
                    rows = await client.notebooks.list()
                    return [NotebookItem(id=row.id, title=row.title) for row in rows]
        except (AuthError, AuthExtractionError, ValueError, FileNotFoundError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_AUTH_EXPIRED", "The NotebookLM session must be renewed.", 401
            ) from exc
        except NotebookLMError as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_UNAVAILABLE", "NotebookLM is temporarily unavailable.", 503
            ) from exc

    async def add_file(self, content: str, notebook_id: str, path: Path) -> str:
        try:
            with temporary_storage(content) as storage_path:
                async with NotebookLMClient.from_storage(path=str(storage_path)) as client:
                    source = await client.sources.add_file(notebook_id, path)
                    return source.id
        except (AuthError, AuthExtractionError, ValueError, FileNotFoundError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_AUTH_EXPIRED", "The NotebookLM session must be renewed.", 401
            ) from exc
        except NotebookLMError as exc:
            raise NotebookImportError(
                "UPLOAD_OUTCOME_UNKNOWN", "Check the notebook before retrying this import.", 503
            ) from exc

    async def wait_ready(self, content: str, notebook_id: str, source_id: str) -> None:
        from notebooklm import SourceTimeoutError

        try:
            with temporary_storage(content) as path:
                async with NotebookLMClient.from_storage(path=str(path)) as client:
                    await client.sources.wait_until_ready(
                        notebook_id, source_id,
                        timeout=notebook_import_config.processing_timeout_seconds,
                    )
        except (AuthError, AuthExtractionError, ValueError, FileNotFoundError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_AUTH_EXPIRED", "The NotebookLM session must be renewed.", 401
            ) from exc
        except (SourceTimeoutError, TimeoutError) as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_PROCESSING_TIMEOUT", "NotebookLM did not finish processing in time."
            ) from exc
        except NotebookLMError as exc:
            raise NotebookImportError(
                "NOTEBOOKLM_PROCESSING_FAILED", "NotebookLM could not process the PDF."
            ) from exc
