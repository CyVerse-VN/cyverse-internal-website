from __future__ import annotations

import asyncio
import logging
import socket
from uuid import uuid4

from sqlalchemy import text

from app.db.session import async_session_factory, engine
from app.models.research import ResearchPaper
from app.tools.research.config import research_config
from app.tools.research.errors import ResearchCancelledError, ResearchPipelineError
from app.tools.research.pipeline import ResearchPipeline
from app.tools.research.ranking import normalized_paper_type
from app.tools.research.repository import ResearchRepository
from app.tools.research.schemas import ResearchSettingsInput

logger = logging.getLogger(__name__)


class ResearchWorker:
    def __init__(self) -> None:
        self.worker_id = f"{socket.gethostname()}-{uuid4().hex[:8]}"
        self.pipeline = ResearchPipeline()

    async def run_supervised(self) -> None:
        """Keep the embedded queue consumer alive across transient database failures."""

        while True:
            try:
                await self.run_forever()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Research queue loop stopped", exc_info=False)
                await asyncio.sleep(research_config.worker_restart_seconds)

    async def run_forever(self) -> None:
        while True:
            async with engine.connect() as lock_connection:
                acquired = True
                if lock_connection.dialect.name == "postgresql":
                    acquired = bool(
                        await lock_connection.scalar(
                            text("SELECT pg_try_advisory_lock(:lock_id)"),
                            {"lock_id": research_config.worker_advisory_lock_id},
                        )
                    )
                    await lock_connection.commit()
                if not acquired:
                    logger.info("Another process owns the research queue lock")
                else:
                    logger.info(
                        "Research queue consumer started",
                        extra={"worker_id": self.worker_id},
                    )
                    try:
                        while True:
                            processed = await self.run_once()
                            if not processed:
                                await asyncio.sleep(research_config.worker_poll_seconds)
                    finally:
                        if lock_connection.dialect.name == "postgresql":
                            try:
                                await lock_connection.execute(
                                    text("SELECT pg_advisory_unlock(:lock_id)"),
                                    {"lock_id": research_config.worker_advisory_lock_id},
                                )
                                await lock_connection.commit()
                            except Exception:
                                # Closing the database connection also releases a session lock.
                                logger.exception(
                                    "Research queue lock release failed", exc_info=False
                                )
            await asyncio.sleep(research_config.worker_restart_seconds)

    async def run_once(self) -> bool:
        async with async_session_factory() as database_session:
            repository = ResearchRepository(database_session)
            await repository.recover_stale_runs(
                research_config.worker_lease_seconds,
                research_config.worker_max_attempts,
            )
            research_session = await repository.claim_next(self.worker_id)
            if research_session is None:
                return False

            async def progress(
                stage: str,
                value: float,
                message: str,
                metadata: dict[str, object] | None,
            ) -> None:
                await repository.transition(
                    research_session.run_id,
                    stage=stage,
                    progress=value,
                    message=message,
                    metadata=metadata,
                )

            async def cancelled() -> bool:
                # Use a short-lived session so concurrent source tasks can check safely.
                async with async_session_factory() as cancellation_session:
                    return await ResearchRepository(
                        cancellation_session
                    ).is_cancel_requested(research_session.run_id)

            try:
                result = await self.pipeline.run(
                    query=research_session.query,
                    settings=ResearchSettingsInput.model_validate(
                        research_session.effective_settings
                    ),
                    on_progress=progress,
                    is_cancelled=cancelled,
                )
                if await cancelled():
                    raise ResearchCancelledError
                await progress(
                    "saving", 0.94, "Saving the final research papers.", {"result_count": len(result.papers)}
                )
                papers = []
                for rank, item in enumerate(result.papers, start=1):
                    ranked = item.ranked
                    paper = ranked.paper
                    papers.append(
                        ResearchPaper(
                            rank=rank,
                            relevance_score=ranked.relevance_score,
                            read_priority=ranked.read_priority,
                            dedup_key=ranked.dedup_key,
                            title=paper.title,
                            authors=paper.authors,
                            year=paper.year,
                            published_at=paper.published_at,
                            venue=paper.venue,
                            doi=paper.doi,
                            arxiv_id=paper.arxiv_id,
                            sources=paper.sources,
                            paper_type=normalized_paper_type(paper.publication_types),
                            fields=paper.fields[:12],
                            citation_count=paper.citation_count,
                            is_open_access=paper.is_open_access,
                            pdf_url=paper.pdf_url,
                            landing_url=paper.landing_url,
                            summary_vi=item.summary_vi,
                            why_read_vi=item.why_read_vi,
                        )
                    )
                await repository.complete(
                    research_session,
                    papers,
                    warnings=result.warnings,
                    result_stats=result.stats,
                )
            except asyncio.CancelledError:
                await database_session.rollback()
                try:
                    async with async_session_factory() as recovery_session:
                        await ResearchRepository(recovery_session).release_worker_claim(
                            research_session.run_id, self.worker_id
                        )
                except Exception:
                    logger.exception(
                        "Research run could not be requeued during shutdown",
                        exc_info=False,
                        extra={"run_id": str(research_session.run_id)},
                    )
                raise
            except ResearchCancelledError:
                await repository.mark_cancelled(research_session.run)
            except ResearchPipelineError:
                await repository.fail(
                    research_session.run_id,
                    code="pipeline_no_results",
                    message="No fully analyzed papers were available for this search.",
                )
            except Exception:
                logger.exception(
                    "Research session failed",
                    exc_info=False,
                    extra={"run_id": str(research_session.run_id)},
                )
                await repository.fail(
                    research_session.run_id,
                    code="pipeline_unavailable",
                    message="The research service could not complete this session.",
                )
            return True


def main() -> None:
    asyncio.run(ResearchWorker().run_supervised())


if __name__ == "__main__":
    main()
