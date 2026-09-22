"""Greedy MMR reranking de giam cac paper qua giong nhau trong top ket qua."""

from __future__ import annotations

from typing import Any

import config
from deduplicator import normalize_title


def _tokens(item: dict[str, Any]) -> set[str]:
    paper = item.get("paper") or {}
    text = f"{paper.get('title') or ''} {(paper.get('abstract') or '')[:config.DIVERSITY_TEXT_MAX_CHARS]}"
    return {token for token in normalize_title(text).split() if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def diversify_ranked(
    ranked: list[dict[str, Any]],
    result_limit: int,
    *,
    enabled: bool = True,
) -> list[dict[str, Any]]:
    """Chon top-k bang MMR, van giu recommendation score goc de giai thich."""
    if result_limit <= 0 or not ranked:
        return []

    pool = [dict(item) for item in ranked[:max(config.DIVERSITY_POOL_LIMIT, result_limit)]]
    if not enabled or len(pool) <= 1:
        selected = pool[:result_limit]
        for index, item in enumerate(selected, start=1):
            item["pre_diversity_rank"] = item.get("rank")
            item["diversity_penalty"] = 0.0
            item["diversity_score"] = item.get("recommendation_score", item.get("score", 0.0))
            item["rank"] = index
        return selected

    relevance_max = max(
        (float(item.get("recommendation_score", item.get("score", 0.0))) for item in pool),
        default=1.0,
    ) or 1.0
    token_sets = {item["dedup_key"]: _tokens(item) for item in pool}
    remaining = list(pool)
    selected: list[dict[str, Any]] = []
    diversity_lambda = max(0.0, min(float(config.DIVERSITY_LAMBDA), 1.0))

    while remaining and len(selected) < result_limit:
        best_item = None
        best_mmr = float("-inf")
        best_similarity = 0.0
        for item in remaining:
            relevance = float(item.get("recommendation_score", item.get("score", 0.0))) / relevance_max
            similarity = max(
                (_jaccard(token_sets[item["dedup_key"]], token_sets[chosen["dedup_key"]]) for chosen in selected),
                default=0.0,
            )
            mmr = diversity_lambda * relevance - (1.0 - diversity_lambda) * similarity
            if mmr > best_mmr:
                best_item = item
                best_mmr = mmr
                best_similarity = similarity
        assert best_item is not None
        remaining.remove(best_item)
        best_item["pre_diversity_rank"] = best_item.get("rank")
        best_item["diversity_penalty"] = round(best_similarity, 6)
        best_item["diversity_score"] = round(best_mmr, 6)
        selected.append(best_item)

    for index, item in enumerate(selected, start=1):
        item["rank"] = index
    return selected
