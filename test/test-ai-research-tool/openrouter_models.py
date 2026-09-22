"""Discover and order currently available free OpenRouter text models."""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any

import config
from common import SourceError, get_json


_MEMORY_CACHE: list[dict[str, Any]] | None = None


def _zero_price(value: Any) -> bool:
    try:
        return float(value or 0) == 0.0
    except (TypeError, ValueError):
        return False


def _is_free_text_model(model: dict[str, Any]) -> bool:
    model_id = model.get("id")
    pricing = model.get("pricing") or {}
    architecture = model.get("architecture") or {}
    outputs = architecture.get("output_modalities") or []
    if not isinstance(model_id, str) or not model_id:
        return False
    if "prompt" not in pricing or "completion" not in pricing:
        return False
    if any(
        term in model_id.casefold()
        for term in ("safety", "guard", "moderation", "embedding", "rerank", "tts", "music")
    ):
        return False
    if outputs and set(outputs) != {"text"}:
        return False
    return (
        _zero_price(pricing.get("prompt"))
        and _zero_price(pricing.get("completion"))
        and _zero_price(pricing.get("request"))
    )


def _parameter_billions(model: dict[str, Any]) -> float:
    """Best-effort active/dense parameter count; the Models API has no standard size field."""
    text = " ".join(str(model.get(key) or "") for key in ("id", "name", "description"))
    patterns = (
        r"(\d+(?:\.\d+)?)\s*[Bb]\s+active\s+parameters",
        r"(\d+(?:\.\d+)?)\s+billion\s+active\s+parameters",
        r"(?:^|[-_/\s])(\d+(?:\.\d+)?)\s*[Bb](?:$|[-_/\s])",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return float(match.group(1))
    return math.inf


def _compact_priority(model: dict[str, Any]) -> tuple[Any, ...]:
    text = f"{model.get('id', '')} {model.get('name', '')}".casefold()
    parameters = _parameter_billions(model)
    if re.search(r"\b(?:xs|nano|tiny|micro)\b", text):
        size_tier = 0
    elif parameters <= 4:
        size_tier = 1
    elif re.search(r"\b(?:s|mini|small|lite|flash)\b", text) or parameters <= 12:
        size_tier = 2
    elif parameters <= 32:
        size_tier = 3
    elif math.isfinite(parameters):
        size_tier = 5
    else:
        size_tier = 4
    if re.search(r"\b(?:pro|max|large|ultra)\b", text):
        size_tier += 2
    supported = set(model.get("supported_parameters") or [])
    tool_penalty = 0 if {"tools", "tool_choice"}.issubset(supported) else 1
    context_length = int(model.get("context_length") or 0)
    return (size_tier, parameters, tool_penalty, -context_length, str(model.get("id")))


def _load_disk_cache(path: Path) -> list[dict[str, Any]] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - float(value["saved_at"])
        models = value["models"]
        if age <= config.OPENROUTER_MODEL_CATALOG_TTL_SECONDS and isinstance(models, list):
            return [item for item in models if isinstance(item, dict)]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return None


def _save_disk_cache(path: Path, models: list[dict[str, Any]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"saved_at": time.time(), "models": models}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def discover_free_models(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    """Return all suitable zero-price models, ordered from compact to large/unknown."""
    global _MEMORY_CACHE
    if _MEMORY_CACHE is not None and not force_refresh:
        return list(_MEMORY_CACHE)
    if not force_refresh:
        cached = _load_disk_cache(config.OPENROUTER_MODEL_CATALOG_CACHE)
        if cached is not None:
            cached = [
                item for item in cached
                if _is_free_text_model(item)
                and int(item.get("context_length") or 0) >= config.OPENROUTER_MIN_CONTEXT_LENGTH
            ]
            cached.sort(key=_compact_priority)
            _MEMORY_CACHE = cached
            return list(cached)

    headers = {}
    if api_key := config.secret("OPENROUTER_API_KEY"):
        headers["Authorization"] = f"Bearer {api_key}"
    response = get_json(
        config.OPENROUTER_MODELS_URL,
        params={},
        headers=headers,
        timeout=config.OPENROUTER_MODEL_CATALOG_TIMEOUT_SECONDS,
    )
    raw_models = response.get("data")
    if not isinstance(raw_models, list):
        raise SourceError("OpenRouter models response không có data array")
    models = [
        item for item in raw_models
        if isinstance(item, dict)
        and _is_free_text_model(item)
        and int(item.get("context_length") or 0) >= config.OPENROUTER_MIN_CONTEXT_LENGTH
    ]
    models.sort(key=_compact_priority)
    if not models:
        raise SourceError("OpenRouter không trả model text miễn phí phù hợp")
    _MEMORY_CACHE = models
    _save_disk_cache(config.OPENROUTER_MODEL_CATALOG_CACHE, models)
    return list(models)


def free_model_candidates() -> tuple[list[dict[str, Any]], str | None]:
    """Build exhaustive candidates; configured IDs remain usable if discovery fails."""
    discovery_error = None
    try:
        discovered = discover_free_models()
    except SourceError as exc:
        discovered = []
        discovery_error = str(exc)

    by_id = {
        str(item["id"]): item for item in discovered
        if isinstance(item.get("id"), str)
    }
    ordered_ids = []
    if config.OPENROUTER_MODEL:
        ordered_ids.append(config.OPENROUTER_MODEL)
    ordered_ids.extend(
        str(item["id"]) for item in discovered
        if item.get("id") != config.OPENROUTER_FALLBACK_MODEL
    )
    if config.OPENROUTER_FALLBACK_MODEL:
        ordered_ids.append(config.OPENROUTER_FALLBACK_MODEL)

    result = []
    for model_id in dict.fromkeys(ordered_ids):
        metadata = by_id.get(model_id, {})
        supported = set(metadata.get("supported_parameters") or [])
        result.append({
            "id": model_id,
            "supports_tools": not metadata or {"tools", "tool_choice"}.issubset(supported),
            "context_length": metadata.get("context_length"),
            "parameter_billions": (
                None if not metadata or not math.isfinite(_parameter_billions(metadata))
                else _parameter_billions(metadata)
            ),
        })
    if config.OPENROUTER_FREE_MODEL_MAX_TRIES > 0:
        result = result[:config.OPENROUTER_FREE_MODEL_MAX_TRIES]
    return result, discovery_error
