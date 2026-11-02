from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.tools.threads.repository import ThreadsRepository
from app.tools.threads.schemas import (
    ThreadsConfigResponse,
    ThreadsRequest,
    ThreadsRunResponse,
    ThreadsUpdate,
)
from app.tools.threads.service import ThreadsService
from app.tools.threads.storage import render_text

router = APIRouter(prefix="/threads")


class KeywordAnalysisRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    count: int = Field(default=5, ge=1, le=10)


class KeywordGroupResponse(BaseModel):
    category: str
    keywords: list[str]


class KeywordAnalysisResponse(BaseModel):
    keywords: list[str]
    groups: list[KeywordGroupResponse] = Field(default_factory=list)


def get_threads_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ThreadsService:
    return ThreadsService(ThreadsRepository(session))


@router.post("/keywords", response_model=KeywordAnalysisResponse)
async def analyze_keywords(
    payload: KeywordAnalysisRequest,
    _user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> KeywordAnalysisResponse:
    result = await service.analyze_keywords(payload.query, payload.count)
    return KeywordAnalysisResponse.model_validate(result)


@router.get("/config", response_model=ThreadsConfigResponse)
async def get_threads_config(
    _user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> ThreadsConfigResponse:
    return service.get_config()


@router.post("/runs", response_model=ThreadsRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_threads_run(
    request: ThreadsRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
    ] = None,
) -> ThreadsRunResponse:
    return await service.create(user, request, idempotency_key)


@router.get("/runs", response_model=list[ThreadsRunResponse])
async def list_threads_runs(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
    mode: Annotated[str | None, Query(pattern=r"^(scraper|travel)$")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> list[ThreadsRunResponse]:
    return await service.list(user, limit, offset, mode=mode)


@router.get("/runs/{run_id}", response_model=ThreadsRunResponse)
async def get_threads_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> ThreadsRunResponse:
    return await service.get(run_id, user)


@router.post("/runs/{run_id}/cancel", response_model=ThreadsRunResponse)
async def cancel_threads_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> ThreadsRunResponse:
    return await service.cancel(run_id, user)


@router.patch("/runs/{run_id}", response_model=ThreadsRunResponse)
async def update_threads_run(
    run_id: UUID,
    request: ThreadsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> ThreadsRunResponse:
    return await service.update(run_id, user, request.visibility)


@router.delete(
    "/runs/{run_id}", response_model=ThreadsRunResponse, status_code=status.HTTP_202_ACCEPTED
)
async def delete_threads_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
) -> ThreadsRunResponse:
    return await service.delete(run_id, user)


@router.get("/runs/{run_id}/export")
async def export_threads_run(
    run_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ThreadsService, Depends(get_threads_service)],
    format: Literal["json", "txt"] = "json",
) -> Response:
    run = await service.export(run_id, user)
    assert run.result is not None
    if format == "json":
        content, media_type = run.result.model_dump_json(indent=2), "application/json"
    else:
        content, media_type = render_text(run), "text/plain; charset=utf-8"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="threads-{run_id}.{format}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
