from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.tools.notebooklm.provider import NotebookLMPyProvider
from app.tools.notebooklm.repository import NotebookImportRepository
from app.tools.notebooklm.schemas import (
    BrowserSessionRequest,
    CreateImportRequest,
    ImportResponse,
    NotebookAccountsResponse,
    NotebookListResponse,
    SelectedSessionRequest,
)
from app.tools.notebooklm.service import NotebookImportService

router = APIRouter()


def get_notebook_import_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotebookImportService:
    return NotebookImportService(NotebookImportRepository(session), NotebookLMPyProvider())


@router.post("/notebooklm/accounts/discover", response_model=NotebookAccountsResponse)
async def discover_notebooklm_accounts(
    request: BrowserSessionRequest,
    _user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotebookImportService, Depends(get_notebook_import_service)],
) -> NotebookAccountsResponse:
    return NotebookAccountsResponse(items=await service.discover(request.cookies))


@router.post("/notebooklm/notebooks", response_model=NotebookListResponse)
async def list_notebooks(
    request: SelectedSessionRequest,
    _user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotebookImportService, Depends(get_notebook_import_service)],
) -> NotebookListResponse:
    return await service.list_notebooks(request.cookies, request.account_email)


@router.post(
    "/notebooklm/imports", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_import(
    request: CreateImportRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotebookImportService, Depends(get_notebook_import_service)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
    ] = None,
) -> ImportResponse:
    return await service.create(user, request, idempotency_key)


@router.get("/notebooklm/imports/{import_id}", response_model=ImportResponse)
async def get_import(
    import_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotebookImportService, Depends(get_notebook_import_service)],
) -> ImportResponse:
    return await service.get(user, import_id)
