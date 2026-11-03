import asyncio
import json
import logging
from pathlib import Path
from uuid import UUID

import httpx

from app.core.config import settings
from app.models.user import User
from app.tools.threads.ai import GroqThreadsAI
from app.tools.threads.cloudinary import cloudinary_config
from app.tools.threads.config import ThreadsConfig, threads_config
from app.tools.threads.errors import ThreadsError
from app.tools.threads.repository import TERMINAL_STATUSES, ThreadsRepository, to_response
from app.tools.threads.schemas import (
    ThreadsConfigResponse,
    ThreadsParameters,
    ThreadsRequest,
    ThreadsRunResponse,
)
from app.tools.threads.session import (
    create_session_bundle,
    inspect_session_data,
    inspect_session_file,
    parse_session_bundle,
)

logger = logging.getLogger(__name__)


def _write_session_file(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    temp_path.replace(path)


class ThreadsService:
    def __init__(
        self, repository: ThreadsRepository, config: ThreadsConfig = threads_config
    ) -> None:
        self.repository = repository
        self.config = config

    async def analyze_keywords(self, query: str, count: int = 5) -> dict[str, object]:
        if not settings.groq_api_key or not settings.groq_api_key.get_secret_value().strip():
            words = [w.strip() for w in query.replace("\n", ",").split(",") if w.strip()]
            keywords = words[:count] if words else [query.strip()[:100]]
            return {
                "keywords": keywords,
                "groups": [{"category": "Từ khóa tìm kiếm", "keywords": keywords}],
            }
        async with httpx.AsyncClient(follow_redirects=False) as client:
            ai = GroqThreadsAI(self.config, client)
            grouped = await ai.analyze_grouped_keywords(query)
            return {
                "keywords": grouped.keywords,
                "groups": [g.model_dump(mode="json") for g in grouped.groups],
            }

    async def restore_sessions_from_db(self) -> None:
        """Restore any missing session files from persistent database storage or local threads_sessions.json bundle."""
        if hasattr(self.repository, "list_account_sessions"):
            records = await self.repository.list_account_sessions()
            for record in records:
                account = next(
                    (item for item in self.config.accounts if item.id == record.account_id),
                    None,
                )
                if account:
                    path = self.config.session_path(account)
                    if not path.is_file() or path.stat().st_mtime < record.updated_at.timestamp():
                        await asyncio.to_thread(_write_session_file, path, record.session_data)

        bundle_path = self.config.sessions_dir / "threads_sessions.json"
        if bundle_path.is_file():
            try:
                content = bundle_path.read_text(encoding="utf-8")
                bundle_data = json.loads(content)
                parsed = parse_session_bundle(bundle_data)
                for account in self.config.accounts:
                    if account.id in parsed:
                        path = self.config.session_path(account)
                        if not path.is_file():
                            await asyncio.to_thread(_write_session_file, path, parsed[account.id])
            except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
                logger.warning("Could not unpack local threads_sessions.json: %s", exc)

    def list_accounts(self) -> list[dict[str, object]]:
        """List configured accounts and indicate whether their session is ready and not expired."""
        results = []
        for account in self.config.accounts:
            path = self.config.session_path(account)
            has_session, is_expired, expires_at = inspect_session_file(path)
            results.append(
                {
                    "id": account.id,
                    "username": account.username.get_secret_value() if account.username else None,
                    "enabled": account.enabled,
                    "has_session": has_session,
                    "is_expired": is_expired,
                    "expires_at": expires_at,
                }
            )
        return results

    async def import_session(
        self, account_id: str, data: dict[str, object]
    ) -> dict[str, object]:
        """Validate and persist a Playwright storage_state session for a configured account."""
        account = next(
            (item for item in self.config.accounts if item.id == account_id),
            None,
        )
        if account is None:
            raise ThreadsError(
                "ACCOUNT_NOT_FOUND",
                f"Account '{account_id}' is not configured in THREADS_ACCOUNTS.",
                404,
            )

        has_session, is_expired, expires_at = inspect_session_data(data)
        if not has_session:
            raise ThreadsError(
                "INVALID_SESSION_COOKIES",
                "Session JSON does not contain an authenticated Threads/Instagram sessionid cookie.",
                400,
            )
        if is_expired:
            raise ThreadsError(
                "SESSION_EXPIRED",
                f"The provided session expired on {expires_at}. Please provide an active session.",
                400,
            )

        record = await self.repository.save_account_session(account_id, data)

        path = self.config.session_path(account)
        await asyncio.to_thread(_write_session_file, path, data)

        return {
            "account_id": account_id,
            "updated_at": record.updated_at.isoformat(),
            "status": "ready",
            "expires_at": expires_at,
        }

    async def import_bundled_sessions(
        self, data: object
    ) -> dict[str, object]:
        """Validate and persist multiple account sessions from a single JSON bundle."""
        bundle = parse_session_bundle(data)
        if not bundle:
            raise ThreadsError(
                "INVALID_SESSION_BUNDLE",
                "No valid account sessions found in the uploaded JSON bundle. Expecting a map of account IDs to session data or 'sessions' object.",
                400,
            )

        imported: list[dict[str, object]] = []
        errors: list[str] = []
        configured_ids = {account.id for account in self.config.accounts}

        for account_id, session_data in bundle.items():
            if account_id not in configured_ids:
                errors.append(f"Account '{account_id}' is not in THREADS_ACCOUNTS configuration (skipped).")
                continue

            has_session, is_expired, expires_at = inspect_session_data(session_data)
            if not has_session:
                errors.append(f"Account '{account_id}' does not have a valid sessionid cookie.")
                continue
            if is_expired:
                errors.append(f"Account '{account_id}' session expired on {expires_at}.")
                continue

            account = next(acc for acc in self.config.accounts if acc.id == account_id)
            record = await self.repository.save_account_session(account_id, session_data)
            path = self.config.session_path(account)
            await asyncio.to_thread(_write_session_file, path, session_data)

            imported.append(
                {
                    "account_id": account_id,
                    "updated_at": record.updated_at.isoformat(),
                    "status": "ready",
                    "expires_at": expires_at,
                }
            )

        if not imported and errors:
            raise ThreadsError("BUNDLE_IMPORT_FAILED", "; ".join(errors), 400)

        return {
            "imported": imported,
            "warnings": errors,
            "total_imported": len(imported),
        }

    async def export_bundled_sessions(self) -> dict[str, object]:
        """Export all available account sessions as a single threads_sessions.json bundle."""
        sessions_map: dict[str, dict[str, object]] = {}
        for account in self.config.accounts:
            path = self.config.session_path(account)
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    data = json.loads(content)
                    if isinstance(data, dict):
                        has_sess, _, _ = inspect_session_data(data)
                        if has_sess:
                            sessions_map[account.id] = data
                except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                    pass

        if hasattr(self.repository, "list_account_sessions"):
            records = await self.repository.list_account_sessions()
            for record in records:
                if record.account_id not in sessions_map and isinstance(record.session_data, dict):
                    sessions_map[record.account_id] = record.session_data

        return create_session_bundle(sessions_map)

    def get_config(self) -> ThreadsConfigResponse:
        accounts = [account for account in self.config.accounts if account.enabled]
        active_count = 0
        for account in accounts:
            has_session, is_expired, _ = inspect_session_file(self.config.session_path(account))
            if (has_session and not is_expired) or (account.username and account.password):
                active_count += 1
        ready = (active_count > 0) or self.config.anonymous
        return ThreadsConfigResponse(
            enabled=self.config.enabled,
            accounts_ready=ready and (bool(accounts) or self.config.anonymous),
            ai_available=bool(
                settings.groq_api_key and settings.groq_api_key.get_secret_value().strip()
            ),
            cloudinary_ready=cloudinary_config.ready,
            defaults=ThreadsParameters(),
            limits={
                "keywords": 20,
                "posts_per_keyword": 100,
                "comment_posts": 500,
                "comments_per_post": 500,
                "run_timeout_seconds": 86400,
                "search_timeout_seconds": 600,
            },
        )

    async def create(
        self, user: User, request: ThreadsRequest, key: str | None
    ) -> ThreadsRunResponse:
        if not self.config.enabled:
            raise ThreadsError("THREADS_DISABLED", "The Threads tool is disabled.", 503)
        requires_ai = (
            request.curate
            or (request.pre_filter and request.pre_filter_strictness != "none")
            or (request.expand_query and not request.keywords)
        )
        if requires_ai and (
            not settings.groq_api_key or not settings.groq_api_key.get_secret_value().strip()
        ):
            raise ThreadsError("GROQ_NOT_CONFIGURED", "Configure GROQ_API_KEY for Threads AI.", 503)
        accounts = [account for account in self.config.accounts if account.enabled]
        if not accounts and not self.config.anonymous:
            raise ThreadsError(
                "THREADS_NOT_CONFIGURED",
                "Configure Threads accounts or enable anonymous mode.",
                503,
            )
        active_accounts = [
            account
            for account in accounts
            if (inspect_session_file(self.config.session_path(account))[0]
            and not inspect_session_file(self.config.session_path(account))[1])
            or (account.username and account.password)
        ]
        if not active_accounts and not self.config.anonymous:
            raise ThreadsError(
                "THREADS_REAUTH_REQUIRED",
                "Create login sessions for enabled Threads accounts.",
                503,
            )
        if not request.keywords and not request.expand_query and len(request.query) > 100:
            raise ThreadsError(
                "KEYWORDS_REQUIRED", "Supply short keywords or enable query expansion."
            )
        run = await self.repository.create(user, request, key)
        logger.info("Created Threads run %s for user %s (query: %r)", run.id, user.username, request.query)
        return to_response(run, user=user)

    async def get(self, run_id: UUID, user: User) -> ThreadsRunResponse:
        return to_response(await self.repository.get(run_id, user), user=user)

    async def list(
        self, user: User, limit: int, offset: int, mode: str | None = None
    ) -> list[ThreadsRunResponse]:
        runs = await self.repository.list(user, limit, offset)
        items = [to_response(run, include_result=False, user=user) for run in runs]
        if mode:
            items = [item for item in items if getattr(item.request, "mode", "scraper") == mode]
        return items

    async def cancel(self, run_id: UUID, user: User) -> ThreadsRunResponse:
        logger.info("User %s requested cancellation of Threads run %s", user.username, run_id)
        return to_response(await self.repository.cancel(run_id, user), user=user)

    async def update(self, run_id: UUID, user: User, visibility: str) -> ThreadsRunResponse:
        return to_response(
            await self.repository.update_visibility(run_id, user, visibility), user=user
        )

    async def delete(self, run_id: UUID, user: User) -> ThreadsRunResponse:
        logger.info("User %s requested deletion of Threads run %s", user.username, run_id)
        return to_response(await self.repository.request_delete(run_id, user), user=user)

    async def export(self, run_id: UUID, user: User) -> ThreadsRunResponse:
        run = await self.get(run_id, user)
        if run.deletion_requested:
            raise ThreadsError("SESSION_DELETING", "This session is being deleted.", 409)
        if run.status == "cancelled":
            raise ThreadsError(
                "SESSION_CANCELLED", "This session was cancelled and its data was removed.", 409
            )
        if run.status not in TERMINAL_STATUSES or run.result is None:
            raise ThreadsError("RESULT_NOT_READY", "The Threads result is not ready.", 409)
        return run
