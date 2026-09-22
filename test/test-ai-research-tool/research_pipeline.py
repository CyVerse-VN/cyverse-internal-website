#!/usr/bin/env python3
"""Configurable research pipeline for Semantic Scholar, arXiv and OpenAlex."""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from academic_rate_limiter import rate_limit_snapshot
from ai_reranker import apply_ai_rerank, rerank_with_ai
from arxiv_test import search_expression as search_arxiv
from common import SourceError, configure_utf8_console, save_json
from deduplicator import deduplicate_papers
from diversifier import diversify_ranked
from filters import filter_papers, filter_ranked_by_relevance
from openalex_test import search_with_options as search_openalex
from paper_assessor import assess_ranked_papers
from pipeline_cache import load_cached, save_cached
from query_builders import compile_source_queries
from query_planner import create_query_plan
from ranker import rank_papers
from semantic_scholar_test import search_with_options as search_semantic_scholar


def _default_request_limits() -> dict[str, int]:
    return {
        "semantic_scholar": config.SEMANTIC_SCHOLAR_RESULTS_PER_QUERY,
        "arxiv": config.ARXIV_RESULTS_PER_QUERY,
        "openalex_lexical": config.OPENALEX_LEXICAL_RESULTS_PER_QUERY,
        "openalex_semantic": config.OPENALEX_SEMANTIC_RESULTS_PER_QUERY,
    }


def _resolve_search_settings(
    search_depth: str,
    request_limits: dict[str, int] | None,
    source_caps: dict[str, int] | None,
    max_candidates: int | None,
    pre_rank_limit: int | None,
    ai_rerank_limit: int | None,
    ai_enrich_limit: int | None,
    result_limit: int | None,
) -> dict[str, Any]:
    if search_depth not in config.SEARCH_DEPTH_PRESETS:
        raise ValueError(f"Unknown search depth: {search_depth}")
    preset = config.SEARCH_DEPTH_PRESETS[search_depth]
    limits = dict(preset.get("request_limits") or _default_request_limits())
    limits.update(request_limits or {})
    caps = dict(preset.get("source_caps") or config.SOURCE_MAX_CANDIDATES)
    caps.update(source_caps or {})
    settings = {
        "search_depth": search_depth,
        "request_limits": limits,
        "source_caps": caps,
        "max_candidates": max_candidates or int(preset["max_candidates"]),
        "pre_rank_limit": pre_rank_limit or int(preset["pre_rank_limit"]),
        "ai_rerank_limit": ai_rerank_limit or int(preset["ai_rerank_limit"]),
        "ai_enrich_limit": ai_enrich_limit or int(preset["ai_enrich_limit"]),
        "result_limit": result_limit or int(preset["result_limit"]),
    }
    if settings["result_limit"] > settings["pre_rank_limit"]:
        raise ValueError("result_limit cannot exceed pre_rank_limit")
    if settings["ai_rerank_limit"] > settings["pre_rank_limit"]:
        raise ValueError("ai_rerank_limit cannot exceed pre_rank_limit")
    return settings


def _limit_for_spec(source: str, spec: dict[str, Any], limits: dict[str, int]) -> int:
    if source == "openalex":
        key = "openalex_semantic" if spec.get("mode") == "semantic" else "openalex_lexical"
        limit = limits[key]
        return min(limit, 50) if spec.get("mode") == "semantic" else limit
    return limits[source]


def _candidate_identity(paper: dict[str, Any]) -> str:
    return str(
        paper.get("source_id") or paper.get("doi") or paper.get("arxiv_id")
        or paper.get("title") or id(paper)
    ).casefold()


def _retrieve_source(
    source: str,
    specs: list[dict[str, Any]],
    request_limits: dict[str, int],
    source_cap: int,
    timeout: float,
    use_cache: bool,
    adaptive_retrieval: bool,
) -> dict[str, Any]:
    papers: list[dict[str, Any]] = []
    requests = []
    errors = []
    request_cost = 0.0
    unique_candidates: set[str] = set()
    target_count = max(
        1, math.ceil(source_cap * float(config.ADAPTIVE_TARGET_SOURCE_CAP_RATIO))
    )
    minimum_requests = max(int(config.ADAPTIVE_MIN_REQUESTS_BY_SOURCE.get(source, 1)), 1)
    last_marginal_ratio: float | None = None
    stop_reason = None
    for index, spec in enumerate(specs):
        if adaptive_retrieval and index >= minimum_requests:
            if len(unique_candidates) >= target_count:
                stop_reason = "source_target_reached"
            elif (
                last_marginal_ratio is not None
                and last_marginal_ratio < float(config.ADAPTIVE_MIN_MARGINAL_UNIQUE_RATIO)
            ):
                stop_reason = "low_marginal_unique_yield"
            if stop_reason:
                for skipped in specs[index:]:
                    requests.append({
                        "mode": skipped.get("mode"), "query": skipped.get("query"),
                        "ok": None, "skipped": True, "skip_reason": stop_reason,
                        "paper_count": 0,
                    })
                break
        started = time.perf_counter()
        effective_limit = _limit_for_spec(source, spec, request_limits)
        try:
            result = load_cached(source, spec, effective_limit) if use_cache else None
            cached = result is not None
            if result is None:
                if source == "semantic_scholar":
                    result = search_semantic_scholar(
                        spec["query"], effective_limit, timeout, filters=spec.get("filters")
                    )
                elif source == "arxiv":
                    result = search_arxiv(spec["query"], effective_limit, timeout)
                elif source == "openalex":
                    result = search_openalex(
                        spec["query"], effective_limit, timeout,
                        filter_query=spec.get("filter"),
                        semantic=spec.get("mode") == "semantic",
                    )
                else:
                    raise ValueError(f"Unsupported source: {source}")
                if use_cache:
                    save_cached(source, spec, effective_limit, result)

            fetched = result.get("papers") or []
            before_unique = len(unique_candidates)
            for paper in fetched:
                value = copy.deepcopy(paper)
                value.setdefault("source_specific", {})["retrieval"] = {
                    "source": source,
                    "mode": spec.get("mode"),
                    "query": spec.get("query"),
                    "query_index": index,
                    "rank": paper.get("source_rank"),
                }
                papers.append(value)
                unique_candidates.add(_candidate_identity(value))
            new_unique = len(unique_candidates) - before_unique
            last_marginal_ratio = new_unique / max(len(fetched), 1)
            cost = result.get("request_cost_usd")
            if isinstance(cost, (int, float)):
                request_cost += float(cost)
            requests.append({
                "mode": spec.get("mode"),
                "query": spec.get("query"),
                "ok": True,
                "cached": cached,
                "requested_limit": request_limits.get(source, effective_limit),
                "effective_limit": effective_limit,
                "paper_count": len(fetched),
                "new_unique_count": new_unique,
                "marginal_unique_ratio": round(last_marginal_ratio, 6),
                "total_available": result.get("total_available"),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            })
        except (SourceError, ValueError) as exc:
            error = {
                "mode": spec.get("mode"),
                "query": spec.get("query"),
                "error": str(exc),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }
            errors.append(error)
            requests.append({**error, "ok": False, "paper_count": 0})

    return {
        "source": source,
        "raw_paper_count": len(papers),
        "papers": papers[:source_cap],
        "source_cap": source_cap,
        "requests": requests,
        "errors": errors,
        "request_cost_usd": round(request_cost, 6) if request_cost else None,
        "adaptive": {
            "enabled": adaptive_retrieval,
            "minimum_requests": minimum_requests,
            "target_unique_candidates": target_count,
            "unique_candidates": len(unique_candidates),
            "stopped_early": stop_reason is not None,
            "stop_reason": stop_reason,
        },
    }


def _round_robin(source_results: dict[str, dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    buckets = [source_results[name]["papers"] for name in sorted(source_results)]
    result = []
    index = 0
    while len(result) < maximum and any(index < len(bucket) for bucket in buckets):
        for bucket in buckets:
            if index < len(bucket) and len(result) < maximum:
                result.append(bucket[index])
        index += 1
    return result


def _elapsed(stage_started: float) -> float:
    return round(time.perf_counter() - stage_started, 3)


def _ranking_config_snapshot(profile: str) -> dict[str, Any]:
    """Record the exact knobs used so a ranking run is reproducible."""
    return {
        "profile": profile,
        "rrf_k": config.RRF_K,
        "source_rrf_weights": config.SOURCE_RRF_WEIGHTS,
        "query_match_weights": config.QUERY_MATCH_WEIGHTS,
        "text_match_weights": config.TEXT_MATCH_WEIGHTS,
        "final_score_weights": config.FINAL_SCORE_WEIGHTS.get(profile),
        "paper_quality_weights": config.PAPER_QUALITY_WEIGHTS.get(profile),
        "impact_signal_weights": config.IMPACT_SIGNAL_WEIGHTS,
        "recent_citation_window_years": config.RECENT_CITATION_WINDOW_YEARS,
        "recency_half_life_years": config.RECENCY_HALF_LIFE_YEARS.get(profile),
        "publication_type_scores": config.PUBLICATION_TYPE_SCORES,
        "access_scores": config.ACCESS_SCORES,
        "metadata_completeness_fields": config.METADATA_COMPLETENESS_FIELDS,
        "ai_rerank_weight": config.AI_RERANK_WEIGHT,
        "ai_rerank_min_confidence": config.AI_RERANK_MIN_CONFIDENCE,
        "ai_rerank_cross_model_penalty": config.AI_RERANK_CROSS_MODEL_PENALTY,
        "ai_rerank_signal_weights": config.AI_RERANK_SIGNAL_WEIGHTS,
        "relevance_gate": {
            "enabled": config.ENABLE_RELEVANCE_GATE,
            "min_text_match_score": config.MIN_TEXT_MATCH_SCORE,
            "min_ai_relevance_score": config.MIN_AI_RELEVANCE_SCORE,
            "ai_min_confidence": config.AI_RELEVANCE_GATE_MIN_CONFIDENCE,
            "min_required_concept_coverage": config.MIN_REQUIRED_CONCEPT_COVERAGE,
            "ai_required_concept_override_score": config.AI_REQUIRED_CONCEPT_OVERRIDE_SCORE,
        },
        "diversity_lambda": config.DIVERSITY_LAMBDA,
    }


def _ranked_ids(items: list[dict[str, Any]]) -> list[str]:
    return [str(item["dedup_key"]) for item in items]


def _result_assessment(
    item: dict[str, Any], paper_analysis: dict[str, Any] | None
) -> dict[str, Any]:
    paper_analysis = dict(paper_analysis) if paper_analysis else None
    assessor_why_read = paper_analysis.pop("why_read", None) if paper_analysis else None
    ai = item.get("ai_rerank") or {}
    search_analysis = None
    if ai:
        search_analysis = {
            "source": "ai_reranker",
            "relevance": ai.get("relevance"),
            "intent_match": ai.get("intent_match"),
            "method_match": ai.get("method_match"),
            "read_priority": ai.get("read_priority"),
            "matched_concepts": ai.get("matched_concepts") or [],
            "why_read": ai.get("reason"),
            "confidence": ai.get("confidence"),
            "evidence_scope": "abstract",
        }
    else:
        relevance = float(item.get("query_match_score") or 0.0)
        priority = "high" if relevance >= 0.70 else "medium" if relevance >= 0.45 else "low"
        search_analysis = {
            "source": "deterministic_fallback",
            "relevance": round(relevance, 6),
            "intent_match": None,
            "method_match": None,
            "read_priority": priority,
            "matched_concepts": [],
            "why_read": (
                "Paper được chọn từ thứ hạng tổng hợp nguồn và mức khớp khái niệm trong tiêu đề/tóm tắt; "
                "nên kiểm tra abstract trước khi sử dụng kết luận."
            ),
            "confidence": round(relevance, 6),
            "evidence_scope": "abstract",
        }
    if assessor_why_read:
        search_analysis["source"] = "ai_final_assessor"
        search_analysis["why_read"] = assessor_why_read
    return {
        "paper_analysis": paper_analysis,
        "search_analysis": search_analysis,
    }


def _llm_usage_current_run(
    planner: dict[str, Any], reranker: dict[str, Any], assessor: dict[str, Any]
) -> dict[str, float | int]:
    rows: list[dict[str, Any]] = []
    if not planner.get("cached") and isinstance(planner.get("usage"), dict):
        rows.append(planner["usage"])
    for usage in reranker.get("usage_by_batch") or []:
        if isinstance(usage, dict) and not usage.get("cached"):
            rows.append(usage)
    for usage in assessor.get("usage_by_batch") or []:
        if isinstance(usage, dict) and not usage.get("cached"):
            rows.append(usage)
    keys = ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
    return {
        key: round(sum(float(row.get(key) or 0) for row in rows), 8)
        for key in keys
    }


def run_pipeline(
    prompt: str,
    *,
    search_depth: str = config.DEFAULT_SEARCH_DEPTH,
    per_query: int | None = None,
    request_limits: dict[str, int] | None = None,
    source_caps: dict[str, int] | None = None,
    max_candidates: int | None = None,
    pre_rank_limit: int | None = None,
    ai_rerank_limit: int | None = None,
    ai_enrich_limit: int | None = None,
    result_limit: int | None = None,
    timeout: float = config.DEFAULT_TIMEOUT_SECONDS,
    use_ai_planner: bool = True,
    use_ai_reranker: bool = True,
    use_ai_assessor: bool = True,
    use_diversity: bool = config.ENABLE_DIVERSITY_RERANK,
    adaptive_retrieval: bool = config.ENABLE_ADAPTIVE_RETRIEVAL,
    require_abstract: bool = config.REQUIRE_ABSTRACT_BY_DEFAULT,
    use_cache: bool = True,
    include_source_records: bool = config.INCLUDE_SOURCE_RECORDS_IN_OUTPUT,
    include_stage_rankings: bool = config.INCLUDE_STAGE_RANKINGS_IN_OUTPUT,
    year_from_override: int | None = None,
    year_to_override: int | None = None,
    ranking_profile_override: str | None = None,
) -> dict[str, Any]:
    pipeline_started = time.perf_counter()
    timings: dict[str, float] = {}
    settings = _resolve_search_settings(
        search_depth, request_limits, source_caps, max_candidates, pre_rank_limit,
        ai_rerank_limit, ai_enrich_limit, result_limit,
    )
    limits = settings["request_limits"]
    if per_query is not None:  # Backward-compatible global override.
        limits = {key: per_query for key in limits}
    caps = settings["source_caps"]
    max_candidates = settings["max_candidates"]
    pre_rank_limit = settings["pre_rank_limit"]
    ai_rerank_limit = settings["ai_rerank_limit"]
    ai_enrich_limit = settings["ai_enrich_limit"]
    result_limit = settings["result_limit"]

    stage = time.perf_counter()
    plan, planner_meta = create_query_plan(prompt, use_ai=use_ai_planner)
    if year_from_override is not None:
        plan["filters"]["year_from"] = year_from_override
    if year_to_override is not None:
        plan["filters"]["year_to"] = year_to_override
    if ranking_profile_override is not None:
        plan["ranking_profile"] = ranking_profile_override
        if ranking_profile_override == "latest":
            plan["intent"] = "latest"
    source_queries = compile_source_queries(plan)
    timings["query_planning"] = _elapsed(stage)

    stage = time.perf_counter()
    source_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _retrieve_source, source, specs, limits, caps[source], timeout, use_cache,
                adaptive_retrieval,
            ): source
            for source, specs in source_queries.items()
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                source_results[source] = future.result()
            except Exception as exc:
                source_results[source] = {
                    "source": source, "raw_paper_count": 0, "papers": [],
                    "source_cap": caps[source], "requests": [],
                    "errors": [{"error": f"Unexpected error: {exc}"}], "request_cost_usd": None,
                    "adaptive": {"enabled": adaptive_retrieval, "stopped_early": False},
                }
    timings["retrieval"] = _elapsed(stage)

    candidates = _round_robin(source_results, max_candidates)
    stage = time.perf_counter()
    groups = deduplicate_papers(candidates)
    timings["deduplication"] = _elapsed(stage)

    stage = time.perf_counter()
    kept, rejected = filter_papers(groups, plan["filters"], require_abstract=require_abstract)
    timings["filtering"] = _elapsed(stage)

    stage = time.perf_counter()
    deterministic_ranked = rank_papers(kept, plan["ranking_profile"], plan)
    pre_ranked = deterministic_ranked[:pre_rank_limit]
    timings["deterministic_ranking"] = _elapsed(stage)

    stage = time.perf_counter()
    ai_scores, reranker_meta = rerank_with_ai(
        plan["english_question"], plan, pre_ranked,
        use_ai=use_ai_reranker, limit=ai_rerank_limit,
    )
    reranked = apply_ai_rerank(pre_ranked, ai_scores, plan["ranking_profile"])
    timings["ai_reranking"] = _elapsed(stage)

    stage = time.perf_counter()
    relevance_eligible, relevance_rejected = filter_ranked_by_relevance(
        reranked, enabled=config.ENABLE_RELEVANCE_GATE
    )
    timings["relevance_gate"] = _elapsed(stage)

    stage = time.perf_counter()
    diversified = diversify_ranked(relevance_eligible, result_limit, enabled=use_diversity)
    timings["diversity_ranking"] = _elapsed(stage)

    stage = time.perf_counter()
    assessments, assessor_meta = assess_ranked_papers(
        plan["english_question"], diversified,
        use_ai=use_ai_assessor, limit=ai_enrich_limit,
    )
    output_papers = [
        {
            **item,
            "assessment": _result_assessment(item, assessments.get(item["dedup_key"])),
        }
        for item in diversified
    ]
    timings["ai_enrichment"] = _elapsed(stage)

    source_summary = {
        source: {
            "raw_paper_count": result["raw_paper_count"],
            "candidate_count": len(result["papers"]),
            "source_cap": result["source_cap"],
            "requests": result["requests"],
            "errors": result["errors"],
            "request_cost_usd": result["request_cost_usd"],
            "adaptive": result["adaptive"],
        }
        for source, result in source_results.items()
    }
    failed_sources = sum(
        bool(value["errors"]) and not value["papers"] for value in source_results.values()
    )
    error_count = sum(len(value["errors"]) for value in source_results.values())
    degraded_components = []
    if use_ai_planner and not planner_meta.get("used_ai"):
        degraded_components.append("query_planner")
    if use_ai_reranker and pre_ranked and not reranker_meta.get("used_ai"):
        degraded_components.append("ai_reranker")
    if use_ai_assessor and diversified and (
        not assessor_meta.get("used_ai")
        or assessor_meta.get("paper_count", 0) < assessor_meta.get("expected_paper_count", len(diversified))
    ):
        degraded_components.append("ai_enrichment")
    status = (
        "failed" if failed_sources == len(source_results)
        else "partial_success" if error_count or degraded_components
        else "success"
    )
    duplicate_rate = 1.0 - len(groups) / len(candidates) if candidates else 0.0
    all_rejected = [*rejected, *relevance_rejected]
    rejection_rate = len(all_rejected) / len(groups) if groups else 0.0
    timings["total"] = round(time.perf_counter() - pipeline_started, 3)

    output: dict[str, Any] = {
        "pipeline_version": "2.2.0",
        "paper_schema_version": config.PAPER_SCHEMA_VERSION,
        "status": status,
        "prompt": prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": timings["total"],
        "timings_seconds": timings,
        "llm_provider": config.llm_provider(),
        "model": config.llm_primary_model("enrich_papers"),
        "runtime_config": {
            "search_depth": search_depth,
            "request_limits": limits,
            "source_caps": caps,
            "max_candidates": max_candidates,
            "pre_rank_limit": pre_rank_limit,
            "ai_rerank_limit": ai_rerank_limit,
            "ai_enrich_limit": ai_enrich_limit,
            "result_limit": result_limit,
            "require_abstract": require_abstract,
            "use_cache": use_cache,
            "use_diversity": use_diversity,
            "adaptive_retrieval": adaptive_retrieval,
            "academic_rate_limits": rate_limit_snapshot(),
            "ranking": _ranking_config_snapshot(plan["ranking_profile"]),
        },
        "query_plan": plan,
        "planner": planner_meta,
        "source_queries": source_queries,
        "retrieval": {
            "raw_candidate_count": len(candidates),
            "deduplicated_count": len(groups),
            "filtered_count": len(kept),
            "pre_ranked_count": len(pre_ranked),
            "relevance_eligible_count": len(relevance_eligible),
            "result_count": len(output_papers),
            "rejected_count": len(all_rejected),
            "metadata_rejected_count": len(rejected),
            "relevance_rejected_count": len(relevance_rejected),
            "sources": source_summary,
        },
        "metrics": {
            "duplicate_rate": round(duplicate_rate, 6),
            "filter_rejection_rate": round(rejection_rate, 6),
            "source_error_count": error_count,
            "degraded_components": degraded_components,
            "llm_usage_current_run": _llm_usage_current_run(
                planner_meta, reranker_meta, assessor_meta
            ),
        },
        "rejected": all_rejected,
        "ai_reranker": reranker_meta,
        "assessor": assessor_meta,
        "papers": output_papers,
    }
    if include_stage_rankings:
        output["stage_rankings"] = {
            "rrf_only": _ranked_ids(sorted(
                deterministic_ranked,
                key=lambda item: item["score_breakdown"]["source_rrf"], reverse=True,
            )),
            "query_match_only": _ranked_ids(sorted(
                deterministic_ranked,
                key=lambda item: item["query_match_score"], reverse=True,
            )),
            "deterministic": _ranked_ids(deterministic_ranked),
            "pre_ranked": _ranked_ids(pre_ranked),
            "ai_reranked": _ranked_ids(reranked),
            "final_diversified": _ranked_ids(diversified),
        }
    if include_source_records:
        output["source_records"] = {
            source: result["papers"] for source, result in source_results.items()
        }
    return output


def _positive(parser: argparse.ArgumentParser, option: str, value: int, maximum: int = 500) -> None:
    if not 1 <= value <= maximum:
        parser.error(f"{option} must be between 1 and {maximum}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI research pipeline for Semantic Scholar, arXiv and OpenAlex.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("prompt", help="research request in Vietnamese or English")
    parser.add_argument(
        "--search-depth", choices=sorted(config.SEARCH_DEPTH_PRESETS),
        default=config.DEFAULT_SEARCH_DEPTH,
    )
    parser.add_argument("--per-query", type=int, default=None, help="override all source request limits")
    parser.add_argument("--s2-per-query", type=int, default=None)
    parser.add_argument("--arxiv-per-query", type=int, default=None)
    parser.add_argument("--openalex-lexical-per-query", type=int, default=None)
    parser.add_argument("--openalex-semantic-per-query", type=int, default=None)
    parser.add_argument("--s2-max-candidates", type=int, default=None)
    parser.add_argument("--arxiv-max-candidates", type=int, default=None)
    parser.add_argument("--openalex-max-candidates", type=int, default=None)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--pre-rank-limit", type=int, default=None)
    parser.add_argument("--ai-rerank-limit", type=int, default=None)
    parser.add_argument("--ai-enrich-limit", type=int, default=None)
    parser.add_argument("--result-limit", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=config.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path, default=config.OUTPUT_DIR / "research_pipeline.json")
    parser.add_argument("--no-ai", action="store_true", help="disable planner, reranker and enrichment")
    parser.add_argument("--no-ai-rerank", action="store_true", help="disable only AI reranking")
    parser.add_argument("--no-assess", action="store_true", help="disable only AI enrichment")
    adaptive_group = parser.add_mutually_exclusive_group()
    adaptive_group.add_argument("--adaptive-retrieval", dest="adaptive_retrieval", action="store_true")
    adaptive_group.add_argument("--no-adaptive-retrieval", dest="adaptive_retrieval", action="store_false")
    diversity_group = parser.add_mutually_exclusive_group()
    diversity_group.add_argument("--diversity", dest="use_diversity", action="store_true")
    diversity_group.add_argument("--no-diversity", dest="use_diversity", action="store_false")
    abstract_group = parser.add_mutually_exclusive_group()
    abstract_group.add_argument("--require-abstract", dest="require_abstract", action="store_true")
    abstract_group.add_argument("--keep-missing-abstract", dest="require_abstract", action="store_false")
    records_group = parser.add_mutually_exclusive_group()
    records_group.add_argument("--include-source-records", dest="include_source_records", action="store_true")
    records_group.add_argument("--no-source-records", dest="include_source_records", action="store_false")
    stages_group = parser.add_mutually_exclusive_group()
    stages_group.add_argument("--include-stage-rankings", dest="include_stage_rankings", action="store_true")
    stages_group.add_argument("--no-stage-rankings", dest="include_stage_rankings", action="store_false")
    parser.set_defaults(
        use_diversity=config.ENABLE_DIVERSITY_RERANK,
        require_abstract=config.REQUIRE_ABSTRACT_BY_DEFAULT,
        include_source_records=config.INCLUDE_SOURCE_RECORDS_IN_OUTPUT,
        include_stage_rankings=config.INCLUDE_STAGE_RANKINGS_IN_OUTPUT,
        adaptive_retrieval=config.ENABLE_ADAPTIVE_RETRIEVAL,
    )
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--no-cache", action="store_true", help="bypass academic API response cache")
    parser.add_argument("--year-from", type=int)
    parser.add_argument("--year-to", type=int)
    parser.add_argument("--latest-years", type=int)
    parser.add_argument(
        "--ranking-profile", choices=["balanced", "latest", "seminal", "evidence_review"]
    )
    args = parser.parse_args()

    limit_options = {
        "--s2-per-query": args.s2_per_query,
        "--arxiv-per-query": args.arxiv_per_query,
        "--openalex-lexical-per-query": args.openalex_lexical_per_query,
        "--openalex-semantic-per-query": args.openalex_semantic_per_query,
        "--s2-max-candidates": args.s2_max_candidates,
        "--arxiv-max-candidates": args.arxiv_max_candidates,
        "--openalex-max-candidates": args.openalex_max_candidates,
        "--max-candidates": args.max_candidates,
        "--pre-rank-limit": args.pre_rank_limit,
        "--ai-rerank-limit": args.ai_rerank_limit,
        "--ai-enrich-limit": args.ai_enrich_limit,
        "--result-limit": args.result_limit,
    }
    if args.per_query is not None:
        _positive(parser, "--per-query", args.per_query, 100)
    for option, value in limit_options.items():
        if value is not None:
            _positive(parser, option, value, 100 if "per-query" in option else 500)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    request_overrides = {
        key: value for key, value in {
            "semantic_scholar": args.s2_per_query,
            "arxiv": args.arxiv_per_query,
            "openalex_lexical": args.openalex_lexical_per_query,
            "openalex_semantic": args.openalex_semantic_per_query,
        }.items() if value is not None
    }
    cap_overrides = {
        key: value for key, value in {
            "semantic_scholar": args.s2_max_candidates,
            "arxiv": args.arxiv_max_candidates,
            "openalex": args.openalex_max_candidates,
        }.items() if value is not None
    }
    try:
        _resolve_search_settings(
            args.search_depth, request_overrides, cap_overrides,
            args.max_candidates, args.pre_rank_limit, args.ai_rerank_limit,
            args.ai_enrich_limit, args.result_limit,
        )
    except ValueError as exc:
        parser.error(str(exc))

    current_year = datetime.now(timezone.utc).year
    for option, year in (("--year-from", args.year_from), ("--year-to", args.year_to)):
        if year is not None and not 1900 <= year <= current_year + 1:
            parser.error(f"{option} must be between 1900 and {current_year + 1}")
    if args.latest_years is not None and not 1 <= args.latest_years <= 50:
        parser.error("--latest-years must be between 1 and 50")

    year_from, year_to, ranking_profile = args.year_from, args.year_to, args.ranking_profile
    if args.latest_years is not None:
        year_from = year_from or current_year - args.latest_years + 1
        year_to = year_to or current_year
        ranking_profile = ranking_profile or "latest"
    if year_from is not None and year_to is not None and year_from > year_to:
        parser.error("--year-from cannot be greater than --year-to")

    result = run_pipeline(
        args.prompt,
        search_depth=args.search_depth,
        per_query=args.per_query,
        request_limits=request_overrides,
        source_caps=cap_overrides,
        max_candidates=args.max_candidates,
        pre_rank_limit=args.pre_rank_limit,
        ai_rerank_limit=args.ai_rerank_limit,
        ai_enrich_limit=args.ai_enrich_limit,
        result_limit=args.result_limit,
        timeout=args.timeout,
        use_ai_planner=not args.no_ai,
        use_ai_reranker=not args.no_ai and not args.no_ai_rerank,
        use_ai_assessor=not args.no_ai and not args.no_assess,
        use_diversity=args.use_diversity,
        adaptive_retrieval=args.adaptive_retrieval,
        require_abstract=args.require_abstract,
        use_cache=config.ENABLE_QUERY_CACHE and not args.no_cache,
        include_source_records=args.include_source_records,
        include_stage_rankings=args.include_stage_rankings,
        year_from_override=year_from,
        year_to_override=year_to,
        ranking_profile_override=ranking_profile,
    )
    save_json(result, args.output)
    retrieval = result["retrieval"]
    if args.print_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Candidates: {retrieval['raw_candidate_count']} -> dedup: "
            f"{retrieval['deduplicated_count']} -> kept: {retrieval['filtered_count']} "
            f"-> final: {retrieval['result_count']}"
        )
        print(
            f"Status: {result['status']}; planner AI: {result['planner'].get('used_ai')}; "
            f"reranker AI: {result['ai_reranker'].get('used_ai')}; "
            f"enrichment AI: {result['assessor'].get('used_ai')}"
        )
        for item in result["papers"][:10]:
            print(f"{item['rank']:>2}. {item['score']:.3f}  {item['paper']['title']}")
        print(f"Saved: {args.output.resolve()}")
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    configure_utf8_console()
    raise SystemExit(main())
