import asyncio
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from app.tools.research.config import research_config
from app.tools.research.domain import PaperCandidate, compact_text, normalize_arxiv_id
from app.tools.research.http import (
    RETRYABLE_STATUS_CODES,
    ResearchSourceError,
    rate_limiter,
    retry_delay,
)
from app.tools.research.sources.base import PaperSource

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def xml_text(node: ET.Element, path: str) -> str | None:
    return compact_text(node.findtext(path))


def _fetch_arxiv_sync(url: str, user_agent: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/atom+xml,application/xml,text/xml,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "are", "is", "was", "were", "be", "been", "being", "the", "a", "an",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "and", "or",
    "recent", "latest", "overview", "advancements", "developments", "study",
}


class ArxivSource(PaperSource):
    name = "arxiv"

    async def search(
        self, query: str, *, limit: int, filters: dict[str, object]
    ) -> list[PaperCandidate]:
        words = [w for w in re.findall(r"[\w-]+", query.lower()) if len(w) > 1]
        content_words = [w for w in words if w not in STOP_WORDS]
        terms = content_words[:5] if content_words else words[:5]
        search_query = "+AND+".join(f"all:{w}" for w in terms) if terms else "all:research"
        url = (
            f"{research_config.arxiv_url}?"
            f"search_query={search_query}&start=0&max_results={limit}"
            f"&sortBy=relevance&sortOrder=descending"
        )
        user_agent = "CyVerse-AI-Research/3.0"
        if research_config.contact_email:
            user_agent = f"{user_agent} ({research_config.contact_email})"

        content: bytes | None = None
        last_error: Exception | None = None
        for attempt in range(research_config.request_attempts):
            await rate_limiter.wait(self.name)
            await self.checkpoint()
            try:
                content = await asyncio.to_thread(
                    _fetch_arxiv_sync,
                    url,
                    user_agent,
                    research_config.http_timeout_seconds,
                )
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 429:
                    if attempt + 1 < research_config.request_attempts:
                        await asyncio.sleep(retry_delay(exc.headers, attempt, 3.0))
                        continue
                    raise ResearchSourceError(
                        self.name,
                        "The source rate limit was reached.",
                        code="source_rate_limited",
                    ) from exc
                if exc.code not in RETRYABLE_STATUS_CODES:
                    raise ResearchSourceError(
                        self.name,
                        f"The source returned an unavailable response ({exc.code}).",
                    ) from exc
                if attempt + 1 < research_config.request_attempts:
                    await asyncio.sleep(retry_delay(exc.headers, attempt, 3.0))
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt + 1 >= research_config.request_attempts:
                    raise ResearchSourceError(
                        self.name,
                        "The source did not respond in time.",
                        code="source_timeout",
                    ) from exc
                await asyncio.sleep(retry_delay({}, attempt, 3.0))

        if content is None:
            raise ResearchSourceError(
                self.name,
                f"The source returned an unavailable response ({last_error}).",
            )

        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ResearchSourceError(self.name, "arXiv returned malformed data.") from exc
        papers: list[PaperCandidate] = []
        for rank, entry in enumerate(root.findall(f"{ATOM}entry"), start=1):
            identifier = xml_text(entry, f"{ATOM}id")
            arxiv_id = normalize_arxiv_id(identifier)
            title = xml_text(entry, f"{ATOM}title")
            if not title or not arxiv_id:
                continue
            pdf_url = None
            landing_url = identifier
            for link in entry.findall(f"{ATOM}link"):
                href = link.attrib.get("href")
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = href
                elif link.attrib.get("rel") == "alternate":
                    landing_url = href
            published = xml_text(entry, f"{ATOM}published")
            categories = [item.attrib.get("term", "") for item in entry.findall(f"{ATOM}category")]
            doi = xml_text(entry, f"{ARXIV}doi")
            papers.append(
                PaperCandidate(
                    source=self.name,
                    source_id=arxiv_id,
                    source_rank=rank,
                    title=title,
                    abstract=xml_text(entry, f"{ATOM}summary"),
                    authors=[
                        name
                        for node in entry.findall(f"{ATOM}author")
                        if (name := xml_text(node, f"{ATOM}name"))
                    ],
                    year=int(published[:4]) if published and re.match(r"^\d{4}", published) else None,
                    published_at=published[:10] if published else None,
                    venue="arXiv",
                    doi=doi,
                    arxiv_id=arxiv_id,
                    landing_url=landing_url,
                    pdf_url=pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
                    is_open_access=True,
                    fields=categories,
                    publication_types=["preprint"],
                    sources=[self.name],
                )
            )
        return papers
