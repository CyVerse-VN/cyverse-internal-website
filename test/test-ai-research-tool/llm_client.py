"""Validated structured-output client for Groq (default) and OpenRouter."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from typing import Any, Callable

import config
from common import SourceError, compact_text, post_json
from groq_rate_limiter import observe_headers, record_usage, wait_for_capacity
from llm_cache import load_llm_cache, save_llm_cache
from openrouter_models import free_model_candidates


Validator = Callable[[dict[str, Any]], dict[str, Any]]
_SUCCESSFUL_MODEL_BY_TOOL: dict[str, str] = {}
_FAILED_MODELS_BY_TOOL: dict[str, set[str]] = {}
_OUTPUT_CONTRACT_VERSION = "1.0"


def _structured_system_prompt(
    system_prompt: str,
    tool_name: str,
    parameters: dict[str, Any],
) -> str:
    """Attach one provider-independent JSON contract to every structured AI task."""
    schema_text = json.dumps(parameters, ensure_ascii=False, separators=(",", ":"))
    return (
        system_prompt.strip()
        + "\n\nMANDATORY OUTPUT CONTRACT (version "
        + _OUTPUT_CONTRACT_VERSION
        + "):\n"
        + f"- Return exactly one JSON object for `{tool_name}` that matches the JSON Schema below.\n"
        + "- Output JSON only: no Markdown, code fence, prose, comments, or text before/after it.\n"
        + "- Include every required field and use the exact property names and JSON data types.\n"
        + "- Do not add properties that are absent from the schema.\n"
        + "- Obey every enum, range, item-count, and uniqueness constraint.\n"
        + "- When the input contains paper_id values, copy every requested paper_id exactly once; "
        + "never alter, omit, or invent an ID.\n"
        + "- Never invent paper facts. If evidence is missing, use a conservative schema-valid value.\n"
        + f"Exact JSON Schema: {schema_text}"
    )


def _parse_mapping(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        # Some free models return a Python-style dict. literal_eval cannot execute code.
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"Model output is not valid JSON/data literal: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Model output is not an object")
    return parsed


@dataclass(frozen=True)
class ToolResult:
    value: dict[str, Any]
    requested_model: str
    response_model: str
    cached: bool = False
    usage: dict[str, Any] = field(default_factory=dict)
    attempted_models: tuple[str, ...] = ()
    model_errors: tuple[str, ...] = ()
    model_discovery_error: str | None = None
    provider: str = "unknown"
    rate_limit_wait_seconds: float = 0.0


def _extract_json(text: str | None) -> dict[str, Any]:
    value = compact_text(text)
    if not value:
        raise ValueError("Model không trả tool call hoặc JSON")
    if value.startswith("```"):
        value = value.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start, end = value.find("{"), value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Không tìm thấy JSON object trong output model")
    parsed = _parse_mapping(value[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Output model không phải JSON object")
    return parsed


def _tool_arguments(message: dict[str, Any], tool_name: str) -> dict[str, Any]:
    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        if function.get("name") != tool_name:
            continue
        arguments = function.get("arguments")
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            parsed = _parse_mapping(arguments)
            if isinstance(parsed, dict):
                return parsed
    return _extract_json(message.get("content"))


def _provider_candidates(provider: str, tool_name: str) -> tuple[list[dict[str, Any]], str | None]:
    if provider == "groq":
        models = config.GROQ_TASK_MODELS.get(tool_name) or config.GROQ_TASK_MODELS["enrich_papers"]
        return [{
            "id": model,
            "strict_json": model in config.GROQ_STRICT_JSON_MODELS,
        } for model in models], None
    return free_model_candidates()


def _groq_payload(
    *,
    model: str,
    tool_name: str,
    tool_description: str,
    parameters: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    strict = model in config.GROQ_STRICT_JSON_MODELS
    outbound_messages = messages or [
        {
            "role": "system",
            "content": _structured_system_prompt(system_prompt, tool_name, parameters),
        },
        {"role": "user", "content": user_prompt},
    ]
    payload: dict[str, Any] = {
        "model": model,
        "messages": outbound_messages,
        "temperature": 0.1,
        "max_completion_tokens": max_tokens,
    }
    if strict:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": tool_name,
                "description": tool_description,
                "schema": parameters,
                "strict": True,
            },
        }
    else:
        payload["response_format"] = {"type": "json_object"}
    if model.startswith("openai/gpt-oss-"):
        payload["reasoning_effort"] = "low"
    elif model.startswith("qwen/"):
        payload["reasoning_effort"] = "none"
    return payload


def _estimated_request_tokens(payload: dict[str, Any], max_tokens: int) -> int:
    # Conservative dependency-free estimate for English/Vietnamese JSON prompts.
    input_estimate = (len(json.dumps(payload, ensure_ascii=False)) + 2) // 3
    return max(input_estimate + max_tokens, 1)


def call_tool(
    *,
    tool_name: str,
    tool_description: str,
    parameters: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    validator: Validator,
    max_tokens: int = 3000,
) -> ToolResult:
    """Call configured provider, validate output, rate-limit, and fail over by task."""
    provider = config.llm_provider()
    api_key = config.llm_api_key()
    if not api_key:
        raise SourceError(f"Thiếu {'GROQ_API_KEY' if provider == 'groq' else 'OPENROUTER_API_KEY'} trong .env")

    if provider == "groq":
        headers = {"Authorization": f"Bearer {api_key}"}
        endpoint = config.GROQ_URL
        max_tokens = min(max_tokens, int(config.GROQ_TASK_MAX_COMPLETION_TOKENS.get(tool_name, max_tokens)))
    else:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": config.secret("OPENROUTER_HTTP_REFERER") or config.OPENROUTER_DEFAULT_REFERER,
            "X-OpenRouter-Title": config.secret("OPENROUTER_APP_TITLE") or "CyVerse AI Research Tool",
            "X-OpenRouter-Categories": config.OPENROUTER_APP_CATEGORIES,
            "X-OpenRouter-App-Visibility": "hidden",
        }
        endpoint = config.OPENROUTER_URL

    effective_system_prompt = _structured_system_prompt(system_prompt, tool_name, parameters)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": effective_system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    candidates, discovery_error = _provider_candidates(provider, tool_name)
    state_key = f"{provider}:{tool_name}"
    failed_before = _FAILED_MODELS_BY_TOOL.setdefault(state_key, set())
    candidates = [item for item in candidates if str(item["id"]) not in failed_before]
    if preferred := _SUCCESSFUL_MODEL_BY_TOOL.get(state_key):
        candidates.sort(key=lambda item: str(item["id"]) != preferred)
    models = [str(item["id"]) for item in candidates]
    cache_identity = {
        "tool_name": tool_name,
        "provider": provider,
        "parameters": parameters,
        "system_prompt": effective_system_prompt,
        "user_prompt": user_prompt,
        "models": models,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if cached := load_llm_cache(cache_identity):
        try:
            return ToolResult(
                value=validator(cached["value"]),
                requested_model=str(cached["requested_model"]),
                response_model=str(cached["response_model"]),
                cached=True,
                usage=cached.get("usage") if isinstance(cached.get("usage"), dict) else {},
                attempted_models=tuple(cached.get("attempted_models") or ()),
                model_errors=tuple(cached.get("model_errors") or ()),
                model_discovery_error=cached.get("model_discovery_error"),
                provider=str(cached.get("provider") or provider),
                rate_limit_wait_seconds=float(cached.get("rate_limit_wait_seconds") or 0.0),
            )
        except (KeyError, TypeError, ValueError):
            pass
    model_errors: list[str] = []
    attempted_models: list[str] = []
    total_rate_limit_wait = 0.0
    for candidate in candidates:
        model = str(candidate["id"])
        model_max_tokens = min(
            max_tokens,
            int(config.GROQ_MODEL_MAX_COMPLETION_TOKENS.get(model, max_tokens)),
        ) if provider == "groq" else max_tokens
        attempted_models.append(model)
        model_messages = list(messages)
        for attempt in range(1, config.LLM_ATTEMPTS + 1):
            if provider == "groq":
                payload = _groq_payload(
                    model=model,
                    tool_name=tool_name,
                    tool_description=tool_description,
                    parameters=parameters,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=model_max_tokens,
                    messages=model_messages,
                )
            else:
                payload = {
                    "model": model,
                    "messages": model_messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "tools": [{
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": tool_description,
                            "parameters": parameters,
                        },
                    }],
                    "tool_choice": {"type": "function", "function": {"name": tool_name}},
                }
            response_headers: dict[str, str] = {}
            try:
                if provider == "groq":
                    total_rate_limit_wait += wait_for_capacity(
                        model, _estimated_request_tokens(payload, model_max_tokens)
                    )
                response = post_json(
                    endpoint,
                    payload=payload,
                    headers=headers,
                    timeout=config.LLM_TIMEOUT_SECONDS,
                    attempts=1,
                    response_headers_out=response_headers,
                )
            except SourceError as exc:
                if provider == "groq":
                    observe_headers(model, response_headers)
                if attempt >= config.LLM_ATTEMPTS:
                    model_errors.append(
                        f"{model}: request lỗi sau {config.LLM_ATTEMPTS} attempt: {exc}"
                    )
                    failed_before.add(model)
                    break
                continue
            try:
                if provider == "groq":
                    record_usage(
                        model,
                        response.get("usage") if isinstance(response.get("usage"), dict) else {},
                        response_headers,
                    )
                choices = response.get("choices") or []
                if not choices:
                    raise ValueError(f"{provider} response không có choices")
                message = choices[0].get("message") or {}
                value = validator(_tool_arguments(message, tool_name))
                result = ToolResult(
                    value=value,
                    requested_model=model,
                    response_model=str(response.get("model") or model),
                    usage=response.get("usage") if isinstance(response.get("usage"), dict) else {},
                    attempted_models=tuple(attempted_models),
                    model_errors=tuple(model_errors),
                    model_discovery_error=discovery_error,
                    provider=provider,
                    rate_limit_wait_seconds=round(total_rate_limit_wait, 3),
                )
                save_llm_cache(cache_identity, {
                    "value": result.value,
                    "requested_model": result.requested_model,
                    "response_model": result.response_model,
                    "usage": result.usage,
                    "attempted_models": list(result.attempted_models),
                    "model_errors": list(result.model_errors),
                    "model_discovery_error": result.model_discovery_error,
                    "provider": result.provider,
                    "rate_limit_wait_seconds": result.rate_limit_wait_seconds,
                })
                _SUCCESSFUL_MODEL_BY_TOOL[state_key] = model
                return result
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                if attempt >= config.LLM_ATTEMPTS:
                    model_errors.append(f"{model}: output không hợp lệ: {exc}")
                    failed_before.add(model)
                    break
                model_messages.append({
                    "role": "user",
                    "content": (
                        f"RETRY 1/1. Output trước không hợp lệ: {exc}. "
                        f"Hãy tạo lại đúng một JSON object cho `{tool_name}` theo toàn bộ OUTPUT CONTRACT "
                        "và exact JSON Schema trong system message. Không thêm bất kỳ nội dung nào ngoài JSON."
                    ),
                })
    raise SourceError(
        f"Đã thử hết {len(attempted_models)} model {provider} nhưng không có output hợp lệ: "
        + " | ".join(model_errors)
    )
