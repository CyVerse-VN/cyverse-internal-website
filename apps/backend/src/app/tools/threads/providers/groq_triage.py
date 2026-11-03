"""Groq baseline provider for post triage."""

import logging

from pydantic import BaseModel, Field, ValidationError

from app.tools.threads.ai import GroqThreadsAI
from app.tools.threads.discovery_schemas import PostTriage
from app.tools.threads.schemas import ThreadsPost

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
_POST_TEXT_LIMIT = 1500

_INSTRUCTION = (
    "You triage Threads posts for a place-discovery task. For each post return an item with "
    "post_id, geo_match (yes/no/uncertain; use uncertain when the location is not stated), "
    "topic_relevance (0 to 1), direct_poi_score (0-4: the post body names specific places), "
    "discussion_poi_score (0-4: the post asks for or invites place recommendations, so the "
    "comments may name places), promotion_risk (0-4), and reasons (short strings). "
    "A question post such as asking where to go this weekend has low direct_poi_score and "
    "high discussion_poi_score; do not mark it irrelevant because it names no place. "
    "Return {\"items\": [...]} with one item per supplied post_id."
)


class _TriageResponse(BaseModel):
    items: list[dict[str, object]] = Field(default_factory=list, max_length=BATCH_SIZE)


class GroqTriageProvider:
    name = "groq"

    def __init__(self, ai: GroqThreadsAI) -> None:
        self.ai = ai

    async def classify(self, query: str, posts: list[ThreadsPost]) -> dict[str, PostTriage]:
        results: dict[str, PostTriage] = {}
        for start in range(0, len(posts), BATCH_SIZE):
            batch = posts[start : start + BATCH_SIZE]
            known = {post.post_id for post in batch}
            response = await self.ai._complete(
                _INSTRUCTION,
                {
                    "query": query,
                    "posts": [
                        {"post_id": post.post_id, "text": post.text[:_POST_TEXT_LIMIT]}
                        for post in batch
                    ],
                },
                _TriageResponse,
            )
            for item in response.items:
                post_id = item.get("post_id")
                if not isinstance(post_id, str) or post_id not in known:
                    continue
                payload = {key: value for key, value in item.items() if key != "post_id"}
                payload["provider"] = self.name
                try:
                    results[post_id] = PostTriage.model_validate(payload)
                except ValidationError:
                    # Invalid scores are rejected; the post stays unclassified, not excluded.
                    logger.warning("Rejected invalid triage item for post %s", post_id)
        return results
