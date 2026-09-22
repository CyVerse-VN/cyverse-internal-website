from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime

from app.tools.research.config import research_config
from app.tools.research.domain import PaperCandidate, RankedPaper
from app.tools.research.schemas import ResearchSettingsInput

TYPE_ALIASES = {
    "journalarticle": "article",
    "journal-article": "article",
    "proceedings-article": "conference",
    "conferencepaper": "conference",
    "conference": "conference",
    "review": "review",
    "review-article": "review",
    "preprint": "preprint",
    "article": "article",
    "book": "book",
    "booksection": "book",
    "dataset": "dataset",
}


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token for token in re.findall(r"\w+", value.casefold(), flags=re.UNICODE) if len(token) > 2}


def candidate_key(paper: PaperCandidate) -> str:
    if paper.doi:
        return f"doi:{paper.doi}"
    if paper.arxiv_id:
        return f"arxiv:{paper.arxiv_id.casefold()}"
    normalized = normalize_title(paper.title)
    return f"title:{hashlib.sha256(normalized.encode()).hexdigest()}"


def deduplicate(candidates: list[PaperCandidate]) -> list[tuple[str, PaperCandidate]]:
    groups: dict[str, list[PaperCandidate]] = defaultdict(list)
    aliases: dict[str, str] = {}
    for paper in candidates:
        identifiers = [candidate_key(paper)]
        if paper.doi:
            identifiers.append(f"doi:{paper.doi}")
        if paper.arxiv_id:
            identifiers.append(f"arxiv:{paper.arxiv_id.casefold()}")
        normalized = normalize_title(paper.title)
        identifiers.append(f"title:{hashlib.sha256(normalized.encode()).hexdigest()}")
        key = next((aliases[value] for value in identifiers if value in aliases), identifiers[0])
        groups[key].append(paper)
        for value in identifiers:
            aliases[value] = key

    result: list[tuple[str, PaperCandidate]] = []
    for key, records in groups.items():
        best = max(records, key=lambda item: (bool(item.abstract), len(item.abstract or ""), item.citation_count or 0))
        merged = best.model_copy(deep=True)
        merged.sources = list(dict.fromkeys(item.source for item in records))
        merged.authors = list(dict.fromkeys(name for item in records for name in item.authors))[:50]
        merged.fields = list(dict.fromkeys(name for item in records for name in item.fields))[:12]
        merged.publication_types = list(
            dict.fromkeys(value for item in records for value in item.publication_types)
        )
        merged.citation_count = max((item.citation_count or 0 for item in records), default=0)
        merged.is_open_access = True if any(item.is_open_access is True for item in records) else best.is_open_access
        merged.pdf_url = next((item.pdf_url for item in records if item.pdf_url), best.pdf_url)
        merged.landing_url = next(
            (item.landing_url for item in records if item.landing_url), best.landing_url
        )
        merged.doi = next((item.doi for item in records if item.doi), best.doi)
        merged.arxiv_id = next((item.arxiv_id for item in records if item.arxiv_id), best.arxiv_id)
        merged.is_retracted = any(item.is_retracted for item in records)
        merged.influential_citation_count = max(
            (item.influential_citation_count or 0 for item in records), default=0
        )
        merged.fwci = max((item.fwci or 0.0 for item in records), default=0.0)
        merged.citation_percentile = max(
            (item.citation_percentile or 0.0 for item in records), default=0.0
        )
        result.append((key, merged))
    return result


def normalized_paper_type(values: list[str]) -> str:
    normalized = [TYPE_ALIASES.get(value.casefold(), value.casefold()) for value in values]
    for preferred in ("review", "dataset", "conference", "article", "preprint", "book"):
        if preferred in normalized:
            return preferred
    return "other"


def filter_candidates(
    candidates: list[tuple[str, PaperCandidate]], settings: ResearchSettingsInput
) -> tuple[list[tuple[str, PaperCandidate]], int]:
    allowed_types = {value.value for value in settings.publication_types}
    allowed_languages = set(settings.languages)
    kept: list[tuple[str, PaperCandidate]] = []
    rejected = 0
    for item in candidates:
        paper = item[1]
        paper_type = normalized_paper_type(paper.publication_types)
        remove = (
            paper.is_retracted
            or (settings.require_abstract and not paper.abstract)
            or (
                settings.year_from is not None
                and (paper.year is None or paper.year < settings.year_from)
            )
            or (
                settings.year_to is not None
                and (paper.year is None or paper.year > settings.year_to)
            )
            or (settings.open_access_only and paper.is_open_access is not True)
            or (bool(allowed_types) and paper_type not in allowed_types)
            or (bool(allowed_languages) and paper.language not in allowed_languages)
        )
        if remove:
            rejected += 1
        else:
            kept.append(item)
    return kept, rejected


def rank_candidates(
    query: str, candidates: list[tuple[str, PaperCandidate]]
) -> list[RankedPaper]:
    query_tokens = tokens(query)
    current_year = datetime.now(UTC).year
    result: list[RankedPaper] = []
    for key, paper in candidates:
        title_overlap = len(tokens(paper.title) & query_tokens) / max(len(query_tokens), 1)
        abstract_overlap = len(tokens(paper.abstract) & query_tokens) / max(len(query_tokens), 1)
        relevance = min(1.0, 0.65 * title_overlap + 0.35 * abstract_overlap)
        citations = math.log1p(paper.citation_count or 0) / math.log(1001)
        age = max(current_year - paper.year, 0) if paper.year else 8
        recency = math.exp(-age / 5.0)
        access = 1.0 if paper.pdf_url else 0.7 if paper.is_open_access else 0.2
        metadata = sum(
            bool(value)
            for value in (paper.abstract, paper.authors, paper.year, paper.venue, paper.doi or paper.arxiv_id)
        ) / 5
        quality = min(1.0, 0.35 * citations + 0.30 * recency + 0.20 * access + 0.15 * metadata)
        source_bonus = min(len(paper.sources), 3) * 0.015
        weight_total = research_config.relevance_weight + research_config.quality_weight
        score = min(
            1.0,
            (
                research_config.relevance_weight * relevance
                + research_config.quality_weight * quality
            )
            / weight_total
            + source_bonus,
        )
        priority = "high" if relevance >= 0.55 else "medium" if relevance >= 0.25 else "low"
        result.append(
            RankedPaper(
                dedup_key=key,
                paper=paper,
                relevance_score=round(relevance, 6),
                quality_score=round(quality, 6),
                score=round(score, 6),
                read_priority=priority,
            )
        )
    return sorted(result, key=lambda item: item.score, reverse=True)


def apply_ai_scores(
    papers: list[RankedPaper], scores: dict[str, tuple[float, str]]
) -> list[RankedPaper]:
    result: list[RankedPaper] = []
    for paper in papers:
        ai = scores.get(paper.dedup_key)
        if ai:
            relevance, priority = ai
            ai_weight = research_config.rerank_ai_weight
            paper = paper.model_copy(
                update={
                    "relevance_score": round(
                        (1 - ai_weight) * paper.relevance_score + ai_weight * relevance, 6
                    ),
                    "score": round((1 - ai_weight) * paper.score + ai_weight * relevance, 6),
                    "read_priority": priority,
                }
            )
        result.append(paper)
    return sorted(result, key=lambda item: item.score, reverse=True)


def apply_relevance_gate(papers: list[RankedPaper]) -> tuple[list[RankedPaper], int]:
    kept = [
        paper
        for paper in papers
        if paper.relevance_score >= research_config.min_relevance_score
    ]
    return kept, len(papers) - len(kept)


def diversify(papers: list[RankedPaper], limit: int) -> list[RankedPaper]:
    pool = list(papers[: max(limit * 3, limit)])
    selected: list[RankedPaper] = []
    while pool and len(selected) < limit:
        if not selected:
            selected.append(pool.pop(0))
            continue
        best_index = 0
        best_score = -1.0
        for index, candidate in enumerate(pool):
            candidate_tokens = tokens(candidate.paper.title)
            similarity = max(
                len(candidate_tokens & tokens(chosen.paper.title))
                / max(len(candidate_tokens | tokens(chosen.paper.title)), 1)
                for chosen in selected
            )
            diversity_weight = research_config.diversity_lambda
            diversity_score = (
                diversity_weight * candidate.score - (1 - diversity_weight) * similarity
            )
            if diversity_score > best_score:
                best_score = diversity_score
                best_index = index
        selected.append(pool.pop(best_index))
    return selected
