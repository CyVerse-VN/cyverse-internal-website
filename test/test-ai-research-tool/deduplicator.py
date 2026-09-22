"""Deduplicate paper theo ID trước, rồi title/author/year; giữ provenance."""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from common import normalize_arxiv_id, normalize_doi, prune_empty


def normalize_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _title_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    return SequenceMatcher(None, normalize_title(left.get("title")), normalize_title(right.get("title"))).ratio()


def _same_year_window(left: dict[str, Any], right: dict[str, Any], window: int = 2) -> bool:
    left_year, right_year = left.get("year"), right.get("year")
    return not isinstance(left_year, int) or not isinstance(right_year, int) or abs(left_year - right_year) <= window


def _author_token(paper: dict[str, Any]) -> str | None:
    authors = paper.get("authors") or []
    if not authors:
        return None
    normalized = normalize_title(str(authors[0]))
    return normalized.split()[-1] if normalized else None


def _compatible(left: dict[str, Any], right: dict[str, Any], threshold: float) -> bool:
    if not _same_year_window(left, right):
        return False
    similarity = _title_similarity(left, right)
    if similarity < threshold:
        return False
    left_author, right_author = _author_token(left), _author_token(right)
    return not left_author or not right_author or left_author == right_author or similarity >= 0.985


def _persistent_keys(paper: dict[str, Any]) -> list[str]:
    keys = []
    if doi := normalize_doi(paper.get("doi")):
        keys.append(f"doi:{doi}")
    if arxiv_id := normalize_arxiv_id(paper.get("arxiv_id")):
        keys.append(f"arxiv:{arxiv_id.casefold()}")
    specific = paper.get("source_specific") or {}
    external_ids = specific.get("external_ids") or {}
    if not isinstance(external_ids, dict):
        external_ids = {}
    if specific.get("corpus_id") is not None:
        external_ids = {**external_ids, "corpusid": specific["corpus_id"]}

    aliases = {
        "pubmed": "pmid", "pmid": "pmid",
        "pubmedcentral": "pmcid", "pmcid": "pmcid",
        "mag": "mag", "dblp": "dblp", "acl": "acl", "corpusid": "corpusid",
    }
    for raw_kind, raw_value in external_ids.items():
        kind = aliases.get(str(raw_kind).replace("_", "").casefold())
        if not kind or raw_value is None:
            continue
        value = str(raw_value).strip().rstrip("/")
        if not value:
            continue
        if kind in {"pmid", "pmcid", "mag", "corpusid"}:
            value = value.rsplit("/", 1)[-1]
        if kind == "pmcid":
            value = value.upper()
        else:
            value = value.casefold()
        keys.append(f"{kind}:{value}")
    return list(dict.fromkeys(keys))


def _best_record_score(paper: dict[str, Any]) -> tuple[int, int, int, int, int]:
    types = {str(value).casefold() for value in paper.get("publication_types") or []}
    published = int(bool(types & {"article", "journalarticle", "conference", "review"}))
    non_repository_venue = int(bool(paper.get("venue")) and str(paper["venue"]).casefold() != "arxiv")
    direct_pdf = int(bool(paper.get("pdf_url")) and "/reader/" not in str(paper["pdf_url"]))
    return (
        published,
        non_repository_venue,
        int(bool(paper.get("doi"))),
        len(paper.get("abstract") or ""),
        direct_pdf,
    )


def _dedup_key(records: list[dict[str, Any]], paper: dict[str, Any]) -> str:
    dois = [normalize_doi(item.get("doi")) for item in records]
    dois = [value for value in dois if value]
    published_dois = [value for value in dois if not value.startswith("10.48550/arxiv.")]
    if published_dois or dois:
        return f"doi:{(published_dois or dois)[0]}"
    arxiv_ids = [normalize_arxiv_id(item.get("arxiv_id")) for item in records]
    arxiv_ids = [value for value in arxiv_ids if value]
    if arxiv_ids:
        return f"arxiv:{arxiv_ids[0]}"
    digest = hashlib.sha1(normalize_title(paper.get("title")).encode("utf-8")).hexdigest()[:16]
    return f"title:{digest}"


def _merge_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    best = max(records, key=_best_record_score)
    merged = copy.deepcopy(best)
    compatible_records = [item for item in records if _title_similarity(best, item) >= 0.78]
    if compatible_records:
        merged["abstract"] = max(
            (item.get("abstract") for item in compatible_records if item.get("abstract")),
            key=len,
            default=merged.get("abstract"),
        )
        merged["authors"] = max(
            (item.get("authors") or [] for item in compatible_records),
            key=len,
            default=merged.get("authors") or [],
        )

    dois = list(dict.fromkeys(
        value for item in compatible_records
        if (value := normalize_doi(item.get("doi")))
    ))
    published_dois = [value for value in dois if not value.startswith("10.48550/arxiv.")]
    merged["doi"] = (published_dois or dois or [None])[0]
    if not merged.get("arxiv_id"):
        merged["arxiv_id"] = next(
            (normalize_arxiv_id(item.get("arxiv_id")) for item in compatible_records if item.get("arxiv_id")),
            None,
        )

    direct_pdfs = []
    for item in compatible_records:
        source_specific = item.get("source_specific") or {}
        for candidate in (source_specific.get("direct_pdf_url"), item.get("pdf_url")):
            if candidate and "/reader/" not in str(candidate) and candidate not in direct_pdfs:
                direct_pdfs.append(candidate)
    if direct_pdfs:
        merged["pdf_url"] = direct_pdfs[0]
    merged["citation_count"] = max(
        (item["citation_count"] for item in compatible_records if isinstance(item.get("citation_count"), int)),
        default=None,
    )
    merged["reference_count"] = max(
        (item["reference_count"] for item in compatible_records if isinstance(item.get("reference_count"), int)),
        default=None,
    )
    access_values = [item.get("is_open_access") for item in compatible_records]
    merged["is_open_access"] = True if True in access_values else False if False in access_values else None
    merged["fields"] = list(dict.fromkeys(
        value for item in compatible_records for value in item.get("fields") or []
    ))
    merged["publication_types"] = list(dict.fromkeys(
        value for item in compatible_records for value in item.get("publication_types") or []
    ))
    if not merged.get("venue") or str(merged["venue"]).casefold() == "arxiv":
        merged["venue"] = next((
            item.get("venue") for item in compatible_records
            if item.get("venue") and str(item["venue"]).casefold() != "arxiv"
        ), merged.get("venue"))

    sources = []
    citation_counts: dict[str, int] = {}
    signals_by_source: dict[str, dict[str, Any]] = {}
    retrieval_hits = []
    for item in records:
        identity = {"source": item.get("source"), "source_id": item.get("source_id")}
        if identity not in sources:
            sources.append(identity)
        if isinstance(item.get("citation_count"), int):
            citation_counts[str(item.get("source"))] = max(
                citation_counts.get(str(item.get("source")), 0), item["citation_count"]
            )
        specific = copy.deepcopy(item.get("source_specific") or {})
        hit = specific.pop("retrieval", None)
        if hit and hit not in retrieval_hits:
            retrieval_hits.append(hit)
        if specific:
            source_name = str(item.get("source"))
            signals_by_source.setdefault(source_name, {}).update(specific)

    merged["source_specific"] = prune_empty({
        "merged_sources": sources,
        "retrieval_hits": retrieval_hits,
        "citation_counts_by_source": citation_counts,
        "alternate_dois": [value for value in dois if value != merged.get("doi")],
        "signals_by_source": signals_by_source,
        "is_retracted": any(
            bool((item.get("source_specific") or {}).get("is_retracted")) for item in records
        ),
    })
    return merged


def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    count = len(papers)
    parent = list(range(count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    exact_record: dict[str, int] = {}
    persistent: dict[str, list[int]] = {}
    for index, paper in enumerate(papers):
        if paper.get("source") and paper.get("source_id"):
            record_key = f"{paper['source']}:{paper['source_id']}"
            if record_key in exact_record:
                union(index, exact_record[record_key])
            else:
                exact_record[record_key] = index
        for key in _persistent_keys(paper):
            for other in persistent.get(key, []):
                if _compatible(paper, papers[other], 0.78):
                    union(index, other)
            persistent.setdefault(key, []).append(index)

    for left in range(count):
        for right in range(left + 1, count):
            if find(left) == find(right):
                continue
            if _compatible(papers[left], papers[right], 0.94):
                union(left, right)

    grouped: dict[int, list[dict[str, Any]]] = {}
    for index, paper in enumerate(papers):
        grouped.setdefault(find(index), []).append(paper)

    result = []
    for records in grouped.values():
        merged = _merge_records(records)
        result.append({
            "dedup_key": _dedup_key(records, merged),
            "paper": merged,
            "records": records,
        })
    return result
