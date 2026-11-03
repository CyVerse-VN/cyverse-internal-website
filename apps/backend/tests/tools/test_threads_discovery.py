from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import settings
from app.tools.threads.ai import GroqThreadsAI
from app.tools.threads.config import ThreadsConfig
from app.tools.threads.errors import ThreadsError
from app.tools.threads.pipeline import ThreadsPipeline
from app.tools.threads.query_planning import combine_queries
from app.tools.threads.ranking import rank_comment_targets
from app.tools.threads.schemas import (
    DiscoveryQuery,
    DiscoveryQueryPlan,
    PostTriage,
    ThreadsPost,
    ThreadsRequest,
)


def test_planning_retains_manual_seed_and_limits_queries() -> None:
    plan = DiscoveryQueryPlan(topic="places", queries=[
        DiscoveryQuery(text="SÀI GÒN ĐI ĐÂU", angle="demand", target_content="discussion", origin="generated"),
        DiscoveryQuery(text="quán ruột sg", angle="experience", target_content="direct", origin="generated"),
        DiscoveryQuery(text="sai gon di dau", angle="demand", target_content="discussion", origin="generated"),
    ])
    result = combine_queries(plan, ["sài gòn đi đâu"], 3)
    assert [item.text for item in result.queries] == ["sài gòn đi đâu", "quán ruột sg", "sai gon di dau"]
    assert result.queries[0].origin == "manual"
    assert result.queries[1].angle == "experience"


def triage(**overrides: object) -> PostTriage:
    data: dict[str, object] = {"geo_match": "uncertain", "topic_relevance": 0.9, "direct_poi_score": 0,
                               "discussion_poi_score": 4, "promotion_risk": 0, "reasons": [], "provider": "groq"}
    return PostTriage.model_validate(data | overrides)


def test_ranking_prioritizes_discussion_over_viral_off_topic() -> None:
    question = ThreadsPost(post_id="1", url="a", username="a", reply_count=1, triage=triage())
    viral = ThreadsPost(post_id="2", url="b", username="b", reply_count=10000,
                        triage=triage(topic_relevance=0.1, discussion_poi_score=0))
    wrong_city = ThreadsPost(post_id="3", url="c", username="c", triage=triage(geo_match="no"))
    assert rank_comment_targets([viral, wrong_city, question]) == [question, viral]


def test_validation_rejects_invalid_scores_and_discovery_scraper() -> None:
    with pytest.raises(ValidationError):
        triage(discussion_poi_score=5)
    with pytest.raises(ValidationError):
        ThreadsRequest(query="places", discovery_mode="evidence_poi")


@pytest.mark.asyncio
async def test_discovery_preserves_posts_and_prioritizes_discussion() -> None:
    question = ThreadsPost(post_id="question", url="question", username="a", text="Where should I go?", reply_count=1)
    viral = ThreadsPost(post_id="viral", url="viral", username="b", reply_count=1000)
    crawler = SimpleNamespace(search=AsyncMock(return_value=[viral, question]), comments=AsyncMock(return_value=[]))
    ai = SimpleNamespace(classify=AsyncMock(return_value={
        "question": triage(), "viral": triage(topic_relevance=0.1, discussion_poi_score=0),
    }))
    snapshots = AsyncMock()
    result = await ThreadsPipeline(ThreadsConfig()).run(
        ThreadsRequest(query="places", mode="travel", discovery_mode="evidence_poi",
                       discovery_query_planning=False, keywords=["places"], discovery_comment_budget=1,
                       min_delay_seconds=0, max_delay_seconds=0),
        AsyncMock(), AsyncMock(return_value=False), crawler=crawler, ai=ai, on_snapshot=snapshots,
    )
    assert len(result.posts) == 2
    crawler.comments.assert_awaited_once_with("question", 25)
    assert question.comment_collection_status == "completed"
    assert viral.comment_collection_status == "not_attempted"
    assert snapshots.await_count >= 2


@pytest.mark.asyncio
async def test_invalid_groq_plan_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", SecretStr("test"))
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200, json={"choices": [{"message": {"content": '{"topic":"places","queries":"invalid"}'}}]},
    ))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ThreadsError) as error:
            await GroqThreadsAI(ThreadsConfig(), client).plan_discovery("places", [], 5)
    assert error.value.code == "GROQ_UNAVAILABLE"
