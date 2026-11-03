import asyncio
import logging
import sys
from concurrent.futures import Future
from contextlib import suppress
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.session import async_session_factory, engine
from app.tools.base.registry import ToolRegistry
from app.tools.threads.artifacts import ThreadsArtifacts
from app.tools.threads.cloudinary import CloudinaryTextStore, cloudinary_config
from app.tools.threads.config import ThreadsConfig, threads_config
from app.tools.threads.crawler import SessionCallback
from app.tools.threads.errors import ThreadsCancelled, ThreadsError
from app.tools.threads.pipeline import CancellationCallback, ProgressCallback, SnapshotCallback
from app.tools.threads.repository import ThreadsRepository
from app.tools.threads.schemas import ThreadsResult
from app.tools.threads.service import ThreadsService
from app.tools.threads.tool import ThreadsTool

logger = logging.getLogger(__name__)


class ThreadsWorker:
    def __init__(self, config: ThreadsConfig = threads_config) -> None:
        self.config = config
        self.worker_id = f"threads-{uuid4().hex}"

    async def _execute_tool(
        self,
        payload: dict[str, object],
        progress: ProgressCallback,
        cancelled: CancellationCallback,
        snapshot: SnapshotCallback | None = None,
        existing_post_ids: set[str] | None = None,
    ) -> dict[str, object]:
        async def registered_run(
            on_progress: ProgressCallback,
            is_cancelled: CancellationCallback,
            on_snapshot: SnapshotCallback | None,
            on_session: SessionCallback,
        ) -> dict[str, object]:
            registry = ToolRegistry()
            registry.register(
                ThreadsTool(
                    self.config,
                    on_progress,
                    is_cancelled,
                    on_snapshot,
                    existing_post_ids=existing_post_ids,
                    on_session=on_session,
                )
            )
            return await registry.get("threads").run(payload)

        async def save_refreshed_session(account_id: str, state: dict[str, object]) -> None:
            async with async_session_factory() as session:
                await ThreadsRepository(session).save_account_session(account_id, state)

        if sys.platform != "win32":
            return await registered_run(progress, cancelled, snapshot, save_refreshed_session)

        # Psycopg needs Selector on Windows; Playwright subprocesses need Proactor.
        database_loop = asyncio.get_running_loop()
        ready: Future[tuple[asyncio.AbstractEventLoop, asyncio.Task[dict[str, object]]]] = Future()

        async def forwarded_progress(stage: str, value: float) -> None:
            await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(progress(stage, value), database_loop)
            )

        async def forwarded_cancelled() -> bool:
            return await asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(cancelled(), database_loop)
            )

        async def forwarded_snapshot(result: ThreadsResult) -> None:
            if snapshot is not None:
                # Copy mutable posts before handing them to the database event loop.
                await asyncio.wrap_future(
                    asyncio.run_coroutine_threadsafe(
                        snapshot(result.model_copy(deep=True)), database_loop
                    )
                )

        async def forwarded_session(account_id: str, state: dict[str, object]) -> None:
            await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                save_refreshed_session(account_id, state), database_loop
            ))

        async def browser_run() -> dict[str, object]:
            task = asyncio.current_task()
            assert task is not None
            ready.set_result((asyncio.get_running_loop(), task))
            return await registered_run(forwarded_progress, forwarded_cancelled, forwarded_snapshot,
                                        forwarded_session)

        def run_browser_loop() -> dict[str, object]:
            with asyncio.Runner(loop_factory=asyncio.ProactorEventLoop) as runner:
                return runner.run(browser_run())

        thread_task = asyncio.create_task(asyncio.to_thread(run_browser_loop))
        try:
            return await asyncio.shield(thread_task)
        except asyncio.CancelledError:
            ready_future = asyncio.wrap_future(ready)
            done, _ = await asyncio.wait(
                {thread_task, ready_future}, return_when=asyncio.FIRST_COMPLETED
            )
            if ready_future in done:
                browser_loop, browser_task = ready_future.result()
                if not browser_task.done():
                    browser_loop.call_soon_threadsafe(browser_task.cancel)
            else:
                ready_future.cancel()
            await asyncio.gather(thread_task, return_exceptions=True)
            raise

    async def run_supervised(self) -> None:
        while True:
            try:
                await self.run_forever()
            except asyncio.CancelledError:
                raise
            except SQLAlchemyError:
                # Do not log driver exceptions, which can contain connection credentials.
                logger.error("Threads queue database connection failed")
                await asyncio.sleep(self.config.worker_restart_seconds)

    async def run_forever(self) -> None:
        while True:
            async with engine.connect() as connection:
                postgres = connection.dialect.name == "postgresql"
                acquired = not postgres or bool(
                    await connection.scalar(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": self.config.worker_advisory_lock_id},
                    )
                )
                await connection.commit()
                if acquired:
                    try:
                        async with async_session_factory() as session:
                            await ThreadsRepository(session).recover_interrupted()
                            await ThreadsService(ThreadsRepository(session), self.config).restore_sessions_from_db()
                        while True:
                            await connection.execute(text("SELECT 1"))
                            await connection.commit()
                            stored = await self.storage_once()
                            if not await self.run_once(connection) and not stored:
                                await asyncio.sleep(self.config.worker_poll_seconds)
                    finally:
                        if postgres:
                            try:
                                await connection.execute(
                                    text("SELECT pg_advisory_unlock(:lock_id)"),
                                    {"lock_id": self.config.worker_advisory_lock_id},
                                )
                                await connection.commit()
                            except SQLAlchemyError:
                                logger.error("Threads queue lock connection was lost")
            await asyncio.sleep(self.config.worker_restart_seconds)

    async def _progress(self, run_id: UUID, stage: str, value: float) -> None:
        logger.info("Threads run %s stage=%s progress=%.2f", run_id, stage, value)
        async with async_session_factory() as session:
            await ThreadsRepository(session).progress(run_id, stage, value)

    async def _cancelled(self, run_id: UUID) -> bool:
        async with async_session_factory() as session:
            return await ThreadsRepository(session).is_cancelled(run_id)

    async def _snapshot(self, run_id: UUID, result: ThreadsResult) -> None:
        async with async_session_factory() as session:
            await ThreadsRepository(session).save_snapshot(run_id, result)

    async def storage_once(self) -> bool:
        async with (
            async_session_factory() as session,
            httpx.AsyncClient(follow_redirects=False) as client,
        ):
            return await ThreadsArtifacts(
                ThreadsRepository(session), CloudinaryTextStore(cloudinary_config, client),
            ).run_once()

    async def _monitor(
        self,
        run_id: UUID,
        execution: asyncio.Task[dict[str, object]],
        connection: AsyncConnection | None,
    ) -> None:
        while not execution.done():
            await asyncio.sleep(self.config.worker_poll_seconds)
            if await self._cancelled(run_id):
                execution.cancel()
                return
            if connection is not None:
                await connection.execute(text("SELECT 1"))
                await connection.commit()

    async def run_once(self, connection: AsyncConnection | None = None) -> bool:
        async with async_session_factory() as session:
            run = await ThreadsRepository(session).claim_next(self.worker_id)
            if run is None:
                return False
            run_id, payload = run.id, dict(run.details["request"])

        async def progress(stage: str, value: float) -> None:
            await self._progress(run_id, stage, value)

        async def cancelled() -> bool:
            return await self._cancelled(run_id)

        async def snapshot(result: ThreadsResult) -> None:
            await self._snapshot(run_id, result)

        existing_post_ids: set[str] = set()
        if payload.get("check_duplicate", False):
            async with async_session_factory() as session:
                repo = ThreadsRepository(session)
                if hasattr(repo, "get_existing_post_ids"):
                    existing_post_ids = await repo.get_existing_post_ids(
                        user_id=getattr(run, "owner_id", None)
                    )

        execution = asyncio.create_task(
            self._execute_tool(
                payload,
                progress,
                cancelled,
                snapshot,
                existing_post_ids=existing_post_ids,
            )
        )
        monitor = asyncio.create_task(self._monitor(run_id, execution, connection))
        result: dict[str, object] | None = None
        error: ThreadsError | None = None
        raw_timeout = payload.get("run_timeout_seconds")
        timeout_seconds = (
            self.config.run_timeout_seconds if raw_timeout is None else int(raw_timeout)
        )
        timeout_arg = None if timeout_seconds <= 0 else timeout_seconds
        logger.info(
            "Worker %s claimed Threads run %s (query: %r, timeout: %s)",
            self.worker_id,
            run_id,
            payload.get("query"),
            timeout_seconds if timeout_seconds > 0 else "unlimited",
        )
        try:
            async with asyncio.timeout(timeout_arg):
                done, _ = await asyncio.wait(
                    {execution, monitor}, return_when=asyncio.FIRST_COMPLETED
                )
                if monitor in done:
                    await monitor
                result = await execution
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling():
                raise
            logger.info("Threads run %s was cancelled by user", run_id)
            error = ThreadsCancelled()
        except TimeoutError:
            logger.warning(
                "Threads run %s timed out after %s seconds",
                run_id,
                timeout_seconds,
            )
            error = ThreadsError("THREADS_TIMEOUT", "The Threads run exceeded its time limit.", 504)
        except ThreadsError as exc:
            logger.error(
                "Threads run %s failed with ThreadsError [%s]: %s",
                run_id,
                exc.code,
                exc.detail,
            )
            error = exc
        except SQLAlchemyError as exc:
            logger.error("Threads run %s database error: %s", run_id, type(exc).__name__)
            raise
        except (RuntimeError, ValueError, TypeError, LookupError, AttributeError):
            # The job boundary must finalize unexpected failures without persisting raw payloads.
            logger.exception(
                "Threads run %s execution failed unexpectedly",
                run_id,
                extra={"run_id": str(run_id)},
            )
            error = ThreadsError("THREADS_FAILED", "The Threads run could not be completed.", 502)
        finally:
            execution.cancel()
            monitor.cancel()
            await asyncio.gather(execution, monitor, return_exceptions=True)
        async with async_session_factory() as session:
            await ThreadsRepository(session).finish(run_id, result=result, error=error)
        logger.info(
            "Threads run %s finished (status=%s, error_code=%s)",
            run_id,
            "failed" if error else "completed",
            error.code if error else None,
        )
        return True


async def main() -> None:
    from app.core.logging import configure_logging

    configure_logging()
    if not threads_config.enabled:
        raise SystemExit("Enable THREADS_ENABLED before starting the Threads worker.")
    try:
        await ThreadsWorker().run_supervised()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(
            main(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None
        )
