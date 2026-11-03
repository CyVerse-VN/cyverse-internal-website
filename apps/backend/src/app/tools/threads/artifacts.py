"""Durable cleanup processed by the single Threads queue consumer."""

import logging

from app.tools.threads.cloudinary import TextStore
from app.tools.threads.errors import ThreadsError
from app.tools.threads.repository import ThreadsRepository

logger = logging.getLogger(__name__)


class ThreadsArtifacts:
    def __init__(self, repository: ThreadsRepository, store: TextStore) -> None:
        self.repository = repository
        self.store = store

    async def run_once(self) -> bool:
        run_id = await self.repository.next_storage_run()
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
        except ThreadsError as error:
            logger.error("Threads artifact storage failed for run %s: [%s] %s", run_id, error.code, error.detail)
            await self.repository.storage_failed(run_id, error)
        except Exception as exc:
            logger.exception("Unexpected error in Threads artifact storage for run %s", run_id)
            await self.repository.storage_failed(run_id, ThreadsError("STORAGE_FAILED", str(exc), 500))
        return True
