from app.tools.base.contract import InternalTool
from app.tools.threads.config import ThreadsConfig, threads_config
from app.tools.threads.crawler import SessionCallback
from app.tools.threads.pipeline import (
    CancellationCallback,
    ProgressCallback,
    SnapshotCallback,
    ThreadsPipeline,
)
from app.tools.threads.schemas import ThreadsRequest


async def ignore_progress(_stage: str, _progress: float) -> None:
    pass


async def never_cancelled() -> bool:
    return False


class ThreadsTool(InternalTool):
    name = "threads"

    def __init__(
        self,
        config: ThreadsConfig = threads_config,
        on_progress: ProgressCallback = ignore_progress,
        is_cancelled: CancellationCallback = never_cancelled,
        on_snapshot: SnapshotCallback | None = None,
        existing_post_ids: set[str] | None = None,
        on_session: SessionCallback | None = None,
    ) -> None:
        self.pipeline = ThreadsPipeline(config)
        self.on_progress = on_progress
        self.is_cancelled = is_cancelled
        self.on_snapshot = on_snapshot
        self.existing_post_ids = existing_post_ids
        self.on_session = on_session

    async def run(self, payload: dict[str, object]) -> dict[str, object]:
        request = ThreadsRequest.model_validate(payload)
        result = await self.pipeline.run(
            request,
            self.on_progress,
            self.is_cancelled,
            on_snapshot=self.on_snapshot,
            existing_post_ids=self.existing_post_ids,
            on_session=self.on_session,
        )
        return result.model_dump(mode="json")
