"""Conservative per-model Groq RPM/TPM/RPD/TPD limiter with header feedback."""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque
from datetime import date
from typing import Any

import config
from common import SourceError


_LOCK = threading.RLock()
_LAST_REQUEST: dict[str, float] = {}
_TOKEN_EVENTS: dict[str, deque[tuple[float, int]]] = defaultdict(deque)
_DAY_COUNTS: dict[str, dict[str, Any]] = {}
_OBSERVED: dict[str, dict[str, float]] = defaultdict(dict)


def _duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip().casefold()
    if text.replace(".", "", 1).isdigit():
        return float(text)
    match = re.fullmatch(
        r"(?:(?P<hours>\d+(?:\.\d+)?)h)?"
        r"(?:(?P<minutes>\d+(?:\.\d+)?)m)?"
        r"(?:(?P<seconds>\d+(?:\.\d+)?)s)?",
        text,
    )
    if not match:
        return None
    return (
        float(match.group("hours") or 0) * 3600
        + float(match.group("minutes") or 0) * 60
        + float(match.group("seconds") or 0)
    )


def _number(headers: dict[str, str], key: str) -> float | None:
    value = headers.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def observe_headers(model: str, headers: dict[str, str]) -> None:
    """Use Groq's exact remaining/reset headers when they are available."""
    normalized = {str(key).casefold(): str(value) for key, value in headers.items()}
    now = time.monotonic()
    with _LOCK:
        observed = _OBSERVED[model]
        if (remaining := _number(normalized, "x-ratelimit-remaining-tokens")) is not None:
            observed["remaining_tokens"] = remaining
        if (reset := _duration_seconds(normalized.get("x-ratelimit-reset-tokens"))) is not None:
            observed["tokens_reset_at"] = now + reset
        if (remaining := _number(normalized, "x-ratelimit-remaining-requests")) is not None:
            observed["remaining_requests"] = remaining
        if (retry := _duration_seconds(normalized.get("retry-after"))) is not None:
            observed["retry_at"] = now + retry


def _today_state(model: str) -> dict[str, Any]:
    today = date.today().isoformat()
    state = _DAY_COUNTS.get(model)
    if not state or state["date"] != today:
        state = {"date": today, "requests": 0, "tokens": 0}
        _DAY_COUNTS[model] = state
    return state


def wait_for_capacity(model: str, estimated_tokens: int) -> float:
    """Wait before a request so configured free-tier limits retain a 20% safety margin."""
    limits = config.GROQ_MODEL_LIMITS[model]
    utilization = max(0.1, min(float(config.GROQ_RATE_LIMIT_UTILIZATION), 1.0))
    rpm_budget = max(int(float(limits["rpm"]) * utilization), 1)
    tpm_budget = max(int(float(limits["tpm"]) * utilization), 1)
    rpd_budget = max(int(float(limits["rpd"]) * utilization), 1)
    tpd = limits.get("tpd")
    tpd_budget = int(float(tpd) * utilization) if tpd else None
    interval = 60.0 / rpm_budget + float(config.GROQ_REQUEST_INTERVAL_MARGIN_SECONDS)
    estimated_tokens = max(int(estimated_tokens), 1)
    total_wait = 0.0

    while True:
        with _LOCK:
            now = time.monotonic()
            events = _TOKEN_EVENTS[model]
            while events and now - events[0][0] >= config.GROQ_RATE_LIMIT_WINDOW_SECONDS:
                events.popleft()
            state = _today_state(model)
            if state["requests"] >= rpd_budget:
                raise SourceError(f"Groq local limiter: {model} đã đạt ngưỡng an toàn RPD")
            if tpd_budget is not None and state["tokens"] + estimated_tokens > tpd_budget:
                raise SourceError(f"Groq local limiter: {model} đã đạt ngưỡng an toàn TPD")

            delays = [max(0.0, _LAST_REQUEST.get(model, 0.0) + interval - now)]
            minute_tokens = sum(tokens for _, tokens in events)
            if events and minute_tokens + estimated_tokens > tpm_budget:
                delays.append(max(
                    0.0,
                    events[0][0] + config.GROQ_RATE_LIMIT_WINDOW_SECONDS - now,
                ))
            observed = _OBSERVED[model]
            if observed.get("remaining_requests") is not None and observed["remaining_requests"] <= 0:
                raise SourceError(f"Groq header: {model} không còn request trong quota ngày")
            if observed.get("retry_at", 0.0) > now:
                delays.append(observed["retry_at"] - now)
            remaining = observed.get("remaining_tokens")
            reset_at = observed.get("tokens_reset_at", 0.0)
            if remaining is not None and estimated_tokens > remaining and reset_at > now:
                delays.append(reset_at - now)
            delay = max(delays)
            if delay <= 0.01:
                _LAST_REQUEST[model] = now
                state["requests"] += 1
                return round(total_wait, 3)
        time.sleep(min(delay + 0.05, config.GROQ_RATE_LIMIT_WINDOW_SECONDS))
        total_wait += min(delay + 0.05, config.GROQ_RATE_LIMIT_WINDOW_SECONDS)


def record_usage(model: str, usage: dict[str, Any], headers: dict[str, str]) -> None:
    observe_headers(model, headers)
    try:
        tokens = int(usage.get("total_tokens") or 0)
    except (TypeError, ValueError):
        tokens = 0
    if tokens <= 0:
        return
    with _LOCK:
        now = time.monotonic()
        _TOKEN_EVENTS[model].append((now, tokens))
        _today_state(model)["tokens"] += tokens
