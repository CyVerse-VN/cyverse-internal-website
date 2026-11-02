from __future__ import annotations

from uuid import UUID

from app.models.user import User
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.provider import NotebookProvider, storage_json
from app.tools.notebooklm.repository import NotebookImportRepository, to_response
from app.tools.notebooklm.schemas import (
    BrowserCookie,
    CreateImportRequest,
    ImportResponse,
    NotebookAccount,
    NotebookListResponse,
)
from app.tools.notebooklm.session import encrypt_session


class NotebookImportService:
    def __init__(self, repository: NotebookImportRepository, provider: NotebookProvider) -> None:
        self.repository = repository
        self.provider = provider

    async def discover(self, cookies: list[BrowserCookie]) -> list[NotebookAccount]:
        return await self.provider.discover(cookies)

    async def _verified_storage(self, cookies: list[BrowserCookie], email: str) -> str:
        accounts = await self.discover(cookies)
        account = next((item for item in accounts if item.email == email.lower()), None)
        if account is None:
            raise NotebookImportError(
                "NOTEBOOKLM_ACCOUNT_MISMATCH",
                "The selected email is not signed in to NotebookLM in this browser.",
                403,
            )
        return storage_json(cookies, account)

    async def list_notebooks(self, cookies: list[BrowserCookie], email: str) -> NotebookListResponse:
        storage = await self._verified_storage(cookies, email)
        return NotebookListResponse(
            account_email=email.lower(), items=await self.provider.list_notebooks(storage)
        )

    async def create(
        self, user: User, request: CreateImportRequest, idempotency_key: str | None
    ) -> ImportResponse:
        storage = await self._verified_storage(request.cookies, request.account_email)
        notebooks = await self.provider.list_notebooks(storage)
        if request.notebook_id not in {item.id for item in notebooks}:
            raise NotebookImportError("NOTEBOOK_NOT_FOUND", "Notebook not found.", 404)
        return to_response(await self.repository.create(
            user, request, idempotency_key, encrypt_session(storage)
        ))

    async def get(self, user: User, import_id: UUID) -> ImportResponse:
        return to_response(await self.repository.get(import_id, user))

