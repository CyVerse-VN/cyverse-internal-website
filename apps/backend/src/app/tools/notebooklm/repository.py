from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utc_now
from app.models.notebook_import import NotebookImport
from app.models.tool_run import ToolRun, ToolRunEvent
from app.models.user import ROLE_ADMIN, User
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.schemas import CreateImportRequest, ImportResponse, PaperSeed


class NotebookImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _detail():
        return select(NotebookImport).options(
            selectinload(NotebookImport.run).selectinload(ToolRun.events)
        )

    async def get(self, import_id: UUID, user: User) -> NotebookImport:
        statement = self._detail().join(NotebookImport.run).where(NotebookImport.id == import_id)
        if user.role != ROLE_ADMIN:
            statement = statement.where(ToolRun.owner_id == user.id)
        item = await self.session.scalar(statement)
        if item is None:
            raise NotebookImportError("IMPORT_NOT_FOUND", "Import not found.", 404)
        return item

    async def create(
        self, user: User, request: CreateImportRequest, idempotency_key: str | None,
        session_ciphertext: str,
    ) -> NotebookImport:
        if idempotency_key:
            existing = await self._existing(user, request, idempotency_key)
            if existing is not None:
                return existing
        run = ToolRun(
            owner_id=user.id,
            tool_name="notebooklm",
            status="queued",
            current_stage="queued",
            progress=0.0,
            idempotency_key=idempotency_key,
        )
        item = NotebookImport(
            run=run,
            notebook_id=request.notebook_id,
            account_email=request.account_email.lower(),
            session_ciphertext=session_ciphertext,
            paper=request.paper.model_dump(mode="json"),
        )
        self.session.add(item)
        self.session.add(
            ToolRunEvent(
                run=run,
                sequence=1,
                stage="queued",
                status="completed",
                message="Paper import queued.",
                progress=0.0,
                metadata_json={},
                created_at=utc_now(),
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            if idempotency_key:
                existing = await self._existing(user, request, idempotency_key)
                if existing is not None:
                    return existing
            raise
        return await self.get(item.id, user)

    async def _existing(
        self, user: User, request: CreateImportRequest, idempotency_key: str
    ) -> NotebookImport | None:
        run = await self.session.scalar(
            select(ToolRun).where(
                ToolRun.owner_id == user.id, ToolRun.idempotency_key == idempotency_key
            )
        )
        if run is None:
            return None
        if run.tool_name != "notebooklm":
            raise NotebookImportError(
                "IDEMPOTENCY_CONFLICT", "This idempotency key is already in use.", 409
            )
        item = await self.session.scalar(
            self._detail().where(NotebookImport.run_id == run.id)
        )
        if (
            item is None
            or item.notebook_id != request.notebook_id
            or item.account_email != request.account_email.lower()
            or item.paper != request.paper.model_dump(mode="json")
        ):
            raise NotebookImportError(
                "IDEMPOTENCY_CONFLICT", "This idempotency key has different input.", 409
            )
        return item

    async def claim_next(self, worker_id: str) -> NotebookImport | None:
        run = await self.session.scalar(
            select(ToolRun)
            .where(ToolRun.tool_name == "notebooklm", ToolRun.status == "queued")
            .order_by(ToolRun.created_at, ToolRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            return None
        run.status = "running"
        run.current_stage = "resolving"
        run.progress = 0.05
        run.worker_id = worker_id
        run.started_at = run.started_at or utc_now()
        run.heartbeat_at = utc_now()
        run.attempt_count += 1
        await self._event(run, "resolving", "running", "Resolving the paper PDF.")
        await self.session.commit()
        return await self.session.scalar(self._detail().where(NotebookImport.run_id == run.id))

    async def transition(
        self,
        item: NotebookImport,
        stage: str,
        progress: float,
        message: str,
        *,
        pdf_url: str | None = None,
        source_id: str | None = None,
    ) -> None:
        run = item.run
        run.current_stage = stage
        run.progress = progress
        run.heartbeat_at = utc_now()
        if pdf_url:
            item.resolved_pdf_url = pdf_url
        if source_id:
            item.source_id = source_id
        await self._event(run, stage, "running", message)
        await self.session.commit()

    async def complete(self, item: NotebookImport) -> None:
        run = item.run
        item.session_ciphertext = None
        run.status = "completed"
        run.current_stage = "completed"
        run.progress = 1.0
        run.completed_at = utc_now()
        await self._event(run, "completed", "completed", "Paper is ready in NotebookLM.")
        await self.session.commit()

    async def fail(self, run: ToolRun, error: NotebookImportError) -> None:
        item = await self.session.scalar(
            select(NotebookImport).where(NotebookImport.run_id == run.id)
        )
        if item is not None:
            item.session_ciphertext = None
        run.status = "failed"
        run.current_stage = "failed"
        run.error_code = error.code
        run.error_message = error.detail
        run.completed_at = utc_now()
        await self._event(run, "failed", "failed", error.detail)
        await self.session.commit()

    async def recover_stale(self, lease_seconds: int, max_attempts: int) -> None:
        cutoff = utc_now() - timedelta(seconds=lease_seconds)
        rows = list((await self.session.scalars(
            self._detail().join(NotebookImport.run).where(
                ToolRun.tool_name == "notebooklm",
                ToolRun.status == "running",
                ToolRun.heartbeat_at < cutoff,
            )
        )).all())
        for item in rows:
            run = item.run
            if run.current_stage in {"uploading", "processing"} and item.source_id is None:
                await self.fail(run, NotebookImportError(
                    "UPLOAD_OUTCOME_UNKNOWN", "Check the notebook before retrying this import."
                ))
            elif run.attempt_count >= max_attempts:
                await self.fail(run, NotebookImportError(
                    "WORKER_INTERRUPTED", "The import worker stopped before completion."
                ))
            else:
                run.status = "queued"
                run.current_stage = "queued"
                run.worker_id = None
                run.heartbeat_at = None
                await self._event(run, "queued", "completed", "Interrupted import returned to the queue.")
                await self.session.commit()

    async def _event(self, run: ToolRun, stage: str, status: str, message: str) -> None:
        with self.session.no_autoflush:
            await self.session.execute(select(ToolRun.id).where(ToolRun.id == run.id).with_for_update())
        sequence = await self.session.scalar(
            select(func.max(ToolRunEvent.sequence)).where(ToolRunEvent.run_id == run.id)
        )
        self.session.add(ToolRunEvent(
            run=run,
            sequence=int(sequence or 0) + 1,
            stage=stage,
            status=status,
            message=message,
            progress=run.progress,
            metadata_json={},
            created_at=utc_now(),
        ))


def to_response(item: NotebookImport) -> ImportResponse:
    run = item.run
    return ImportResponse(
        id=item.id,
        notebook_id=item.notebook_id,
        account_email=item.account_email,
        paper=PaperSeed.model_validate(item.paper),
        status=run.status,
        current_stage=run.current_stage,
        source_id=item.source_id,
        error={"code": run.error_code, "message": run.error_message}
        if run.error_code and run.error_message else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
