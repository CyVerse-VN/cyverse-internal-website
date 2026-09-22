"""Dùng LLM tạo QueryPlan nhỏ, có validate và fallback deterministic."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import config
from common import SourceError, compact_text
from llm_client import call_tool


INTENTS = {"exploratory", "evidence_review", "latest", "seminal", "comparison"}
RANKING_PROFILES = {"balanced", "latest", "seminal", "evidence_review"}
PUBLICATION_TYPES = {"article", "conference", "preprint", "review", "book", "dataset"}


def _apply_prompt_constraints(plan: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Sửa các constraint rõ ràng trong prompt mà model nhỏ thường hiểu nhầm."""
    text = compact_text(prompt) or ""
    filters = plan["filters"]
    since = re.search(r"(?:từ\s+năm|kể\s+từ|since|from)\s+((?:19|20)\d{2})(?!\s*(?:đến|tới|to|-))", text, re.I)
    between = re.search(
        r"(?:từ|between|from)\s+((?:19|20)\d{2})\s*(?:đến|tới|and|to|-)\s*((?:19|20)\d{2})",
        text,
        re.I,
    )
    exact = re.search(r"(?:trong\s+năm|năm|in)\s+((?:19|20)\d{2})", text, re.I)
    if between:
        filters["year_from"], filters["year_to"] = map(int, between.groups())
    elif since:
        filters["year_from"], filters["year_to"] = int(since.group(1)), None
    elif exact and not filters.get("year_from"):
        year = int(exact.group(1))
        filters["year_from"], filters["year_to"] = year, year

    if plan["intent"] == "evidence_review":
        evidence_markers = {
            "empirical", "evaluation", "benchmark", "experimental", "thực nghiệm", "đánh giá",
        }
        required_groups = [group for group in plan["concept_groups"] if group.get("required", True)]
        if len(required_groups) > 2:
            for group in plan["concept_groups"]:
                group_text = " ".join([group["concept"], *(group.get("synonyms") or [])]).casefold()
                if any(marker in group_text for marker in evidence_markers):
                    group["required"] = False
    return plan


def _unique_text(values: Any, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values if isinstance(values, list) else []:
        text = compact_text(value)
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        result.append(text)
        if len(result) >= limit:
            break
    return result


def validate_query_plan(value: dict[str, Any]) -> dict[str, Any]:
    question = compact_text(value.get("research_question"))
    english_question = compact_text(value.get("english_question"))
    if not question or not english_question:
        raise ValueError("Thiếu research_question hoặc english_question")

    raw_groups = value.get("concept_groups")
    if not isinstance(raw_groups, list):
        raise ValueError("concept_groups phải là array")
    concept_groups = []
    for raw in raw_groups[:4]:
        if not isinstance(raw, dict) or not (concept := compact_text(raw.get("concept"))):
            continue
        synonyms = _unique_text(raw.get("synonyms"), 5)
        synonyms = [item for item in synonyms if item.casefold() != concept.casefold()]
        concept_groups.append({
            "concept": concept,
            "synonyms": synonyms,
            "required": bool(raw.get("required", True)),
        })
    if not concept_groups:
        concept_groups = [{"concept": english_question, "synonyms": [], "required": True}]

    raw_filters = value.get("filters") if isinstance(value.get("filters"), dict) else {}
    current_year = datetime.now(timezone.utc).year
    year_from = raw_filters.get("year_from")
    year_to = raw_filters.get("year_to")
    year_from = year_from if isinstance(year_from, int) and 1900 <= year_from <= current_year + 1 else None
    year_to = year_to if isinstance(year_to, int) and 1900 <= year_to <= current_year + 1 else None
    if year_from and year_to and year_from > year_to:
        year_from, year_to = year_to, year_from
    publication_types = [
        item for item in _unique_text(raw_filters.get("publication_types"), 6)
        if item in PUBLICATION_TYPES
    ]
    languages = [item.lower() for item in _unique_text(raw_filters.get("languages"), 5)]
    languages = [item for item in languages if 2 <= len(item) <= 3 and item.isalpha()]

    variants = _unique_text(value.get("query_variants"), config.MAX_QUERY_VARIANTS)
    if not variants:
        variants = [english_question]
    intent = value.get("intent") if value.get("intent") in INTENTS else "exploratory"
    profile = (
        value.get("ranking_profile")
        if value.get("ranking_profile") in RANKING_PROFILES else "balanced"
    )
    return {
        "research_question": question,
        "english_question": english_question,
        "intent": intent,
        "ranking_profile": profile,
        "concept_groups": concept_groups,
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "publication_types": publication_types,
            "open_access_only": bool(raw_filters.get("open_access_only", False)),
            "languages": languages,
        },
        "query_variants": variants,
    }


def fallback_query_plan(prompt: str) -> dict[str, Any]:
    question = compact_text(prompt) or prompt
    return validate_query_plan({
        "research_question": question,
        "english_question": question,
        "intent": "exploratory",
        "ranking_profile": "balanced",
        "concept_groups": [{"concept": question, "synonyms": [], "required": True}],
        "filters": {
            "year_from": None,
            "year_to": None,
            "publication_types": [],
            "open_access_only": False,
            "languages": [],
        },
        "query_variants": [question],
    })


def create_query_plan(prompt: str, *, use_ai: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    """Trả QueryPlan và metadata cho biết AI hay fallback đã được dùng."""
    if not use_ai or not config.llm_api_key():
        reason = "ai_disabled" if not use_ai else "missing_llm_api_key"
        return _apply_prompt_constraints(fallback_query_plan(prompt), prompt), {
            "used_ai": False,
            "fallback_reason": reason,
        }

    schema = json.loads((config.BASE_DIR / "query_plan.schema.json").read_text(encoding="utf-8"))
    parameters = {
        key: value for key, value in schema.items()
        if key not in {"$schema", "$id", "title"}
    }
    try:
        result = call_tool(
            tool_name="plan_paper_search",
            tool_description="Create a source-independent, structured academic paper search plan.",
            parameters=parameters,
            system_prompt=(
                "You plan academic literature searches. Extract research concepts, English synonyms, "
                "safe metadata filters, and at most three concise English query variants. A phrase like "
                "'since/from YEAR' means year_from=YEAR and year_to=null, not one exact year. Mark only "
                "the one or two indispensable topic concepts as required; methodological preferences such "
                "as empirical evaluation or benchmarking should normally be optional. Do not create URLs "
                "or source-specific query syntax. Do not invent constraints the user did not request."
            ),
            user_prompt=prompt,
            validator=validate_query_plan,
            max_tokens=2200,
        )
        plan = _apply_prompt_constraints(result.value, prompt)
        primary_model = config.llm_primary_model("plan_paper_search")
        return plan, {
            "used_ai": True,
            "provider": result.provider,
            "requested_model": primary_model,
            "model": result.response_model,
            "fallback_model_used": result.requested_model != primary_model,
            "cached": result.cached,
            "usage": result.usage,
            "rate_limit_wait_seconds": result.rate_limit_wait_seconds,
            "attempted_models": list(result.attempted_models),
            "model_errors": list(result.model_errors),
        }
    except SourceError as exc:
        return _apply_prompt_constraints(fallback_query_plan(prompt), prompt), {
            "used_ai": False,
            "fallback_reason": "llm_error",
            "error": str(exc),
        }
