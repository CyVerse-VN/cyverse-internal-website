from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utc_now
from app.models.research import ResearchPaper, ResearchSession
from app.models.tool_run import ToolRun, ToolRunEvent
from app.models.user import ROLE_ADMIN, User

TERMINAL_STATUSES = {"completed", "completed_with_warnings", "failed", "cancelled"}


def encode_cursor(created_at: datetime, session_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{session_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, UUID] | None:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        timestamp, identifier = raw.rsplit("|", 1)
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed, UUID(identifier)
    except (ValueError, UnicodeError):
        return None


class ResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        *,
        owner: User,
        query: str,
        title: str,
        visibility: str,
        effective_settings: dict[str, object],
        idempotency_key: str | None,
    ) -> ResearchSession:
        if idempotency_key:
            existing_run = await self.session.scalar(
                select(ToolRun).where(
                    ToolRun.owner_id == owner.id,
                    ToolRun.idempotency_key == idempotency_key,
                    ToolRun.deleted_at.is_(None),
                )
            )
            if existing_run is not None:
                existing = await self.session.scalar(
                    self._detail_statement().where(ResearchSession.run_id == existing_run.id)
                )
                if existing is not None:
                    return existing

        run = ToolRun(
            owner_id=owner.id,
            owner=owner,
            tool_name="research",
            status="queued",
            current_stage="queued",
            progress=0.0,
            idempotency_key=idempotency_key,
        )
        session = ResearchSession(
            run=run,
            query=query,
            title=title,
            visibility=visibility,
            effective_settings=effective_settings,
        )
        self.session.add(
            ToolRunEvent(
                run=run,
                sequence=1,
                stage="queued",
                status="completed",
                message="Research session added to the queue.",
                progress=0.0,
                metadata_json={},
                created_at=utc_now(),
            )
        )
        self.session.add(session)
        try:
            await self.session.commit()
        except IntegrityError:
            if not idempotency_key:
                raise
            await self.session.rollback()
            existing = await self.session.scalar(
                self._detail_statement().where(
                    ToolRun.owner_id == owner.id,
                    ToolRun.idempotency_key == idempotency_key,
                )
            )
            if existing is None:
                raise
            return existing
        return await self.get_accessible_session(session.id, owner)

    async def list_accessible_sessions(
        self, user: User, *, cursor: str | None, limit: int
    ) -> tuple[list[ResearchSession], str | None]:
        statement = self._summary_statement().where(self._access_clause(user))
        if cursor and (decoded := decode_cursor(cursor)):
            created_at, identifier = decoded
            statement = statement.where(
                or_(
                    ResearchSession.created_at < created_at,
                    and_(
                        ResearchSession.created_at == created_at,
                        ResearchSession.id < identifier,
                    ),
                )
            )
        statement = statement.order_by(
            ResearchSession.created_at.desc(), ResearchSession.id.desc()
        ).limit(limit + 1)
        rows = list((await self.session.scalars(statement)).unique().all())
        next_cursor = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return rows, next_cursor

    async def get_accessible_session(self, session_id: UUID, user: User) -> ResearchSession:
        result = await self.session.scalar(
            self._detail_statement().where(
                ResearchSession.id == session_id,
                self._access_clause(user),
            )
        )
        if result is None:
            from app.tools.research.errors import ResearchSessionNotFoundError

            raise ResearchSessionNotFoundError
        return result

    async def get_session_for_management(self, session_id: UUID, user: User) -> ResearchSession:
        statement = self._detail_statement().where(
            ResearchSession.id == session_id,
            ResearchSession.deleted_at.is_(None),
            ToolRun.deleted_at.is_(None),
        )
        if user.role != ROLE_ADMIN:
            statement = statement.where(ToolRun.owner_id == user.id)
        result = await self.session.scalar(statement)
        if result is None:
            from app.tools.research.errors import ResearchSessionNotFoundError

            raise ResearchSessionNotFoundError
        return result

    async def update_session(
        self,
        session: ResearchSession,
        *,
        visibility: str | None,
        title: str | None,
    ) -> ResearchSession:
        if visibility is not None:
            session.visibility = visibility
        if title is not None:
            session.title = title
        await self.session.commit()
        return session

    async def delete_session(self, session: ResearchSession) -> None:
        if session.run.status not in TERMINAL_STATUSES:
            await self.request_cancellation(session)
        run = session.run
        await self.session.delete(session)
        if run is not None:
            await self.session.delete(run)
        await self.session.commit()

    async def request_cancellation(self, session: ResearchSession) -> ResearchSession:
        run = await self.session.scalar(
            select(ToolRun).where(ToolRun.id == session.run_id).with_for_update()
        )
        if run is None:
            return session
        if run.status in TERMINAL_STATUSES:
            session.run = run
            return session
        run.cancel_requested = True
        if run.status == "queued":
            run.status = "cancelled"
            run.current_stage = "cancelled"
            run.completed_at = utc_now()
            run.progress = 0.0
            await self._append_event(
                run, "cancelled", "completed", "Research session cancelled."
            )
        else:
            await self._append_event(
                run,
                run.current_stage,
                "running",
                "Cancellation requested; the current external request will finish first.",
            )
        await self.session.commit()
        session.run = run
        return session

    async def queue_position(self, run: ToolRun) -> int | None:
        if run.status != "queued":
            return None
        preceding = await self.session.scalar(
            select(func.count())
            .select_from(ToolRun)
            .where(
                ToolRun.tool_name == "research",
                ToolRun.status == "queued",
                ToolRun.deleted_at.is_(None),
                or_(
                    ToolRun.created_at < run.created_at,
                    and_(ToolRun.created_at == run.created_at, ToolRun.id < run.id),
                ),
            )
        )
        active = await self.session.scalar(
            select(func.count())
            .select_from(ToolRun)
            .where(ToolRun.tool_name == "research", ToolRun.status == "running")
        )
        return int(preceding or 0) + int(active or 0) + 1

    async def claim_next(self, worker_id: str) -> ResearchSession | None:
        run = await self.session.scalar(
            select(ToolRun)
            .where(
                ToolRun.tool_name == "research",
                ToolRun.status == "queued",
                ToolRun.cancel_requested.is_(False),
                ToolRun.deleted_at.is_(None),
            )
            .order_by(ToolRun.created_at, ToolRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            return None
        now = utc_now()
        run.status = "running"
        run.current_stage = "planning"
        run.progress = 0.05
        run.worker_id = worker_id
        run.heartbeat_at = now
        run.started_at = run.started_at or now
        run.attempt_count += 1
        await self._append_event(run, "planning", "running", "Planning the academic search.")
        await self.session.commit()
        return await self.session.scalar(
            self._detail_statement().where(ResearchSession.run_id == run.id)
        )

    async def transition(
        self,
        run_id: UUID,
        *,
        stage: str,
        progress: float,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        run = await self.session.get(ToolRun, run_id)
        if run is None:
            return
        run.current_stage = stage
        run.progress = progress
        run.heartbeat_at = utc_now()
        if metadata:
            run.details = {**run.details, **metadata}
        await self._append_event(run, stage, "running", message, metadata)
        await self.session.commit()

    async def is_cancel_requested(self, run_id: UUID) -> bool:
        return bool(
            await self.session.scalar(select(ToolRun.cancel_requested).where(ToolRun.id == run_id))
        )

    async def complete(
        self,
        research_session: ResearchSession,
        papers: list[ResearchPaper],
        *,
        warnings: list[object],
        result_stats: dict[str, object],
    ) -> None:
        run = research_session.run
        await self.session.refresh(run, attribute_names=["cancel_requested"])
        if run.cancel_requested:
            await self.mark_cancelled(run)
            return
        for paper in papers:
            research_session.papers.append(paper)
        research_session.warnings = warnings
        research_session.result_stats = result_stats
        run.status = "completed_with_warnings" if warnings else "completed"
        run.current_stage = "completed"
        run.progress = 1.0
        run.completed_at = utc_now()
        run.heartbeat_at = run.completed_at
        await self._append_event(
            run, "completed", "completed", "Research results are ready."
        )
        await self.session.commit()

    async def mark_cancelled(self, run: ToolRun) -> None:
        run.status = "cancelled"
        run.current_stage = "cancelled"
        run.completed_at = utc_now()
        await self._append_event(
            run, "cancelled", "completed", "Research session cancelled."
        )
        await self.session.commit()

    async def fail(self, run_id: UUID, *, code: str, message: str) -> None:
        run = await self.session.get(ToolRun, run_id)
        if run is None:
            return
        run.status = "failed"
        run.current_stage = "failed"
        run.error_code = code
        run.error_message = message
        run.completed_at = utc_now()
        await self._append_event(run, "failed", "failed", message)
        await self.session.commit()

    async def recover_stale_runs(self, lease_seconds: int, max_attempts: int) -> int:
        cutoff = utc_now() - timedelta(seconds=lease_seconds)
        runs = list(
            (
                await self.session.scalars(
                    select(ToolRun).where(
                        ToolRun.tool_name == "research",
                        ToolRun.status == "running",
                        ToolRun.heartbeat_at < cutoff,
                    )
                )
            ).all()
        )
        for run in runs:
            if run.cancel_requested:
                await self.mark_cancelled(run)
            elif run.attempt_count < max_attempts:
                run.status = "queued"
                run.current_stage = "queued"
                run.worker_id = None
                await self._append_event(
                    run, "queued", "completed", "Interrupted work was returned to the queue."
                )
            else:
                run.status = "failed"
                run.current_stage = "failed"
                run.error_code = "worker_interrupted"
                run.error_message = "The research worker stopped before completing this session."
                run.completed_at = utc_now()
                await self._append_event(run, "failed", "failed", run.error_message)
        if runs:
            await self.session.commit()
        return len(runs)

    async def release_worker_claim(self, run_id: UUID, worker_id: str) -> None:
        """Return an interrupted embedded run to the queue during graceful shutdown."""

        run = await self.session.scalar(
            select(ToolRun).where(ToolRun.id == run_id).with_for_update()
        )
        if run is None or run.status != "running" or run.worker_id != worker_id:
            return
        if run.cancel_requested:
            run.status = "cancelled"
            run.current_stage = "cancelled"
            run.completed_at = utc_now()
            await self._append_event(
                run, "cancelled", "completed", "Research session cancelled."
            )
        else:
            run.status = "queued"
            run.current_stage = "queued"
            run.progress = 0.0
            run.worker_id = None
            run.heartbeat_at = None
            run.attempt_count = max(run.attempt_count - 1, 0)
            await self._append_event(
                run,
                "queued",
                "completed",
                "Backend shutdown returned the research session to the queue.",
            )
        await self.session.commit()

    @staticmethod
    def _access_clause(user: User):
        if user.role == ROLE_ADMIN:
            return ResearchSession.deleted_at.is_(None)
        return and_(
            ResearchSession.deleted_at.is_(None),
            or_(ResearchSession.visibility == "public", ToolRun.owner_id == user.id),
        )

    @staticmethod
    def _summary_statement():
        return (
            select(ResearchSession)
            .join(ResearchSession.run)
            .options(selectinload(ResearchSession.run).selectinload(ToolRun.owner))
        )

    @classmethod
    def _detail_statement(cls):
        return cls._summary_statement().options(
            selectinload(ResearchSession.run).selectinload(ToolRun.events),
            selectinload(ResearchSession.papers),
        )

    async def _append_event(
        self,
        run: ToolRun,
        stage: str,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        # The API may request cancellation while the worker records progress. Lock the
        # run row before allocating the next sequence so both writers remain ordered.
        with self.session.no_autoflush:
            await self.session.execute(
                select(ToolRun.id).where(ToolRun.id == run.id).with_for_update()
            )
        current_sequence = await self.session.scalar(
            select(func.max(ToolRunEvent.sequence)).where(ToolRunEvent.run_id == run.id)
        )
        self.session.add(
            ToolRunEvent(
                run=run,
                sequence=int(current_sequence or 0) + 1,
                stage=stage,
                status=status,
                message=message,
                progress=run.progress,
                metadata_json=metadata or {},
                created_at=utc_now(),
            )
        )


__all__ = ["TERMINAL_STATUSES", "ResearchRepository", "decode_cursor", "encode_cursor"]
