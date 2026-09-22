from __future__ import annotations

import re
from datetime import date
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


def compact_text(value: object, *, maximum: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    result = " ".join(value.split()).strip()
    if not result:
        return None
    return result[:maximum] if maximum else result


def safe_http_url(value: object) -> str | None:
    text = compact_text(value, maximum=2048)
    if text is None:
        return None
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else None


def normalize_doi(value: object) -> str | None:
    text = compact_text(value)
    if not text:
        return None
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.IGNORECASE).lower()


def normalize_arxiv_id(value: object) -> str | None:
    text = compact_text(value)
    if not text:
        return None
    text = re.sub(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:)", "", text, flags=re.IGNORECASE)
    return re.sub(r"v\d+(?:\.pdf)?$", "", text, flags=re.IGNORECASE).removesuffix(".pdf")


class PaperCandidate(BaseModel):
    source: Literal["semantic_scholar", "arxiv", "openalex"]
    source_id: str | None = None
    source_rank: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=1000)
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    published_at: date | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    landing_url: str | None = None
    pdf_url: str | None = None
    citation_count: int | None = Field(default=None, ge=0)
    is_open_access: bool | None = None
    fields: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    language: str | None = None
    is_retracted: bool = False
    influential_citation_count: int | None = Field(default=None, ge=0)
    fwci: float | None = None
    citation_percentile: float | None = None
    sources: list[str] = Field(default_factory=list)

    @field_validator("authors", "fields", "publication_types", "sources")
    @classmethod
    def unique_text(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in values:
            value = compact_text(item)
            if value and value.casefold() not in seen:
                seen.add(value.casefold())
                result.append(value)
        return result

    @field_validator("landing_url", "pdf_url", mode="before")
    @classmethod
    def validate_url(cls, value: object) -> str | None:
        return safe_http_url(value)

    @field_validator("doi", mode="before")
    @classmethod
    def validate_doi(cls, value: object) -> str | None:
        return normalize_doi(value)

    @field_validator("arxiv_id", mode="before")
    @classmethod
    def validate_arxiv_id(cls, value: object) -> str | None:
        return normalize_arxiv_id(value)


class RankedPaper(BaseModel):
    dedup_key: str
    paper: PaperCandidate
    relevance_score: float = Field(ge=0, le=1)
    quality_score: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    read_priority: Literal["high", "medium", "low"] = "medium"


class EnrichedPaper(BaseModel):
    ranked: RankedPaper
    summary_vi: str
    why_read_vi: list[str] = Field(min_length=1, max_length=3)


class PipelineResult(BaseModel):
    papers: list[EnrichedPaper]
    warnings: list[dict[str, object]]
    stats: dict[str, object]
