import unicodedata

from app.tools.threads.schemas import DiscoveryQuery, DiscoveryQueryPlan


def combine_queries(plan: DiscoveryQueryPlan, seeds: list[str], limit: int) -> DiscoveryQueryPlan:
    """Keep manual seeds first and deduplicate without changing the submitted text."""
    manual = [DiscoveryQuery(text=seed, angle="topic_specific", target_content="both", origin="manual") for seed in seeds]
    queries: list[DiscoveryQuery] = []
    seen: set[str] = set()
    for item in [*manual, *plan.queries]:
        text = " ".join(item.text.split())
        key = unicodedata.normalize("NFKC", text).casefold()
        if key not in seen:
            seen.add(key)
            queries.append(item.model_copy(update={"text": text, "origin": "manual" if item in manual else "generated"}))
        if len(queries) >= limit:
            break
    return plan.model_copy(update={"queries": queries})
