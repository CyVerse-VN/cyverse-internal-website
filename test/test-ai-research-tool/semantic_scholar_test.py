#!/usr/bin/env python3
"""Test riêng API Semantic Scholar."""

from __future__ import annotations

from typing import Any

import config
from common import (
    compact_text,
    get_json,
    normalize_arxiv_id,
    normalize_doi,
    paper_record,
    run_source_cli,
)


FIELD_NAMES = [
    "paperId", "corpusId", "title", "abstract", "authors", "year", "publicationDate",
    "venue", "citationCount", "influentialCitationCount", "url", "openAccessPdf",
    "externalIds", "fieldsOfStudy", "s2FieldsOfStudy", "publicationTypes",
    "referenceCount", "isOpenAccess", "publicationVenue", "journal", "tldr",
]
if config.SEMANTIC_SCHOLAR_INCLUDE_EMBEDDING:
    FIELD_NAMES.append("embedding.specter_v2")
FIELDS = ",".join(FIELD_NAMES)


def build_pdf_links(
    paper_id: str | None,
    arxiv_id: str | None,
    api_pdf_url: str | None,
) -> tuple[str | None, str | None, str | None, str]:
    """Return display URL, reader URL, direct PDF URL, and selected origin.

    Semantic Scholar Reader is an HTML reading page rather than a guaranteed
    direct PDF response. We expose both so later download code can distinguish
    the two kinds of URL.
    """
    reader_url = f"https://www.semanticscholar.org/reader/{paper_id}" if paper_id else None
    arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None
    if api_pdf_url:
        return api_pdf_url, reader_url, api_pdf_url, "api_open_access_pdf"
    if reader_url:
        return reader_url, reader_url, arxiv_pdf_url, "semantic_scholar_reader_fallback"
    return arxiv_pdf_url, None, arxiv_pdf_url, "arxiv_fallback" if arxiv_pdf_url else "unavailable"


def search_with_options(
    query: str,
    limit: int,
    timeout: float,
    *,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if api_key := config.secret("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = api_key
    params: dict[str, Any] = {
        "query": query.replace("-", " "), "limit": limit, "fields": FIELDS,
    }
    params.update(filters or {})
    payload = get_json(
        config.SEMANTIC_SCHOLAR_URL,
        params=params,
        headers=headers,
        timeout=timeout,
        minimum_retry_delay=config.RETRY_MIN_DELAY_BY_SOURCE["semantic_scholar"],
        rate_limit_source="semantic_scholar",
    )
    papers: list[dict[str, Any]] = []
    for source_rank, item in enumerate(payload.get("data") or [], start=1):
        if not isinstance(item, dict) or not compact_text(item.get("title")):
            continue
        external_ids = item.get("externalIds") or {}
        oa_pdf = item.get("openAccessPdf") or {}
        paper_id = compact_text(item.get("paperId"))
        arxiv_id = normalize_arxiv_id(external_ids.get("ArXiv"))
        api_pdf_url = compact_text(oa_pdf.get("url")) if isinstance(oa_pdf, dict) else None
        read_url, reader_url, direct_pdf_url, read_url_origin = build_pdf_links(
            paper_id, arxiv_id, api_pdf_url
        )
        publication_venue = item.get("publicationVenue") or {}
        journal = item.get("journal") or {}
        tldr = item.get("tldr") or {}
        authors = [
            name for author in item.get("authors") or []
            if isinstance(author, dict) and (name := compact_text(author.get("name")))
        ]
        fields: list[str] = []
        topic_names: set[str] = set()
        for field in item.get("s2FieldsOfStudy") or []:
            if isinstance(field, dict) and (name := compact_text(field.get("category"))):
                if name.casefold() in topic_names:
                    continue
                topic_names.add(name.casefold())
                fields.append(name)
        for field in item.get("fieldsOfStudy") or []:
            if (name := compact_text(field)) and name.casefold() not in topic_names:
                topic_names.add(name.casefold())
                fields.append(name)
        doi = normalize_doi(external_ids.get("DOI"))
        data_quality_flags = []
        if arxiv_id and not doi:
            data_quality_flags.append("semantic_scholar_missing_doi_for_arxiv_record")
        papers.append(paper_record(
            source_name="semantic_scholar",
            source_id=paper_id,
            source_rank=source_rank,
            title=compact_text(item.get("title")) or "",
            abstract=compact_text(item.get("abstract")),
            authors=authors,
            year=item.get("year"),
            published_at=item.get("publicationDate"),
            venue=compact_text(publication_venue.get("name")) or compact_text(item.get("venue")),
            doi=doi,
            arxiv_id=arxiv_id,
            url=compact_text(item.get("url")),
            pdf_url=read_url,
            citation_count=item.get("citationCount"),
            reference_count=item.get("referenceCount"),
            is_open_access=item.get("isOpenAccess"),
            fields=fields,
            publication_types=item.get("publicationTypes") or [],
            source_specific={
                "corpus_id": item.get("corpusId"),
                "influential_citation_count": item.get("influentialCitationCount"),
                "external_ids": external_ids,
                "tldr": compact_text(tldr.get("text")) if isinstance(tldr, dict) else None,
                "journal": journal,
                "pdf_url_origin": read_url_origin,
                "reader_url": reader_url,
                "direct_pdf_url": direct_pdf_url,
                "oa_status": compact_text(oa_pdf.get("status")) if isinstance(oa_pdf, dict) else None,
                "license": compact_text(oa_pdf.get("license")) if isinstance(oa_pdf, dict) else None,
                "embedding": item.get("embedding") if config.SEMANTIC_SCHOLAR_INCLUDE_EMBEDDING else None,
                "data_quality_flags": data_quality_flags,
                "raw_data": item if config.PRESERVE_RAW_SOURCE_DATA else None,
            },
        ))
    return {"total_available": payload.get("total"), "papers": papers}


def search(query: str, limit: int, timeout: float) -> dict[str, Any]:
    return search_with_options(query, limit, timeout)


if __name__ == "__main__":
    from common import configure_utf8_console
    configure_utf8_console()
    raise SystemExit(run_source_cli("semantic_scholar", search))
