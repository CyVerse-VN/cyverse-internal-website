import math
from dataclasses import dataclass

from app.tools.threads.schemas import ThreadsPost


@dataclass(frozen=True)
class RankingWeights:
    topic: float = 4.0
    geography: float = 2.0
    discussion: float = 4.0
    direct: float = 1.0
    promotion: float = 1.0
    novelty: float = 0.5
    replies: float = 0.1


DEFAULT_WEIGHTS = RankingWeights()


def rank_comment_targets(posts: list[ThreadsPost], weights: RankingWeights = DEFAULT_WEIGHTS) -> list[ThreadsPost]:
    remaining = [post for post in posts if post.triage is not None and post.triage.geo_match != "no"]
    ranked: list[ThreadsPost] = []
    used_queries: set[str] = set()
    while remaining:
        def score(post: ThreadsPost) -> float:
            triage = post.triage
            assert triage is not None
            return (weights.topic * triage.topic_relevance
                    + weights.geography * {"yes": 1, "uncertain": 0.5, "no": 0}[triage.geo_match]
                    + weights.discussion * triage.discussion_poi_score / 4
                    + weights.direct * triage.direct_poi_score / 4
                    - weights.promotion * triage.promotion_risk / 4
                    + weights.novelty * bool(set(post.search_keywords) - used_queries)
                    + weights.replies * min(math.log1p(post.reply_count), 5) / 5)
        best = max(remaining, key=score)
        remaining.remove(best)
        ranked.append(best)
        used_queries.update(best.search_keywords)
    return ranked
