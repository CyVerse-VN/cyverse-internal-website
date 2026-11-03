"""Schemas shared by the Discovery Engine (query planning, triage, routing)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QueryAngle = Literal["demand", "experience", "neighborhood", "topic_specific"]
TargetContent = Literal["direct", "discussion", "both"]
CommentStatus = Literal["not_attempted", "completed", "partial", "failed"]
DiscoveryRoute = Literal["direct", "discussion", "both", "excluded", "unclassified"]


class DiscoveryQuery(BaseModel):
    text: str = Field(min_length=1, max_length=100)
    angle: QueryAngle
    target_content: TargetContent
    origin: Literal["manual", "generated"]
    rationale: str = Field(default="", max_length=300)


class DiscoveryQueryPlan(BaseModel):
    topic: str = Field(default="", max_length=300)
    geographic_scope: str | None = Field(default=None, max_length=200)
    desired_attributes: list[str] = Field(default_factory=list, max_length=20)
    exclusions: list[str] = Field(default_factory=list, max_length=20)
    queries: list[DiscoveryQuery] = Field(default_factory=list)


class PostTriage(BaseModel):
    """Multi-signal post classification. Scores are model-reported, not calibrated."""

    model_config = ConfigDict(extra="forbid")

    geo_match: Literal["yes", "no", "uncertain"]
    topic_relevance: float = Field(ge=0, le=1)
    direct_poi_score: int = Field(ge=0, le=4)
    discussion_poi_score: int = Field(ge=0, le=4)
    promotion_risk: int = Field(ge=0, le=4)
    reasons: list[str] = Field(default_factory=list, max_length=8)
    provider: str = Field(default="unknown", max_length=64)


class PostDiscovery(BaseModel):
    """Per-post discovery state stored next to the raw post data."""

    triage: PostTriage | None = None
    route: DiscoveryRoute = "unclassified"
    rank_score: float | None = None
    comment_status: CommentStatus = "not_attempted"
    comment_error: str | None = Field(default=None, max_length=200)
