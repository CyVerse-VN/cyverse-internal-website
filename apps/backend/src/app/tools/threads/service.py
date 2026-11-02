import logging
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

logger = logging.getLogger(__name__)


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

    def get_config(self) -> ThreadsConfigResponse:
        accounts = [account for account in self.config.accounts if account.enabled]
        ready = all(self.config.session_path(account).is_file() for account in accounts)
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
                "run_timeout_seconds": 10800,
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
        if any(not self.config.session_path(account).is_file() for account in accounts):
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
