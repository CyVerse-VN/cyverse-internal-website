"""Merge manual seed keywords with generated discovery queries."""

import re
import unicodedata

from app.tools.threads.discovery_schemas import DiscoveryQuery, DiscoveryQueryPlan

MAX_QUERY_LENGTH = 100
_NEGATION_PATTERN = re.compile(r"(^|\s)(-\S|không\s|khong\s|not\s)", re.IGNORECASE)


def normalize_query_key(text: str) -> str:
    """Comparison key only. Diacritics are kept so unaccented queries stay distinct."""
    folded = unicodedata.normalize("NFC", text).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", folded).split())


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def merge_query_plan(
    manual_keywords: list[str],
    generated: DiscoveryQueryPlan | None,
    max_queries: int,
) -> DiscoveryQueryPlan:
    """Manual seeds always come first and are never replaced by generated queries.

    Generated queries that are empty, too long, negated, or duplicates of an
    earlier query (by normalized key) are dropped. Manual seeds are never
    dropped by the negation filter because the user chose them explicitly.
    """
    seen: set[str] = set()
    queries: list[DiscoveryQuery] = []

    for keyword in manual_keywords:
        text = _clean(keyword)
        key = normalize_query_key(text)
        if not text or len(text) > MAX_QUERY_LENGTH or key in seen:
            continue
        seen.add(key)
        queries.append(
            DiscoveryQuery(
                text=text, angle="topic_specific", target_content="both", origin="manual"
            )
        )

    plan = generated or DiscoveryQueryPlan()
    for query in plan.queries:
        if len(queries) >= max_queries:
            break
        text = _clean(query.text)
        key = normalize_query_key(text)
        if not text or len(text) > MAX_QUERY_LENGTH or key in seen:
            continue
        if _NEGATION_PATTERN.search(text):
            continue
        seen.add(key)
        queries.append(query.model_copy(update={"text": text, "origin": "generated"}))

    # Manual seeds can exceed the cap on their own; the cap still bounds total searches.
    return plan.model_copy(update={"queries": queries[:max_queries]})
