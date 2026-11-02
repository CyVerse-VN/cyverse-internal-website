from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

import httpx

from app.tools.notebooklm.config import notebook_import_config
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.schemas import PaperSeed
from app.tools.research.domain import PaperCandidate, normalize_arxiv_id, normalize_doi
from app.tools.research.http import ResearchSourceError
from app.tools.research.sources.arxiv import ArxivSource
from app.tools.research.sources.openalex import OpenAlexSource
from app.tools.research.sources.semantic_scholar import SemanticScholarSource


def normalize_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", folded, flags=re.UNICODE))


def match_score(seed: PaperSeed, candidate: PaperCandidate) -> float:
    seed_doi = normalize_doi(seed.doi)
    candidate_doi = normalize_doi(candidate.doi)
    seed_arxiv = normalize_arxiv_id(seed.arxiv_id)
    candidate_arxiv = normalize_arxiv_id(candidate.arxiv_id)
    if seed_doi and candidate_doi and seed_doi != candidate_doi:
        return 0.0
    if seed_arxiv and candidate_arxiv and seed_arxiv != candidate_arxiv:
        return 0.0
    title = SequenceMatcher(
        None, normalize_text(seed.title), normalize_text(candidate.title)
    ).ratio()
    identifier_match = (
        (seed_doi and candidate_doi and seed_doi == candidate_doi)
        or (seed_arxiv and candidate_arxiv and seed_arxiv == candidate_arxiv)
    )
    if identifier_match:
        if title < 0.75:
            return 0.0
        if seed.year and candidate.year and abs(seed.year - candidate.year) > 1:
            return 0.0
        if seed.authors and candidate.authors:
            expected = {normalize_text(author).split()[-1] for author in seed.authors if normalize_text(author)}
            actual = {normalize_text(author).split()[-1] for author in candidate.authors if normalize_text(author)}
            if not expected & actual:
                return 0.0
        return 1.0
    if title < 0.88 or (not seed.authors and seed.year is None):
        return 0.0
    weights = [(0.7, title)]
    if seed.authors:
        expected = {normalize_text(author).split()[-1] for author in seed.authors if normalize_text(author)}
        actual = {normalize_text(author).split()[-1] for author in candidate.authors if normalize_text(author)}
        weights.append((0.2, len(expected & actual) / len(expected) if expected else 0.0))
    if seed.year is not None:
        weights.append((0.1, 1.0 if seed.year == candidate.year else 0.0))
    return sum(weight * value for weight, value in weights) / sum(weight for weight, _ in weights)


class PaperResolver:
    async def resolve(self, seed: PaperSeed) -> str:
        if seed.pdf_url:
            return seed.pdf_url
        arxiv_id = normalize_arxiv_id(seed.arxiv_id)
        if arxiv_id:
            if re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})", arxiv_id, re.IGNORECASE):
                return f"https://arxiv.org/pdf/{arxiv_id}"
            raise NotebookImportError("INVALID_ARXIV_ID", "The arXiv identifier is invalid.")

        async with httpx.AsyncClient(follow_redirects=False) as client:
            sources = [
                SemanticScholarSource(client),
                OpenAlexSource(client),
                ArxivSource(client),
            ]
            doi = normalize_doi(seed.doi)
            if doi:
                for source in sources[:2]:
                    try:
                        rows = await source.search(doi, limit=10, filters={})
                    except ResearchSourceError:
                        continue
                    exact = [row for row in rows if normalize_doi(row.doi) == doi and row.pdf_url]
                    match = self._best(seed, exact)
                    if match:
                        return match.pdf_url or ""

            for source in sources:
                try:
                    rows = await source.search(seed.title, limit=10, filters={})
                except ResearchSourceError:
                    continue
                match = self._best(seed, [row for row in rows if row.pdf_url])
                if match:
                    return match.pdf_url or ""
        raise NotebookImportError(
            "LOW_CONFIDENCE_MATCH", "No sufficiently reliable PDF match was found."
        )

    @staticmethod
    def _best(seed: PaperSeed, candidates: list[PaperCandidate]) -> PaperCandidate | None:
        scored = sorted(
            ((match_score(seed, row), row) for row in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        if scored and scored[0][0] >= notebook_import_config.match_threshold:
            return scored[0][1]
        return None
