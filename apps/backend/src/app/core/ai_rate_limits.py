"""Authoritative rate limits and pacing calculators for Gemini and Groq AI models.

These values ensure that the internal platform respects upstream quotas, applies
conservative safety buffers (typically 80% utilization headroom), and prevents
account rate-limit bans (HTTP 429) during batch processing and background crawling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ModelRateLimit:
    """Rate limit thresholds and safety calculations for an AI model."""

    model_id: str
    provider: Literal["gemini", "groq"]
    rpm: int  # Requests per minute
    rpd: int  # Requests per day
    tpm: int | None = None  # Tokens per minute
    tpd: int | None = None  # Tokens per day
    ash: float | None = None  # Audio seconds per hour (for audio/speech models)
    asd: float | None = None  # Audio seconds per day (for audio/speech models)
    category: str = "general"

    def safe_rpm(self, utilization: float = 0.80) -> float:
        """Return the conservative RPM limit with safety buffer."""
        budget = self.rpm * max(0.1, min(utilization, 1.0))
        return max(1.0, budget)

    def min_request_interval(
        self, utilization: float = 0.80, margin_seconds: float = 0.15
    ) -> float:
        """Return the minimum safe interval in seconds between consecutive requests.

        Formula: (60.0 / (RPM * utilization)) + margin_seconds
        """
        return round((60.0 / self.safe_rpm(utilization)) + margin_seconds, 2)

    def safe_tpm(self, utilization: float = 0.80) -> int | None:
        """Return the conservative TPM limit with safety buffer."""
        if self.tpm is None:
            return None
        return max(1, int(self.tpm * max(0.1, min(utilization, 1.0))))

    def safe_rpd(self, utilization: float = 0.80) -> int:
        """Return the conservative daily request cap."""
        return max(1, int(self.rpd * max(0.1, min(utilization, 1.0))))


# ============================================================================
# Google Gemini / Gemma Model Rate Limits
# ============================================================================
GEMINI_MODEL_LIMITS: dict[str, ModelRateLimit] = {
    "gemma-4-26b": ModelRateLimit(
        model_id="gemma-4-26b",
        provider="gemini",
        rpm=30,
        tpm=16_000,
        rpd=14_400,
        category="Other models",
    ),
    "gemma-4-31b": ModelRateLimit(
        model_id="gemma-4-31b",
        provider="gemini",
        rpm=30,
        tpm=16_000,
        rpd=14_400,
        category="Other models",
    ),
}

# ============================================================================
# Groq Model Rate Limits
# ============================================================================
GROQ_MODEL_LIMITS: dict[str, ModelRateLimit] = {
    "canopylabs/orpheus-arabic-saudi": ModelRateLimit(
        model_id="canopylabs/orpheus-arabic-saudi",
        provider="groq",
        rpm=10,
        rpd=100,
        tpm=1_200,
        tpd=3_600,
        category="TTS/Audio",
    ),
    "canopylabs/orpheus-v1-english": ModelRateLimit(
        model_id="canopylabs/orpheus-v1-english",
        provider="groq",
        rpm=10,
        rpd=100,
        tpm=1_200,
        tpd=3_600,
        category="TTS/Audio",
    ),
    "meta-llama/llama-prompt-guard-2-22m": ModelRateLimit(
        model_id="meta-llama/llama-prompt-guard-2-22m",
        provider="groq",
        rpm=30,
        rpd=14_400,
        tpm=15_000,
        tpd=500_000,
        category="Guardrails",
    ),
    "meta-llama/llama-prompt-guard-2-86m": ModelRateLimit(
        model_id="meta-llama/llama-prompt-guard-2-86m",
        provider="groq",
        rpm=30,
        rpd=14_400,
        tpm=15_000,
        tpd=500_000,
        category="Guardrails",
    ),
    "openai/gpt-oss-120b": ModelRateLimit(
        model_id="openai/gpt-oss-120b",
        provider="groq",
        rpm=30,
        rpd=1_000,
        tpm=8_000,
        tpd=200_000,
        category="LLM",
    ),
    "openai/gpt-oss-20b": ModelRateLimit(
        model_id="openai/gpt-oss-20b",
        provider="groq",
        rpm=30,
        rpd=1_000,
        tpm=8_000,
        tpd=200_000,
        category="LLM",
    ),
    "openai/gpt-oss-safeguard-20b": ModelRateLimit(
        model_id="openai/gpt-oss-safeguard-20b",
        provider="groq",
        rpm=3,
        rpd=1_000,
        tpm=2_000,
        tpd=200_000,
        category="Guardrails",
    ),
    "qwen/qwen3.8-27b": ModelRateLimit(
        model_id="qwen/qwen3.8-27b",
        provider="groq",
        rpm=30,
        rpd=1_000,
        tpm=8_000,
        tpd=200_000,
        category="LLM",
    ),
    "whisper-large-v3": ModelRateLimit(
        model_id="whisper-large-v3",
        provider="groq",
        rpm=20,
        rpd=2_000,
        ash=7_200.0,
        asd=28_800.0,
        category="Speech-to-Text",
    ),
    "whisper-large-v3-turbo": ModelRateLimit(
        model_id="whisper-large-v3-turbo",
        provider="groq",
        rpm=20,
        rpd=2_000,
        ash=7_200.0,
        asd=28_800.0,
        category="Speech-to-Text",
    ),
}

# Unified catalog index
ALL_MODEL_LIMITS: dict[str, ModelRateLimit] = {
    **GEMINI_MODEL_LIMITS,
    **GROQ_MODEL_LIMITS,
}


def get_model_rate_limit(
    model_id: str, provider: Literal["gemini", "groq"] | None = None
) -> ModelRateLimit | None:
    """Retrieve rate limits for a model ID from unified or provider catalog."""
    normalized = model_id.strip().lower()
    if provider == "gemini":
        return GEMINI_MODEL_LIMITS.get(normalized)
    if provider == "groq":
        return GROQ_MODEL_LIMITS.get(normalized)
    return ALL_MODEL_LIMITS.get(normalized)


def get_safe_request_delay(
    model_id: str,
    provider: Literal["gemini", "groq"] | None = None,
    utilization: float = 0.80,
    margin_seconds: float = 0.15,
) -> float:
    """Calculate the minimum delay (in seconds) between requests to stay within RPM.

    Defaults to a safe 2.5s delay if the model is unknown.
    """
    limit = get_model_rate_limit(model_id, provider)
    if limit is None:
        return 2.5
    return limit.min_request_interval(utilization=utilization, margin_seconds=margin_seconds)
