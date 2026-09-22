import httpx
import pytest

from app.tools.research.ai import (
    QueryPlan,
    StructuredAIClient,
    _parse_json_object,
)
from app.tools.research.config import research_config
from app.tools.research.http import rate_limiter


def test_json_parser_accepts_wrapped_and_python_style_objects() -> None:
    assert _parse_json_object("```json\n{'english_question': 'test'}\n```") == {
        "english_question": "test"
    }


def test_groq_uses_json_object_only_for_models_without_strict_schema_support() -> None:
    client = StructuredAIClient(httpx.AsyncClient())
    messages = [{"role": "user", "content": "test"}]
    schema = QueryPlan.model_json_schema()

    qwen_body = client._body(
        task="plan_paper_search",
        model="qwen/qwen3.6-27b",
        messages=messages,
        schema=schema,
        max_completion_tokens=900,
    )
    gpt_body = client._body(
        task="plan_paper_search",
        model="openai/gpt-oss-20b",
        messages=messages,
        schema=schema,
        max_completion_tokens=1200,
    )

    assert qwen_body["response_format"] == {"type": "json_object"}
    assert qwen_body["reasoning_effort"] == "none"
    assert gpt_body["response_format"]["type"] == "json_schema"
    assert gpt_body["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_invalid_ai_output_is_retried_with_a_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = (
            {"english_question": "deepfake detection"}
            if calls == 1
            else {
                "english_question": "deepfake detection",
                "query_variants": ["deepfake detection"],
            }
        )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = StructuredAIClient(http_client)
        monkeypatch.setattr(client, "_api_key", lambda: "test-key")
        monkeypatch.setattr(client, "_url", lambda: "https://llm.test/chat")
        monkeypatch.setitem(rate_limiter._intervals, "llm", 0.0)
        result = await client.complete(
            task="plan_paper_search",
            models=["openai/gpt-oss-20b"],
            system_prompt="Plan the search.",
            payload={"research_request": "deepfake detection"},
            response_model=QueryPlan,
        )

    assert QueryPlan.model_validate(result).english_question == "deepfake detection"
    assert calls == research_config.llm_attempts_per_model
