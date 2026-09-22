from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchRuntimeConfig(BaseModel):
    """Non-secret AI Research configuration managed in source control."""

    model_config = ConfigDict(validate_assignment=True)

    # AI provider and model routing
    llm_provider: Literal["groq", "openrouter"] = "groq"
    groq_url: str = "https://api.groq.com/openai/v1/chat/completions"
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_referer: str = "http://localhost"
    openrouter_app_title: str = "CyVerse AI Research Tool"
    openrouter_app_categories: str = "personal-agent"
    planner_models: list[str] = Field(
        default_factory=lambda: [
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "groq/compound-mini",
            "groq/compound",
        ],
        min_length=1,
    )
    reranker_models: list[str] = Field(
        default_factory=lambda: [
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "groq/compound-mini",
            "groq/compound",
        ],
        min_length=1,
    )
    enrichment_models: list[str] = Field(
        default_factory=lambda: [
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "groq/compound-mini",
            "groq/compound",
        ],
        min_length=1,
    )
    groq_strict_json_models: set[str] = Field(
        default_factory=lambda: {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}
    )
    groq_model_max_completion_tokens: dict[str, int] = Field(
        default_factory=lambda: {
            "qwen/qwen3.6-27b": 900,
            "qwen/qwen3.8-27b": 900,
            "openai/gpt-oss-20b": 1800,
            "openai/gpt-oss-120b": 1800,
            "groq/compound-mini": 1600,
            "groq/compound": 1600,
        }
    )
    planner_max_completion_tokens: int = Field(default=1200, ge=200, le=8000)
    reranker_max_completion_tokens: int = Field(default=1500, ge=200, le=8000)
    enrichment_max_completion_tokens: int = Field(default=1800, ge=200, le=8000)

    # Academic source endpoints and polite-pool identity
    semantic_scholar_url: str = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
    )
    arxiv_url: str = "https://export.arxiv.org/api/query"
    openalex_url: str = "https://api.openalex.org/works"
    openalex_mailto: str | None = None
    contact_email: str | None = None

    # Network resilience and provider pacing
    http_timeout_seconds: float = Field(default=30.0, ge=5.0, le=90.0)
    llm_timeout_seconds: float = Field(default=45.0, ge=5.0, le=120.0)
    request_attempts: int = Field(default=2, ge=1, le=5)
    retry_safety_margin_seconds: float = Field(default=0.5, ge=0.0, le=5.0)
    max_retry_delay_seconds: float = Field(default=90.0, ge=1.0, le=300.0)
    source_retry_min_seconds: dict[str, float] = Field(
        default_factory=lambda: {
            "semantic_scholar": 5.0,
            "arxiv": 5.0,
            "openalex": 2.0,
            "llm": 1.0,
        }
    )
    semantic_scholar_interval_seconds: float = Field(default=1.5, ge=0.0, le=30.0)
    arxiv_interval_seconds: float = Field(default=3.5, ge=0.0, le=30.0)
    openalex_interval_seconds: float = Field(default=1.5, ge=0.0, le=30.0)
    llm_interval_seconds: float = Field(default=0.4, ge=0.0, le=30.0)

    # User-facing defaults and authoritative safety limits
    query_min_length: int = Field(default=3, ge=1, le=100)
    query_max_length: int = Field(default=1000, ge=100, le=5000)
    default_raw_per_source: int = Field(default=50, ge=1, le=100)
    max_raw_per_source: int = Field(default=100, ge=1, le=100)
    default_result_limit: int = Field(default=20, ge=1, le=50)
    max_result_limit: int = Field(default=50, ge=1, le=50)

    # Embedded queue consumer
    embedded_worker: bool = True
    worker_poll_seconds: float = Field(default=1.0, ge=0.2, le=30.0)
    worker_restart_seconds: float = Field(default=5.0, ge=1.0, le=60.0)
    worker_lease_seconds: int = Field(default=300, ge=60, le=3600)
    worker_max_attempts: int = Field(default=2, ge=1, le=5)
    worker_advisory_lock_id: int = 724991

    # Ranking and enrichment policy
    ai_rerank_limit: int = Field(default=60, ge=0, le=100)
    reranker_batch_size: int = Field(default=5, ge=1, le=10)
    enrichment_batch_size: int = Field(default=5, ge=1, le=20)
    llm_attempts_per_model: int = Field(default=2, ge=1, le=3)
    rerank_ai_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    min_relevance_score: float = Field(default=0.10, ge=0.0, le=1.0)
    relevance_weight: float = Field(default=0.62, ge=0.0, le=1.0)
    quality_weight: float = Field(default=0.38, ge=0.0, le=1.0)
    diversity_lambda: float = Field(default=0.82, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_related_limits(self) -> "ResearchRuntimeConfig":
        if self.default_raw_per_source > self.max_raw_per_source:
            raise ValueError("default_raw_per_source cannot exceed max_raw_per_source")
        if self.default_result_limit > self.max_result_limit:
            raise ValueError("default_result_limit cannot exceed max_result_limit")
        if self.query_min_length > self.query_max_length:
            raise ValueError("query_min_length cannot exceed query_max_length")
        if self.relevance_weight + self.quality_weight <= 0:
            raise ValueError("ranking weights must contain a positive value")
        return self


research_config = ResearchRuntimeConfig()
