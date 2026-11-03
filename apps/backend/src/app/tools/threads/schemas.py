from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ThreadsParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: Literal["scraper", "travel"] = "scraper"
    keywords: list[str] = Field(default_factory=list, max_length=20)
    max_posts_per_keyword: int = Field(default=25, ge=1, le=100)
    search_type: Literal["top", "recent", "both"] = "recent"
    check_duplicate: bool = True
    include_comments: bool = True
    max_comment_posts: int = Field(default=-1, ge=-1, le=500)
    max_comments_per_post: int = Field(default=25, ge=-1, le=500)
    min_replies: int = Field(default=0, ge=0, le=10000)
    expand_query: bool = True
    keywords_per_query: int = Field(default=3, ge=1, le=5)
    pre_filter: bool = False
    pre_filter_strictness: Literal["high", "medium", "none"] = "high"
    curate: bool = False
    max_accounts: int = Field(default=3, ge=-1, le=10)
    use_proxy: bool = True
    run_timeout_seconds: int = Field(default=1800, ge=-1, le=86400)
    search_timeout_seconds: int = Field(default=120, ge=15, le=600)
    min_delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
    max_delay_seconds: float = Field(default=4.0, ge=0.0, le=60.0)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(" ".join(value.split()) for value in values))
        if any(not value or len(value) > 100 for value in cleaned):
            raise ValueError("Keywords must contain between 1 and 100 characters")
        return cleaned

    @model_validator(mode="after")
    def validate_delays(self) -> "ThreadsParameters":
        if self.min_delay_seconds > self.max_delay_seconds:
            raise ValueError("Minimum delay must not exceed maximum delay")
        return self


class ThreadsRequest(ThreadsParameters):
    query: str = Field(min_length=1, max_length=1000)
    visibility: Literal["public", "private"] = "public"


class ThreadsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visibility: Literal["public", "private"]


class ThreadsOwner(BaseModel):
    id: UUID
    display_name: str | None = None


class ThreadsConfigResponse(BaseModel):
    enabled: bool
    accounts_ready: bool
    ai_available: bool
    cloudinary_ready: bool = False
    txt_archive_enabled: bool = False
    defaults: ThreadsParameters
    limits: dict[str, int]


class ThreadsComment(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=64)
    text: str = Field(max_length=50000)
    like_count: int = Field(default=0, ge=0)
    depth: int = Field(default=1, ge=1, le=100)
    reply_to_username: str | None = None
    parent_id: str | None = None
    source: Literal["structured", "dom", "unknown"] = "unknown"
    parent_inferred: bool = False
    collected_at: datetime | None = None
    source_data: dict[str, object] | None = None
    source_data_status: Literal["captured", "omitted", "unknown"] = "unknown"


class RecommendedPlace(BaseModel):
    name: str
    category: str = ""
    address_or_area: str = ""
    note: str = ""


class ThreadsAnalysis(BaseModel):
    is_relevant: bool
    confidence_score: float = Field(ge=0, le=1)
    topic: str = Field(max_length=300)
    summary: str = Field(max_length=6000)
    recommended_places: list[RecommendedPlace] = Field(default_factory=list, max_length=20)
    key_entities: list[str] = Field(default_factory=list, max_length=30)
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"


class ThreadsPost(BaseModel):
    post_id: str = Field(min_length=1, max_length=128)
    url: str = Field(max_length=500)
    username: str = Field(min_length=1, max_length=64)
    text: str = Field(default="", max_length=50000)
    published_at: str | None = None
    like_count: int = Field(default=0, ge=0)
    reply_count: int = Field(default=0, ge=0)
    repost_count: int = Field(default=0, ge=0)
    images: list[str] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    comments: list[ThreadsComment] = Field(default_factory=list)
    ai_analysis: ThreadsAnalysis | None = None
    collected_at: datetime | None = None
    source_data: dict[str, object] | None = None
    source_data_status: Literal["captured", "omitted", "unknown"] = "unknown"
    filter_selected: bool | None = None


class ThreadsResult(BaseModel):
    query: str
    keywords: list[str]
    posts: list[ThreadsPost]
    curated_post_ids: list[str] = Field(default_factory=list)
    total_comments: int = 0
    duplicate_count: int = 0
    duration_seconds: float
    warnings: list[str] = Field(default_factory=list)
    schema_version: int = 1
    search_attempts: list[dict[str, object]] = Field(default_factory=list)


class ThreadsRunResponse(BaseModel):
    id: UUID
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    stage: str
    progress: float
    request: ThreadsRequest
    visibility: Literal["public", "private"] = "private"
    owner: ThreadsOwner | None = None
    can_manage: bool = False
    post_count: int = 0
    comment_count: int = 0
    archive_status: Literal["pending", "uploading", "ready", "failed"] = "pending"
    archive_uploaded_at: datetime | None = None
    storage_error: str | None = None
    deletion_requested: bool = False
    result: ThreadsResult | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
