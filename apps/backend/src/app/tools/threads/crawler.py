import asyncio
import hashlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import quote, urlsplit

from playwright.async_api import BrowserContext, Page, Response, Route, async_playwright
from playwright.async_api import Error as PlaywrightError
from pydantic import BaseModel, Field, ValidationError

from app.tools.threads.config import ThreadsAccount, ThreadsConfig
from app.tools.threads.content import dom_comment_text
from app.tools.threads.errors import ThreadsError
from app.tools.threads.parser import (
    extract_comments,
    extract_search_posts,
    has_search_results,
    parse_script_json,
    search_has_next_page,
)
from app.tools.threads.schemas import ThreadsComment, ThreadsPost
from app.tools.threads.session import inspect_session_file

ALLOWED_DOMAINS = ("threads.com", "threads.net", "instagram.com", "cdninstagram.com", "fbcdn.net")
MAX_PAYLOAD_BYTES = 5_000_000
MAX_CAPTURED_BYTES = 8_000_000
SearchWarning = Callable[[str], None]
logger = logging.getLogger(__name__)

# A search feed can scroll inside a container rather than the document itself.
SCROLL_CONTAINER = """
    let scroller = document.elementFromPoint(innerWidth / 2, innerHeight * 0.65);
    while (scroller && scroller !== document.documentElement) {
        const overflow = getComputedStyle(scroller).overflowY;
        if (/^(auto|scroll)$/.test(overflow) && scroller.clientHeight > 150 &&
            scroller.scrollHeight > scroller.clientHeight + 20) break;
        scroller = scroller.parentElement;
    }
    if (!scroller || scroller === document.documentElement) {
        scroller = document.scrollingElement || document.documentElement;
    }
"""
READ_SCROLL_STATE = (
    "() => {"
    + SCROLL_CONTAINER
    + """
    return {top: scroller.scrollTop, height: scroller.scrollHeight, viewport: scroller.clientHeight};
}"""
)
SCROLL_SEARCH = "() => {" + SCROLL_CONTAINER + "scroller.scrollBy(0, 1100); }"


class ScrollState(BaseModel):
    top: float = Field(ge=0)
    height: float = Field(ge=0)
    viewport: float = Field(gt=0)

    @property
    def at_bottom(self) -> bool:
        return self.top + self.viewport >= self.height - 100


def allowed_browser_url(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.port in (None, 443)
        and not parsed.username
        and any(host == domain or host.endswith("." + domain) for domain in ALLOWED_DOMAINS)
    )


def playwright_proxy(url: str) -> dict[str, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https", "socks5"} or not parsed.hostname or not parsed.port:
        raise ThreadsError("INVALID_PROXY", "Configure a valid Threads proxy URL.", 503)
    from urllib.parse import unquote

    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    proxy = {"server": f"{parsed.scheme}://{host}:{parsed.port}"}
    if parsed.username:
        proxy["username"] = unquote(parsed.username)
    if parsed.password:
        proxy["password"] = unquote(parsed.password)
    return proxy


async def guard_request(route: Route) -> None:
    try:
        allowed = allowed_browser_url(route.request.url)
    except ValueError:
        allowed = False
    if not allowed or route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


class ThreadsCrawler(Protocol):
    async def search(
        self,
        keyword: str,
        limit: int,
        search_type: str,
        *,
        on_warning: SearchWarning | None = None,
    ) -> list[ThreadsPost]: ...
    async def comments(self, url: str, limit: int) -> list[ThreadsComment]: ...


class PlaywrightThreadsCrawler:
    def __init__(self, pages: list[Page], *, search_timeout_seconds: int = 120) -> None:
        self.pages = pages
        self.index = 0
        self.search_timeout_seconds = search_timeout_seconds

    def _page(self) -> Page:
        if not self.pages:
            raise ThreadsError("THREADS_REAUTH_REQUIRED", "No active Threads account sessions remaining.", 503)
        page = self.pages[self.index % len(self.pages)]
        self.index += 1
        return page

    @asynccontextmanager
    async def _sources(self, page: Page, url: str) -> AsyncIterator[list[object]]:
        payloads: list[object] = []
        tasks: set[asyncio.Task[None]] = set()
        received_bytes = 0
        skipped = 0

        async def capture(response: Response) -> None:
            nonlocal received_bytes, skipped
            if "graphql" not in response.url and "json" not in response.headers.get(
                "content-type", ""
            ):
                return
            if len(payloads) >= 100 or received_bytes >= MAX_CAPTURED_BYTES:
                skipped += 1
                return
            try:
                length = int(response.headers.get("content-length", "0"))
                if length > MAX_PAYLOAD_BYTES:
                    skipped += 1
                    return
                body = await response.body()
                received_bytes += len(body)
                if len(body) <= MAX_PAYLOAD_BYTES and received_bytes <= MAX_CAPTURED_BYTES:
                    payloads.append(json.loads(body))
                else:
                    skipped += 1
            except (PlaywrightError, ValueError, UnicodeDecodeError):
                # Non-JSON responses and responses aborted by media blocking are expected.
                return

        def on_response(response: Response) -> None:
            nonlocal skipped
            if "graphql" not in response.url and "json" not in response.headers.get("content-type", ""):
                return
            if len(tasks) >= 2:
                skipped += 1
                return
            task = asyncio.create_task(capture(response))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        page.on("response", on_response)
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is not None and response.status >= 400:
                logger.error("Threads page request failed: %s (status %d)", url, response.status)
                raise ThreadsError("THREADS_HTTP_ERROR", "Threads rejected the page request.", 502)
            await page.wait_for_timeout(1500)
            if "/login" in page.url or "/challenge" in page.url:
                logger.error("Threads session redirected to login or challenge: %s", page.url)
                raise ThreadsError(
                    "THREADS_REAUTH_REQUIRED", "Refresh the Threads login session.", 503
                )
            for name in (
                "Allow all cookies",
                "Allow essential and optional cookies",
                "Only allow essential cookies",
            ):
                button = page.get_by_role("button", name=name, exact=True).first
                if await button.is_visible():
                    await button.click(timeout=2000)
                    break
            yield payloads
        finally:
            page.remove_listener("response", on_response)
            for task in list(tasks):
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if skipped:
                logger.warning("Threads skipped %d responses due to capture limits", skipped)

    async def _scripts(self, page: Page) -> list[object]:
        texts = await page.locator('script[type="application/json"]').evaluate_all(
            "nodes => nodes.slice(0, 100).map(n => (n.textContent || '').slice(0, 1000000))"
        )
        sources: list[object] = []
        for text in texts:
            if isinstance(text, str):
                sources.extend(parse_script_json(text))
        return sources

    async def search(
        self,
        keyword: str,
        limit: int,
        search_type: str,
        *,
        on_warning: SearchWarning | None = None,
    ) -> list[ThreadsPost]:
        while self.pages:
            page = self._page()
            url = f"https://www.threads.com/search/?q={quote(keyword, safe='')}"
            if search_type == "recent":
                url += "&filter=latest"
            posts: dict[str, ThreadsPost] = {}
            stalled = 0
            search_ready = False
            previous_state: ScrollState | None = None
            deadline = time.monotonic() + self.search_timeout_seconds
            stop_reason = "the search scroll limit was reached"
            try:
                async with self._sources(page, url) as captured:
                    for _ in range(200):
                        before = len(posts)
                        scripts = await self._scripts(page)
                        sources = captured + scripts
                        search_ready = search_ready or has_search_results(sources)
                        try:
                            batch = extract_search_posts(sources, keyword)
                            state = ScrollState.model_validate(await page.evaluate(READ_SCROLL_STATE))
                        except (ValidationError, TypeError, ValueError, AttributeError, OverflowError) as exc:
                            logger.error(
                                "Threads returned invalid post data or scroll state for keyword %r: %s (%s)",
                                keyword,
                                type(exc).__name__,
                                exc,
                            )
                            raise ThreadsError(
                                "THREADS_INVALID_DATA", "Threads returned invalid post data.", 502
                            ) from exc
                        for post in batch:
                            if post.collected_at is None:
                                post.collected_at = datetime.now(UTC)
                            posts.setdefault(post.post_id, post)
                        has_next = search_has_next_page(captured)
                        if has_next is None:
                            has_next = search_has_next_page(scripts)
                        if len(posts) >= limit:
                            break
                        if search_ready and state.at_bottom and has_next is False:
                            stop_reason = "Threads reported no further results"
                            break
                        unchanged = (
                            previous_state is not None
                            and abs(state.height - previous_state.height) < 1
                            and abs(state.top - previous_state.top) < 1
                        )
                        stalled = (
                            stalled + 1 if state.at_bottom and unchanged and len(posts) == before else 0
                        )
                        if search_ready and stalled >= (8 if has_next is True else 4):
                            stop_reason = (
                                "pagination stopped loading although Threads advertised more results"
                                if has_next
                                else "the end of the feed stopped loading new results"
                            )
                            break
                        if time.monotonic() >= deadline:
                            stop_reason = "the per-keyword search time limit was reached"
                            break
                        previous_state = state
                        await page.evaluate(SCROLL_SEARCH)
                        await page.wait_for_timeout(1500)
                if not search_ready and not posts:
                    logger.error(
                        "Threads search failed to load any results for keyword %r (stop_reason: %s)",
                        keyword,
                        stop_reason,
                    )
                    raise ThreadsError(
                        "THREADS_SEARCH_UNAVAILABLE",
                        "Threads did not finish loading search results. Retry or refresh the account session.",
                        502,
                    )
                selected = list(posts.values())[:limit]
                logger.info(
                    "Threads search for %r collected %d unique posts (requested: %d, stop_reason: %s)",
                    keyword,
                    len(selected),
                    limit,
                    stop_reason,
                )
                if len(selected) < limit and on_warning is not None:
                    on_warning(
                        f"Collected {len(selected)} of {limit} requested unique posts: {stop_reason}."
                    )
                return selected
            except ThreadsError as exc:
                if exc.code == "THREADS_REAUTH_REQUIRED" and len(self.pages) > 1:
                    logger.warning(
                        "Threads session redirected to login/challenge on %s; skipping this account (%d remaining)",
                        page.url,
                        len(self.pages) - 1,
                    )
                    if page in self.pages:
                        self.pages.remove(page)
                    if on_warning is not None:
                        on_warning(
                            f"An account encountered a login/challenge prompt and was skipped ({len(self.pages)} account(s) remaining)."
                        )
                    continue
                raise
        raise ThreadsError(
            "THREADS_REAUTH_REQUIRED", "No active Threads account sessions remaining.", 503
        )

    async def comments(self, url: str, limit: int) -> list[ThreadsComment]:
        if not re.fullmatch(
            r"https://(?:www\.)?threads\.(?:com|net)/@[A-Za-z0-9_.]+/post/[A-Za-z0-9_-]+/?", url
        ):
            logger.error("Invalid Threads post URL for comments extraction: %s", url)
            raise ThreadsError("INVALID_POST_URL", "Threads returned an invalid post URL.", 502)
        while self.pages:
            page = self._page()
            comments: dict[str, ThreadsComment] = {}
            idle = 0
            fetch_all = limit <= 0
            max_rounds = 35 if fetch_all else max(6, limit // 4 + 3)
            try:
                async with self._sources(page, url) as captured:
                    for round_index in range(max_rounds):
                        before = len(comments)
                        for comment in extract_comments(captured + await self._scripts(page)):
                            comment.collected_at = datetime.now(UTC)
                            comments.setdefault(comment.id, comment)
                        # SSR pages can omit reply payloads; preserve their text with unknown parents.
                        dom = await page.locator('div[data-pressable-container="true"]').evaluate_all(
                            """nodes => nodes.slice(1, 150).map(node => {
                                const text = [];
                                const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                                while (walker.nextNode()) {
                                    const parent = walker.currentNode.parentElement;
                                    if (!parent?.closest('span[dir="auto"]')) continue;
                                    if (parent.closest('[data-pressable-container="true"]') !== node) continue;
                                    const control = parent.closest('time, button, [role="button"]');
                                    if (control && control !== node && node.contains(control)) continue;
                                    const value = walker.currentNode.textContent?.trim();
                                    if (value) text.push(value);
                                }
                                return {
                                    username: node.querySelector('a[href^="/@"]')?.getAttribute('href')
                                        ?.split('/@')[1]?.split(/[/?]/)[0],
                                    text
                                };
                            })"""
                        )
                        seen = {
                            (comment.username, " ".join(comment.text.split()))
                            for comment in comments.values()
                        }
                        for item in dom:
                            username = item.get("username")
                            texts = item.get("text")
                            if not isinstance(username, str) or not isinstance(texts, list):
                                continue
                            text = dom_comment_text(
                                username, [value for value in texts if isinstance(value, str)]
                            )
                            fingerprint = (username, " ".join(text.split()))
                            if len(text) < 3 or fingerprint in seen:
                                continue
                            identifier = (
                                "dom_" + hashlib.sha256(f"{username}:{text}".encode()).hexdigest()[:20]
                            )
                            comments.setdefault(
                                identifier, ThreadsComment(
                                    id=identifier, username=username, text=text,
                                    source="dom", collected_at=datetime.now(UTC),
                                )
                            )
                            seen.add(fingerprint)
                        idle = idle + 1 if len(comments) == before else 0
                        # Give cold post pages time to deliver replies before declaring them empty.
                        idle_complete = idle >= 3 and (bool(comments) or round_index >= 5)
                        if (not fetch_all and len(comments) >= limit) or idle_complete:
                            break
                        buttons = page.get_by_role(
                            "button", name=re.compile(r"View (more )?replies", re.IGNORECASE)
                        )
                        for index in range(min(await buttons.count(), 3)):
                            button = buttons.nth(index)
                            if await button.is_visible():
                                await button.click(timeout=2000)
                        await page.evaluate("window.scrollBy(0, 1100)")
                        await page.wait_for_timeout(1500)
                results = list(comments.values()) if fetch_all else list(comments.values())[:limit]
                logger.debug("Extracted %d comments from %s", len(results), url)
                return results
            except ThreadsError as exc:
                if exc.code == "THREADS_REAUTH_REQUIRED" and len(self.pages) > 1:
                    logger.warning(
                        "Threads session redirected to login/challenge during comments on %s; skipping this account (%d remaining)",
                        page.url,
                        len(self.pages) - 1,
                    )
                    if page in self.pages:
                        self.pages.remove(page)
                    continue
                raise
        return list(comments.values()) if fetch_all else list(comments.values())[:limit]


@asynccontextmanager
async def open_crawler(
    config: ThreadsConfig,
    max_accounts: int = -1,
    use_proxy: bool = True,
    search_timeout_seconds: int | None = None,
) -> AsyncIterator[ThreadsCrawler]:
    accounts = [account for account in config.accounts if account.enabled]
    if not accounts and not config.anonymous:
        logger.error("No enabled Threads accounts and anonymous mode is disabled")
        raise ThreadsError(
            "THREADS_NOT_CONFIGURED", "Configure Threads accounts or enable anonymous mode.", 503
        )

    valid_accounts: list[ThreadsAccount] = []
    for account in accounts:
        session_file = config.session_path(account)
        has_session, is_expired, _ = inspect_session_file(session_file)
        if has_session and not is_expired:
            valid_accounts.append(account)
        elif has_session and is_expired:
            logger.warning(
                "Session file for account %s is expired at %s",
                account.id,
                session_file,
            )
        else:
            logger.warning(
                "Session file for account %s missing at %s",
                account.id,
                session_file,
            )

    if not valid_accounts and not config.anonymous:
        logger.error("No active Threads account sessions available and anonymous mode is disabled")
        raise ThreadsError(
            "THREADS_REAUTH_REQUIRED",
            "Create login sessions for enabled Threads accounts.",
            503,
        )

    use_accounts = valid_accounts
    if max_accounts > 0:
        use_accounts = use_accounts[:max_accounts]

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            contexts: list[BrowserContext] = []
            try:
                for account in use_accounts or [None]:
                    proxy_cfg = (
                        playwright_proxy(account.proxy.get_secret_value())
                        if account and account.proxy and use_proxy
                        else None
                    )
                    context = await browser.new_context(
                        storage_state=str(config.session_path(account)) if account else None,
                        proxy=proxy_cfg,
                        locale="en-US",
                        viewport={"width": 1280, "height": 900},
                        service_workers="block",
                    )
                    contexts.append(context)
                    await context.route("**/*", guard_request)
                pages = [await context.new_page() for context in contexts]
                yield PlaywrightThreadsCrawler(
                    pages,
                    search_timeout_seconds=(
                        search_timeout_seconds
                        if search_timeout_seconds is not None
                        else config.search_timeout_seconds
                    ),
                )
            finally:
                await browser.close()
    except (PlaywrightError, OSError, ValueError) as exc:
        logger.error("Threads browser launch/execution failed: %s (%s)", type(exc).__name__, exc)
        raise ThreadsError(
            "THREADS_BROWSER_UNAVAILABLE",
            "Check Chromium installation, sessions, and proxy settings.",
            503,
        ) from exc
