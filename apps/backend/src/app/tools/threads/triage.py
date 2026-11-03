"""Post triage contract and routing rules for Discovery Mode."""

from typing import Protocol

from app.tools.threads.discovery_schemas import DiscoveryRoute, PostTriage
from app.tools.threads.schemas import ThreadsPost

__all__ = ["MIN_TOPIC_RELEVANCE", "ROUTE_SCORE_THRESHOLD", "PostTriage", "PostTriageProvider", "route_post"]

MIN_TOPIC_RELEVANCE = 0.2
ROUTE_SCORE_THRESHOLD = 2
MAX_PROMOTION_RISK = 4


class PostTriageProvider(Protocol):
    name: str

    async def classify(self, query: str, posts: list[ThreadsPost]) -> dict[str, PostTriage]: ...


def route_post(triage: PostTriage | None) -> DiscoveryRoute:
    """Decide which collection branches a post feeds.

    A missing triage is "unclassified" and is never treated as a rejection.
    `uncertain` geography is kept; only an explicit `no` excludes a post.
    A question post with no POI in its body still routes to `discussion`.
    """
    if triage is None:
        return "unclassified"
    if (
        triage.geo_match == "no"
        or triage.topic_relevance < MIN_TOPIC_RELEVANCE
        or triage.promotion_risk >= MAX_PROMOTION_RISK
    ):
        return "excluded"
    direct = triage.direct_poi_score >= ROUTE_SCORE_THRESHOLD
    discussion = triage.discussion_poi_score >= ROUTE_SCORE_THRESHOLD
    if direct and discussion:
        return "both"
    if direct:
        return "direct"
    if discussion:
        return "discussion"
    return "excluded"
