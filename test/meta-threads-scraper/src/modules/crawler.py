from __future__ import annotations

import asyncio
import random
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote
from playwright.async_api import Browser, BrowserContext, Page

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


from threads_parser.browser import collect_script_json, dismiss_cookie_banner
from threads_parser.search import extract_search_posts
from .proxy import format_playwright_proxy


async def simulate_human_mouse(page: Page) -> None:
    """Mô phỏng thao tác di chuột tự nhiên của người thật trên trang."""
    try:
        vp = page.viewport_size or {"width": 1280, "height": 900}
        w, h = vp["width"], vp["height"]
        for _ in range(random.randint(1, 2)):
            x = random.randint(int(w * 0.2), int(w * 0.8))
            y = random.randint(int(h * 0.2), int(h * 0.8))
            steps = random.randint(3, 7)
            await page.mouse.move(x, y, steps=steps)
            await asyncio.sleep(random.uniform(0.1, 0.25))
    except Exception:
        pass


def format_post(raw: dict[str, Any], keyword: str, timestamp: str) -> dict[str, Any]:
    """Chuẩn hóa dữ liệu bài viết sang định dạng schema đồng nhất."""
    media_items = raw.get("media", [])
    images = (
        [m["url"] for m in media_items if isinstance(m, dict) and m.get("type") == "image"]
        if media_items else raw.get("images", [])
    )
    videos = (
        [m["url"] for m in media_items if isinstance(m, dict) and m.get("type") == "video"]
        if media_items else raw.get("videos", [])
    )
    code_val = raw.get("code")
    permalink_val = raw.get("permalink") or raw.get("url")
    if not code_val and permalink_val and "/post/" in permalink_val:
        code_val = permalink_val.rstrip("/").split("/post/")[-1].split("/")[0]

    return {
        "post_id": raw.get("id") or raw.get("post_id"),
        "code": code_val,
        "url": permalink_val,
        "username": raw.get("username"),
        "user_id": raw.get("user_id"),
        "text": raw.get("text"),
        "published_at": raw.get("timestamp") or raw.get("published_at"),
        "like_count": raw.get("like_count", 0) or 0,
        "reply_count": raw.get("reply_count", 0) or 0,
        "repost_count": raw.get("repost_count", 0) or 0,
        "images": images,
        "videos": videos,
        "search_keywords": [keyword],
        "scraped_at": timestamp,
    }


async def scrape_single_keyword(
    page: Page,
    keyword: str,
    limit: int = 15,
    enable_mouse_move: bool = True,
) -> list[dict[str, Any]]:
    """Cào danh sách bài viết từ một từ khóa trên Threads."""
    encoded_query = quote(keyword)
    search_url = f"https://www.threads.com/search/?q={encoded_query}&filter=latest"

    captured_payloads: list[Any] = []

    async def on_response(res: Any):
        try:
            lower = res.url.lower()
            if "graphql" in lower or ("threads." in lower and any(k in lower for k in ("api", "query", "search"))):
                c_type = res.headers.get("content-type", "").lower()
                if "json" in c_type or "graphql" in lower:
                    data = await res.json()
                    if isinstance(data, (dict, list)):
                        captured_payloads.append(data)
        except Exception:
            pass

    page.on("response", on_response)

    try:
        await page.goto(search_url, wait_until="networkidle", timeout=25000)
    except Exception:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    await dismiss_cookie_banner(page)
    await asyncio.sleep(2.0)

    all_posts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    no_new_rounds = 0
    max_scrolls = max(3, limit // 3)

    for _ in range(max_scrolls):
        scripts = await collect_script_json(page)
        all_sources = list(captured_payloads) + list(scripts)
        new_batch = extract_search_posts(all_sources)

        added = 0
        for p in new_batch:
            pid = p.get("id") or p.get("post_id") or p.get("permalink") or p.get("url")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_posts.append(p)
                added += 1

        if len(all_posts) >= limit:
            break

        if added == 0:
            no_new_rounds += 1
            if no_new_rounds >= 3:
                break
        else:
            no_new_rounds = 0

        if enable_mouse_move:
            await simulate_human_mouse(page)

        scroll_y = random.randint(800, 1400)
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await asyncio.sleep(random.uniform(1.2, 2.0))

    try:
        page.remove_listener("response", on_response)
    except Exception:
        pass

    return all_posts[:limit]


def extract_hierarchical_comments(sources: list[Any]) -> list[dict[str, Any]]:
    """
    Trích xuất toàn diện bình luận từ GraphQL và Script JSON của Threads,
    bảo toàn ID, nội dung, lượt thích, độ sâu phân cấp (depth), người được phản hồi và parent_id.
    """
    extracted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def parse_node(obj: Any):
        if isinstance(obj, dict):
            # Nhận diện cấu trúc comment / reply của Threads
            if ("caption" in obj or "text" in obj) and "user" in obj and isinstance(obj.get("user"), dict):
                u = obj["user"].get("username")
                caption = obj.get("caption")
                text = None
                if isinstance(caption, dict):
                    text = caption.get("text")
                elif isinstance(caption, str):
                    text = caption
                elif isinstance(obj.get("text"), str):
                    text = obj.get("text")

                pk = str(obj.get("pk") or obj.get("id") or "")
                tp = obj.get("text_post_app_info") or {}

                is_reply = tp.get("is_reply", False) or tp.get("reply_level") is not None
                if u and text and pk and pk not in seen_ids and is_reply:
                    seen_ids.add(pk)
                    clean_text = " ".join(text.split())
                    depth = tp.get("reply_level", 1)
                    reply_to = tp.get("reply_to_author")
                    reply_to_user = (
                        reply_to.get("username")
                        if isinstance(reply_to, dict)
                        else (str(reply_to) if reply_to else None)
                    )
                    extracted.append({
                        "id": pk,
                        "username": u,
                        "text": clean_text,
                        "like_count": int(obj.get("like_count", 0) or 0),
                        "depth": int(depth or 1),
                        "reply_to_username": reply_to_user,
                        "parent_id": None,
                    })

            for v in obj.values():
                parse_node(v)
        elif isinstance(obj, list):
            for item in obj:
                parse_node(item)

    for data in sources:
        parse_node(data)

    # Tái tạo parent_id theo mô hình ngăn xếp độ sâu (Depth Stack Tree)
    depth_stack: list[tuple[int, str]] = []  # [(depth, comment_id)]
    for c in extracted:
        d = c["depth"]
        while depth_stack and depth_stack[-1][0] >= d:
            depth_stack.pop()
        c["parent_id"] = depth_stack[-1][1] if depth_stack else None
        depth_stack.append((d, c["id"]))

    return extracted


async def scrape_post_comments(
    page: Page,
    post_url: str,
    max_comments: int = 25,
    enable_mouse_move: bool = True,
) -> list[dict[str, Any]]:
    """
    Mở bài viết Threads và cào sâu các bình luận thảo luận bên dưới.
    - Hỗ trợ cuộn động vô hạn (infinite dynamic scroll) nếu max_comments <= 0 hoặc -1 (lấy tất cả).
    - Tự động click các nút 'Xem thêm phản hồi' / 'View more replies'.
    - Bóc tách phân cấp độ sâu (depth, reply_to_username, parent_id).
    """
    captured_payloads: list[Any] = []

    async def on_response(res: Any):
        try:
            lower = res.url.lower()
            if "graphql" in lower or ("threads." in lower and any(k in lower for k in ("api", "query", "post", "reply"))):
                c_type = res.headers.get("content-type", "").lower()
                if "json" in c_type or "graphql" in lower:
                    data = await res.json()
                    if isinstance(data, (dict, list)):
                        captured_payloads.append(data)
        except Exception:
            pass

    page.on("response", on_response)

    try:
        await page.goto(post_url, wait_until="networkidle", timeout=25000)
    except Exception:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    await dismiss_cookie_banner(page)
    await asyncio.sleep(1.5)

    fetch_all = (max_comments <= 0)
    target_count = 999999 if fetch_all else max_comments

    # Giới hạn số lượt cuộn: nếu lấy tất cả thì tối đa 35 vòng cuộn, nếu có giới hạn thì dựa vào target
    max_scroll_rounds = 35 if fetch_all else max(6, (max_comments // 4) + 3)
    no_new_rounds = 0
    all_comments: list[dict[str, Any]] = []
    seen_texts: set[str] = set()

    for _ in range(max_scroll_rounds):
        # 1. Trích xuất từ GraphQL & Scripts JSON
        scripts = await collect_script_json(page)
        all_sources = list(captured_payloads) + list(scripts)
        gql_comments = extract_hierarchical_comments(all_sources)

        existing_ids = {c["id"] for c in all_comments if c.get("id")}
        newly_added = 0
        for gc in gql_comments:
            if gc["id"] not in existing_ids:
                existing_ids.add(gc["id"])
                seen_texts.add(gc["text"])
                all_comments.append(gc)
                newly_added += 1

        # 2. Bổ trợ trích xuất DOM (cho bài viết tải dạng SSR)
        try:
            dom_items = await page.evaluate('''() => {
                const results = [];
                const elements = document.querySelectorAll('div[data-pressable-container="true"]');
                elements.forEach((el, index) => {
                    if (index === 0) return; // Bỏ qua bài viết gốc
                    const userLink = el.querySelector('a[href^="/@"]');
                    const username = userLink ? userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0] : null;
                    const textNodes = Array.from(el.querySelectorAll('span[dir="auto"]')).map(s => s.innerText.trim()).filter(Boolean);
                    if (username && textNodes.length > 0) {
                        results.push({ username, textNodes });
                    }
                });
                return results;
            }''')
            for item in dom_items:
                uname = item.get("username")
                nodes = item.get("textNodes", [])
                parts = []
                likes = 0
                for node in nodes:
                    n_clean = node.strip()
                    if not n_clean:
                        continue
                    if uname and n_clean.lower() == uname.lower():
                        continue
                    if n_clean in ("·", "Tác giả", "Author", "Theo dõi", "Đang theo dõi", "Translate", "Dịch", "Trả lời", "Reply"):
                        continue
                    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", n_clean) or re.match(r"^\d+[hdwmys]$", n_clean):
                        continue
                    if re.match(r"^\d+$", n_clean):
                        try:
                            likes = int(n_clean)
                        except Exception:
                            pass
                        continue
                    parts.append(n_clean)
                full_c = " ".join(" ".join(parts).split())
                if len(full_c) > 2 and full_c not in seen_texts and uname:
                    seen_texts.add(full_c)
                    dom_id = f"dom_{len(all_comments) + 1:03d}"
                    all_comments.append({
                        "id": dom_id,
                        "username": uname,
                        "text": full_c,
                        "like_count": likes,
                        "depth": 1,
                        "reply_to_username": None,
                        "parent_id": None,
                    })
                    newly_added += 1
        except Exception:
            pass

        # Kiểm tra điều kiện đủ số lượng
        if not fetch_all and len(all_comments) >= target_count:
            break

        # Tự động click các nút "Xem thêm phản hồi"
        try:
            more_buttons = [
                'div[role="button"]:has-text("Xem thêm câu trả lời")',
                'div[role="button"]:has-text("Xem thêm phản hồi")',
                'div[role="button"]:has-text("Xem câu trả lời")',
                'div[role="button"]:has-text("Xem thêm")',
                'div[role="button"]:has-text("View replies")',
                'div[role="button"]:has-text("View more replies")',
            ]
            clicked_any = False
            for sel in more_buttons:
                loc = page.locator(sel)
                cnt = await loc.count()
                for i in range(min(cnt, 3)):
                    btn = loc.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        clicked_any = True
                        await asyncio.sleep(0.3)
            if clicked_any:
                no_new_rounds = 0
        except Exception:
            pass

        # Kiểm tra xem có lấy thêm được comment mới không
        if newly_added > 0:
            no_new_rounds = 0
        else:
            no_new_rounds += 1

        # Nếu sau 3 vòng cuộn liên tiếp không có comment nào mới -> Đã tải hết
        if no_new_rounds >= 3:
            break

        # Mô phỏng chuột và cuộn trang
        if enable_mouse_move:
            await simulate_human_mouse(page)

        scroll_y = random.randint(900, 1400)
        await page.evaluate(f"window.scrollBy(0, {scroll_y})")
        await asyncio.sleep(random.uniform(1.2, 1.8))

    try:
        page.remove_listener("response", on_response)
    except Exception:
        pass

    return all_comments if fetch_all else all_comments[:target_count]


class WorkerPool:
    """Quản lý các Playwright Context cô lập cho từng tài khoản và hỗ trợ xoay vòng (Round-Robin)."""

    def __init__(self, browser: Browser):
        self.browser = browser
        self.workers: list[dict[str, Any]] = []

    async def initialize(
        self,
        session_files: list[Path],
        accounts: list[dict[str, Any]],
        block_media: bool = True,
        fallback_proxy: str | None = None,
        auth_enabled: bool = True,
        account_proxy_toggle: dict[str, bool] | None = None,
        proxy_pool: list[str] | None = None,
        global_proxy_enabled: bool = False,
    ) -> None:
        proxy_map = {
            str(a.get("id") or a.get("username", "")).lower(): a.get("proxy", "")
            for a in accounts
        }
        proxy_toggle = {k.lower(): v for k, v in (account_proxy_toggle or {}).items()}
        pool = list(proxy_pool or [])

        # Khởi tạo worker cho từng tài khoản đã có session
        if auth_enabled and session_files:
            for s_idx, s_path in enumerate(session_files):
                acc_key = s_path.stem.lower()

                # Kiểm tra tài khoản này có bật proxy không
                if acc_key in proxy_toggle:
                    use_proxy = bool(proxy_toggle[acc_key])
                else:
                    use_proxy = global_proxy_enabled

                acc_proxy = None
                if use_proxy:
                    explicit_p = proxy_map.get(acc_key)
                    if explicit_p:
                        acc_proxy = explicit_p
                    elif pool:
                        acc_proxy = pool[s_idx % len(pool)]
                    else:
                        acc_proxy = fallback_proxy

                c_kwargs: dict[str, Any] = {
                    "viewport": {"width": 1280, "height": 900},
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "extra_http_headers": {
                        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"',
                    },
                    "storage_state": str(s_path),
                }

                p_dict = format_playwright_proxy(acc_proxy) if acc_proxy else None
                if p_dict:
                    c_kwargs["proxy"] = p_dict

                try:
                    ctx = await self.browser.new_context(**c_kwargs)
                    if block_media:
                        await ctx.route(
                            "**/*",
                            lambda r: r.abort() if r.request.resource_type in ["image", "media", "font"] else r.continue_(),
                        )
                    pg = await ctx.new_page()
                    self.workers.append({
                        "id": acc_key,
                        "session": s_path.name,
                        "proxy": acc_proxy,
                        "context": ctx,
                        "page": pg,
                    })
                except Exception as exc:
                    print(f"⚠️ Lỗi khởi tạo context cho {acc_key}: {exc}")
                    continue

                p_info = f"Proxy: {acc_proxy}" if acc_proxy else "Kết nối: Trực tiếp (Direct IP)"
                icon = "🌐" if acc_proxy else "🏠"
                try:
                    print(f"🔑 [Auth Pool Worker] {acc_key} ({s_path.name}) ➡️ {icon} {p_info}")
                except Exception:
                    pass

        # Fallback Anonymous Worker nếu không có session
        if not self.workers:
            c_kwargs = {
                "viewport": {"width": 1280, "height": 900},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "extra_http_headers": {
                    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            }
            p_dict = format_playwright_proxy(fallback_proxy) if fallback_proxy else None
            if p_dict:
                c_kwargs["proxy"] = p_dict

            ctx = await self.browser.new_context(**c_kwargs)
            if block_media:
                await ctx.route(
                    "**/*",
                    lambda r: r.abort() if r.request.resource_type in ["image", "media", "font"] else r.continue_(),
                )
            pg = await ctx.new_page()
            self.workers.append({
                "id": "anonymous",
                "session": None,
                "proxy": fallback_proxy,
                "context": ctx,
                "page": pg,
            })
            if auth_enabled:
                print("⚠️ [Auth] auth.enabled=true nhưng chưa tìm thấy session trong 'sessions/'. Đang chạy Ẩn danh.")
            else:
                p_info = f"Proxy: {fallback_proxy}" if fallback_proxy else "Kết nối: Trực tiếp (Direct)"
                print(f"🌐 [Crawler Ready] Chế độ Ẩn danh (Guest) ➡️ {p_info}")

    def get_worker(self, index: int) -> dict[str, Any]:
        """Lấy worker luân phiên theo chỉ số (Round-Robin)."""
        return self.workers[index % len(self.workers)]

    async def close(self) -> None:
        """Đóng tất cả browser context của các worker."""
        for w in self.workers:
            try:
                await w["context"].close()
            except Exception:
                pass
        self.workers.clear()
