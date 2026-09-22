from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.tools.research.repository import ResearchRepository
from app.tools.research.schemas import (
    CreateResearchSessionRequest,
    ResearchConfigResponse,
    ResearchSessionDetail,
    ResearchSessionListResponse,
    UpdateResearchSessionRequest,
)
from app.tools.research.service import ResearchService

router = APIRouter()


def get_research_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchService:
    return ResearchService(ResearchRepository(session))


@router.get("/research/config", response_model=ResearchConfigResponse)
async def get_research_config(
    _user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchConfigResponse:
    return service.get_config()


@router.post(
    "/research/sessions",
    response_model=ResearchSessionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_session(
    request: CreateResearchSessionRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$"),
    ] = None,
) -> ResearchSessionDetail:
    return await service.create_session(
        user=user, request=request, idempotency_key=idempotency_key
    )


@router.get("/research/sessions", response_model=ResearchSessionListResponse)
async def list_research_sessions(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 30,
) -> ResearchSessionListResponse:
    return await service.list_sessions(user=user, cursor=cursor, limit=limit)


@router.get("/research/sessions/{session_id}", response_model=ResearchSessionDetail)
async def get_research_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchSessionDetail:
    return await service.get_session(user=user, session_id=session_id)


@router.patch("/research/sessions/{session_id}", response_model=ResearchSessionDetail)
async def update_research_session(
    session_id: UUID,
    request: UpdateResearchSessionRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchSessionDetail:
    return await service.update_session(
        user=user, session_id=session_id, request=request
    )


@router.delete(
    "/research/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_research_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> Response:
    await service.delete_session(user=user, session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/research/sessions/{session_id}/cancel", response_model=ResearchSessionDetail)
async def cancel_research_session(
    session_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ResearchService, Depends(get_research_service)],
) -> ResearchSessionDetail:
    return await service.cancel_session(user=user, session_id=session_id)
