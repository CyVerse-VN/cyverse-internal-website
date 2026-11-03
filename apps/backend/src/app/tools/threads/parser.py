from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from app.tools.threads.schemas import ThreadsComment, ThreadsPost

BASE_URL = "https://www.threads.com"
SENSITIVE_SOURCE_KEYS = frozenset({"password", "authorization", "cookie", "cookies", "access_token", "refresh_token", "sessionid", "csrf_token"})


def source_record(value: dict[str, object]) -> dict[str, object]:
    """Preserve source records while excluding common authentication fields."""
    def clean(item: object) -> object:
        if isinstance(item, dict):
            return {key: clean(child) for key, child in item.items()
                    if isinstance(key, str) and key.lower() not in SENSITIVE_SOURCE_KEYS}
        if isinstance(item, list):
            return [clean(child) for child in item]
        return item

    cleaned = clean(value)
    assert isinstance(cleaned, dict)
    return cleaned


POST_HINT_KEYS = frozenset(
    {
        "id",
        "pk",
        "text",
        "caption",
        "permalink",
        "media_url",
        "image_versions2",
        "video_versions",
        "carousel_media",
        "timestamp",
        "taken_at",
        "code",
        "shortcode",
        "searchResults",
        "search_results",
        "inform_module",
    }
)
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".m4v", ".webm"})
POST_URL_RE = re.compile(r"https?://(?:www\.)?threads\.(?:com|net)/@[^/\s\"']+/post/[^?\s\"']+")
AVATAR_PATH_RE = re.compile(r"/t51\.\d+-19/")


def walk_json(value: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            found.append(item)
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return found


def parse_script_json(text: str) -> list[object]:
    text = text.strip()
    if not text or not any(key in text for key in POST_HINT_KEYS):
        return []

    decoder = json.JSONDecoder()
    parsed: list[object] = []
    starts = [0] if text[:1] in "[{" else [m.start() for m in re.finditer(r"[\[{]", text)]

    for start in starts[:400]:
        try:
            item, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(item, (dict, list)):
            parsed.append(item)
    return parsed


def first_value(item: dict[str, object], keys: tuple[str, ...]) -> object:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, UTC).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.isdigit():
            return normalize_timestamp(int(value))
        return value
    return None


def normalize_permalink(value: str) -> str | None:
    value = unquote(value.strip())
    if not value:
        return None
    if value.startswith("/@"):
        value = f"{BASE_URL}{value}"
    match = POST_URL_RE.fullmatch(value)
    if not match:
        return None
    return re.sub(r"/media/?$", "", match.group(0))


def media_type_from_url(key: str, url: str) -> str | None:
    lower_key = key.lower()
    parsed = urlparse(url)
    suffix = Path(parsed.path.lower()).suffix
    host = parsed.netloc.lower()

    if suffix in VIDEO_EXTENSIONS or "video" in lower_key:
        return "video"
    if suffix in IMAGE_EXTENSIONS or any(
        marker in lower_key for marker in ("image", "photo", "thumbnail", "display")
    ):
        return "image"
    if "media_url" in lower_key and any(
        marker in host for marker in ("fbcdn", "cdninstagram", "scontent", "threads.")
    ):
        return "unknown"
    return None


def normalize_media_entry(item: dict[str, object]) -> dict[str, str] | None:
    url = item.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    if is_ignored_media_url(url):
        return None
    media_type = item.get("type")
    if not isinstance(media_type, str) or not media_type:
        media_type = media_type_from_url("", url) or "unknown"
    local_path = item.get("local_path")
    return {
        "type": media_type,
        "url": url,
        "local_path": local_path if isinstance(local_path, str) else "",
    }


def media_key(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    source_url = query.get("url", [""])[0]
    if source_url:
        parsed = urlparse(unquote(source_url))
    filename = Path(unquote(parsed.path)).name.lower()
    return filename or f"{parsed.netloc.lower()}{parsed.path}"


def is_ignored_media_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return (
        bool(AVATAR_PATH_RE.search(path))
        or "/static/images/spotify_branding/" in path
        or "/static/images/apple_podcasts_branding/" in path
    )


def media_score(item: dict[str, object]) -> int:
    width = item.get("width") or item.get("original_width") or item.get("w") or 0
    height = item.get("height") or item.get("original_height") or item.get("h") or 0
    try:
        return int(width) * int(height)
    except (TypeError, ValueError):
        return 0


def best_candidate_url(value: object) -> str | None:
    candidates: list[dict[str, object]] = []
    if isinstance(value, list):
        candidates = [item for item in value if isinstance(item, dict)]
    elif isinstance(value, dict):
        raw_candidates = value.get("candidates") or value.get("additional_candidates")
        if isinstance(raw_candidates, list):
            candidates = [item for item in raw_candidates if isinstance(item, dict)]
        elif isinstance(value.get("url"), str):
            candidates = [value]

    best = max(candidates, key=media_score, default=None)
    url = best.get("url") if best else None
    return url if isinstance(url, str) else None


def add_media_url(
    media: list[dict[str, str]], seen: set[str], url: object, media_type: str | None
) -> None:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return
    if is_ignored_media_url(url):
        return
    key = media_key(url)
    if key in seen:
        return
    seen.add(key)
    media.append({"type": media_type or "unknown", "url": url, "local_path": ""})


def collect_media(item: dict[str, object]) -> list[dict[str, str]]:
    media: list[dict[str, str]] = []
    seen: set[str] = set()
    stack: list[tuple[object, str | None]] = [(item, None)]

    while stack:
        current, forced_type = stack.pop()
        if isinstance(current, list):
            stack.extend((entry, forced_type) for entry in current)
            continue
        if not isinstance(current, dict):
            continue

        for key, value in current.items():
            lower_key = key.lower()
            if lower_key in {"user", "owner", "author", "viewer"} or any(
                marker in lower_key for marker in ("avatar", "profile_pic", "profile_image")
            ):
                continue
            if lower_key in {"image_versions2", "image_versions"}:
                add_media_url(media, seen, best_candidate_url(value), "image")
                continue
            if lower_key == "video_versions":
                add_media_url(media, seen, best_candidate_url(value), "video")
                continue
            if lower_key in {"carousel_media", "carousel_media_v2"}:
                stack.append((value, None))
                continue
            if isinstance(value, str):
                media_type = forced_type or media_type_from_url(key, value)
                if media_type:
                    add_media_url(media, seen, value, media_type)
            elif isinstance(value, (dict, list)):
                stack.append((value, forced_type))

    return media


def normalize_post(item: dict[str, object], target_username: str) -> dict[str, object] | None:
    if not set(item) & POST_HINT_KEYS:
        return None

    username = target_username
    for source in (item, item.get("user"), item.get("owner"), item.get("author")):
        if not isinstance(source, dict):
            continue
        value = first_value(source, ("username", "user_name"))
        if isinstance(value, str) and value.strip():
            username = value.strip().lstrip("@")
            break

    permalink = None
    for value in (item.get(key) for key in ("permalink", "url", "post_url", "share_url")):
        if isinstance(value, str) and (permalink := normalize_permalink(value)):
            break

    code = first_value(item, ("code", "shortcode"))
    shortcode = (
        code.strip()
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_-]{6,}", code.strip())
        else None
    )
    if not permalink and shortcode and re.fullmatch(r"[A-Za-z0-9_.]+", username):
        permalink = f"{BASE_URL}/@{username}/post/{shortcode}"

    identifier = first_value(item, ("id", "pk", "media_id")) or shortcode
    if not identifier and permalink:
        identifier = permalink.rstrip("/").split("/")[-1]
    if not identifier:
        return None

    text = ""
    text_value = first_value(item, ("text", "caption", "caption_text"))
    if isinstance(text_value, dict):
        text_value = first_value(text_value, ("text", "body", "plain_text"))
    if isinstance(text_value, str):
        text = text_value.strip()

    timestamp = None
    for value in (
        item.get(key)
        for key in ("timestamp", "taken_at", "taken_at_timestamp", "created_at", "created_time")
    ):
        if timestamp := normalize_timestamp(value):
            break
    if not text and not timestamp and not permalink:
        return None

    display_name = None
    for source in (item.get("user"), item.get("owner"), item.get("author")):
        if isinstance(source, dict):
            name_val = first_value(source, ("full_name", "display_name", "name"))
            if isinstance(name_val, str) and name_val.strip():
                display_name = name_val.strip()
                break

    like_count = item.get("like_count")
    if not isinstance(like_count, (int, float)):
        like_count = None

    text_app_info = item.get("text_post_app_info")
    reply_count = None
    if isinstance(text_app_info, dict):
        reply_val = text_app_info.get("direct_reply_count")
        if isinstance(reply_val, (int, float)):
            reply_count = int(reply_val)
    if reply_count is None:
        raw_reply = item.get("reply_count") or item.get("comment_count")
        if isinstance(raw_reply, (int, float)):
            reply_count = int(raw_reply)

    repost_count = None
    if isinstance(text_app_info, dict):
        repost_val = text_app_info.get("repost_count")
        if isinstance(repost_val, (int, float)):
            repost_count = int(repost_val)
    if repost_count is None:
        raw_repost = item.get("repost_count") or item.get("reshare_count")
        if isinstance(raw_repost, (int, float)):
            repost_count = int(raw_repost)

    media_items = collect_media(item)
    media_urls = [m["url"] for m in media_items if isinstance(m, dict) and m.get("url")]

    return {
        "id": str(identifier),
        "username": username,
        "display_name": display_name,
        "text": text,
        "timestamp": timestamp,
        "permalink": permalink,
        "like_count": like_count,
        "reply_count": reply_count,
        "repost_count": repost_count,
        "media": media_items,
        "media_urls": media_urls,
    }


def has_search_results(sources: list[object]) -> bool:
    """Distinguish a valid empty search response from a page that is still loading."""
    return any(
        isinstance(result := item.get("searchResults"), dict)
        and isinstance(result.get("edges"), list)
        for source in sources
        for item in walk_json(source)
    )


def search_has_next_page(sources: list[object]) -> bool | None:
    """Read the latest available pagination flag; missing metadata is not exhaustion."""
    for source in reversed(sources):
        for item in walk_json(source):
            result = item.get("searchResults")
            page_info = result.get("page_info") if isinstance(result, dict) else None
            has_next = page_info.get("has_next_page") if isinstance(page_info, dict) else None
            if isinstance(has_next, bool):
                return has_next
    return None


def extract_search_posts(sources: list[object], keyword: str) -> list[ThreadsPost]:
    """Read only root posts from search edges, excluding embedded quoted posts."""
    posts: dict[str, ThreadsPost] = {}
    for source in sources:
        for item in walk_json(source):
            result = item.get("searchResults")
            if not isinstance(result, dict) or not isinstance(result.get("edges"), list):
                continue
            for edge in result["edges"]:
                if not isinstance(edge, dict):
                    continue
                node = edge.get("node")
                thread = node.get("thread") if isinstance(node, dict) else None
                entries = thread.get("thread_items") if isinstance(thread, dict) else None
                if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
                    continue
                raw = entries[0].get("post")
                if not isinstance(raw, dict):
                    continue
                normalized = normalize_post(raw, "")
                if not normalized or not normalized["username"] or not normalized["permalink"]:
                    continue
                media = normalized["media"]
                source_data = source_record(raw)
                post = ThreadsPost.model_validate(
                    {
                        "post_id": normalized["id"],
                        "url": normalized["permalink"],
                        "username": normalized["username"],
                        "text": normalized["text"],
                        "published_at": normalized["timestamp"],
                        "like_count": count(normalized["like_count"]),
                        "reply_count": count(normalized["reply_count"]),
                        "repost_count": count(normalized["repost_count"]),
                        "images": [entry["url"] for entry in media if entry["type"] == "image"],
                        "videos": [entry["url"] for entry in media if entry["type"] == "video"],
                        "search_keywords": [keyword],
                        "source_data": source_data,
                        "source_data_status": "captured" if source_data is not None else "omitted",
                    }
                )
                posts.setdefault(post.post_id, post)
    return list(posts.values())


def count(value: object) -> int:
    try:
        return max(0, int(value)) if isinstance(value, (str, int, float)) else 0
    except (ValueError, OverflowError):
        return 0


def extract_comments(sources: list[object]) -> list[ThreadsComment]:
    """Preserve explicit parents and infer missing parents from reply levels."""
    comments: dict[str, ThreadsComment] = {}
    stack: list[ThreadsComment] = []
    # walk_json uses a LIFO stack; reversing children preserves response order here.
    pending = list(reversed(sources))
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            pending.extend(reversed(item))
            continue
        if not isinstance(item, dict):
            continue
        pending.extend(reversed(list(item.values())))
        user = item.get("user")
        info = item.get("text_post_app_info")
        if not isinstance(user, dict) or not isinstance(info, dict):
            continue
        if not info.get("is_reply") and info.get("reply_level") is None:
            continue
        caption = item.get("caption")
        text = caption.get("text") if isinstance(caption, dict) else caption or item.get("text")
        identifier = item.get("pk") or item.get("id")
        username = user.get("username")
        if not identifier or not isinstance(username, str) or not isinstance(text, str):
            continue
        identifier = str(identifier)
        if identifier in comments or not text.strip():
            continue
        depth = max(1, min(100, count(info.get("reply_level")) or 1))
        while stack and stack[-1].depth >= depth:
            stack.pop()
        parent = info.get("reply_to_id") or info.get("replied_to_post_id")
        reply_to = info.get("reply_to_author")
        reply_username = reply_to.get("username") if isinstance(reply_to, dict) else reply_to
        source_data = source_record(item)
        comment = ThreadsComment(
            id=identifier,
            username=username,
            text=text,
            like_count=count(item.get("like_count")),
            depth=depth,
            parent_id=str(parent) if parent else stack[-1].id if stack else None,
            reply_to_username=reply_username if isinstance(reply_username, str) else None,
            source="structured",
            parent_inferred=not bool(parent) and bool(stack),
            source_data=source_data,
            source_data_status="captured" if source_data is not None else "omitted",
        )
        comments[identifier] = comment
        stack.append(comment)
    return list(comments.values())
