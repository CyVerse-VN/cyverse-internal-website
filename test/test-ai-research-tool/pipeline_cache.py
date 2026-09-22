"""Cache normalized API responses theo source/query/filter/limit."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import config
from common import save_json


def _path(source: str, spec: dict[str, Any], limit: int) -> Path:
    normalized_spec = dict(spec)
    if isinstance(normalized_spec.get("query"), str):
        normalized_spec["query"] = re.sub(r"\s+", " ", normalized_spec["query"]).strip().casefold()
    identity = json.dumps(
        {"source": source, "spec": normalized_spec, "limit": limit},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return config.QUERY_CACHE_DIR / source / f"{digest}.json"


def load_cached(source: str, spec: dict[str, Any], limit: int) -> dict[str, Any] | None:
    if not config.ENABLE_QUERY_CACHE:
        return None
    path = _path(source, spec, limit)
    try:
        age = time.time() - path.stat().st_mtime
        ttl = config.QUERY_CACHE_TTL_BY_SOURCE.get(source, config.QUERY_CACHE_TTL_SECONDS)
        if age > ttl:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_cached(source: str, spec: dict[str, Any], limit: int, value: dict[str, Any]) -> None:
    if config.ENABLE_QUERY_CACHE:
        save_json(value, _path(source, spec, limit))
