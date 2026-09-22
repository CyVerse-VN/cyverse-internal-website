"""Cache structured LLM output; cache key không chứa API key."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import config
from common import save_json


def _path(identity: dict[str, Any]) -> Path:
    serialized = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return config.LLM_CACHE_DIR / f"{digest}.json"


def load_llm_cache(identity: dict[str, Any]) -> dict[str, Any] | None:
    if not config.ENABLE_LLM_CACHE:
        return None
    path = _path(identity)
    try:
        if time.time() - path.stat().st_mtime > config.LLM_CACHE_TTL_SECONDS:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_llm_cache(identity: dict[str, Any], value: dict[str, Any]) -> None:
    if config.ENABLE_LLM_CACHE:
        save_json(value, _path(identity))
