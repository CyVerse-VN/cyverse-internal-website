from __future__ import annotations

from uuid import UUID

from app.models.research import ResearchSession
from app.models.user import ROLE_ADMIN, User
from app.tools.research.config import research_config
from app.tools.research.repository import ResearchRepository
from app.tools.research.schemas import (
    CreateResearchSessionRequest,
    OwnerSummary,
    ProgressEventResponse,
    ResearchConfigResponse,
    ResearchPaperResponse,
    ResearchSessionDetail,
    ResearchSessionListResponse,
    ResearchSessionSummary,
    ResearchSettingsInput,
    UpdateResearchSessionRequest,
    default_year_range,
)


class ResearchService:
    """Coordinates durable research sessions and their access rules."""

    def __init__(self, repository: ResearchRepository) -> None:
        self.repository = repository

    def get_config(self) -> ResearchConfigResponse:
        year_from, year_to = default_year_range()
        defaults = ResearchSettingsInput(year_from=year_from, year_to=year_to).effective()
        return ResearchConfigResponse(
            defaults=defaults,
            limits={
                "query_min": research_config.query_min_length,
                "query_max": research_config.query_max_length,
                "year_min": 2020,
                "year_max": year_to + 1,
                "raw_per_source_max": research_config.max_raw_per_source,
                "total_raw_max": research_config.max_raw_per_source * 3,
                "result_max": research_config.max_result_limit,
            },
        )

    async def create_session(
        self,
        *,
        user: User,
        request: CreateResearchSessionRequest,
        idempotency_key: str | None,
    ) -> ResearchSessionDetail:
        effective = request.settings.effective()
        title = request.query if len(request.query) <= 117 else f"{request.query[:117].rstrip()}…"
        research_session = await self.repository.create_session(
            owner=user,
            query=request.query,
            title=title,
            visibility=request.visibility.value,
            effective_settings=effective.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return await self._detail(research_session, user)

    async def list_sessions(
        self, *, user: User, cursor: str | None, limit: int
    ) -> ResearchSessionListResponse:
        sessions, next_cursor = await self.repository.list_accessible_sessions(
            user, cursor=cursor, limit=limit
        )
        items = [await self._summary(item, user) for item in sessions]
        return ResearchSessionListResponse(items=items, next_cursor=next_cursor)

    async def get_session(self, *, user: User, session_id: UUID) -> ResearchSessionDetail:
        research_session = await self.repository.get_accessible_session(session_id, user)
        return await self._detail(research_session, user)

    async def update_session(
        self,
        *,
        user: User,
        session_id: UUID,
        request: UpdateResearchSessionRequest,
    ) -> ResearchSessionDetail:
        research_session = await self.repository.get_session_for_management(session_id, user)
        await self.repository.update_session(
            research_session,
            visibility=request.visibility.value if request.visibility else None,
            title=request.title,
        )
        return await self._detail(research_session, user)

    async def delete_session(self, *, user: User, session_id: UUID) -> None:
        research_session = await self.repository.get_session_for_management(session_id, user)
        await self.repository.delete_session(research_session)

    async def cancel_session(self, *, user: User, session_id: UUID) -> ResearchSessionDetail:
        research_session = await self.repository.get_session_for_management(session_id, user)
        await self.repository.request_cancellation(research_session)
        return await self._detail(research_session, user)

    async def _summary(
        self, research_session: ResearchSession, viewer: User
    ) -> ResearchSessionSummary:
        run = research_session.run
        is_owner = run.owner_id == viewer.id
        return ResearchSessionSummary(
            id=research_session.id,
            query=research_session.query,
            title=research_session.title,
            visibility=research_session.visibility,
            owner=OwnerSummary(id=run.owner.id, display_name=run.owner.display_name),
            is_owner=is_owner,
            can_manage=is_owner or viewer.role == ROLE_ADMIN,
            status=run.status,
            current_stage=run.current_stage,
            progress=run.progress,
            queue_position=await self.repository.queue_position(run),
            result_count=int(research_session.result_stats.get("result_count", 0)),
            created_at=research_session.created_at,
            updated_at=research_session.updated_at,
        )

    async def _detail(
        self, research_session: ResearchSession, viewer: User
    ) -> ResearchSessionDetail:
        summary = await self._summary(research_session, viewer)
        run = research_session.run
        error = None
        if run.error_code and run.error_message:
            error = {"code": run.error_code, "message": run.error_message}
        return ResearchSessionDetail(
            **summary.model_dump(),
            effective_settings=ResearchSettingsInput.model_validate(
                research_session.effective_settings
            ),
            pipeline_version=research_session.pipeline_version,
            warnings=research_session.warnings,
            result_stats=research_session.result_stats,
            error=error,
            events=[
                ProgressEventResponse(
                    sequence=event.sequence,
                    stage=event.stage,
                    status=event.status,
                    message=event.message,
                    progress=event.progress,
                    metadata=event.metadata_json,
                    created_at=event.created_at,
                )
                for event in run.events
            ],
            papers=[ResearchPaperResponse.model_validate(paper) for paper in research_session.papers],
        )
