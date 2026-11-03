"""Pydantic schemas for Evidence-grounded POI Mentions, Claims, and Candidates."""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

ClaimType = Literal[
    "location",
    "food",
    "price",
    "experience",
    "feature",
    "warning",
    "correction",
    "closure",
]
SentimentType = Literal["positive", "neutral", "negative", "unknown"]
VerificationStatus = Literal["unresolved", "candidate", "verified", "rejected"]


class POIClaim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    mention_id: str
    claim_type: ClaimType
    value: str = Field(min_length=1, max_length=512)
    evidence_text: str = Field(min_length=1, max_length=2000)
    source_post_id: str
    source_comment_id: str | None = None
    sentiment: SentimentType = "unknown"


class POIMention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    name_text: str = Field(min_length=1, max_length=256)
    category_text: str | None = Field(default=None, max_length=128)
    area_text: str | None = Field(default=None, max_length=256)
    address_text: str | None = Field(default=None, max_length=512)

    source_post_id: str
    source_comment_id: str | None = None

    evidence_text: str = Field(min_length=1, max_length=2000)
    start_offset: int | None = None
    end_offset: int | None = None

    context_incomplete: bool = False


class POICandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_name: str = Field(min_length=1, max_length=256)
    category: str | None = None
    area: str | None = None
    address: str | None = None
    verification_status: VerificationStatus = "candidate"

    mentions: list[POIMention] = Field(default_factory=list)
    claims: list[POIClaim] = Field(default_factory=list)
    distinct_sources_count: int = 1
