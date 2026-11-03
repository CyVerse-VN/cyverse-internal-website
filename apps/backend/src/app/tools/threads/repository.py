from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utc_now
from app.models.threads import (
    ThreadsAccountSessionRecord,
    ThreadsCommentRecord,
    ThreadsPostRecord,
    ThreadsResultRecord,
)
from app.models.tool_run import ToolRun
from app.models.user import ROLE_ADMIN, User
from app.tools.threads.content import clean_stored_comment
from app.tools.threads.errors import ThreadsCancelled, ThreadsError
from app.tools.threads.schemas import ThreadsRequest, ThreadsResult, ThreadsRunResponse

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class ThreadsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _query(
        self,
        user: User | None = None,
        *,
        include_posts: bool = True,
        manage: bool = False,
    ) -> Select[tuple[ToolRun]]:
        statement = (
            select(ToolRun)
            .outerjoin(ThreadsResultRecord, ThreadsResultRecord.run_id == ToolRun.id)
            .where(ToolRun.tool_name == "threads")
            .options(selectinload(ToolRun.owner))
        )
        snapshots = selectinload(ToolRun.threads_result)
        if include_posts:
            snapshots = snapshots.selectinload(ThreadsResultRecord.posts).selectinload(
                ThreadsPostRecord.comments
            )
        statement = statement.options(snapshots)
        if user is not None and user.role != ROLE_ADMIN:
            condition = ToolRun.owner_id == user.id
            if not manage:
                condition = or_(
                    condition,
                    (
                        (ThreadsResultRecord.visibility == "public")
                        & ThreadsResultRecord.deletion_requested.is_(False)
                    ),
                )
            statement = statement.where(condition)
        return statement

    async def get(self, run_id: UUID, user: User | None, *, manage: bool = False) -> ToolRun:
        run = await self.session.scalar(
            self._query(user, manage=manage)
            .where(ToolRun.id == run_id)
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise ThreadsError("RUN_NOT_FOUND", "Threads run not found.", 404)
        return run

    async def _locked(self, run_id: UUID) -> ToolRun:
        run = await self.session.scalar(
            self._query()
            .where(ToolRun.id == run_id)
            .with_for_update(of=ToolRun)
            .execution_options(populate_existing=True)
        )
        if run is None:
            raise ThreadsError("RUN_NOT_FOUND", "Threads run not found.", 404)
        return run

    async def list(self, user: User, limit: int, offset: int) -> list[ToolRun]:
        return list(
            (
                await self.session.scalars(
                    self._query(user, include_posts=False)
                    .order_by(ToolRun.created_at.desc(), ToolRun.id.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def get_existing_post_ids(self, user_id: UUID | None = None) -> set[str]:
        statement = (
            select(ThreadsPostRecord.post_id)
            .join(ToolRun, ToolRun.id == ThreadsPostRecord.run_id)
            .where(ToolRun.status != "cancelled")
        )
        if user_id is not None:
            statement = statement.where(ToolRun.owner_id == user_id)
        result = await self.session.scalars(statement)
        return set(result.all())

    async def existing(self, user: User, key: str, request: ThreadsRequest) -> ToolRun | None:
        run = await self.session.scalar(
            select(ToolRun).where(
                ToolRun.owner_id == user.id,
                ToolRun.idempotency_key == key,
            )
        )
        if run is not None and (
            run.tool_name != "threads"
            or ThreadsRequest.model_validate(run.details.get("request")).model_dump(mode="json")
            != request.model_dump(mode="json")
        ):
            raise ThreadsError(
                "IDEMPOTENCY_CONFLICT", "This idempotency key has different input.", 409
            )
        return run

    async def create(self, user: User, request: ThreadsRequest, key: str | None) -> ToolRun:
        if key and (existing := await self.existing(user, key, request)) is not None:
            return await self.get(existing.id, user)
        initial = ThreadsResult(query=request.query, keywords=[], posts=[], duration_seconds=0)
        run = ToolRun(
            owner_id=user.id,
            tool_name="threads",
            status="queued",
            current_stage="queued",
            progress=0,
            details={"request": request.model_dump(mode="json")},
            idempotency_key=key,
            threads_result=ThreadsResultRecord(
                visibility=request.visibility,
                summary=initial.model_dump(mode="json", exclude={"posts"}),
                posts=[],
            ),
        )
        self.session.add(run)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            if key and (existing := await self.existing(user, key, request)) is not None:
                return await self.get(existing.id, user)
            raise
        return await self.get(run.id, user)

    def _ensure_snapshot(self, run: ToolRun) -> ThreadsResultRecord:
        if run.threads_result is None:
            initial = ThreadsResult.model_validate(
                run.details.get("result")
                or {
                    "query": run.details["request"]["query"],
                    "keywords": [],
                    "posts": [],
                    "duration_seconds": 0,
                }
            )
            snapshot = ThreadsResultRecord(visibility="private", posts=[])
            run.threads_result = snapshot
            self._write_snapshot(snapshot, initial)
            # Legacy payloads are migrated when a session is first managed.
            run.details = {key: value for key, value in run.details.items() if key != "result"}
        return run.threads_result

    def _write_snapshot(self, snapshot: ThreadsResultRecord, result: ThreadsResult) -> None:
        snapshot.summary = result.model_dump(mode="json", exclude={"posts"})
        snapshot.snapshot_ready = True
        snapshot.post_count = len(result.posts)
        snapshot.comment_count = result.total_comments
        current_post_ids = {post.post_id for post in result.posts}
        snapshot.posts = [post for post in snapshot.posts if post.post_id in current_post_ids]
        records = {post.post_id: post for post in snapshot.posts}
        for position, post in enumerate(result.posts):
            record = records.get(post.post_id)
            if record is None:
                record = ThreadsPostRecord(post_id=post.post_id, position=position, comments=[])
                snapshot.posts.append(record)
            else:
                record.position = position
            record.data = post.model_dump(mode="json", exclude={"comments"})
            comments = {comment.comment_id: comment for comment in record.comments}
            current_comment_ids = {comment.id for comment in post.comments}
            record.comments = [c for c in record.comments if c.comment_id in current_comment_ids]
            for index, comment in enumerate(post.comments):
                stored = comments.get(comment.id)
                if stored is None:
                    stored = ThreadsCommentRecord(comment_id=comment.id, position=index)
                    record.comments.append(stored)
                else:
                    stored.position = index
                stored.parent_comment_id = comment.parent_id
                stored.data = comment.model_dump(mode="json")

    async def save_snapshot(self, run_id: UUID, result: ThreadsResult) -> None:
        run = await self._locked(run_id)
        if run.cancel_requested or run.status != "running":
            raise ThreadsCancelled()
        self._write_snapshot(self._ensure_snapshot(run), result)
        run.heartbeat_at = utc_now()
        await self.session.commit()

    async def update_visibility(self, run_id: UUID, user: User, visibility: str) -> ToolRun:
        await self.get(run_id, user, manage=True)
        run = await self._locked(run_id)
        snapshot = self._ensure_snapshot(run)
        if snapshot.deletion_requested:
            raise ThreadsError("SESSION_DELETING", "This session is being deleted.", 409)
        snapshot.visibility = visibility
        snapshot.archive_status = "pending"
        snapshot.next_storage_attempt_at = None
        await self.session.commit()
        return await self.get(run_id, user)

    def _clear_run_data(self, run: ToolRun, snapshot: ThreadsResultRecord) -> None:
        snapshot.posts.clear()
        snapshot.post_count = 0
        snapshot.comment_count = 0
        snapshot.snapshot_ready = False
        snapshot.archive_status = "pending"
        snapshot.summary = {
            "query": run.details.get("request", {}).get("query", ""),
            "keywords": [],
            "posts": [],
            "duration_seconds": 0,
        }
        run.details = {key: value for key, value in run.details.items() if key != "result"}

    async def request_delete(self, run_id: UUID, user: User) -> ToolRun:
        await self.get(run_id, user, manage=True)
        run = await self._locked(run_id)
        snapshot = self._ensure_snapshot(run)
        snapshot.deletion_requested = True
        snapshot.next_storage_attempt_at = None
        run.cancel_requested = True
        self._clear_run_data(run, snapshot)
        if run.status == "queued":
            run.status = run.current_stage = "cancelled"
            run.completed_at = utc_now()
        await self.session.commit()
        return await self.get(run_id, user)

    async def cancel(self, run_id: UUID, user: User) -> ToolRun:
        await self.get(run_id, user, manage=True)
        run = await self._locked(run_id)
        if run.status not in TERMINAL_STATUSES:
            run.cancel_requested = True
            snapshot = self._ensure_snapshot(run)
            self._clear_run_data(run, snapshot)
            if run.status == "queued":
                run.status = run.current_stage = "cancelled"
                run.completed_at = utc_now()
            await self.session.commit()
        return await self.get(run_id, user)

    async def recover_interrupted(self) -> None:
        runs = (
            await self.session.scalars(
                self._query()
                .where(
                    ToolRun.status == "running",
                )
                .with_for_update(of=ToolRun)
            )
        ).all()
        for run in runs:
            if run.cancel_requested:
                run.status = run.current_stage = "cancelled"
                if run.threads_result is not None:
                    self._clear_run_data(run, run.threads_result)
            else:
                run.status = run.current_stage = "failed"
                run.error_code = "WORKER_INTERRUPTED"
                run.error_message = "The worker stopped. Saved posts and comments remain available."
                if run.threads_result is not None:
                    run.threads_result.archive_status = "pending"
                    run.threads_result.next_storage_attempt_at = None
            run.completed_at = utc_now()
        await self.session.commit()

    async def claim_next(self, worker_id: str) -> ToolRun | None:
        run = await self.session.scalar(
            select(ToolRun)
            .where(
                ToolRun.tool_name == "threads",
                ToolRun.status == "queued",
                ToolRun.cancel_requested.is_(False),
            )
            .order_by(ToolRun.created_at, ToolRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if run is None:
            await self.session.rollback()
            return None
        run.status = "running"
        run.current_stage = "planning"
        run.worker_id = worker_id
        run.started_at = run.heartbeat_at = utc_now()
        run.attempt_count += 1
        await self.session.commit()
        return run

    async def progress(self, run_id: UUID, stage: str, value: float) -> None:
        run = await self.session.get(ToolRun, run_id, populate_existing=True)
        if run is not None and run.status == "running":
            run.current_stage, run.progress = stage, value
            run.heartbeat_at = utc_now()
            await self.session.commit()

    async def is_cancelled(self, run_id: UUID) -> bool:
        value = await self.session.scalar(
            select(ToolRun.cancel_requested).where(ToolRun.id == run_id)
        )
        return value is None or bool(value)

    async def finish(
        self,
        run_id: UUID,
        *,
        result: dict[str, object] | None = None,
        error: ThreadsError | None = None,
    ) -> None:
        run = await self._locked(run_id)
        if run.status in TERMINAL_STATUSES:
            return
        snapshot = self._ensure_snapshot(run)
        if run.cancel_requested or isinstance(error, ThreadsCancelled):
            run.cancel_requested = True
            run.status = run.current_stage = "cancelled"
            self._clear_run_data(run, snapshot)
        elif error:
            run.status = run.current_stage = "failed"
            run.error_code, run.error_message = error.code, error.detail
            snapshot.archive_status = "pending"
        else:
            self._write_snapshot(snapshot, ThreadsResult.model_validate(result))
            run.status = run.current_stage = "completed"
            run.progress = 1.0
            snapshot.archive_status = "pending"
        run.completed_at = run.heartbeat_at = utc_now()
        snapshot.next_storage_attempt_at = None
        await self.session.commit()

    async def next_storage_run(self) -> UUID | None:
        return await self.session.scalar(
            select(ThreadsResultRecord.run_id)
            .join(
                ToolRun,
                ToolRun.id == ThreadsResultRecord.run_id,
            )
            .where(
                ToolRun.tool_name == "threads",
                ToolRun.status.in_(TERMINAL_STATUSES),
                or_(
                    ThreadsResultRecord.next_storage_attempt_at.is_(None),
                    ThreadsResultRecord.next_storage_attempt_at <= utc_now(),
                ),
                ThreadsResultRecord.deletion_requested.is_(True),
            )
            .order_by(ThreadsResultRecord.deletion_requested.desc(), ToolRun.created_at)
            .limit(1)
        )

    async def storage_failed(self, run_id: UUID, error: ThreadsError) -> None:
        run = await self._locked(run_id)
        snapshot = self._ensure_snapshot(run)
        snapshot.archive_status = "failed"
        snapshot.storage_error = error.code
        snapshot.storage_attempt_count += 1
        snapshot.next_storage_attempt_at = utc_now() + timedelta(
            seconds=min(3600, 30 * 2 ** min(snapshot.storage_attempt_count - 1, 7))
        )
        await self.session.commit()

    async def delete_database(self, run_id: UUID) -> None:
        run = await self._locked(run_id)
        snapshot = self._ensure_snapshot(run)
        if not snapshot.deletion_requested or run.status not in TERMINAL_STATUSES:
            raise ThreadsError("SESSION_BUSY", "The session must stop before cleanup.", 409)
        await self.session.delete(run)
        await self.session.commit()

    async def get_account_session(self, account_id: str) -> ThreadsAccountSessionRecord | None:
        return await self.session.get(ThreadsAccountSessionRecord, account_id)

    async def list_account_sessions(self) -> list[ThreadsAccountSessionRecord]:
        result = await self.session.scalars(select(ThreadsAccountSessionRecord))
        return list(result.all())

    async def save_account_session(
        self, account_id: str, session_data: dict[str, object]
    ) -> ThreadsAccountSessionRecord:
        record = await self.session.get(ThreadsAccountSessionRecord, account_id)
        if record is None:
            record = ThreadsAccountSessionRecord(
                account_id=account_id,
                session_data=session_data,
                updated_at=utc_now(),
            )
            self.session.add(record)
        else:
            record.session_data = session_data
            record.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(record)
        return record



def to_response(
    run: ToolRun,
    *,
    include_result: bool = True,
    user: User | None = None,
) -> ThreadsRunResponse:
    snapshot = run.threads_result
    result = run.details.get("result") if include_result else None
    if (
        include_result
        and snapshot is not None
        and (snapshot.snapshot_ready or run.status in TERMINAL_STATUSES)
    ):
        result = {
            **snapshot.summary,
            "posts": [
                {
                    **post.data,
                    "comments": [clean_stored_comment(comment.data) for comment in post.comments],
                }
                for post in snapshot.posts
            ],
        }
    return ThreadsRunResponse.model_validate(
        {
            "id": run.id,
            "status": run.status,
            "stage": run.current_stage,
            "progress": run.progress,
            "request": run.details["request"],
            "result": result,
            "visibility": snapshot.visibility if snapshot else "private",
            "owner": {
                "id": run.owner_id,
                "display_name": run.owner.display_name if run.owner else None,
            },
            "can_manage": bool(user and (user.id == run.owner_id or user.role == ROLE_ADMIN)),
            "post_count": snapshot.post_count if snapshot else 0,
            "comment_count": snapshot.comment_count if snapshot else 0,
            "archive_status": snapshot.archive_status if snapshot else "pending",
            "archive_uploaded_at": snapshot.archive_uploaded_at if snapshot else None,
            "storage_error": snapshot.storage_error if snapshot else None,
            "deletion_requested": snapshot.deletion_requested if snapshot else False,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }
    )
