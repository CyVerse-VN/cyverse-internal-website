"""Thread-safe in-process rate limiter for academic source APIs."""

from __future__ import annotations

import threading
import time

import config


_lock = threading.Lock()
_next_request_at: dict[str, float] = {}


def request_interval_seconds(source: str) -> float:
    """Return the configured base interval plus a conservative safety margin."""
    base = float(config.SOURCE_REQUEST_INTERVAL_SECONDS.get(source, 0.0))
    margin = float(config.SOURCE_RATE_LIMIT_SAFETY_MARGIN_SECONDS.get(source, 0.0))
    return max(base + margin, 0.0)


def rate_limit_snapshot() -> dict[str, dict[str, float]]:
    """Return serializable settings for audit metadata in pipeline output."""
    sources = set(config.SOURCE_REQUEST_INTERVAL_SECONDS) | set(
        config.SOURCE_RATE_LIMIT_SAFETY_MARGIN_SECONDS
    )
    return {
        source: {
            "base_interval_seconds": float(
                config.SOURCE_REQUEST_INTERVAL_SECONDS.get(source, 0.0)
            ),
            "safety_margin_seconds": float(
                config.SOURCE_RATE_LIMIT_SAFETY_MARGIN_SECONDS.get(source, 0.0)
            ),
            "effective_interval_seconds": request_interval_seconds(source),
        }
        for source in sorted(sources)
    }


def wait_for_source(source: str) -> float:
    """Reserve the next request slot for a source and sleep until it is available."""
    interval = request_interval_seconds(source)
    if interval <= 0:
        return 0.0

    with _lock:
        now = time.monotonic()
        reserved_at = max(now, _next_request_at.get(source, now))
        _next_request_at[source] = reserved_at + interval
        delay = max(reserved_at - now, 0.0)
    if delay:
        time.sleep(delay)
    return delay


def reset_rate_limiter() -> None:
    """Clear reservations; intended for isolated tests."""
    with _lock:
        _next_request_at.clear()
