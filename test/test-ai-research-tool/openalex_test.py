#!/usr/bin/env python3
"""Test riêng API OpenAlex."""

from __future__ import annotations

from typing import Any

import config
from common import (
    compact_text,
    get_json,
    normalize_arxiv_id,
    normalize_doi,
    paper_record,
    reconstruct_abstract,
    run_source_cli,
    strip_id_url,
)


SELECT_FIELDS = ",".join([
    "id", "doi", "title", "abstract_inverted_index", "authorships", "publication_year",
    "publication_date", "cited_by_count", "primary_location", "best_oa_location",
    "open_access", "topics", "keywords", "ids", "type", "language", "updated_date",
    "referenced_works_count", "counts_by_year", "fwci", "citation_normalized_percentile",
    "relevance_score", "is_retracted", "has_fulltext", "content_urls",
])


def search_with_options(
    query: str,
    limit: int,
    timeout: float,
    *,
    filter_query: str | None = None,
    semantic: bool = False,
) -> dict[str, Any]:
    search_key = "search.semantic" if semantic else "search"
    params: dict[str, Any] = {search_key: query, "per_page": limit,
                              "sort": "relevance_score:desc", "select": SELECT_FIELDS}
    if filter_query:
        params["filter"] = filter_query
    if api_key := config.secret("OPENALEX_API_KEY"):
        params["api_key"] = api_key
    if mailto := config.secret("OPENALEX_MAILTO"):
        params["mailto"] = mailto
    payload = get_json(
        config.OPENALEX_URL, params=params, timeout=timeout,
        minimum_retry_delay=config.RETRY_MIN_DELAY_BY_SOURCE["openalex"],
        rate_limit_source="openalex",
    )
    papers: list[dict[str, Any]] = []
    for source_rank, item in enumerate(payload.get("results") or [], start=1):
        if not isinstance(item, dict) or not compact_text(item.get("title")):
            continue
        primary_location = item.get("primary_location") or {}
        best_oa_location = item.get("best_oa_location") or {}
        primary_source = primary_location.get("source") or {}
        ids = item.get("ids") or {}
        paper_id = item.get("id")
        doi = normalize_doi(item.get("doi"))
        open_access = item.get("open_access") or {}
        content_urls = item.get("content_urls") or {}
        authors = [
            name for authorship in item.get("authorships") or []
            if isinstance(authorship, dict)
            and (name := compact_text((authorship.get("author") or {}).get("display_name")))
        ]
        fields = [
            name for topic in item.get("topics") or []
            if isinstance(topic, dict) and (name := compact_text(topic.get("display_name")))
        ]
        keywords = [
            {"name": name, "score": keyword.get("score")}
            for keyword in item.get("keywords") or []
            if isinstance(keyword, dict) and (name := compact_text(keyword.get("display_name")))
        ]
        direct_pdf_url = (
            compact_text(best_oa_location.get("pdf_url"))
            or compact_text(primary_location.get("pdf_url"))
            or compact_text(content_urls.get("pdf"))
        )
        landing_page_url = (
            f"https://doi.org/{doi}" if doi
            else compact_text(primary_location.get("landing_page_url")) or compact_text(paper_id)
        )
        papers.append(paper_record(
            source_name="openalex",
            source_id=strip_id_url(paper_id),
            source_rank=source_rank,
            title=compact_text(item.get("title")) or "",
            abstract=reconstruct_abstract(item.get("abstract_inverted_index")),
            authors=authors,
            year=item.get("publication_year"),
            published_at=item.get("publication_date"),
            updated_at=item.get("updated_date"),
            venue=compact_text(primary_source.get("display_name")),
            doi=doi,
            arxiv_id=normalize_arxiv_id(ids.get("arxiv")),
            url=landing_page_url,
            pdf_url=direct_pdf_url,
            citation_count=item.get("cited_by_count"),
            reference_count=item.get("referenced_works_count"),
            is_open_access=open_access.get("is_oa"),
            fields=fields,
            publication_types=[item["type"]] if item.get("type") else [],
            source_specific={
                "relevance_score": item.get("relevance_score"),
                "fwci": item.get("fwci"),
                "citation_normalized_percentile": item.get("citation_normalized_percentile"),
                "citations_by_year": item.get("counts_by_year") or [],
                "is_retracted": item.get("is_retracted"),
                "language": compact_text(item.get("language")),
                "keywords": keywords,
                "external_ids": ids,
                "oa_status": compact_text(open_access.get("oa_status")),
                "oa_url": compact_text(open_access.get("oa_url")),
                "license": compact_text(best_oa_location.get("license")),
                "version": compact_text(best_oa_location.get("version")),
                "has_fulltext": item.get("has_fulltext"),
                "content_urls": content_urls,
                "raw_data": item if config.PRESERVE_RAW_SOURCE_DATA else None,
            },
        ))
    meta = payload.get("meta") or {}
    return {"total_available": meta.get("count"), "request_cost_usd": meta.get("cost_usd"),
            "papers": papers}


def search(query: str, limit: int, timeout: float) -> dict[str, Any]:
    return search_with_options(query, limit, timeout)


if __name__ == "__main__":
    from common import configure_utf8_console
    configure_utf8_console()
    raise SystemExit(run_source_cli("openalex", search))
