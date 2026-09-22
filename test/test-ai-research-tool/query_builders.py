"""Biên dịch QueryPlan nguồn-độc-lập thành cú pháp của từng API."""

from __future__ import annotations

import re
from typing import Any

import config


S2_PUBLICATION_TYPES = {
    "article": "JournalArticle",
    "conference": "Conference",
    "review": "Review",
    "book": "Book",
    "dataset": "Dataset",
}


def _escape_phrase(value: str) -> str:
    return re.sub(r'["\\]+', " ", value).strip()


def _terms(group: dict[str, Any]) -> list[str]:
    values = [group["concept"], *(group.get("synonyms") or [])]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _escape_phrase(str(value))
        if not cleaned or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        result.append(cleaned)
    return result[:config.MAX_TERMS_PER_CONCEPT]


def _plain_query(value: str) -> str:
    """Semantic Scholar relevance search không hỗ trợ cú pháp hoặc từ ghép có gạch nối."""
    return re.sub(r"[-‐‑‒–—]+", " ", value).strip()


def _quote(value: str) -> str:
    return f'"{value}"' if " " in value else value


def build_arxiv_query(plan: dict[str, Any]) -> str:
    groups = []
    for group in plan["concept_groups"]:
        terms = [f"all:{_quote(term)}" for term in _terms(group)]
        if not terms:
            continue
        expression = terms[0] if len(terms) == 1 else f"({' OR '.join(terms)})"
        if group.get("required", True):
            groups.append(expression)
    query = " AND ".join(groups) or f'all:"{_escape_phrase(plan["english_question"])}"'
    filters = plan["filters"]
    if filters.get("year_from") or filters.get("year_to"):
        year_from = filters.get("year_from") or 1900
        year_to = filters.get("year_to") or 2100
        query += f" AND submittedDate:[{year_from}01010000 TO {year_to}12312359]"
    return query


def build_openalex_query(plan: dict[str, Any]) -> str:
    groups = []
    for group in plan["concept_groups"]:
        terms = [_quote(term) for term in _terms(group)]
        if not terms:
            continue
        expression = terms[0] if len(terms) == 1 else f"({' OR '.join(terms)})"
        if group.get("required", True):
            groups.append(expression)
    return " AND ".join(groups) or plan["english_question"]


def build_openalex_filter(plan: dict[str, Any], *, semantic: bool = False) -> str | None:
    filters = plan["filters"]
    parts = ["has_abstract:true"]
    year_from, year_to = filters.get("year_from"), filters.get("year_to")
    if semantic:
        if year_from and year_to and year_from == year_to:
            parts.append(f"publication_year:{year_from}")
        else:
            if year_from:
                parts.append(f"publication_year:>{year_from - 1}")
            if year_to:
                parts.append(f"publication_year:<{year_to + 1}")
    else:
        if year_from:
            parts.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            parts.append(f"to_publication_date:{year_to}-12-31")
    if filters.get("open_access_only"):
        parts.append("open_access.is_oa:true")
    languages = filters.get("languages") or []
    if languages:
        parts.append("language:" + "|".join(languages))
    return ",".join(parts) if parts else None


def build_semantic_scholar_filters(plan: dict[str, Any]) -> dict[str, Any]:
    filters = plan["filters"]
    result: dict[str, Any] = {}
    if filters.get("year_from") or filters.get("year_to"):
        start = str(filters.get("year_from") or "")
        end = str(filters.get("year_to") or "")
        result["publicationDateOrYear"] = f"{start}:{end}"
    types = [
        mapped for item in filters.get("publication_types") or []
        if (mapped := S2_PUBLICATION_TYPES.get(item))
    ]
    if types:
        result["publicationTypes"] = ",".join(dict.fromkeys(types))
    if filters.get("open_access_only"):
        result["openAccessPdf"] = ""
    return result


def compile_source_queries(plan: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    variants = plan["query_variants"][:config.MAX_QUERY_VARIANTS]
    openalex_queries = [{
        "mode": "lexical",
        "query": build_openalex_query(plan),
        "filter": build_openalex_filter(plan),
    }]
    if config.OPENALEX_ENABLE_SEMANTIC_SEARCH:
        openalex_queries.append({
            "mode": "semantic",
            "query": plan["english_question"],
            "filter": build_openalex_filter(plan, semantic=True),
        })
    return {
        "semantic_scholar": [{
            "mode": "relevance",
            "query": _plain_query(variant),
            "filters": build_semantic_scholar_filters(plan),
        } for variant in variants],
        "arxiv": [{"mode": "boolean", "query": build_arxiv_query(plan)}],
        "openalex": openalex_queries,
    }
