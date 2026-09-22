"""HTTP, chuẩn hóa dữ liệu và CLI dùng chung cho ba nguồn paper."""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import config
from academic_rate_limiter import wait_for_source


RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
SearchFunction = Callable[[str, int, float], dict[str, Any]]
VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class SourceError(RuntimeError):
    """Lỗi từ API nguồn, an toàn để hiển thị."""


def compact_text(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def normalize_doi(value: Any) -> str | None:
    text = compact_text(value)
    if not text:
        return None
    text = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.I)
    return text.lower() or None


def normalize_arxiv_id(value: Any) -> str | None:
    text = compact_text(value)
    if not text:
        return None
    text = re.sub(r"^https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/", "", text, flags=re.I)
    text = re.sub(r"\.pdf$", "", text, flags=re.I)
    return re.sub(r"v\d+$", "", text.rstrip("/")) or None


def normalize_date_vietnam(value: Any) -> str | None:
    """Normalize a paper date to YYYY-MM-DD using Vietnam calendar time."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        return value.isoformat()
    else:
        text = compact_text(value)
        if not text:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            try:
                return date.fromisoformat(text).isoformat()
            except ValueError:
                return None
        parsed = None
        try:
            parsed = datetime.fromisoformat(re.sub(r"[zZ]$", "+00:00", text))
        except ValueError:
            for pattern in ("%Y/%m/%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(text, pattern).date().isoformat()
                except ValueError:
                    continue
        if parsed is None:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(VIETNAM_TIMEZONE).date().isoformat()


def reconstruct_abstract(inverted_index: Any) -> str | None:
    if not isinstance(inverted_index, dict):
        return None
    positioned_words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            positioned_words.extend(
                (position, str(word)) for position in positions if isinstance(position, int)
            )
    positioned_words.sort(key=lambda item: item[0])
    return compact_text(" ".join(word for _, word in positioned_words))


def strip_id_url(value: Any) -> str | None:
    """Rút ID cuối URL nhưng vẫn chấp nhận ID đã được rút gọn."""
    text = compact_text(value)
    if not text:
        return None
    return text.rstrip("/").rsplit("/", 1)[-1]


def prune_empty(value: Any) -> Any:
    """Bỏ None/chuỗi/list/object rỗng nhưng giữ False và 0."""
    if isinstance(value, dict):
        cleaned = {key: prune_empty(item) for key, item in value.items()}
        return {
            key: item for key, item in cleaned.items()
            if item is not None and item != "" and item != [] and item != {}
        }
    if isinstance(value, list):
        cleaned = [prune_empty(item) for item in value]
        return [item for item in cleaned if item is not None and item != "" and item != [] and item != {}]
    return value


def paper_record(
    *,
    source_name: str,
    source_id: str | None,
    source_rank: int,
    title: str,
    abstract: str | None,
    authors: list[str] | None = None,
    year: int | None = None,
    published_at: Any = None,
    updated_at: Any = None,
    venue: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
    url: str | None = None,
    pdf_url: str | None = None,
    citation_count: int | None = None,
    reference_count: int | None = None,
    is_open_access: bool | None = None,
    fields: list[str] | None = None,
    publication_types: list[str] | None = None,
    source_specific: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tạo paper phẳng, ổn định và gọn cho cả ba nguồn."""
    normalized_published_at = normalize_date_vietnam(published_at)
    normalized_updated_at = normalize_date_vietnam(updated_at)
    normalized_year = year
    if normalized_year is None and normalized_published_at:
        normalized_year = int(normalized_published_at[:4])
    return {
        "schema_version": config.PAPER_SCHEMA_VERSION,
        "source": source_name,
        "source_id": source_id,
        "source_rank": source_rank,
        "title": title,
        "abstract": abstract,
        "authors": authors or [],
        "year": normalized_year,
        "published_at": normalized_published_at,
        "updated_at": normalized_updated_at,
        "venue": venue,
        "doi": normalize_doi(doi),
        "arxiv_id": normalize_arxiv_id(arxiv_id),
        "url": url,
        "pdf_url": pdf_url,
        "citation_count": citation_count,
        "reference_count": reference_count,
        "is_open_access": is_open_access,
        "fields": fields or [],
        "publication_types": list(dict.fromkeys(publication_types or [])),
        "source_specific": prune_empty(source_specific or {}),
    }


def _retry_delay(headers: Any, attempt: int, minimum_delay: float) -> float:
    value = headers.get("Retry-After") if headers else None
    if value:
        try:
            requested_delay = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                requested_delay = max(
                    (retry_at - datetime.now(timezone.utc)).total_seconds(), 0.0
                )
            except (TypeError, ValueError, OverflowError):
                requested_delay = 0.0
        return min(
            max(requested_delay + config.RETRY_SAFETY_MARGIN_SECONDS, minimum_delay),
            config.MAX_RETRY_DELAY_SECONDS,
        )
    base = max(float(minimum_delay), 1.0)
    return min(
        base * (2 ** (attempt - 1)) + config.RETRY_SAFETY_MARGIN_SECONDS,
        config.MAX_RETRY_DELAY_SECONDS,
    )


def http_get(
    url: str,
    *,
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float,
    minimum_retry_delay: float = 0.0,
    rate_limit_source: str | None = None,
) -> bytes:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"Accept": "*/*", "User-Agent": config.user_agent(), **(headers or {})},
    )
    for attempt in range(1, config.REQUEST_ATTEMPTS + 1):
        if rate_limit_source:
            wait_for_source(rate_limit_source)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_HTTP_CODES and attempt < config.REQUEST_ATTEMPTS:
                time.sleep(_retry_delay(exc.headers, attempt, minimum_retry_delay))
                continue
            try:
                detail = compact_text(exc.read(300).decode("utf-8", errors="replace"))
            except Exception:
                detail = None
            raise SourceError(f"HTTP {exc.code}{f': {detail}' if detail else ''}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            if attempt < config.REQUEST_ATTEMPTS:
                time.sleep(_retry_delay(None, attempt, minimum_retry_delay))
                continue
            raise SourceError(f"Lỗi mạng: {getattr(exc, 'reason', exc)}") from exc
    raise SourceError("Request thất bại sau các lần retry")


def get_json(
    url: str,
    *,
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float,
    minimum_retry_delay: float = 0.0,
    rate_limit_source: str | None = None,
) -> dict[str, Any]:
    try:
        payload = json.loads(http_get(
            url, params=params, headers=headers, timeout=timeout,
            minimum_retry_delay=minimum_retry_delay,
            rate_limit_source=rate_limit_source,
        ))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceError("Response không phải JSON hợp lệ") from exc
    if not isinstance(payload, dict):
        raise SourceError("Cấu trúc JSON response không đúng dự kiến")
    return payload


def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float,
    attempts: int | None = None,
    response_headers_out: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST JSON với retry và thông báo lỗi an toàn, không log headers/secret."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": config.user_agent(),
            **(headers or {}),
        },
    )
    maximum_attempts = max(int(attempts or config.REQUEST_ATTEMPTS), 1)
    for attempt in range(1, maximum_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response_headers_out is not None:
                    response_headers_out.update(dict(response.headers.items()))
                value = json.loads(response.read())
                if not isinstance(value, dict):
                    raise SourceError("Cấu trúc JSON response không đúng dự kiến")
                return value
        except urllib.error.HTTPError as exc:
            if response_headers_out is not None and exc.headers:
                response_headers_out.update(dict(exc.headers.items()))
            if exc.code in RETRYABLE_HTTP_CODES and attempt < maximum_attempts:
                time.sleep(_retry_delay(exc.headers, attempt, 0.0))
                continue
            try:
                detail = compact_text(exc.read(500).decode("utf-8", errors="replace"))
            except Exception:
                detail = None
            raise SourceError(f"HTTP {exc.code}{f': {detail}' if detail else ''}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            if attempt < maximum_attempts:
                time.sleep(_retry_delay(None, attempt, 0.0))
                continue
            raise SourceError(f"Lỗi mạng: {getattr(exc, 'reason', exc)}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SourceError("Response không phải JSON hợp lệ") from exc
    raise SourceError("Request thất bại sau các lần retry")


def source_parser(source_name: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Test lấy paper từ {source_name}.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", nargs="?", default=config.DEFAULT_QUERY, help="keyword/câu tìm kiếm")
    parser.add_argument("--limit", type=int, default=config.DEFAULT_LIMIT, help="số paper cần lấy (1-20)")
    parser.add_argument("--timeout", type=float, default=config.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path, help="đường dẫn JSON output tùy chỉnh")
    parser.add_argument("--no-save", action="store_true", help="chỉ in JSON, không lưu file")
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not 1 <= args.limit <= 20:
        parser.error("--limit phải nằm trong khoảng 1-20")
    if args.timeout <= 0:
        parser.error("--timeout phải lớn hơn 0")


def result_path(source_name: str, custom_path: Path | None, no_save: bool) -> Path | None:
    if no_save or (not config.SAVE_RESULTS_BY_DEFAULT and custom_path is None):
        return None
    return custom_path or config.OUTPUT_DIR / f"{source_name}.json"


def save_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def execute_source(
    source_name: str,
    search: SearchFunction,
    query: str,
    limit: int,
    timeout: float,
) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    print(f"[{source_name}] Đang lấy dữ liệu...", file=sys.stderr, flush=True)
    try:
        result = search(query, limit, timeout)
        payload = {
            "schema_version": config.PAPER_SCHEMA_VERSION,
            "source": source_name, "ok": True, "query": query, "limit": limit,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 3), **result,
        }
        print(f"[{source_name}] Thành công: {len(result['papers'])} paper", file=sys.stderr)
        return payload, 0
    except (SourceError, ValueError) as exc:
        payload = {
            "schema_version": config.PAPER_SCHEMA_VERSION,
            "source": source_name, "ok": False, "query": query, "limit": limit,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error": str(exc), "papers": [],
        }
        print(f"[{source_name}] Thất bại: {exc}", file=sys.stderr)
        return payload, 1


def run_source_cli(source_name: str, search: SearchFunction) -> int:
    parser = source_parser(source_name)
    args = parser.parse_args()
    validate_args(parser, args)
    payload, exit_code = execute_source(source_name, search, args.query, args.limit, args.timeout)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    output_path = result_path(source_name, args.output, args.no_save)
    if output_path:
        save_json(payload, output_path)
        print(f"Đã lưu: {output_path.resolve()}", file=sys.stderr)
    return exit_code


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
