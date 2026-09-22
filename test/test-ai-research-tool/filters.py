"""Các filter deterministic áp dụng sau khi đã merge paper."""

from __future__ import annotations

from typing import Any

import config


TYPE_ALIASES = {
    "journalarticle": "article",
    "journal-article": "article",
    "proceedings-article": "conference",
    "conferencepaper": "conference",
    "conference": "conference",
    "review": "review",
    "preprint": "preprint",
    "article": "article",
    "book": "book",
    "booksection": "book",
    "dataset": "dataset",
}


def _paper_language(paper: dict[str, Any]) -> str | None:
    specific = paper.get("source_specific") or {}
    if language := specific.get("language"):
        return str(language).lower()
    for signals in (specific.get("signals_by_source") or {}).values():
        if isinstance(signals, dict) and signals.get("language"):
            return str(signals["language"]).lower()
    return None


def filter_papers(
    groups: list[dict[str, Any]],
    filters: dict[str, Any],
    *,
    require_abstract: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    kept = []
    rejected = []
    requested_types = set(filters.get("publication_types") or [])
    requested_languages = {str(value).lower() for value in filters.get("languages") or []}

    for group in groups:
        paper = group["paper"]
        reason = None
        if (paper.get("source_specific") or {}).get("is_retracted") is True:
            reason = "retracted"
        elif require_abstract and not paper.get("abstract"):
            reason = "missing_abstract"
        elif filters.get("year_from") and isinstance(paper.get("year"), int) \
                and paper["year"] < filters["year_from"]:
            reason = "before_year_from"
        elif filters.get("year_to") and isinstance(paper.get("year"), int) \
                and paper["year"] > filters["year_to"]:
            reason = "after_year_to"
        elif filters.get("open_access_only") and paper.get("is_open_access") is not True:
            reason = "not_open_access"
        elif requested_types:
            paper_types = {
                TYPE_ALIASES.get(str(value).casefold(), str(value).casefold())
                for value in paper.get("publication_types") or []
            }
            if paper_types and not paper_types.intersection(requested_types):
                reason = "publication_type_mismatch"
        if not reason and requested_languages:
            language = _paper_language(paper)
            if language and language not in requested_languages:
                reason = "language_mismatch"

        if reason:
            rejected.append({"dedup_key": group["dedup_key"], "reason": reason})
        else:
            kept.append(group)
    return kept, rejected


def filter_ranked_by_relevance(
    ranked: list[dict[str, Any]],
    *,
    enabled: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Reject clearly off-topic papers after deterministic and AI reranking."""
    if not enabled:
        return ranked, []

    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for item in ranked:
        breakdown = item.get("score_breakdown") or {}
        text_match = float(breakdown.get("text_match") or 0.0)
        ai = item.get("ai_rerank") or {}
        ai_relevance = float(ai.get("relevance") or 0.0) if ai else None
        ai_confidence = float(ai.get("confidence") or 0.0) if ai else 0.0
        required_coverage = float(
            breakdown.get("required_concept_coverage", 1.0)
        )

        reason = None
        ai_overrides_concept_gap = (
            ai_relevance is not None
            and ai_relevance >= float(config.AI_REQUIRED_CONCEPT_OVERRIDE_SCORE)
            and ai_confidence >= float(config.AI_RELEVANCE_GATE_MIN_CONFIDENCE)
        )
        if (
            required_coverage < float(config.MIN_REQUIRED_CONCEPT_COVERAGE)
            and not ai_overrides_concept_gap
        ):
            reason = "missing_required_concept"
        elif (
            ai_relevance is not None
            and ai_confidence >= float(config.AI_RELEVANCE_GATE_MIN_CONFIDENCE)
            and ai_relevance < float(config.MIN_AI_RELEVANCE_SCORE)
        ):
            reason = "ai_high_confidence_irrelevant"
        elif (
            text_match < float(config.MIN_TEXT_MATCH_SCORE)
            and (ai_relevance is None or ai_relevance < float(config.MIN_AI_RELEVANCE_SCORE))
        ):
            reason = "insufficient_relevance_evidence"

        if reason:
            rejected.append({"dedup_key": str(item["dedup_key"]), "reason": reason})
        else:
            kept.append(item)
    return kept, rejected
