from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.models.research import ResearchPaper, ResearchSession
from app.models.tool_run import ToolRun, ToolRunEvent
from app.tools.research.ai import EnrichmentResponse, _is_vietnamese
from app.tools.research.domain import PaperCandidate
from app.tools.research.http import ResearchSourceError, rate_limiter, request
from app.tools.research.ranking import (
    apply_relevance_gate,
    deduplicate,
    diversify,
    filter_candidates,
    rank_candidates,
)
from app.tools.research.repository import ResearchRepository, decode_cursor, encode_cursor
from app.tools.research.schemas import (
    ResearchSettingsInput,
    ResearchSource,
    UpdateResearchSessionRequest,
)


def paper(
    *,
    source: str = "arxiv",
    title: str = "Retrieval augmented generation for clinical evidence",
    doi: str | None = None,
    citations: int = 5,
) -> PaperCandidate:
    return PaperCandidate(
        source=source,
        source_id=f"{source}-1",
        source_rank=1,
        title=title,
        abstract="A study of retrieval augmented generation grounded in clinical evidence.",
        authors=["A. Researcher"],
        year=datetime.now(UTC).year,
        doi=doi,
        citation_count=citations,
        is_open_access=True,
        publication_types=["article"],
        sources=[source],
    )


def test_research_models_register_durable_run_and_final_paper_tables() -> None:
    assert ToolRun.__tablename__ == "tool_runs"
    assert ToolRunEvent.__tablename__ == "tool_run_events"
    assert ResearchSession.__tablename__ == "research_sessions"
    assert ResearchPaper.__tablename__ == "research_papers"


def test_settings_apply_defaults_and_enforce_source_caps() -> None:
    values = ResearchSettingsInput(sources=[ResearchSource.ARXIV]).effective()

    assert values.raw_limits == {ResearchSource.ARXIV: 50}
    assert values.result_limit == 20
    assert values.year_to == datetime.now(UTC).year
    with pytest.raises(ValidationError):
        ResearchSettingsInput(
            sources=[ResearchSource.ARXIV],
            raw_limits={ResearchSource.ARXIV: 101},
        )


def test_all_years_remains_unbounded() -> None:
    values = ResearchSettingsInput(all_years=True).effective()

    assert values.year_from is None
    assert values.year_to is None


def test_session_update_accepts_a_trimmed_title_or_visibility() -> None:
    rename = UpdateResearchSessionRequest(title="  Renamed research session  ")
    visibility = UpdateResearchSessionRequest(visibility="private")

    assert rename.title == "Renamed research session"
    assert visibility.visibility == "private"
    with pytest.raises(ValidationError):
        UpdateResearchSessionRequest()
    with pytest.raises(ValidationError):
        UpdateResearchSessionRequest(title="   ")


def test_deduplication_merges_sources_without_retaining_raw_records() -> None:
    records = [
        paper(source="arxiv", doi="10.1000/example", citations=2),
        paper(source="openalex", doi="https://doi.org/10.1000/example", citations=12),
    ]

    result = deduplicate(records)

    assert len(result) == 1
    assert result[0][1].sources == ["arxiv", "openalex"]
    assert result[0][1].citation_count == 12


def test_filter_rank_and_diversity_return_observable_results() -> None:
    settings = ResearchSettingsInput(
        sources=[ResearchSource.ARXIV],
        year_from=2020,
        year_to=datetime.now(UTC).year,
        publication_types=["article"],
    ).effective()
    candidates, rejected = filter_candidates(deduplicate([paper()]), settings)
    ranked = rank_candidates("clinical retrieval augmented generation", candidates)
    selected = diversify(ranked, 1)

    assert rejected == 0
    assert len(selected) == 1
    assert selected[0].relevance_score > 0


def test_relevance_gate_does_not_pad_results_with_off_topic_papers() -> None:
    unrelated = paper(
        title="Unrelated observations of coastal sediment transport"
    ).model_copy(update={"abstract": "Measurements of tides and shoreline erosion."})
    candidates = deduplicate(
        [unrelated]
    )
    ranked = rank_candidates("clinical retrieval augmented generation", candidates)

    kept, rejected = apply_relevance_gate(ranked)

    assert kept == []
    assert rejected == 1


def test_ai_enrichment_contract_is_strict_and_vietnamese() -> None:
    response = EnrichmentResponse.model_validate(
        {
            "assessments": [
                {
                    "paper_id": "paper-1",
                    "summary_vi": "Nghiên cứu cung cấp kết quả thực nghiệm đáng tin cậy.",
                    "why_read_vi": ["Giúp xác định khoảng trống nghiên cứu quan trọng."],
                }
            ]
        }
    )

    assert _is_vietnamese(response.assessments[0].summary_vi)
    assert len(response.assessments[0].why_read_vi) <= 3
    with pytest.raises(ValidationError):
        EnrichmentResponse.model_validate(
            {
                "assessments": [
                    {
                        "paper_id": "paper-1",
                        "summary_vi": "Nghiên cứu cung cấp kết quả thực nghiệm đáng tin cậy.",
                        "why_read_vi": ["Một", "Hai", "Ba", "Bốn"],
                        "unexpected": True,
                    }
                ]
            }
        )


def test_cursor_round_trip_is_stable() -> None:
    created_at = datetime.now(UTC)
    identifier = uuid4()

    decoded = decode_cursor(encode_cursor(created_at, identifier))

    assert decoded == (created_at, identifier)
    assert decode_cursor("not-a-cursor") is None


@pytest.mark.asyncio
async def test_delete_permanently_deletes_session_and_cancels_an_active_run() -> None:
    from unittest.mock import call

    database_session = AsyncMock()
    repository = ResearchRepository(database_session)
    repository.request_cancellation = AsyncMock()
    run = ToolRun(
        owner_id=uuid4(),
        tool_name="research",
        status="running",
        current_stage="retrieving",
    )
    research_session = ResearchSession(
        run=run,
        query="deepfake detection",
        title="Deepfake detection",
        visibility="private",
        effective_settings={},
    )

    await repository.delete_session(research_session)

    repository.request_cancellation.assert_awaited_once_with(research_session)
    database_session.delete.assert_has_awaits([call(research_session), call(run)])
    database_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_source_request_retries_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    delays: list[float] = []

    def handler(incoming: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0.5"}, request=incoming)
        return httpx.Response(200, json={"results": []}, request=incoming)

    async def record_delay(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr("app.tools.research.http.asyncio.sleep", record_delay)
    monkeypatch.setitem(rate_limiter._intervals, "openalex", 0.0)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await request(
            client,
            "GET",
            "https://api.openalex.org/works",
            source="openalex",
        )

    assert response.status_code == 200
    assert calls == 2
    assert delays == [2.0]


@pytest.mark.asyncio
async def test_source_request_classifies_rate_limit_without_provider_payload() -> None:
    def handler(incoming: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="provider-specific detail", request=incoming)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ResearchSourceError) as captured:
            await request(
                client,
                "GET",
                "https://api.openalex.org/works",
                source="openalex",
                attempts=1,
            )

    assert captured.value.code == "source_rate_limited"
    assert "provider-specific detail" not in str(captured.value)


@pytest.mark.asyncio
async def test_arxiv_source_search_parses_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tools.research.sources.arxiv import ArxivSource

    sample_feed = b"""<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2305.06564v4</id>
        <title>Undercover Deepfakes</title>
        <summary>A study on detecting deepfakes.</summary>
        <author><name>Author One</name></author>
        <published>2023-05-11T04:43:10Z</published>
        <arxiv:doi>10.1000/182</arxiv:doi>
        <link href="https://arxiv.org/abs/2305.06564v4" rel="alternate"/>
        <link href="https://arxiv.org/pdf/2305.06564v4" rel="related" type="application/pdf"/>
        <category term="cs.CV"/>
      </entry>
    </feed>"""

    def mock_fetch_sync(url: str, user_agent: str, timeout: float) -> bytes:
        assert "search_query=" in url
        assert "CyVerse-AI-Research" in user_agent
        return sample_feed

    monkeypatch.setattr("app.tools.research.sources.arxiv._fetch_arxiv_sync", mock_fetch_sync)
    monkeypatch.setitem(rate_limiter._intervals, "arxiv", 0.0)

    async with httpx.AsyncClient() as client:
        source = ArxivSource(client)
        papers = await source.search("deepfake detection", limit=5, filters={})

    assert len(papers) == 1
    candidate = papers[0]
    assert candidate.source == "arxiv"
    assert candidate.arxiv_id == "2305.06564"
    assert candidate.title == "Undercover Deepfakes"
    assert candidate.year == 2023
    assert candidate.doi == "10.1000/182"
    assert candidate.authors == ["Author One"]
    assert candidate.is_open_access is True

