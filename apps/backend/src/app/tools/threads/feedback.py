"""Analytics and retrieval quality feedback metrics."""

from pydantic import BaseModel, Field

from app.tools.threads.discovery_schemas import DiscoveryQueryPlan
from app.tools.threads.poi_schemas import POICandidate, POIMention
from app.tools.threads.schemas import ThreadsPost


class QueryFeedbackMetric(BaseModel):
    query_text: str
    query_angle: str = "topic_specific"
    search_mode: str = "recent"
    posts_seen: int = 0
    unique_posts: int = 0
    duplicate_posts: int = 0
    relevant_posts: int = 0
    direct_poi_posts: int = 0
    discussion_poi_posts: int = 0
    poi_mentions_extracted: int = 0
    unique_poi_candidates: int = 0
    verified_pois: int = 0
    duration_seconds: float = 0.0


class DiscoveryFeedbackSummary(BaseModel):
    query_metrics: list[QueryFeedbackMetric] = Field(default_factory=list)
    total_unique_posts: int = 0
    total_poi_mentions: int = 0
    total_poi_candidates: int = 0
    total_verified_pois: int = 0
    evidence_grounding_rate: float = 1.0
    verified_poi_yield: float = 0.0


def compute_discovery_feedback(
    posts: list[ThreadsPost],
    candidates: list[POICandidate],
    mentions: list[POIMention],
    plan: DiscoveryQueryPlan | None = None,
    search_attempts: list[dict[str, object]] | None = None,
    duration_seconds: float = 0.0,
) -> DiscoveryFeedbackSummary:
    """Compute observable retrieval and POI yield analytics."""
    unique_posts = len(posts)
    total_mentions = len(mentions)
    total_candidates = len(candidates)
    verified = sum(1 for c in candidates if c.verification_status == "verified")

    # Metrics per query attempt
    metrics: list[QueryFeedbackMetric] = []
    angle_by_kw = {q.text: q.angle for q in (plan.queries if plan else [])}

    for attempt in search_attempts or []:
        kw = str(attempt.get("keyword", ""))
        mode = str(attempt.get("mode", "recent"))
        seen = int(attempt.get("posts", 0))
        new_p = int(attempt.get("new_posts", 0))
        dup = int(attempt.get("collection_duplicates", 0)) + int(attempt.get("previous_session_duplicates", 0))

        # Posts matching this keyword
        kw_posts = [p for p in posts if kw in p.search_keywords]
        direct_count = sum(1 for p in kw_posts if p.discovery and p.discovery.route in {"direct", "both"})
        disc_count = sum(1 for p in kw_posts if p.discovery and p.discovery.route in {"discussion", "both"})
        rel_count = sum(1 for p in kw_posts if p.filter_selected is not False)

        metrics.append(
            QueryFeedbackMetric(
                query_text=kw,
                query_angle=angle_by_kw.get(kw, "topic_specific"),
                search_mode=mode,
                posts_seen=seen,
                unique_posts=new_p,
                duplicate_posts=dup,
                relevant_posts=rel_count,
                direct_poi_posts=direct_count,
                discussion_poi_posts=disc_count,
                poi_mentions_extracted=total_mentions,
                unique_poi_candidates=total_candidates,
                verified_pois=verified,
                duration_seconds=duration_seconds,
            )
        )

    yield_rate = (verified / unique_posts) if unique_posts > 0 else 0.0

    return DiscoveryFeedbackSummary(
        query_metrics=metrics,
        total_unique_posts=unique_posts,
        total_poi_mentions=total_mentions,
        total_poi_candidates=total_candidates,
        total_verified_pois=verified,
        evidence_grounding_rate=1.0,
        verified_poi_yield=round(yield_rate, 4),
    )
