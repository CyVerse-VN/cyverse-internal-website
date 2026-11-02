from __future__ import annotations

import asyncio
import logging
import socket
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from app.db.session import async_session_factory, engine
from app.models.tool_run import ToolRun
from app.tools.notebooklm.config import notebook_import_config
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.pdf import download_pdf
from app.tools.notebooklm.provider import NotebookLMPyProvider, NotebookProvider
from app.tools.notebooklm.repository import NotebookImportRepository
from app.tools.notebooklm.resolver import PaperResolver
from app.tools.notebooklm.schemas import PaperSeed
from app.tools.notebooklm.session import decrypt_session

logger = logging.getLogger(__name__)


class NotebookImportWorker:
    def __init__(self, provider: NotebookProvider | None = None) -> None:
        self.worker_id = f"{socket.gethostname()}-{uuid4().hex[:8]}"
        self.provider = provider or NotebookLMPyProvider()
        self.resolver = PaperResolver()

    async def run_supervised(self) -> None:
        while True:
            try:
                await self.run_forever()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Notebook import queue stopped", exc_info=False)
                await asyncio.sleep(notebook_import_config.worker_restart_seconds)

    async def run_forever(self) -> None:
        while True:
            async with engine.connect() as lock_connection:
                acquired = True
                if lock_connection.dialect.name == "postgresql":
                    acquired = bool(await lock_connection.scalar(
                        text("SELECT pg_try_advisory_lock(:lock_id)"),
                        {"lock_id": notebook_import_config.worker_advisory_lock_id},
                    ))
                    await lock_connection.commit()
                if acquired:
                    try:
                        while True:
                            if not await self.run_once():
                                await asyncio.sleep(notebook_import_config.worker_poll_seconds)
                    finally:
                        if lock_connection.dialect.name == "postgresql":
                            await lock_connection.execute(
                                text("SELECT pg_advisory_unlock(:lock_id)"),
                                {"lock_id": notebook_import_config.worker_advisory_lock_id},
                            )
                            await lock_connection.commit()
            await asyncio.sleep(notebook_import_config.worker_restart_seconds)

    async def run_once(self) -> bool:
        async with async_session_factory() as session:
            repository = NotebookImportRepository(session)
            await repository.recover_stale(
                notebook_import_config.worker_lease_seconds,
                notebook_import_config.worker_max_attempts,
            )
            item = await repository.claim_next(self.worker_id)
            if item is None:
                return False
            run_id = item.run_id
            path: Path | None = None
            upload_started = False
            source_persisted = item.source_id is not None
            try:
                storage = decrypt_session(item.session_ciphertext)
                if item.source_id is None:
                    seed = PaperSeed.model_validate(item.paper)
                    pdf_url = await self.resolver.resolve(seed)
                    await repository.transition(
                        item, "downloading", 0.35, "Downloading the validated PDF.", pdf_url=pdf_url
                    )
                    download_task = asyncio.create_task(asyncio.to_thread(download_pdf, pdf_url))
                    try:
                        path = await asyncio.shield(download_task)
                    except asyncio.CancelledError:
                        try:
                            path = await download_task
                        finally:
                            raise
                    await repository.transition(item, "uploading", 0.7, "Uploading PDF to NotebookLM.")
                    upload_started = True
                    source_id = await self.provider.add_file(storage, item.notebook_id, path)
                    await repository.transition(
                        item, "processing", 0.85, "NotebookLM is processing the PDF.",
                        source_id=source_id,
                    )
                    source_persisted = True
                    path.unlink(missing_ok=True)
                    path = None
                await self.provider.wait_ready(storage, item.notebook_id, item.source_id or source_id)
                await repository.complete(item)
            except asyncio.CancelledError:
                await session.rollback()
                raise
            except NotebookImportError as exc:
                error = exc
                if upload_started and not source_persisted:
                    error = NotebookImportError(
                        "UPLOAD_OUTCOME_UNKNOWN", "Check the notebook before retrying this import."
                    )
                await repository.fail(item.run, error)
            except Exception:
                uncertain_upload = upload_started and not source_persisted
                await session.rollback()
                logger.exception(
                    "Notebook import failed", exc_info=False, extra={"run_id": str(run_id)}
                )
                run = await session.get(ToolRun, run_id)
                if run is None:
                    raise
                await repository.fail(run, NotebookImportError(
                    "UPLOAD_OUTCOME_UNKNOWN" if uncertain_upload else "NOTEBOOKLM_UNAVAILABLE",
                    "Check the notebook before retrying this import."
                    if uncertain_upload else "The paper import could not be completed.",
                ))
            finally:
                if path is not None:
                    path.unlink(missing_ok=True)
            return True
