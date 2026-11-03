"""Jev AI (TypeSafe System One Decisions API) triage provider."""

import logging
from typing import Literal

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.tools.threads.config import ThreadsConfig, threads_config
from app.tools.threads.discovery_schemas import PostTriage
from app.tools.threads.errors import ThreadsError
from app.tools.threads.schemas import ThreadsPost

logger = logging.getLogger(__name__)

DEFAULT_TYPESAFE_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def is_jev_configured(config: ThreadsConfig = threads_config) -> bool:
    """Check whether a Jev / TypeSafe API key or OpenRouter API key is configured."""
    if config.jev_api_key and config.jev_api_key.get_secret_value().strip():
        return True
    if settings.openrouter_api_key and settings.openrouter_api_key.get_secret_value().strip():
        return True
    return False


def _get_api_key(config: ThreadsConfig) -> str:
    if config.jev_api_key and config.jev_api_key.get_secret_value().strip():
        return config.jev_api_key.get_secret_value().strip()
    if settings.openrouter_api_key and settings.openrouter_api_key.get_secret_value().strip():
        return settings.openrouter_api_key.get_secret_value().strip()
    return ""


class JevTriageProvider:
    name = "jev"

    def __init__(
        self,
        config: ThreadsConfig = threads_config,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._external_client = client

    def _resolve_endpoint_and_model(self, api_key: str) -> tuple[str, str]:
        """Automatically pick TypeSafe direct endpoint vs OpenRouter based on key or config."""
        endpoint = self.config.jev_endpoint
        model = self.config.jev_model

        if api_key.startswith("apikey_"):
            # Native TypeSafe AI key
            endpoint = DEFAULT_TYPESAFE_ENDPOINT
            if model.startswith("typesafe/"):
                model = "jev-latest"
        elif api_key.startswith("sk-or-"):
            # OpenRouter key
            endpoint = "https://openrouter.ai/api/alpha/decisions"
            if not model.startswith("typesafe/"):
                model = f"typesafe/{model}"

        return endpoint, model

    async def _post_decision(
        self, client: httpx.AsyncClient, post: ThreadsPost, query: str, api_key: str
    ) -> PostTriage | None:
        endpoint, model = self._resolve_endpoint_and_model(api_key)

        payload = {
            "model": model,
            "state": f"Post by @{post.username}: {post.text[:1500]}",
            "questions": {
                "geo_match": {
                    "type": "choice",
                    "instructions": f"Does this post discuss places in or near the target location: '{query}'?",
                    "criteria": {
                        "yes": "Explicitly in target location",
                        "no": "Explicitly in an unrelated location",
                        "uncertain": "Location not explicitly mentioned or ambiguous",
                    },
                },
                "topic_relevance": {
                    "type": "noul",
                    "instructions": f"Is this post relevant to discovering places or dining for: '{query}'?",
                },
                "direct_poi_score": {
                    "type": "score",
                    "instructions": "Score 0 to 4 based on whether the post body names specific places or venues.",
                    "criteria": [
                        "No place named",
                        "Vague or generic mention",
                        "Mentions a place category without specific name",
                        "Names a specific venue",
                        "Names a specific venue with address or exact details",
                    ],
                },
                "discussion_poi_score": {
                    "type": "score",
                    "instructions": "Score 0 to 4 based on whether this post is asking for recommendations in replies.",
                    "criteria": [
                        "Not a question or discussion",
                        "Passing mention without invitation",
                        "Mild discussion",
                        "Clear question asking for suggestions",
                        "Dedicated recommendation request",
                    ],
                },
                "promotion_risk": {
                    "type": "score",
                    "instructions": "Score 0 to 4 on advertising, affiliate link, or spam risk.",
                    "criteria": [
                        "Authentic organic post",
                        "Mild promotional tone",
                        "Likely sponsored",
                        "Clear commercial ad",
                        "Obvious spam or affiliate spam",
                    ],
                },
            },
        }

        response = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        answers = data.get("answers", {})

        raw_geo = str(answers.get("geo_match", {}).get("choice", "uncertain")).lower()
        geo: Literal["yes", "no", "uncertain"] = (
            "yes" if raw_geo == "yes" else "no" if raw_geo == "no" else "uncertain"
        )

        noul_val = answers.get("topic_relevance", {}).get("noul")
        if noul_val is None:
            noul_val = answers.get("topic_relevance", {}).get("probability", 0.5)
        topic_relevance = max(0.0, min(1.0, float(noul_val)))

        raw_direct = float(answers.get("direct_poi_score", {}).get("score", 0))
        direct_score = max(0, min(4, int(round(raw_direct))))

        raw_disc = float(answers.get("discussion_poi_score", {}).get("score", 0))
        disc_score = max(0, min(4, int(round(raw_disc))))

        raw_promo = float(answers.get("promotion_risk", {}).get("score", 0))
        promo_score = max(0, min(4, int(round(raw_promo))))

        model_version = str(data.get("model", model))

        return PostTriage(
            geo_match=geo,
            topic_relevance=topic_relevance,
            direct_poi_score=direct_score,
            discussion_poi_score=disc_score,
            promotion_risk=promo_score,
            reasons=[f"jev:{model_version}"],
            provider=self.name,
        )

    async def classify(self, query: str, posts: list[ThreadsPost]) -> dict[str, PostTriage]:
        api_key = _get_api_key(self.config)
        if not api_key:
            logger.warning("Jev API key is not configured, triggering fallback.")
            raise ThreadsError("JEV_UNAVAILABLE", "Jev API key is not configured.", 503)

        results: dict[str, PostTriage] = {}

        async def run_classification(client: httpx.AsyncClient) -> None:
            for post in posts:
                try:
                    triage = await self._post_decision(client, post, query, api_key)
                    if triage is not None:
                        results[post.post_id] = triage
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    logger.warning("Jev request failed for post %s: %s", post.post_id, exc)
                    raise ThreadsError(
                        "JEV_UNAVAILABLE", f"Jev API request failed: {type(exc).__name__}", 502
                    ) from exc
                except (ValueError, KeyError, ValidationError) as exc:
                    logger.warning("Jev response invalid for post %s: %s", post.post_id, exc)

        if self._external_client is not None:
            await run_classification(self._external_client)
        else:
            async with httpx.AsyncClient() as client:
                await run_classification(client)

        return results
