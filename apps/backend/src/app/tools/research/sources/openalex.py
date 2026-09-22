from __future__ import annotations

import re

from app.core.config import settings
from app.tools.research.config import research_config
from app.tools.research.domain import PaperCandidate, compact_text
from app.tools.research.http import ResearchSourceError, request
from app.tools.research.sources.base import PaperSource

SELECT_FIELDS = (
    "id,doi,title,abstract_inverted_index,authorships,publication_year,publication_date,"
    "cited_by_count,primary_location,best_oa_location,open_access,topics,ids,type,language,"
    "fwci,citation_normalized_percentile,is_retracted"
)


def reconstruct_abstract(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    positions: list[tuple[int, str]] = []
    for word, raw_positions in value.items():
        if not isinstance(word, str) or not isinstance(raw_positions, list):
            continue
        positions.extend((position, word) for position in raw_positions if isinstance(position, int))
    return compact_text(" ".join(word for _, word in sorted(positions)))


class OpenAlexSource(PaperSource):
    name = "openalex"

    async def search(
        self, query: str, *, limit: int, filters: dict[str, object]
    ) -> list[PaperCandidate]:
        clean_query = re.sub(r"[?*\"'\\\/]", " ", query).strip()
        clean_query = re.sub(r"\s+", " ", clean_query)
        if not clean_query:
            clean_query = query.strip() or "research"

        lexical = await self._search_mode(
            clean_query, limit=limit, filters=filters, semantic=False
        )
        remaining = limit - len(lexical)
        semantic: list[PaperCandidate] = []
        if remaining > 0:
            await self.checkpoint()
            try:
                semantic = await self._search_mode(
                    clean_query, limit=min(remaining, 50), filters=filters, semantic=True
                )
            except ResearchSourceError:
                # Semantic search is an optional recall boost. Preserve valid lexical results.
                pass
        papers: list[PaperCandidate] = []
        seen: set[str] = set()
        for paper in [*lexical, *semantic]:
            identity = paper.source_id or paper.doi or paper.title
            if identity.casefold() in seen:
                continue
            seen.add(identity.casefold())
            papers.append(paper)
            if len(papers) >= limit:
                break
        return papers

    async def _search_mode(
        self,
        query: str,
        *,
        limit: int,
        filters: dict[str, object],
        semantic: bool,
    ) -> list[PaperCandidate]:
        parts: list[str] = []
        if filters.get("require_abstract"):
            parts.append("has_abstract:true")
        if semantic:
            # Semantic search endpoint only supports publication_year, not from/to_publication_date
            year_from = filters.get("year_from")
            year_to = filters.get("year_to")
            if year_from and year_to:
                if year_from == year_to:
                    parts.append(f"publication_year:{year_from}")
            elif year_from:
                parts.append(f"publication_year:>{int(year_from) - 1}")
            elif year_to:
                parts.append(f"publication_year:<{int(year_to) + 1}")
        else:
            if filters.get("year_from"):
                parts.append(f"from_publication_date:{filters['year_from']}-01-01")
            if filters.get("year_to"):
                parts.append(f"to_publication_date:{filters['year_to']}-12-31")
        if filters.get("open_access_only"):
            parts.append("open_access.is_oa:true")
        languages = filters.get("languages") or []
        if languages:
            parts.append("language:" + "|".join(str(value) for value in languages))
        params: dict[str, object] = {
            "search.semantic" if semantic else "search": query,
            "per_page": limit,
            "sort": "relevance_score:desc",
            "select": SELECT_FIELDS,
        }
        if parts:
            params["filter"] = ",".join(parts)
        if settings.research_openalex_api_key:
            params["api_key"] = settings.research_openalex_api_key.get_secret_value()
        if research_config.openalex_mailto:
            params["mailto"] = research_config.openalex_mailto
        elif research_config.contact_email:
            params["mailto"] = research_config.contact_email
        response = await request(
            self.client,
            "GET",
            research_config.openalex_url,
            source=self.name,
            params=params,
        )
        payload = response.json()
        rows = payload.get("results", []) if isinstance(payload, dict) else []
        papers: list[PaperCandidate] = []
        for rank, raw in enumerate(rows, start=1):
            if not isinstance(raw, dict) or not compact_text(raw.get("title")):
                continue
            primary = raw.get("primary_location") if isinstance(raw.get("primary_location"), dict) else {}
            best_oa = raw.get("best_oa_location") if isinstance(raw.get("best_oa_location"), dict) else {}
            source = primary.get("source") if isinstance(primary.get("source"), dict) else {}
            open_access = raw.get("open_access") if isinstance(raw.get("open_access"), dict) else {}
            percentile = raw.get("citation_normalized_percentile")
            authors: list[str] = []
            for authorship in raw.get("authorships") or []:
                if not isinstance(authorship, dict):
                    continue
                author = authorship.get("author") if isinstance(authorship.get("author"), dict) else {}
                if name := compact_text(author.get("display_name")):
                    authors.append(name)
            topics = [
                name
                for item in raw.get("topics") or []
                if isinstance(item, dict) and (name := compact_text(item.get("display_name")))
            ]
            doi = raw.get("doi")
            landing = raw.get("doi") or primary.get("landing_page_url") or raw.get("id")
            papers.append(
                PaperCandidate(
                    source=self.name,
                    source_id=str(raw.get("id") or "").rsplit("/", 1)[-1] or None,
                    source_rank=rank,
                    title=compact_text(raw.get("title")) or "",
                    abstract=reconstruct_abstract(raw.get("abstract_inverted_index")),
                    authors=authors,
                    year=raw.get("publication_year") if isinstance(raw.get("publication_year"), int) else None,
                    published_at=raw.get("publication_date"),
                    venue=compact_text(source.get("display_name")),
                    doi=doi,
                    landing_url=landing,
                    pdf_url=best_oa.get("pdf_url") or primary.get("pdf_url"),
                    citation_count=raw.get("cited_by_count") if isinstance(raw.get("cited_by_count"), int) else None,
                    is_open_access=open_access.get("is_oa") if isinstance(open_access.get("is_oa"), bool) else None,
                    fields=topics,
                    publication_types=[str(raw["type"])] if raw.get("type") else [],
                    language=compact_text(raw.get("language")),
                    is_retracted=bool(raw.get("is_retracted")),
                    fwci=float(raw["fwci"]) if isinstance(raw.get("fwci"), (int, float)) else None,
                    citation_percentile=(
                        float(percentile.get("value"))
                        if isinstance(percentile, dict) and isinstance(percentile.get("value"), (int, float))
                        else None
                    ),
                    sources=[self.name],
                )
            )
        return papers
