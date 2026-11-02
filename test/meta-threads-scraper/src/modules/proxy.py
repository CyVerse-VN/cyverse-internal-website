from __future__ import annotations

import asyncio
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
import httpx

CDN_ENDPOINTS = {
    "http": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt",
    "https": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/https/data.txt",
    "socks5": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
    "all": "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt",
}


def format_playwright_proxy(proxy_url: str) -> dict[str, str] | None:
    """Chuyển đổi chuỗi URL proxy thành định dạng dict chuẩn cho Playwright BrowserContext."""
    if not proxy_url or not proxy_url.strip():
        return None

    try:
        parsed = urlparse(proxy_url.strip())
        netloc = parsed.netloc.rsplit("@", 1)[-1]
        p_dict = {"server": f"{parsed.scheme}://{netloc}"}
        if parsed.username:
            p_dict["username"] = unquote(parsed.username)
        if parsed.password:
            p_dict["password"] = unquote(parsed.password)
        return p_dict
    except Exception:
        return None


async def fetch_proxies_from_cdn(protocol: str = "http") -> list[str]:
    """Tải danh sách proxy mới nhất từ jsDelivr CDN (~300KB, cập nhật mỗi 5 phút từ proxifly)."""
    url = CDN_ENDPOINTS.get(protocol, CDN_ENDPOINTS["http"])
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return [l.strip() for l in resp.text.splitlines() if l.strip()]
    except Exception as exc:
        print(f"⚠️ Lỗi tải proxy từ CDN ({url}): {exc}")
    return []


async def test_proxy_against_threads(proxy_url: str, timeout: float = 4.0) -> tuple[str, float] | None:
    """Kiểm tra xem proxy có thực sự kết nối được đến Threads (Status 200) và đo độ trễ (latency)."""
    t0 = time.time()
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout, verify=False) as client:
            resp = await client.get("https://www.threads.com", follow_redirects=True)
            if resp.status_code == 200:
                latency = round(time.time() - t0, 2)
                return proxy_url, latency
    except Exception:
        pass
    return None


async def get_healthy_proxies(
    needed: int = 5,
    sample_size: int = 60,
    protocol: str = "http",
    timeout: float = 4.0,
    save_file: Path | None = None,
) -> list[str]:
    """Tải và lọc ra top N proxy đang hoạt động tốt nhất cho Threads."""
    print(f"🌐 [Proxy] Đang tải danh sách proxy từ Proxifly CDN ({protocol})...")
    raw_list = await fetch_proxies_from_cdn(protocol)
    if not raw_list:
        print("❌ Không lấy được danh sách proxy từ CDN.")
        return []

    print(f"📦 Đã tải về {len(raw_list)} proxies. Đang kiểm tra {sample_size} proxy đầu tiên với Threads...")
    candidates = raw_list[:sample_size]
    tasks = [test_proxy_against_threads(p, timeout=timeout) for p in candidates]
    results = await asyncio.gather(*tasks)

    working = [r for r in results if r is not None]
    working.sort(key=lambda x: x[1])

    selected = working[:needed]
    print(f"🎉 Tìm thấy {len(working)} proxy sống kết nối được Threads (chọn top {len(selected)}):")
    for p, lat in selected:
        print(f"   ✅ [ALIVE] {p} (Độ trễ: {lat}s)")

    live_urls = [p for p, _ in selected]
    if save_file and live_urls:
        try:
            save_file.parent.mkdir(parents=True, exist_ok=True)
            with open(save_file, "w", encoding="utf-8") as f:
                f.write("# Danh sách proxy sống được lọc tự động từ Proxifly CDN\n")
                f.write("\n".join(live_urls) + "\n")
        except Exception:
            pass

    return live_urls
