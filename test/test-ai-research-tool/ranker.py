"""Pre-rank deterministic, tách Query Match và Paper Quality, có provenance rõ ràng."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import config
from deduplicator import normalize_title


STOPWORDS = {
    "a", "an", "and", "are", "by", "does", "for", "from", "how", "in", "is", "of",
    "on", "paper", "papers", "the", "to", "using", "with",
}


def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    available = {
        key: max(0.0, min(float(value), 1.0))
        for key, value in values.items()
        if key in weights and isinstance(value, (int, float))
    }
    denominator = sum(max(float(weights[key]), 0.0) for key in available)
    if denominator <= 0:
        return 0.0
    return sum(available[key] * max(float(weights[key]), 0.0) for key in available) / denominator


def _signals(paper: dict[str, Any], source: str) -> dict[str, Any]:
    specific = paper.get("source_specific") or {}
    nested = (specific.get("signals_by_source") or {}).get(source)
    if isinstance(nested, dict):
        return nested
    return specific if paper.get("source") == source else {}


def _expected_query_count(source: str, query_plan: dict[str, Any] | None) -> int:
    if source == "semantic_scholar":
        return max(min(len((query_plan or {}).get("query_variants") or []), config.MAX_QUERY_VARIANTS), 1)
    if source == "openalex":
        return 1 + int(config.OPENALEX_ENABLE_SEMANTIC_SEARCH)
    return 1


def _retrieval_signals(
    group: dict[str, Any], query_plan: dict[str, Any] | None
) -> dict[str, Any]:
    paper = group["paper"]
    hits = (paper.get("source_specific") or {}).get("retrieval_hits") or []
    if not hits:
        hits = [{
            "source": paper.get("source"), "mode": "unknown", "query": "unknown",
            "rank": paper.get("source_rank") or 1,
        }]

    by_source: dict[str, list[dict[str, Any]]] = {}
    seen = set()
    for hit in hits:
        if not isinstance(hit, dict) or not hit.get("source"):
            continue
        identity = (hit.get("source"), hit.get("mode"), hit.get("query"), hit.get("rank"))
        if identity in seen:
            continue
        seen.add(identity)
        by_source.setdefault(str(hit["source"]), []).append(hit)

    source_details: dict[str, dict[str, Any]] = {}
    best_scores: dict[str, float] = {}
    coverage_scores: dict[str, float] = {}
    for source, source_hits in by_source.items():
        ranks = [
            int(hit["rank"]) for hit in source_hits
            if isinstance(hit.get("rank"), int) and int(hit["rank"]) > 0
        ]
        if not ranks:
            continue
        best_rank = min(ranks)
        best_score = (config.RRF_K + 1.0) / (config.RRF_K + best_rank)
        unique_queries = {
            (hit.get("mode"), hit.get("query")) for hit in source_hits
            if hit.get("query") is not None
        }
        expected = _expected_query_count(source, query_plan)
        coverage = min(len(unique_queries) / max(expected, 1), 1.0)
        best_scores[source] = best_score
        coverage_scores[source] = coverage
        source_details[source] = {
            "best_rank": best_rank,
            "rank_score": round(best_score, 6),
            "query_hits": len(unique_queries),
            "expected_queries": expected,
            "query_coverage": round(coverage, 6),
        }

    configured_weights = config.SOURCE_RRF_WEIGHTS
    present_weight = sum(max(float(configured_weights.get(source, 1.0)), 0.0) for source in best_scores)
    source_rrf = (
        sum(best_scores[source] * max(float(configured_weights.get(source, 1.0)), 0.0)
            for source in best_scores) / present_weight
        if present_weight else 0.0
    )
    query_coverage = (
        sum(coverage_scores[source] * max(float(configured_weights.get(source, 1.0)), 0.0)
            for source in coverage_scores) / present_weight
        if present_weight else 0.0
    )
    total_source_weight = sum(max(float(value), 0.0) for value in configured_weights.values()) or 1.0
    agreement_weight = sum(
        max(float(configured_weights.get(source, 0.0)), 0.0) for source in best_scores
    )
    return {
        "source_rrf": source_rrf,
        "query_coverage": query_coverage,
        "source_agreement": min(agreement_weight / total_source_weight, 1.0),
        "source_count": len(best_scores),
        "by_source": source_details,
    }


def _citation_percentile(paper: dict[str, Any]) -> float | None:
    value = _signals(paper, "openalex").get("citation_normalized_percentile")
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float)):
        number = float(value)
        return max(0.0, min(number / 100 if number > 1 else number, 1.0))
    return None


def _fwci_score(paper: dict[str, Any]) -> float | None:
    value = _signals(paper, "openalex").get("fwci")
    if isinstance(value, (int, float)) and value >= 0:
        return float(value) / (float(value) + 1.0)
    return None


def _citation_count(paper: dict[str, Any]) -> int:
    counts = (paper.get("source_specific") or {}).get("citation_counts_by_source") or {}
    for source in ("openalex", "semantic_scholar"):
        if isinstance(counts.get(source), int):
            return max(int(counts[source]), 0)
    return max(int(paper.get("citation_count") or 0), 0)


def _influential_citations(paper: dict[str, Any]) -> int:
    value = _signals(paper, "semantic_scholar").get("influential_citation_count")
    return max(int(value), 0) if isinstance(value, int) else 0


def _recent_citations(paper: dict[str, Any]) -> int:
    current_year = datetime.now(timezone.utc).year
    values = _signals(paper, "openalex").get("citations_by_year") or []
    return sum(
        int(item.get("cited_by_count", 0)) for item in values
        if isinstance(item, dict)
        and isinstance(item.get("year"), int)
        and current_year - config.RECENT_CITATION_WINDOW_YEARS + 1 <= item["year"] <= current_year
        and isinstance(item.get("cited_by_count"), int)
    )


def _publication_score(paper: dict[str, Any], profile: str) -> float:
    types = {str(value).casefold() for value in paper.get("publication_types") or []}
    if profile == "evidence_review" and "review" in types:
        return 1.0
    scores = [config.PUBLICATION_TYPE_SCORES.get(value) for value in types]
    values = [float(value) for value in scores if isinstance(value, (int, float))]
    return max(values, default=float(config.PUBLICATION_TYPE_SCORES["unknown"]))


def _metadata_completeness(paper: dict[str, Any]) -> float:
    fields = config.METADATA_COMPLETENESS_FIELDS
    return sum(bool(paper.get(field)) for field in fields) / len(fields) if fields else 1.0


def _text_match_signals(
    paper: dict[str, Any], query_plan: dict[str, Any] | None
) -> dict[str, float]:
    if not query_plan:
        return {
            "text_match": 0.0,
            "concept_coverage": 0.0,
            "required_concept_coverage": 1.0,
            "title_coverage": 0.0,
            "abstract_coverage": 0.0,
        }
    question_tokens = {
        token for token in normalize_title(query_plan.get("english_question")).split()
        if len(token) > 2 and token not in STOPWORDS
    }
    title = normalize_title(paper.get("title"))
    abstract = normalize_title(paper.get("abstract"))
    denominator = max(len(question_tokens), 1)
    title_coverage = len(question_tokens.intersection(title.split())) / denominator
    abstract_coverage = len(question_tokens.intersection(abstract.split())) / denominator

    matched_weight = 0.0
    total_weight = 0.0
    required_matched = 0
    required_total = 0
    combined_text = f"{title} {abstract}"
    for group in query_plan.get("concept_groups") or []:
        terms = [
            normalized for term in [group.get("concept"), *(group.get("synonyms") or [])]
            if term and (normalized := normalize_title(str(term)))
        ]
        required = bool(group.get("required", True))
        weight = 1.0 if required else 0.35
        total_weight += weight
        matched = any(term in combined_text for term in terms)
        if required:
            required_total += 1
            required_matched += int(matched)
        if matched:
            matched_weight += weight
    concept_coverage = matched_weight / max(total_weight, 1.0)
    required_concept_coverage = (
        required_matched / required_total if required_total else 1.0
    )
    text_match = _weighted(
        {
            "concept_coverage": concept_coverage,
            "title_coverage": title_coverage,
            "abstract_coverage": abstract_coverage,
        },
        config.TEXT_MATCH_WEIGHTS,
    )
    return {
        "text_match": text_match,
        "concept_coverage": concept_coverage,
        "required_concept_coverage": required_concept_coverage,
        "title_coverage": title_coverage,
        "abstract_coverage": abstract_coverage,
    }


def _text_match(paper: dict[str, Any], query_plan: dict[str, Any] | None) -> float:
    """Backward-compatible scalar text score."""
    return _text_match_signals(paper, query_plan)["text_match"]


def rank_papers(
    groups: list[dict[str, Any]],
    profile: str,
    query_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Tạo deterministic pre-rank và score breakdown có thể giải thích."""
    if not groups:
        return []
    profile = profile if profile in config.FINAL_SCORE_WEIGHTS else "balanced"
    citations = [_citation_count(group["paper"]) for group in groups]
    influential = [_influential_citations(group["paper"]) for group in groups]
    velocities = [_recent_citations(group["paper"]) for group in groups]
    max_log_citations = max((math.log1p(value) for value in citations), default=1.0) or 1.0
    max_log_influential = max((math.log1p(value) for value in influential), default=1.0) or 1.0
    max_log_velocity = max((math.log1p(value) for value in velocities), default=1.0) or 1.0
    current_year = datetime.now(timezone.utc).year

    ranked = []
    for group, citation_value, influential_value, velocity_value in zip(
        groups, citations, influential, velocities
    ):
        paper = group["paper"]
        retrieval = _retrieval_signals(group, query_plan)
        text_signals = _text_match_signals(paper, query_plan)
        text_match = text_signals["text_match"]
        query_components = {
            "source_rrf": retrieval["source_rrf"],
            "text_match": text_match,
            "query_coverage": retrieval["query_coverage"],
        }
        query_match = _weighted(query_components, config.QUERY_MATCH_WEIGHTS)

        citation_score = math.log1p(citation_value) / max_log_citations
        influential_score = math.log1p(influential_value) / max_log_influential
        impact_components = {
            "citation_count": citation_score,
            "influential_citations": influential_score,
        }
        if (value := _citation_percentile(paper)) is not None:
            impact_components["citation_percentile"] = value
        if (value := _fwci_score(paper)) is not None:
            impact_components["fwci"] = value
        impact = _weighted(impact_components, config.IMPACT_SIGNAL_WEIGHTS)

        citation_velocity = math.log1p(velocity_value) / max_log_velocity
        age = max(current_year - int(paper.get("year") or current_year), 0)
        half_life = max(float(config.RECENCY_HALF_LIFE_YEARS.get(profile, 5.0)), 0.1)
        recency = math.exp(-math.log(2) * age / half_life)
        publication = _publication_score(paper, profile)
        direct_pdf = bool(paper.get("pdf_url")) and "/reader/" not in str(paper.get("pdf_url"))
        access = (
            float(config.ACCESS_SCORES["direct_pdf"]) if direct_pdf
            else float(config.ACCESS_SCORES["open_access"]) if paper.get("is_open_access")
            else float(config.ACCESS_SCORES["metadata_only"])
        )
        quality_components = {
            "impact": impact,
            "citation_velocity": citation_velocity,
            "recency": recency,
            "publication": publication,
            "access": access,
            "source_agreement": retrieval["source_agreement"],
            "metadata_completeness": _metadata_completeness(paper),
        }
        paper_quality = _weighted(quality_components, config.PAPER_QUALITY_WEIGHTS[profile])
        deterministic_score = _weighted(
            {"query_match": query_match, "paper_quality": paper_quality},
            config.FINAL_SCORE_WEIGHTS[profile],
        )
        if (paper.get("source_specific") or {}).get("is_retracted") is True:
            deterministic_score = 0.0

        breakdown = {
            "relevance": query_match,
            "query_match": query_match,
            "paper_quality": paper_quality,
            **query_components,
            "concept_coverage": text_signals["concept_coverage"],
            "required_concept_coverage": text_signals["required_concept_coverage"],
            "title_coverage": text_signals["title_coverage"],
            "abstract_coverage": text_signals["abstract_coverage"],
            **quality_components,
            "citation_count_signal": citation_score,
            "citation_percentile": impact_components.get("citation_percentile", 0.0),
            "fwci": impact_components.get("fwci", 0.0),
            "influential_citations": influential_score,
        }
        ranked.append({
            "dedup_key": group["dedup_key"],
            "score": round(deterministic_score, 6),
            "deterministic_score": round(deterministic_score, 6),
            "query_match_score": round(query_match, 6),
            "paper_quality_score": round(paper_quality, 6),
            "score_breakdown": {key: round(float(value), 6) for key, value in breakdown.items()},
            "retrieval_by_source": retrieval["by_source"],
            "paper": paper,
        })

    ranked.sort(key=lambda item: item["deterministic_score"], reverse=True)
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
        item["pre_rank"] = index
    return ranked
