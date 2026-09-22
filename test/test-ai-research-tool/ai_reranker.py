"""AI rerank một shortlist; citation/venue không được gửi để giảm prestige bias."""

from __future__ import annotations

import json
from typing import Any

import config
from common import SourceError, compact_text
from llm_client import call_tool


def _score(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("AI rerank score phải là number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("AI rerank score phải là number") from exc
    return round(max(0.0, min(numeric, 1.0)), 4)


def _validator_factory(allowed_ids: set[str]):
    def validate(value: dict[str, Any]) -> dict[str, Any]:
        rows = value.get("rerankings")
        if not isinstance(rows, list):
            raise ValueError("rerankings phải là array")
        result = []
        seen = set()
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            paper_id = compact_text(raw.get("paper_id"))
            reason = compact_text(raw.get("reason"))
            if not paper_id or paper_id not in allowed_ids or paper_id in seen or not reason:
                continue
            priority = raw.get("read_priority")
            if priority not in {"high", "medium", "low"}:
                raise ValueError("Invalid read_priority")
            matched_concepts = [
                text for item in raw.get("matched_concepts") or []
                if (text := compact_text(item))
            ]
            result.append({
                "paper_id": paper_id,
                "relevance": _score(raw.get("relevance")),
                "intent_match": _score(raw.get("intent_match")),
                "method_match": _score(raw.get("method_match")),
                "confidence": _score(raw.get("confidence")),
                "read_priority": priority,
                "matched_concepts": list(dict.fromkeys(matched_concepts))[:6],
                "reason": reason,
            })
            seen.add(paper_id)
        if seen != allowed_ids:
            raise ValueError(f"Model thiếu {len(allowed_ids - seen)} paper reranking")
        return {"rerankings": result}
    return validate


def rerank_with_ai(
    question: str,
    query_plan: dict[str, Any],
    ranked: list[dict[str, Any]],
    *,
    use_ai: bool = True,
    limit: int | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    maximum = min(limit or config.AI_RERANK_LIMIT, len(ranked))
    shortlist = ranked[:maximum]
    if not shortlist or not use_ai or not config.llm_api_key():
        reason = "no_papers" if not shortlist else "ai_disabled" if not use_ai else "missing_llm_api_key"
        return {}, {"used_ai": False, "fallback_reason": reason, "paper_count": 0}

    schema = json.loads((config.BASE_DIR / "paper_rerank.schema.json").read_text(encoding="utf-8"))
    parameters = {key: value for key, value in schema.items() if key not in {"$schema", "$id", "title"}}
    all_scores: dict[str, dict[str, Any]] = {}
    errors = []
    models = []
    cached_batches = 0
    usage_by_batch = []
    attempted_models_by_batch = []
    model_errors_by_batch = []
    rate_limit_wait_by_batch = []
    batch_size = max(int(config.AI_RERANK_BATCH_SIZE), 1)
    for start in range(0, len(shortlist), batch_size):
        batch = shortlist[start:start + batch_size]
        papers = [{
            "paper_id": item["dedup_key"],
            "title": item["paper"].get("title"),
            "abstract": (item["paper"].get("abstract") or "")[:config.AI_RERANK_ABSTRACT_MAX_CHARS],
        } for item in batch]
        allowed_ids = {item["paper_id"] for item in papers}
        payload = {
            "research_question": question,
            "intent": query_plan.get("intent"),
            "required_concepts": [
                group.get("concept") for group in query_plan.get("concept_groups") or []
                if group.get("required", True)
            ],
            "preferred_concepts": [
                group.get("concept") for group in query_plan.get("concept_groups") or []
                if not group.get("required", True)
            ],
            "papers": papers,
        }
        try:
            call = call_tool(
                tool_name="rerank_papers",
                tool_description="Score shortlisted papers only for semantic and intent match to a research question.",
                parameters=parameters,
                system_prompt=(
                    "You are a query-specific academic reranker. Use only the research intent, title and abstract. "
                    "Do not infer scientific quality, influence, venue prestige or citation impact. Do not reward "
                    "generic keyword overlap when the paper does not answer the requested topic. "
                    "BẮT BUỘC viết reason và matched_concepts bằng tiếng Việt có dấu."
                ),
                user_prompt=json.dumps(payload, ensure_ascii=False),
                validator=_validator_factory(allowed_ids),
                max_tokens=3500,
            )
            models.append(call.response_model)
            cached_batches += int(call.cached)
            usage_by_batch.append({"cached": call.cached, **call.usage})
            attempted_models_by_batch.append(list(call.attempted_models))
            model_errors_by_batch.append(list(call.model_errors))
            rate_limit_wait_by_batch.append(call.rate_limit_wait_seconds)
            for row in call.value["rerankings"]:
                all_scores[row["paper_id"]] = {
                    **{key: value for key, value in row.items() if key != "paper_id"},
                    "scoring_model": call.response_model,
                    "batch_index": start // batch_size,
                }
        except SourceError as exc:
            errors.append({"batch_start": start, "error": str(exc)})
            break

    unique_models = list(dict.fromkeys(models))
    primary_model = config.llm_primary_model("rerank_papers")
    model_consistent = len(unique_models) <= 1
    for value in all_scores.values():
        value["cross_model_consistent"] = model_consistent
    return all_scores, {
        "used_ai": bool(all_scores),
        "provider": config.llm_provider(),
        "requested_model": primary_model,
        "models": unique_models,
        "fallback_model_used": any(model != primary_model for model in unique_models),
        "cross_model_consistent": model_consistent,
        "paper_count": len(all_scores),
        "batch_count": (len(shortlist) + batch_size - 1) // batch_size,
        "cached_batches": cached_batches,
        "usage_by_batch": usage_by_batch,
        "attempted_models_by_batch": attempted_models_by_batch,
        "model_errors_by_batch": model_errors_by_batch,
        "rate_limit_wait_by_batch": rate_limit_wait_by_batch,
        "errors": errors,
    }


def apply_ai_rerank(
    ranked: list[dict[str, Any]],
    ai_scores: dict[str, dict[str, Any]],
    profile: str,
) -> list[dict[str, Any]]:
    """Kết hợp AI vào Query Match; Paper Quality vẫn hoàn toàn deterministic."""
    final_weights = config.FINAL_SCORE_WEIGHTS.get(profile, config.FINAL_SCORE_WEIGHTS["balanced"])
    denominator = max(sum(max(float(value), 0.0) for value in final_weights.values()), 1e-9)
    signal_weights = config.AI_RERANK_SIGNAL_WEIGHTS
    signal_denominator = max(sum(max(float(value), 0.0) for value in signal_weights.values()), 1e-9)
    result = []
    for original in ranked:
        item = dict(original)
        ai = ai_scores.get(item["dedup_key"])
        deterministic_query_match = float(item["query_match_score"])
        adjusted_query_match = deterministic_query_match
        effective_weight = 0.0
        if ai:
            ai_signal = sum(float(ai[key]) * max(float(signal_weights[key]), 0.0) for key in signal_weights) / signal_denominator
            confidence = float(ai["confidence"])
            if confidence >= float(config.AI_RERANK_MIN_CONFIDENCE):
                effective_weight = float(config.AI_RERANK_WEIGHT) * confidence
                if not ai.get("cross_model_consistent", True):
                    effective_weight *= float(config.AI_RERANK_CROSS_MODEL_PENALTY)
                effective_weight = min(max(effective_weight, 0.0), 1.0)
                adjusted_query_match = (
                    (1.0 - effective_weight) * deterministic_query_match + effective_weight * ai_signal
                )
            item["ai_rerank"] = ai
            item["score_breakdown"]["ai_relevance"] = round(ai_signal, 6)
            item["score_breakdown"]["ai_effective_weight"] = round(effective_weight, 6)
            item["score_breakdown"]["ai_ignored_low_confidence"] = float(
                confidence < float(config.AI_RERANK_MIN_CONFIDENCE)
            )
        else:
            item["ai_rerank"] = None
            item["score_breakdown"]["ai_relevance"] = 0.0
            item["score_breakdown"]["ai_effective_weight"] = 0.0
            item["score_breakdown"]["ai_ignored_low_confidence"] = 0.0
        recommendation_score = (
            adjusted_query_match * max(float(final_weights["query_match"]), 0.0)
            + float(item["paper_quality_score"]) * max(float(final_weights["paper_quality"]), 0.0)
        ) / denominator
        item["deterministic_query_match_score"] = round(deterministic_query_match, 6)
        item["query_match_score"] = round(adjusted_query_match, 6)
        item["score_breakdown"]["query_match"] = round(adjusted_query_match, 6)
        item["score_breakdown"]["relevance"] = round(adjusted_query_match, 6)
        item["recommendation_score"] = round(recommendation_score, 6)
        item["score"] = round(recommendation_score, 6)
        result.append(item)

    result.sort(key=lambda value: value["recommendation_score"], reverse=True)
    for index, item in enumerate(result, start=1):
        item["rank"] = index
        item["post_ai_rank"] = index
    return result
