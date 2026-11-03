"""Independent, testable ranking for Discovery Mode.

The weights below are initial guesses, not tuned or validated values. Adjust
them with benchmark data before relying on the resulting order.
"""

import math
from dataclasses import dataclass

from app.tools.threads.discovery_schemas import PostTriage
from app.tools.threads.schemas import ThreadsPost


@dataclass(frozen=True)
class RankingWeights:
    topic: float = 3.0
    geo_yes: float = 2.0
    geo_uncertain: float = 0.8
    geo_no: float = -5.0
    discussion: float = 1.0
    direct: float = 1.0
    novelty: float = 0.6
    reply_count: float = 0.3
    promotion_penalty: float = 1.5


# Comment crawling favors discussion potential; extraction favors direct potential.
COMMENT_WEIGHTS = RankingWeights(discussion=3.0, direct=0.5)
EXTRACTION_WEIGHTS = RankingWeights(discussion=1.0, direct=2.0)

_REPLY_CAP = 100
_DEFAULT_WEIGHTS = RankingWeights()


def score_post(
    post: ThreadsPost, triage: PostTriage, weights: RankingWeights = _DEFAULT_WEIGHTS
) -> float:
    geo = {"yes": weights.geo_yes, "uncertain": weights.geo_uncertain, "no": weights.geo_no}[
        triage.geo_match
    ]
    # Novelty: posts found through several distinct queries are not penalized for being
    # found once; posts surfaced by a single query get the base value only.
    novelty = min(len(post.search_keywords), 3) / 3
    replies = min(math.log1p(post.reply_count) / math.log1p(_REPLY_CAP), 1.0)
    return (
        weights.topic * triage.topic_relevance
        + geo
        + weights.discussion * triage.discussion_poi_score / 4
        + weights.direct * triage.direct_poi_score / 4
        + weights.novelty * novelty
        + weights.reply_count * replies
        - weights.promotion_penalty * triage.promotion_risk / 4
    )


def rank_posts(
    posts: list[ThreadsPost],
    triage: dict[str, PostTriage],
    weights: RankingWeights = _DEFAULT_WEIGHTS,
) -> list[tuple[ThreadsPost, float]]:
    """Return (post, score) sorted best first; reply count only breaks ties."""
    scored = [(post, score_post(post, triage[post.post_id], weights)) for post in posts if post.post_id in triage]
    return sorted(scored, key=lambda item: (item[1], item[0].reply_count), reverse=True)


def select_comment_targets(
    posts: list[ThreadsPost],
    triage: dict[str, PostTriage],
    budget: int,
) -> list[ThreadsPost]:
    """Pick posts for deep comment crawling, ordered by discussion potential.

    Only posts routed to discussion are eligible; reply count is not a gate so a
    quiet question post is still considered.
    """
    from app.tools.threads.triage import ROUTE_SCORE_THRESHOLD, route_post

    eligible = [
        post
        for post in posts
        if post.post_id in triage
        and route_post(triage[post.post_id]) in {"discussion", "both"}
        and triage[post.post_id].discussion_poi_score >= ROUTE_SCORE_THRESHOLD
    ]
    ranked = rank_posts(eligible, triage, COMMENT_WEIGHTS)
    return [post for post, _ in ranked[: max(budget, 0)]]
