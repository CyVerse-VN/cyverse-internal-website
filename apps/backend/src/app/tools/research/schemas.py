from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.tools.research.config import research_config

PIPELINE_VERSION = "3.0.0"
CONFIG_SCHEMA_VERSION = "1"


class ResearchSource(str, Enum):
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    OPENALEX = "openalex"


class ResearchVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class PublicationType(str, Enum):
    ARTICLE = "article"
    CONFERENCE = "conference"
    PREPRINT = "preprint"
    REVIEW = "review"
    BOOK = "book"
    DATASET = "dataset"


LanguageCode = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=r"^[a-zA-Z]{2,3}$")]


def default_year_range() -> tuple[int, int]:
    current_year = datetime.now(UTC).year
    return current_year - 2, current_year


class ResearchSettingsInput(BaseModel):
    sources: list[ResearchSource] = Field(default_factory=lambda: list(ResearchSource), min_length=1)
    raw_limits: dict[ResearchSource, int] = Field(default_factory=dict)
    result_limit: int = Field(default=research_config.default_result_limit, ge=1)
    all_years: bool = False
    year_from: int | None = None
    year_to: int | None = None
    publication_types: list[PublicationType] = Field(default_factory=list)
    languages: list[LanguageCode] = Field(default_factory=list, max_length=5)
    open_access_only: bool = False
    require_abstract: bool = True

    @field_validator("sources", "publication_types")
    @classmethod
    def unique_enum_values(cls, value: list[object]) -> list[object]:
        return list(dict.fromkeys(value))

    @field_validator("languages")
    @classmethod
    def unique_languages(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_limits_and_years(self) -> ResearchSettingsInput:
        current_year = datetime.now(UTC).year
        maximum_year = current_year + 1
        if self.result_limit > research_config.max_result_limit:
            raise ValueError(
                f"result_limit cannot exceed {research_config.max_result_limit}"
            )
        for source, value in self.raw_limits.items():
            if source not in self.sources:
                raise ValueError(f"raw limit supplied for disabled source {source.value}")
            if not 1 <= value <= research_config.max_raw_per_source:
                raise ValueError(
                    f"raw limit must be between 1 and {research_config.max_raw_per_source}"
                )
        for name, value in (("year_from", self.year_from), ("year_to", self.year_to)):
            if value is not None and not 2020 <= value <= maximum_year:
                raise ValueError(f"{name} must be between 2020 and {maximum_year}")
        if (
            self.all_years
            and (self.year_from is not None or self.year_to is not None)
        ):
            raise ValueError("all_years cannot be combined with year_from or year_to")
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("year_from cannot exceed year_to")
        return self

    def effective(self) -> ResearchSettingsInput:
        year_from, year_to = default_year_range()
        values = self.model_dump()
        if not self.all_years:
            values["year_from"] = self.year_from if self.year_from is not None else year_from
            values["year_to"] = self.year_to if self.year_to is not None else year_to
        values["raw_limits"] = {
            source: self.raw_limits.get(source, research_config.default_raw_per_source)
            for source in self.sources
        }
        return ResearchSettingsInput.model_validate(values)


class CreateResearchSessionRequest(BaseModel):
    query: str
    visibility: ResearchVisibility = ResearchVisibility.PUBLIC
    settings: ResearchSettingsInput = Field(default_factory=ResearchSettingsInput)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = " ".join(value.split())
        if not research_config.query_min_length <= len(value) <= research_config.query_max_length:
            raise ValueError(
                "query length must be between "
                f"{research_config.query_min_length} and {research_config.query_max_length}"
            )
        return value


class UpdateResearchSessionRequest(BaseModel):
    visibility: ResearchVisibility | None = None
    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
    ] | None = None

    @model_validator(mode="after")
    def require_change(self) -> UpdateResearchSessionRequest:
        if self.visibility is None and self.title is None:
            raise ValueError("visibility or title is required")
        return self


class ResearchConfigResponse(BaseModel):
    schema_version: str = CONFIG_SCHEMA_VERSION
    default_visibility: ResearchVisibility = ResearchVisibility.PUBLIC
    sources: list[ResearchSource] = Field(default_factory=lambda: list(ResearchSource))
    publication_types: list[PublicationType] = Field(default_factory=lambda: list(PublicationType))
    defaults: ResearchSettingsInput
    limits: dict[str, int]


class OwnerSummary(BaseModel):
    id: UUID
    display_name: str


class ProgressEventResponse(BaseModel):
    sequence: int
    stage: str
    status: str
    message: str
    progress: float
    metadata: dict[str, object]
    created_at: datetime


class ResearchPaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rank: int
    relevance_score: float
    read_priority: Literal["high", "medium", "low"]
    title: str
    authors: list[str]
    year: int | None
    published_at: date | None
    venue: str | None
    doi: str | None
    arxiv_id: str | None
    sources: list[str]
    paper_type: str
    fields: list[str]
    citation_count: int | None
    is_open_access: bool | None
    pdf_url: str | None
    landing_url: str | None
    summary_vi: str
    why_read_vi: list[str] = Field(min_length=1, max_length=3)
    analysis_basis: Literal["abstract"] = "abstract"


class ResearchSessionSummary(BaseModel):
    id: UUID
    query: str
    title: str
    visibility: ResearchVisibility
    owner: OwnerSummary
    is_owner: bool
    can_manage: bool
    status: str
    current_stage: str
    progress: float
    queue_position: int | None
    result_count: int
    created_at: datetime
    updated_at: datetime


class ResearchSessionDetail(ResearchSessionSummary):
    effective_settings: ResearchSettingsInput
    pipeline_version: str
    warnings: list[object]
    result_stats: dict[str, object]
    error: dict[str, str] | None
    events: list[ProgressEventResponse]
    papers: list[ResearchPaperResponse]


class ResearchSessionListResponse(BaseModel):
    items: list[ResearchSessionSummary]
    next_cursor: str | None
