from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx

from app.tools.research.ai import StructuredAIClient, create_query_plan, enrich, rerank
from app.tools.research.config import research_config
from app.tools.research.domain import PaperCandidate, PipelineResult
from app.tools.research.errors import ResearchCancelledError, ResearchPipelineError
from app.tools.research.http import ResearchSourceError
from app.tools.research.ranking import (
    apply_ai_scores,
    apply_relevance_gate,
    deduplicate,
    diversify,
    filter_candidates,
    rank_candidates,
)
from app.tools.research.schemas import ResearchSettingsInput, ResearchSource
from app.tools.research.sources import ArxivSource, OpenAlexSource, SemanticScholarSource

ProgressCallback = Callable[[str, float, str, dict[str, object] | None], Awaitable[None]]
CancellationCheck = Callable[[], Awaitable[bool]]


class ResearchPipeline:
    """Async, side-effect-free pipeline that returns only validated final papers."""

    async def run(
        self,
        *,
        query: str,
        settings: ResearchSettingsInput,
        on_progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> PipelineResult:
        user_agent = "CyVerse-AI-Research/3.0"
        if research_config.contact_email:
            user_agent = f"{user_agent} ({research_config.contact_email})"
        async with httpx.AsyncClient(
            headers={"User-Agent": user_agent}, follow_redirects=True
        ) as client:
            ai = StructuredAIClient(client, is_cancelled)
            plan, planner_warning = await create_query_plan(ai, query)
            await self._checkpoint(is_cancelled)
            await on_progress(
                "retrieving",
                0.16,
                "Searching the selected academic sources.",
                {"sources": [source.value for source in settings.sources]},
            )
            candidates, warnings, source_counts = await self._retrieve(
                client=client,
                plan_query=plan.english_question,
                query_variants=plan.query_variants,
                settings=settings,
                on_progress=on_progress,
                is_cancelled=is_cancelled,
            )
            if planner_warning:
                warnings.insert(
                    0,
                    {"code": "ai_planner_unavailable", "message": planner_warning},
                )
            if not candidates:
                raise ResearchPipelineError

            await self._checkpoint(is_cancelled)
            await on_progress(
                "deduplicating",
                0.38,
                "Removing duplicate records across sources.",
                {"raw_candidate_count": len(candidates)},
            )
            deduplicated = deduplicate(candidates)

            await self._checkpoint(is_cancelled)
            await on_progress(
                "filtering",
                0.47,
                "Applying publication and access filters.",
                {"deduplicated_count": len(deduplicated)},
            )
            filtered, rejected_count = filter_candidates(deduplicated, settings)
            if not filtered:
                raise ResearchPipelineError

            await self._checkpoint(is_cancelled)
            await on_progress(
                "ranking",
                0.57,
                "Ranking papers by relevance and research quality.",
                {"filtered_count": len(filtered)},
            )
            ranked = rank_candidates(plan.english_question, filtered)

            await self._checkpoint(is_cancelled)
            await on_progress(
                "ai_reranking", 0.67, "Checking semantic relevance with AI.", None
            )
            ai_scores, rerank_warning = await rerank(ai, query, ranked)
            if rerank_warning:
                warnings.append({"code": "ai_rerank_unavailable", "message": rerank_warning})
            ranked = apply_ai_scores(ranked, ai_scores)
            ranked, relevance_rejected_count = apply_relevance_gate(ranked)
            if not ranked:
                raise ResearchPipelineError

            await self._checkpoint(is_cancelled)
            await on_progress(
                "diversifying", 0.75, "Balancing similar papers in the final shortlist.", None
            )
            selected = diversify(ranked, settings.result_limit)

            await self._checkpoint(is_cancelled)
            await on_progress(
                "summarizing",
                0.82,
                "Writing Vietnamese summaries and reading recommendations.",
                {"selected_count": len(selected)},
            )
            enriched, enrichment_warnings = await enrich(ai, query, selected)
            warnings.extend(enrichment_warnings)
            if not enriched:
                raise ResearchPipelineError

            return PipelineResult(
                papers=enriched,
                warnings=warnings,
                stats={
                    "source_counts": source_counts,
                    "raw_candidate_count": len(candidates),
                    "deduplicated_count": len(deduplicated),
                    "filtered_count": len(filtered),
                    "rejected_count": rejected_count,
                    "relevance_rejected_count": relevance_rejected_count,
                    "result_count": len(enriched),
                    "ai_usage": ai.usage_summary(),
                },
            )

    async def _retrieve(
        self,
        *,
        client: httpx.AsyncClient,
        plan_query: str,
        query_variants: list[str],
        settings: ResearchSettingsInput,
        on_progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> tuple[list[PaperCandidate], list[dict[str, object]], dict[str, int]]:
        adapters = {
            ResearchSource.SEMANTIC_SCHOLAR: SemanticScholarSource(client, is_cancelled),
            ResearchSource.ARXIV: ArxivSource(client, is_cancelled),
            ResearchSource.OPENALEX: OpenAlexSource(client, is_cancelled),
        }
        filters = {
            "year_from": settings.year_from,
            "year_to": settings.year_to,
            "publication_types": [value.value for value in settings.publication_types],
            "languages": settings.languages,
            "open_access_only": settings.open_access_only,
            "require_abstract": settings.require_abstract,
        }
        async def retrieve_source(
            source: ResearchSource,
        ) -> tuple[ResearchSource, list[PaperCandidate], ResearchSourceError | None]:
            adapter = adapters[source]
            try:
                await adapter.checkpoint()
                cap = settings.raw_limits[source]
                variants = query_variants if query_variants else [plan_query]
                per_query = max(1, (cap + len(variants) - 1) // len(variants))
                papers: list[PaperCandidate] = []
                seen: set[str] = set()
                partial_error: ResearchSourceError | None = None
                for variant in variants:
                    await adapter.checkpoint()
                    try:
                        found = await adapter.search(
                            variant, limit=per_query, filters=filters
                        )
                    except (ResearchSourceError, ValueError, TypeError, KeyError) as error:
                        if isinstance(error, ResearchSourceError):
                            partial_error = error
                        else:
                            partial_error = ResearchSourceError(
                                source.value, "The source returned invalid data."
                            )
                        if papers:
                            break
                        if isinstance(error, ResearchSourceError):
                            raise
                        raise partial_error from error
                    for paper in found:
                        identity = paper.source_id or paper.doi or paper.arxiv_id or paper.title
                        if identity.casefold() not in seen:
                            seen.add(identity.casefold())
                            papers.append(paper)
                        if len(papers) >= cap:
                            break
                    if len(papers) >= cap:
                        break
                return source, papers, partial_error
            except ResearchSourceError as error:
                return source, [], error
            except (ValueError, TypeError, KeyError):
                return source, [], ResearchSourceError(
                    source.value, "The source returned invalid data."
                )

        tasks: list[asyncio.Task[tuple[ResearchSource, list[PaperCandidate], ResearchSourceError | None]]] = []
        for source in settings.sources:
            tasks.append(asyncio.create_task(retrieve_source(source)))

        candidates: list[PaperCandidate] = []
        warnings: list[dict[str, object]] = []
        source_counts: dict[str, int] = {}
        try:
            for completed, task in enumerate(asyncio.as_completed(tasks), start=1):
                source, papers, error = await task
                if error is not None:
                    source_name = source.value.replace("_", " ").title()
                    message = f"{source_name} was unavailable."
                    if error.code == "source_rate_limited":
                        message = (
                            f"{source_name} rate limit was reached; results from other "
                            "sources were preserved."
                        )
                    elif error.code == "source_timeout":
                        message = (
                            f"{source_name} timed out; results from other sources were "
                            "preserved."
                        )
                    warnings.append(
                        {
                            "code": error.code,
                            "source": error.source,
                            "message": message,
                        }
                    )
                candidates.extend(papers)
                source_counts[source.value] = len(papers)
                await self._checkpoint(is_cancelled)
                await on_progress(
                    "retrieving",
                    0.16 + 0.18 * completed / max(len(tasks), 1),
                    f"Finished searching {source.value.replace('_', ' ').title()}.",
                    {"source_counts": source_counts},
                )
        finally:
            # Let already-issued provider requests settle before leaving the session.
            await asyncio.gather(*tasks, return_exceptions=True)
        return candidates, warnings, source_counts

    @staticmethod
    async def _checkpoint(is_cancelled: CancellationCheck) -> None:
        if await is_cancelled():
            raise ResearchCancelledError
