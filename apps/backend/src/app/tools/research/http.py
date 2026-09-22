from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from email.utils import parsedate_to_datetime

import httpx

from app.tools.research.config import research_config

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ResearchSourceError(RuntimeError):
    def __init__(
        self, source: str, message: str, *, code: str = "source_unavailable"
    ) -> None:
        super().__init__(message)
        self.source = source
        self.code = code


class SourceRateLimiter:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._intervals = {
            "semantic_scholar": research_config.semantic_scholar_interval_seconds,
            "arxiv": research_config.arxiv_interval_seconds,
            "openalex": research_config.openalex_interval_seconds,
            "llm": research_config.llm_interval_seconds,
        }

    async def wait(self, source: str) -> None:
        lock = self._locks.setdefault(source, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            wait_seconds = self._intervals.get(source, 0.0) - (
                now - self._last_request.get(source, 0.0)
            )
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_request[source] = time.monotonic()


rate_limiter = SourceRateLimiter()


def retry_delay(
    headers: Mapping[str, str], attempt: int, minimum_delay: float = 0.0
) -> float:
    value = headers.get("retry-after")
    if value:
        try:
            requested_delay = float(value)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
                requested_delay = parsed.timestamp() - time.time()
            except (TypeError, ValueError, OverflowError):
                requested_delay = 0.0
        return min(
            max(
                requested_delay + research_config.retry_safety_margin_seconds,
                minimum_delay,
            ),
            research_config.max_retry_delay_seconds,
        )
    base_delay = max(minimum_delay, 1.0)
    return min(
        base_delay * (2**attempt) + research_config.retry_safety_margin_seconds,
        research_config.max_retry_delay_seconds,
    )


async def request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    source: str,
    params: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
    json_body: dict[str, object] | None = None,
    attempts: int | None = None,
    timeout_seconds: float | None = None,
) -> httpx.Response:
    last_status: int | None = None
    maximum_attempts = attempts or research_config.request_attempts
    minimum_delay = research_config.source_retry_min_seconds.get(source, 0.0)
    for attempt in range(maximum_attempts):
        await rate_limiter.wait(source)
        try:
            response = await client.request(
                method,
                url,
                params=params,
                headers=headers,
                json=json_body,
                timeout=timeout_seconds or research_config.http_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            if attempt + 1 >= maximum_attempts:
                raise ResearchSourceError(
                    source,
                    "The source did not respond in time.",
                    code="source_timeout",
                ) from exc
            await asyncio.sleep(retry_delay({}, attempt, minimum_delay))
            continue
        last_status = response.status_code
        if response.status_code < 400:
            return response
        if response.status_code not in RETRYABLE_STATUS_CODES:
            break
        if attempt + 1 < maximum_attempts:
            await asyncio.sleep(retry_delay(response.headers, attempt, minimum_delay))
    if last_status == 429:
        raise ResearchSourceError(
            source,
            "The source rate limit was reached.",
            code="source_rate_limited",
        )
    raise ResearchSourceError(
        source,
        f"The source returned an unavailable response ({last_status or 'network error'}).",
    )
