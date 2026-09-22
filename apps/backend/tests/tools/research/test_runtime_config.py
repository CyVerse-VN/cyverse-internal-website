import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.tools.research.config import ResearchRuntimeConfig


def test_research_runtime_config_exposes_safe_defaults() -> None:
    config = ResearchRuntimeConfig()

    assert config.llm_provider == "groq"
    assert config.default_raw_per_source == 50
    assert config.max_raw_per_source == 100
    assert config.default_result_limit == 20
    assert config.max_result_limit == 50
    assert config.embedded_worker is True


def test_environment_cannot_override_operational_research_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEARCH_MAX_RESULT_LIMIT", "1")

    environment_settings = Settings(_env_file=None)
    runtime_config = ResearchRuntimeConfig()

    assert not hasattr(environment_settings, "research_max_result_limit")
    assert runtime_config.max_result_limit == 50


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"default_raw_per_source": 51, "max_raw_per_source": 50},
            "default_raw_per_source cannot exceed max_raw_per_source",
        ),
        (
            {"default_result_limit": 21, "max_result_limit": 20},
            "default_result_limit cannot exceed max_result_limit",
        ),
        (
            {"relevance_weight": 0, "quality_weight": 0},
            "ranking weights must contain a positive value",
        ),
    ],
)
def test_research_runtime_config_validates_related_values(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        ResearchRuntimeConfig(**overrides)
