from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.tools.threads.config import ThreadsConfig
from app.tools.threads.discovery import select_triage_providers, triage_posts
from app.tools.threads.discovery_schemas import DiscoveryQuery, DiscoveryQueryPlan, PostTriage
from app.tools.threads.errors import ThreadsError
from app.tools.threads.pipeline import ThreadsPipeline
from app.tools.threads.query_planner import merge_query_plan, normalize_query_key
from app.tools.threads.ranking import rank_posts, select_comment_targets
from app.tools.threads.schemas import ThreadsComment, ThreadsPost, ThreadsRequest
from app.tools.threads.triage import route_post


def config(**kwargs: object) -> ThreadsConfig:
    return ThreadsConfig(_env_file=None, min_delay_seconds=0, max_delay_seconds=0, **kwargs)


def make_post(identifier: str, text: str = "text", replies: int = 0) -> ThreadsPost:
    return ThreadsPost(
        post_id=identifier,
        url=f"https://www.threads.com/@sample/post/{identifier}",
        username="sample",
        text=text,
        reply_count=replies,
    )


def triage(**kwargs: object) -> PostTriage:
    values: dict[str, object] = {
        "geo_match": "yes",
        "topic_relevance": 0.9,
        "direct_poi_score": 0,
        "discussion_poi_score": 0,
        "promotion_risk": 0,
    }
    return PostTriage.model_validate({**values, **kwargs})


def generated(text: str, angle: str = "demand") -> DiscoveryQuery:
    return DiscoveryQuery(text=text, angle=angle, target_content="discussion", origin="generated")


def discovery_request(**kwargs: object) -> ThreadsRequest:
    return ThreadsRequest.model_validate(
        {"query": "Quiet places in Saigon", "mode": "travel", "discovery_mode": "evidence_poi", **kwargs}
    )


# Query planning


def test_manual_seed_is_kept_and_generated_queries_add_angles() -> None:
    plan = merge_query_plan(
        ["sài gòn đi đâu"],
        DiscoveryQueryPlan(
            queries=[generated("quán ruột sài gòn", "experience"), generated("sg có gì chơi")]
        ),
        max_queries=8,
    )
    assert plan.queries[0].text == "sài gòn đi đâu"
    assert plan.queries[0].origin == "manual"
    assert {query.angle for query in plan.queries} >= {"demand", "experience"}


def test_planner_deduplicates_by_normalized_key_and_keeps_diacritics() -> None:
    plan = merge_query_plan(
        ["Sài Gòn  đi đâu"],
        DiscoveryQueryPlan(queries=[generated("sài gòn đi đâu!"), generated("sai gon di dau")]),
        max_queries=8,
    )
    assert [query.text for query in plan.queries] == ["Sài Gòn đi đâu", "sai gon di dau"]
    assert normalize_query_key("Sài Gòn") != normalize_query_key("Sai Gon")


def test_planner_respects_limit_and_drops_negated_generated_queries() -> None:
    plan = merge_query_plan(
        ["a"],
        DiscoveryQueryPlan(
            queries=[generated("quán b"), generated("quán không du lịch"), generated("quán c")]
        ),
        max_queries=2,
    )
    assert [query.text for query in plan.queries] == ["a", "quán b"]


def test_manual_seed_with_negation_is_not_dropped() -> None:
    plan = merge_query_plan(["quán không đông"], None, max_queries=4)
    assert plan.queries[0].text == "quán không đông"


# Triage validation and routing


def test_invalid_triage_values_are_rejected() -> None:
    cases = [
        {"topic_relevance": 1.5},
        {"direct_poi_score": 5},
        {"discussion_poi_score": -1},
        {"geo_match": "maybe"},
    ]
    for overrides in cases:
        with pytest.raises(ValidationError):
            triage(**overrides)


def test_question_post_routes_to_discussion_not_excluded() -> None:
    assert route_post(triage(direct_poi_score=0, discussion_poi_score=4)) == "discussion"


def test_review_post_routes_to_direct_and_mixed_post_to_both() -> None:
    assert route_post(triage(direct_poi_score=4)) == "direct"
    assert route_post(triage(direct_poi_score=3, discussion_poi_score=3)) == "both"


def test_other_city_is_excluded_but_uncertain_geo_is_kept() -> None:
    assert route_post(triage(geo_match="no", discussion_poi_score=4)) == "excluded"
    assert route_post(triage(geo_match="uncertain", discussion_poi_score=4)) == "discussion"
    assert route_post(None) == "unclassified"


# Ranking


def test_viral_off_topic_post_does_not_outrank_relevant_discussion() -> None:
    viral = make_post("viral", replies=5000)
    relevant = make_post("relevant", replies=1)
    scores = {
        "viral": triage(topic_relevance=0.25, discussion_poi_score=2, promotion_risk=2),
        "relevant": triage(discussion_poi_score=4),
    }
    ranked = rank_posts([viral, relevant], scores)
    assert ranked[0][0].post_id == "relevant"


def test_comment_targets_use_discussion_score_and_ignore_reply_gate() -> None:
    quiet_question = make_post("quiet", replies=0)
    busy_review = make_post("busy", replies=500)
    excluded = make_post("other", replies=900)
    scores = {
        "quiet": triage(discussion_poi_score=4),
        "busy": triage(direct_poi_score=4, discussion_poi_score=0),
        "other": triage(geo_match="no", discussion_poi_score=4),
    }
    targets = select_comment_targets([busy_review, excluded, quiet_question], scores, budget=5)
    assert [item.post_id for item in targets] == ["quiet"]
    assert select_comment_targets([quiet_question], scores, budget=0) == []


# Providers


@pytest.mark.asyncio
async def test_jev_triage_provider_classifies_decisions_response() -> None:
    import httpx
    from pydantic import SecretStr

    from app.tools.threads.providers.jev_triage import JevTriageProvider

    mock_response = httpx.Response(
        200,
        json={
            "answers": {
                "geo_match": {"type": "choice", "choice": "yes"},
                "topic_relevance": {"type": "noul", "probability": 0.95},
                "direct_poi_score": {"type": "score", "score": 3},
                "discussion_poi_score": {"type": "score", "score": 4},
                "promotion_risk": {"type": "score", "score": 0},
            }
        },
        request=httpx.Request("POST", "https://openrouter.ai/api/alpha/decisions"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    cfg = config(jev_api_key=SecretStr("mock-key"))
    provider = JevTriageProvider(config=cfg, client=mock_client)

    post = make_post("p1", "Bún bò Đen 725 Hoàng Sa")
    results = await provider.classify("Sài Gòn", [post])

    assert "p1" in results
    assert results["p1"].geo_match == "yes"
    assert results["p1"].topic_relevance == 0.95
    assert results["p1"].direct_poi_score == 3
    assert results["p1"].discussion_poi_score == 4
    assert results["p1"].provider == "jev"


@pytest.mark.asyncio
async def test_jev_request_falls_back_to_groq_with_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.tools.threads.discovery.is_jev_configured", lambda: False)
    groq = SimpleNamespace(name="groq", classify=AsyncMock(return_value={"a": triage()}))
    warnings: list[str] = []
    primary, fallback = select_triage_providers("jev", groq, warnings)
    assert primary is groq
    assert fallback is None
    assert any("Jev" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_failed_triage_leaves_posts_unclassified() -> None:
    broken = SimpleNamespace(
        name="groq", classify=AsyncMock(side_effect=ThreadsError("GROQ_UNAVAILABLE", "x", 502))
    )
    warnings: list[str] = []
    result = await triage_posts("q", [make_post("a")], broken, None, warnings)
    assert result == {}
    assert warnings


# Request compatibility


def test_discovery_defaults_are_legacy_and_scraper_mode_rejects_discovery() -> None:
    request = ThreadsRequest.model_validate({"query": "x"})
    assert request.discovery_mode == "legacy"
    assert request.discovery_comment_posts == 20
    with pytest.raises(ValidationError):
        ThreadsRequest.model_validate({"query": "x", "discovery_mode": "evidence_poi"})
    with pytest.raises(ValidationError):
        discovery_request(discovery_comment_posts=51)


# Pipeline integration


def fake_ai(plan: DiscoveryQueryPlan | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        plan_discovery_queries=AsyncMock(return_value=plan or DiscoveryQueryPlan()),
        keywords=AsyncMock(),
        filter=AsyncMock(),
        curate=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_discovery_pipeline_routes_posts_and_crawls_comments_by_potential() -> None:
    question = make_post("question", "Sài Gòn đi đâu cuối tuần?", replies=0)
    review = make_post("review", "Bún bò Đen 725 Hoàng Sa", replies=30)
    hanoi = make_post("hanoi", "Hà Nội", replies=999)
    crawler = SimpleNamespace(
        search=AsyncMock(return_value=[hanoi, review, question]),
        comments=AsyncMock(return_value=[ThreadsComment(id="c", username="a", text="Bún bò Đen")]),
    )
    provider = SimpleNamespace(
        name="fake",
        classify=AsyncMock(
            return_value={
                "question": triage(discussion_poi_score=4),
                "review": triage(direct_poi_score=4),
                "hanoi": triage(geo_match="no", discussion_poi_score=4),
            }
        ),
    )
    plan = DiscoveryQueryPlan(queries=[generated("quán ruột sài gòn", "experience")])
    result = await ThreadsPipeline(config()).run(
        discovery_request(keywords=["sài gòn đi đâu"], search_type="recent"),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=fake_ai(plan),
        triage_provider=provider,
    )
    posts = {item.post_id: item for item in result.posts}
    assert result.keywords == ["sài gòn đi đâu", "quán ruột sài gòn"]
    assert [attempt["angle"] for attempt in result.search_attempts] == ["topic_specific", "experience"]
    assert posts["question"].discovery.route == "discussion"
    assert posts["question"].discovery.comment_status == "completed"
    assert posts["review"].discovery.route == "direct"
    assert posts["review"].discovery.comment_status == "not_attempted"
    assert posts["hanoi"].discovery.route == "excluded"
    assert posts["hanoi"].filter_selected is False
    crawler.comments.assert_awaited_once()
    assert crawler.comments.await_args.args[0] == question.url
    assert result.discovery is not None
    assert result.discovery.discussion_posts == 1
    assert result.discovery.direct_posts == 1
    assert result.discovery.triage_provider == "fake"


@pytest.mark.asyncio
async def test_discovery_comment_failure_keeps_other_posts_and_marks_status() -> None:
    first, second = make_post("first"), make_post("second")
    crawler = SimpleNamespace(
        search=AsyncMock(return_value=[first, second]),
        comments=AsyncMock(
            side_effect=[
                ThreadsError("THREADS_COMMENTS_ERROR", "boom", 502),
                [ThreadsComment(id="c", username="a", text="ok")],
            ]
        ),
    )
    provider = SimpleNamespace(
        name="fake",
        classify=AsyncMock(
            return_value={
                "first": triage(discussion_poi_score=4),
                "second": triage(discussion_poi_score=3),
            }
        ),
    )
    result = await ThreadsPipeline(config()).run(
        discovery_request(keywords=["q"], query_planning=False),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=fake_ai(),
        triage_provider=provider,
    )
    posts = {item.post_id: item for item in result.posts}
    assert posts["first"].discovery.comment_status == "failed"
    assert posts["second"].discovery.comment_status == "completed"
    assert posts["second"].comments[0].text == "ok"
    assert result.discovery.comment_posts_failed == 1


@pytest.mark.asyncio
async def test_discovery_comment_budget_is_capped_by_request() -> None:
    posts = [make_post(f"p{index}") for index in range(5)]
    crawler = SimpleNamespace(search=AsyncMock(return_value=posts), comments=AsyncMock(return_value=[]))
    provider = SimpleNamespace(
        name="fake",
        classify=AsyncMock(return_value={item.post_id: triage(discussion_poi_score=4) for item in posts}),
    )
    result = await ThreadsPipeline(config()).run(
        discovery_request(keywords=["q"], query_planning=False, discovery_comment_posts=2),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=fake_ai(),
        triage_provider=provider,
    )
    assert crawler.comments.await_count == 2
    assert result.discovery.comment_posts_selected == 2


@pytest.mark.asyncio
async def test_legacy_travel_mode_does_not_use_discovery_stages() -> None:
    crawler = SimpleNamespace(search=AsyncMock(return_value=[make_post("one")]), comments=AsyncMock())
    ai = fake_ai()
    provider = SimpleNamespace(name="fake", classify=AsyncMock())
    result = await ThreadsPipeline(config()).run(
        ThreadsRequest.model_validate(
            {"query": "q", "mode": "travel", "keywords": ["q"], "include_comments": False}
        ),
        AsyncMock(),
        AsyncMock(return_value=False),
        crawler=crawler,
        ai=ai,
        triage_provider=provider,
    )
    assert result.discovery is None
    assert result.posts[0].discovery is None
    ai.plan_discovery_queries.assert_not_awaited()
    provider.classify.assert_not_awaited()


# Phase 2: Comment Processing, Grounding, POI Extraction & Entity Resolution

from app.tools.threads.comment_processing import (
    clean_comment_text,
    deduplicate_comments,
    reconstruct_conversations,
)
from app.tools.threads.evidence_validator import (
    find_evidence_span,
    is_grounded_attribute,
)
from app.tools.threads.feedback import compute_discovery_feedback
from app.tools.threads.poi_resolver import (
    resolve_poi_mentions,
)
from app.tools.threads.poi_schemas import POIClaim, POIMention


def test_comment_cleaning_and_dom_deduplication() -> None:
    raw = "Bún bò Đen ngon lắm\nTranslate\n  Trả lời  \n2h"
    assert clean_comment_text(raw) == "Bún bò Đen ngon lắm"

    structured = ThreadsComment(id="c1", username="user1", text="Quán ngon", source="structured")
    dom_dup = ThreadsComment(id="dom_c1", username="user1", text="Quán ngon", source="dom")
    dom_other = ThreadsComment(id="dom_c2", username="user2", text="Quán ngon", source="dom")

    deduped = deduplicate_comments([structured, dom_dup, dom_other])
    assert len(deduped) == 2
    assert {c.id for c in deduped} == {"c1", "dom_c2"}


def test_conversation_reconstruction_preserves_hierarchy() -> None:
    p = make_post("p1", "Sài Gòn ăn gì?")
    c1 = ThreadsComment(id="c1", username="u1", text="Bún bò Đen Hoàng Sa nha", parent_id=None)
    c2 = ThreadsComment(id="c2", username="u2", text="725 Hoàng Sa nha", parent_id="c1")
    c3 = ThreadsComment(id="c3", username="u3", text="Quán này hơi đông", parent_id="c1")
    c_orphan = ThreadsComment(id="c_orph", username="u4", text="Chuẩn luôn", parent_id="missing_parent")

    p.comments = [c1, c2, c3, c_orphan]
    units = reconstruct_conversations(p)

    assert len(units) == 2
    parent_unit = next(u for u in units if u.parent_comment.id == "c1")
    assert len(parent_unit.child_replies) == 2
    assert parent_unit.context_incomplete is False

    orphan_unit = next(u for u in units if u.parent_comment.id == "c_orph")
    assert orphan_unit.context_incomplete is True


def test_evidence_grounding_validation() -> None:
    source = "Ghé Bún bò Đen ở 725 Hoàng Sa nha, nước dùng siêu đậm đà."
    match = find_evidence_span(source, "Bún bò Đen")
    assert match.is_valid is True
    assert match.start_offset == source.index("Bún bò Đen")
    assert match.end_offset == match.start_offset + len("Bún bò Đen")

    # Case-insensitive
    match_lower = find_evidence_span(source, "bún bò đen")
    assert match_lower.is_valid is True

    # Ungrounded hallucination
    match_fake = find_evidence_span(source, "Phở Thìn Hà Nội")
    assert match_fake.is_valid is False

    # Attribute grounding
    assert is_grounded_attribute(source, "725 Hoàng Sa") is True
    assert is_grounded_attribute(source, "123 Lê Lợi") is False


def test_entity_resolution_clusters_mentions_and_discriminates_branches() -> None:
    m1 = POIMention(
        name_text="Bún bò Đen",
        area_text="Hoàng Sa",
        source_post_id="post_1",
        evidence_text="Bún bò Đen ngon lắm",
    )
    m2 = POIMention(
        name_text="Bún bò Đen 725 Hoàng Sa",
        address_text="725 Hoàng Sa, Q.3",
        source_post_id="post_2",
        evidence_text="Bún bò Đen 725 Hoàng Sa",
    )
    # Different branch in another district
    m3_branch = POIMention(
        name_text="Bún bò Đen",
        area_text="Bình Thạnh",
        source_post_id="post_3",
        evidence_text="Bún bò Đen Bình Thạnh",
    )

    claims = [
        POIClaim(
            mention_id=m1.id,
            claim_type="food",
            value="bún bò",
            evidence_text="bún bò",
            source_post_id="post_1",
        ),
        POIClaim(
            mention_id=m2.id,
            claim_type="warning",
            value="quán đông vào cuối tuần",
            evidence_text="quán đông vào cuối tuần",
            source_post_id="post_2",
            sentiment="negative",
        ),
    ]

    candidates = resolve_poi_mentions([m1, m2, m3_branch], claims)

    # m1 and m2 should be merged into one candidate with 2 sources -> verified
    # m3_branch should remain a distinct candidate because of branch discrimination
    assert len(candidates) == 2
    main_cand = next(c for c in candidates if "725 Hoàng Sa" in (c.address or c.canonical_name))
    assert main_cand.distinct_sources_count == 2
    assert main_cand.verification_status == "verified"
    assert len(main_cand.claims) == 2
    # Warning claim preserved
    assert any(c.claim_type == "warning" for c in main_cand.claims)

    branch_cand = next(c for c in candidates if c.area == "Bình Thạnh")
    assert branch_cand.distinct_sources_count == 1
    assert branch_cand.verification_status == "candidate"


def test_feedback_analytics_computes_yield_and_metrics() -> None:
    post_a = make_post("p1")
    post_b = make_post("p2")
    m1 = POIMention(name_text="X", source_post_id="p1", evidence_text="X")
    c1 = resolve_poi_mentions([m1], [])[0]

    feedback = compute_discovery_feedback(
        posts=[post_a, post_b],
        candidates=[c1],
        mentions=[m1],
        duration_seconds=12.5,
    )
    assert feedback.total_unique_posts == 2
    assert feedback.total_poi_mentions == 1
    assert feedback.total_poi_candidates == 1
    assert feedback.evidence_grounding_rate == 1.0
