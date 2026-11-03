"""Durable archival and cleanup processed by the single Threads queue consumer."""

import logging

from app.tools.threads.cloudinary import TextStore, archive_public_id
from app.tools.threads.errors import ThreadsError
from app.tools.threads.repository import ThreadsRepository
from app.tools.threads.storage import render_text

logger = logging.getLogger(__name__)


class ThreadsArtifacts:
    def __init__(self, repository: ThreadsRepository, store: TextStore, *, archive_enabled: bool = True) -> None:
        self.repository = repository
        self.store = store
        self.archive_enabled = archive_enabled

    async def run_once(self) -> bool:
        run_id = await self.repository.next_storage_run(include_archives=self.archive_enabled)
        if run_id is None:
            return False
        run = await self.repository.get(run_id, None)
        snapshot = run.threads_result
        assert snapshot is not None
        try:
            if snapshot.deletion_requested:
                logger.info("Executing artifact deletion for run %s", run_id)
                if (snapshot.archive_public_id or snapshot.legacy_archive_public_id) and not self.store.available:
                    raise ThreadsError("CLOUDINARY_NOT_CONFIGURED", "Cloud cleanup requires Cloudinary configuration.", 503)
                if self.store.available:
                    if snapshot.archive_public_id:
                        await self.store.delete(snapshot.archive_public_id)
                    if snapshot.legacy_archive_public_id:
                        await self.store.delete(snapshot.legacy_archive_public_id)
                # Retain the database tombstone until cloud deletion is confirmed.
                await self.repository.delete_database(run_id)
            else:
                if not self.store.available:
                    raise ThreadsError(
                        "CLOUDINARY_NOT_CONFIGURED", "Configure Cloudinary storage.", 503
                    )
                response = await self.repository.prepare_archive(run_id)
                if response is not None:
                    logger.info("Uploading artifact archive for run %s", run_id)
                    await self.store.upload(archive_public_id(run_id), render_text(response))
                    if snapshot.legacy_archive_public_id:
                        await self.store.delete(snapshot.legacy_archive_public_id)
                    await self.repository.archive_ready(run_id, response.visibility)
        except ThreadsError as error:
            logger.error("Threads artifact storage failed for run %s: [%s] %s", run_id, error.code, error.detail)
            await self.repository.storage_failed(run_id, error)
        except Exception as exc:
            logger.exception("Unexpected error in Threads artifact storage for run %s", run_id)
            await self.repository.storage_failed(run_id, ThreadsError("STORAGE_FAILED", str(exc), 500))
        return True
