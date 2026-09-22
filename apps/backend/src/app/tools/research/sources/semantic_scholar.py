from __future__ import annotations

from typing import cast

from app.core.config import settings
from app.tools.research.config import research_config
from app.tools.research.domain import PaperCandidate, compact_text, normalize_arxiv_id
from app.tools.research.http import request
from app.tools.research.sources.base import PaperSource

FIELDS = (
    "paperId,corpusId,title,abstract,authors,year,publicationDate,venue,citationCount,"
    "influentialCitationCount,url,openAccessPdf,externalIds,fieldsOfStudy,s2FieldsOfStudy,"
    "publicationTypes,isOpenAccess"
)


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"

    async def search(
        self, query: str, *, limit: int, filters: dict[str, object]
    ) -> list[PaperCandidate]:
        headers: dict[str, str] = {}
        if settings.research_semantic_scholar_api_key:
            headers["x-api-key"] = (
                settings.research_semantic_scholar_api_key.get_secret_value()
            )
        params: dict[str, object] = {"query": query.replace("-", " "), "limit": limit, "fields": FIELDS}
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")
        if year_from or year_to:
            params["publicationDateOrYear"] = f"{year_from or ''}:{year_to or ''}"
        if filters.get("open_access_only"):
            params["openAccessPdf"] = ""
        response = await request(
            self.client,
            "GET",
            research_config.semantic_scholar_url,
            source=self.name,
            params=params,
            headers=headers,
        )
        payload = response.json()
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        papers: list[PaperCandidate] = []
        for rank, raw in enumerate(rows, start=1):
            if not isinstance(raw, dict) or not compact_text(raw.get("title")):
                continue
            external = raw.get("externalIds") if isinstance(raw.get("externalIds"), dict) else {}
            oa_pdf = raw.get("openAccessPdf") if isinstance(raw.get("openAccessPdf"), dict) else {}
            authors = [
                name
                for item in cast(list[object], raw.get("authors") or [])
                if isinstance(item, dict) and (name := compact_text(item.get("name")))
            ]
            fields = [
                value
                for item in cast(list[object], raw.get("fieldsOfStudy") or [])
                if (value := compact_text(item))
            ]
            paper_id = compact_text(raw.get("paperId"))
            arxiv_id = normalize_arxiv_id(external.get("ArXiv"))
            direct_pdf = compact_text(oa_pdf.get("url"))
            landing = compact_text(raw.get("url"))
            papers.append(
                PaperCandidate(
                    source=self.name,
                    source_id=paper_id,
                    source_rank=rank,
                    title=compact_text(raw.get("title")) or "",
                    abstract=compact_text(raw.get("abstract")),
                    authors=authors,
                    year=raw.get("year") if isinstance(raw.get("year"), int) else None,
                    published_at=raw.get("publicationDate"),
                    venue=compact_text(raw.get("venue")),
                    doi=external.get("DOI"),
                    arxiv_id=arxiv_id,
                    landing_url=landing or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None),
                    pdf_url=direct_pdf or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None),
                    citation_count=raw.get("citationCount") if isinstance(raw.get("citationCount"), int) else None,
                    is_open_access=raw.get("isOpenAccess") if isinstance(raw.get("isOpenAccess"), bool) else None,
                    fields=fields,
                    publication_types=[str(item) for item in raw.get("publicationTypes") or []],
                    influential_citation_count=(
                        raw.get("influentialCitationCount")
                        if isinstance(raw.get("influentialCitationCount"), int)
                        else None
                    ),
                    sources=[self.name],
                )
            )
        return papers
