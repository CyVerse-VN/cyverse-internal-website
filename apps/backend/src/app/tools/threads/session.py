import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def inspect_session_data(data: dict[str, object]) -> tuple[bool, bool, str | None]:
    """Inspect Playwright storage_state session data.

    Returns:
        tuple of (has_session, is_expired, expires_at_iso)
    """
    cookies = data.get("cookies")
    if not isinstance(cookies, list):
        return False, False, None
    session_cookie = next(
        (
            c
            for c in cookies
            if isinstance(c, dict)
            and c.get("name") == "sessionid"
            and c.get("value")
            and str(c.get("domain", "")).lstrip(".") in {"threads.com", "threads.net", "instagram.com"}
        ),
        None,
    )
    if not session_cookie:
        return False, False, None

    expires = session_cookie.get("expires")
    if isinstance(expires, (int, float)) and expires > 0:
        is_expired = expires <= time.time()
        try:
            expires_at = datetime.fromtimestamp(expires, tz=UTC).isoformat()
        except (ValueError, OverflowError, OSError):
            expires_at = None
        return True, is_expired, expires_at

    return True, False, None


def inspect_session_file(path: Path) -> tuple[bool, bool, str | None]:
    """Inspect a Playwright storage_state session file on disk.

    Returns:
        tuple of (has_session, is_expired, expires_at_iso)
    """
    if not path.is_file():
        return False, False, None
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            return inspect_session_data(data)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        logger.warning("Could not read or parse session file at %s: %s", path, exc)
    return False, False, None


def parse_session_bundle(data: object) -> dict[str, dict[str, object]]:
    """Extract individual account sessions from a bundled JSON format.

    Supports:
      - {"sessions": {"acc_01": {...}, "acc_02": {...}}}
      - {"acc_01": {...}, "acc_02": {...}}
      - [{"id": "acc_01", "cookies": [...]}, ...]
    """
    results: dict[str, dict[str, object]] = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                acc_id = item.get("id") or item.get("account_id")
                sess = item.get("session_data") or item.get("session") or item
                if isinstance(acc_id, str) and isinstance(sess, dict) and "cookies" in sess:
                    results[acc_id] = sess
        return results

    if not isinstance(data, dict):
        return results

    sessions_obj = data.get("sessions")
    if isinstance(sessions_obj, dict):
        for acc_id, sess in sessions_obj.items():
            if isinstance(sess, dict) and "cookies" in sess:
                results[acc_id] = sess
        return results

    for key, val in data.items():
        if isinstance(val, dict) and "cookies" in val:
            results[key] = val

    return results


def create_session_bundle(sessions_by_account: dict[str, dict[str, object]]) -> dict[str, object]:
    """Create a unified threads_sessions.json bundle dictionary."""
    return {
        "version": 1,
        "updated_at": datetime.now(UTC).isoformat(),
        "sessions": sessions_by_account,
    }
