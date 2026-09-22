#!/usr/bin/env python3
"""Test riêng API arXiv."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import config
from common import (
    SourceError,
    compact_text,
    http_get,
    normalize_arxiv_id,
    normalize_doi,
    paper_record,
    run_source_cli,
)


ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
OPEN_SEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


def xml_text(node: ET.Element, path: str) -> str | None:
    return compact_text(node.findtext(path))


def arxiv_version(value: str | None) -> str | None:
    match = re.search(r"(v\d+)(?:/)?$", value or "", flags=re.I)
    return match.group(1).lower() if match else None


def search_expression(search_query: str, limit: int, timeout: float) -> dict[str, Any]:
    body = http_get(
        config.ARXIV_URL,
        params={"search_query": search_query, "start": 0, "max_results": limit,
                "sortBy": "relevance", "sortOrder": "descending"},
        headers={"Accept": "application/atom+xml"},
        timeout=timeout,
        minimum_retry_delay=config.RETRY_MIN_DELAY_BY_SOURCE["arxiv"],
        rate_limit_source="arxiv",
    )
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise SourceError("Response không phải Atom XML hợp lệ") from exc

    papers: list[dict[str, Any]] = []
    for source_rank, entry in enumerate(root.findall(f"{ATOM}entry"), start=1):
        title = xml_text(entry, f"{ATOM}title")
        if not title:
            continue
        entry_url = xml_text(entry, f"{ATOM}id")
        links = [link.attrib for link in entry.findall(f"{ATOM}link")]
        pdf_url = next((link.get("href") for link in links if link.get("title") == "pdf"), None)
        page_url = next((link.get("href") for link in links if link.get("rel") == "alternate"), entry_url)
        arxiv_id = normalize_arxiv_id(entry_url)
        published_at = xml_text(entry, f"{ATOM}published")
        updated_at = xml_text(entry, f"{ATOM}updated")
        journal_reference = xml_text(entry, f"{ARXIV}journal_ref")
        doi = normalize_doi(xml_text(entry, f"{ARXIV}doi"))
        primary_category_node = entry.find(f"{ARXIV}primary_category")
        primary_category = (
            compact_text(primary_category_node.attrib.get("term"))
            if primary_category_node is not None else None
        )
        categories = [
            term for category in entry.findall(f"{ATOM}category")
            if (term := compact_text(category.attrib.get("term")))
        ]
        authors = [
            name for author in entry.findall(f"{ATOM}author")
            if (name := xml_text(author, f"{ATOM}name"))
        ]
        derived_doi = f"10.48550/arxiv.{arxiv_id}".lower() if arxiv_id and not doi else None
        papers.append(paper_record(
            source_name="arxiv",
            source_id=arxiv_id,
            source_rank=source_rank,
            title=title,
            abstract=xml_text(entry, f"{ATOM}summary"),
            authors=authors,
            year=int(published_at[:4]) if published_at and published_at[:4].isdigit() else None,
            published_at=published_at,
            updated_at=updated_at,
            venue=journal_reference,
            doi=doi,
            arxiv_id=arxiv_id,
            url=page_url,
            pdf_url=pdf_url,
            is_open_access=True,
            fields=categories,
            publication_types=["preprint"],
            source_specific={
                "version": arxiv_version(entry_url),
                "primary_category": primary_category,
                "comment": xml_text(entry, f"{ARXIV}comment"),
                "derived_doi_candidate": derived_doi,
                "derived_doi_verified": False if derived_doi else None,
                "raw_atom": ET.tostring(entry, encoding="unicode") if config.PRESERVE_RAW_SOURCE_DATA else None,
            },
        ))
    total_text = xml_text(root, f"{OPEN_SEARCH}totalResults")
    return {"total_available": int(total_text) if total_text and total_text.isdigit() else None,
            "papers": papers}


def search(query: str, limit: int, timeout: float) -> dict[str, Any]:
    safe_query = compact_text(query.replace('"', " ")) or query
    return search_expression(f'all:"{safe_query}"', limit, timeout)


if __name__ == "__main__":
    from common import configure_utf8_console
    configure_utf8_console()
    raise SystemExit(run_source_cli("arxiv", search))
