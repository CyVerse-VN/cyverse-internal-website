"""Discovery Mode orchestration helpers used by the Threads pipeline."""

import logging

from app.tools.threads.ai import GroqThreadsAI, ThreadsAI
from app.tools.threads.config import ThreadsConfig
from app.tools.threads.discovery_schemas import (
    DiscoveryQueryPlan,
    PostDiscovery,
    PostTriage,
)
from app.tools.threads.errors import ThreadsError
from app.tools.threads.poi_extractor import POIExtractor
from app.tools.threads.poi_resolver import resolve_poi_mentions
from app.tools.threads.poi_schemas import POICandidate, POIClaim, POIMention
from app.tools.threads.providers.jev_triage import JevTriageProvider, is_jev_configured
from app.tools.threads.query_planner import MAX_QUERY_LENGTH, merge_query_plan
from app.tools.threads.schemas import DiscoverySummary, ThreadsPost, ThreadsRequest
from app.tools.threads.triage import PostTriageProvider, route_post

logger = logging.getLogger(__name__)


async def plan_discovery(
    request: ThreadsRequest, ai: ThreadsAI, config: ThreadsConfig, warnings: list[str]
) -> DiscoveryQueryPlan:
    """Build the search plan. Manual keywords are seeds and are never replaced."""
    max_queries = config.discovery_max_queries
    seeds = request.keywords if request.use_manual_keywords else []
    generated: DiscoveryQueryPlan | None = None
    planner = getattr(ai, "plan_discovery_queries", None)
    if request.query_planning and planner is not None:
        try:
            generated = await planner(request.query, seeds, max_queries)
        except ThreadsError as exc:
            warnings.append(f"Query planning failed ({exc.code}); using seed keywords only.")
            logger.warning("Discovery query planning failed: %s", exc.code)
    plan = merge_query_plan(seeds, generated, max_queries)
    if not plan.queries:
        if len(request.query) > MAX_QUERY_LENGTH:
            raise ThreadsError("KEYWORDS_REQUIRED", "Supply short keywords or enable query planning.")
        plan = merge_query_plan([request.query], generated, max_queries)
    return plan


def select_triage_providers(
    requested: str, groq: PostTriageProvider, warnings: list[str]
) -> tuple[PostTriageProvider, PostTriageProvider | None]:
    """Return (primary, fallback). Jev falls back to Groq while its contract is unverified."""
    if requested == "jev":
        if is_jev_configured():
            return JevTriageProvider(), groq
        warnings.append("Jev triage is unavailable; using Groq triage instead.")
    return groq, None


async def triage_posts(
    query: str,
    posts: list[ThreadsPost],
    primary: PostTriageProvider,
    fallback: PostTriageProvider | None,
    warnings: list[str],
) -> dict[str, PostTriage]:
    """Classify posts; a provider failure leaves posts unclassified, never excluded."""
    for provider in (primary, fallback):
        if provider is None:
            continue
        try:
            return await provider.classify(query, posts)
        except ThreadsError as exc:
            warnings.append(f"Post triage by {provider.name} failed ({exc.code}).")
            logger.warning("Triage provider %s failed: %s", provider.name, exc.code)
    return {}


def apply_triage(posts: list[ThreadsPost], triage: dict[str, PostTriage]) -> None:
    for post in posts:
        item = triage.get(post.post_id)
        previous = post.discovery
        post.discovery = PostDiscovery(
            triage=item,
            route=route_post(item),
            comment_status=previous.comment_status if previous else "not_attempted",
            comment_error=previous.comment_error if previous else None,
        )
        post.filter_selected = post.discovery.route not in {"excluded"}


async def extract_and_resolve_pois(
    posts: list[ThreadsPost],
    ai: ThreadsAI,
    warnings: list[str],
) -> tuple[list[POIMention], list[POICandidate], list[POIClaim]]:
    """Extract grounded POIs from collected candidate posts and resolve canonical entities."""
    if not isinstance(ai, GroqThreadsAI):
        return [], [], []

    extractor = POIExtractor(ai)
    try:
        mentions, claims = await extractor.extract_from_posts(posts)
        candidates = resolve_poi_mentions(mentions, claims)
        return mentions, candidates, claims
    except Exception as exc:  # noqa: BLE001 -- Non-fatal LLM error caught to keep pipeline running
        warnings.append(f"POI extraction encountered an error ({type(exc).__name__}).")
        logger.warning("POI extraction failed: %s", exc)
        return [], [], []


def summarize(
    posts: list[ThreadsPost],
    plan: DiscoveryQueryPlan | None,
    provider_name: str | None,
    selected: int,
    warnings: list[str],
    candidates: list[POICandidate] | None = None,
    mentions: list[POIMention] | None = None,
) -> DiscoverySummary:
    routes = [post.discovery.route if post.discovery else "unclassified" for post in posts]
    statuses = [post.discovery.comment_status if post.discovery else "not_attempted" for post in posts]
    cands = candidates or []
    mens = mentions or []
    return DiscoverySummary(
        plan=plan,
        triage_provider=provider_name,
        direct_posts=sum(route in {"direct", "both"} for route in routes),
        discussion_posts=sum(route in {"discussion", "both"} for route in routes),
        excluded_posts=routes.count("excluded"),
        unclassified_posts=routes.count("unclassified"),
        comment_posts_selected=selected,
        comment_posts_completed=statuses.count("completed"),
        comment_posts_failed=statuses.count("failed"),
        poi_mentions=mens,
        poi_candidates=cands,
        verified_poi_count=sum(1 for c in cands if c.verification_status == "verified"),
        warnings=warnings.copy(),
    )
