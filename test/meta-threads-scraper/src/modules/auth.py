from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from playwright.async_api import Browser, async_playwright, Error as PlaywrightError

from .proxy import format_playwright_proxy, test_proxy_against_threads, get_healthy_proxies


async def dismiss_popups(page: Any) -> None:
    """Tự động tắt các popup 'Lưu thông tin đăng nhập' hoặc 'Bật thông báo' của Meta."""
    selectors = [
        'button:has-text("Lúc khác")',
        'button:has-text("Not now")',
        'button:has-text("Not Now")',
        'button:has-text("Để sau")',
        'div[role="button"]:has-text("Lúc khác")',
        'div[role="button"]:has-text("Not now")',
        'div[role="button"]:has-text("Để sau")',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(0.3)
        except Exception:
            pass


async def login_single_account(
    browser: Browser,
    acc_info: dict[str, Any],
    sessions_dir: Path,
    index: int = 1,
    total: int = 1,
) -> bool:
    """Đăng nhập một tài khoản Threads và lưu phiên vào sessions/{acc_id}.json."""
    acc_id = acc_info.get("id") or f"acc_{index:02d}"
    username = str(acc_info.get("username", "")).strip()
    password = str(acc_info.get("password", "")).strip()
    proxy = str(acc_info.get("proxy", "")).strip()
    if acc_info.get("use_proxy") is False:
        proxy = ""

    if not username or not password or username.startswith("dien_username") or username.startswith("ten_tai_khoan"):
        print(f"⚠️ [{index}/{total}] Bỏ qua {acc_id}: Chưa điền username/password thực tế.")
        return False

    print(f"\n=======================================================")
    print(f"🚀 [{index}/{total}] Đang xử lý đăng nhập cho: @{username} (ID: {acc_id})")

    # Kiểm tra proxy nếu có và được bật
    if proxy and acc_info.get("use_proxy", True):
        print(f"⏳ Đang kiểm tra proxy: {proxy}...", end=" ", flush=True)
        res = await test_proxy_against_threads(proxy, timeout=5.0)
        if res:
            print(f"-> ✅ Hoạt động tốt ({res[1]}s)")
        else:
            print("-> ❌ Proxy không phản hồi! Đang tìm proxy mới thay thế...")
            new_p = await get_healthy_proxies(needed=1, sample_size=50)
            if new_p:
                proxy = new_p[0]
                acc_info["proxy"] = proxy
                print(f"   🔄 Đã thay bằng proxy mới: {proxy}")
            else:
                print("   ⚠️ Không tìm được proxy mới, chuyển sang kết nối trực tiếp.")
                proxy = ""

    context_kwargs: dict[str, Any] = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "extra_http_headers": {
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }
    p_dict = format_playwright_proxy(proxy)
    if p_dict:
        context_kwargs["proxy"] = p_dict
        print(f"🌐 Proxy sử dụng: {proxy}")
    else:
        print("🌐 Kết nối mạng: Trực tiếp (Direct)")

    context = await browser.new_context(**context_kwargs)
    page = await context.new_page()

    try:
        await page.goto("https://www.threads.com/login", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(1.5)

        user_input = page.locator('input[autocomplete="username"], input[name="username"]').first
        pass_input = page.locator('input[autocomplete="current-password"], input[name="password"]').first

        if not await user_input.count() or not await pass_input.count():
            print("⚠️ Không tìm thấy ô nhập tài khoản/mật khẩu trên trang login.")
            await context.close()
            return False

        print(f"   -> Đang điền tài khoản @{username}...")
        await user_input.fill(username)
        await asyncio.sleep(0.5)

        print("   -> Đang điền mật khẩu...")
        await pass_input.fill(password)
        await asyncio.sleep(0.5)

        print("   -> Đang bấm đăng nhập...")
        await pass_input.press("Enter")

        logged_in = False
        print("   -> Đang chờ Meta xác thực đăng nhập...")

        for sec in range(90):
            await asyncio.sleep(1)
            await dismiss_popups(page)

            try:
                cookies = await context.cookies()
                has_session = any(c.get("name") in ("sessionid", "sessionid_ss") and c.get("value") for c in cookies)
                current_url = page.url.lower()

                if has_session and not any(k in current_url for k in ("/login", "/challenge")):
                    logged_in = True
                    break

                body_text = await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''")
                if "mã xác nhận" in body_text or "security code" in body_text or "enter code" in body_text:
                    if sec % 10 == 0:
                        print("   🔔 Meta yêu cầu mã xác thực gửi về Email/SMS! Vui lòng nhập mã trực tiếp trên cửa sổ trình duyệt...")
            except Exception:
                pass

        if logged_in:
            await asyncio.sleep(2)
            await dismiss_popups(page)
            sessions_dir.mkdir(parents=True, exist_ok=True)
            save_path = sessions_dir / f"{acc_id}.json"
            await context.storage_state(path=str(save_path))
            print(f"   ✅ ĐĂNG NHẬP THÀNH CÔNG! Đã lưu phiên vào: {save_path.name}")
            await context.close()
            return True
        else:
            print(f"   ❌ Đăng nhập thất bại hoặc hết thời gian chờ cho @{username}.")
            await context.close()
            return False

    except Exception as exc:
        print(f"   ❌ Lỗi khi đăng nhập @{username}: {exc}")
        await context.close()
        return False


async def auto_login_all_accounts(
    accounts: list[dict[str, Any]],
    sessions_dir: Path,
    headless: bool = False,
) -> int:
    """Tự động đăng nhập hàng loạt tài khoản và lưu session."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    if not accounts:
        print("❌ Danh sách tài khoản đang rỗng!")
        return 0

    print("=" * 70)
    print("🤖 TOOL TỰ ĐỘNG ĐĂNG NHẬP THREADS ACCOUNTS")
    print(f"📦 Tìm thấy: {len(accounts)} tài khoản")
    print("=" * 70)

    success_count = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--start-maximized"])
        for i, acc in enumerate(accounts, 1):
            ok = await login_single_account(browser, acc, sessions_dir, i, len(accounts))
            if ok:
                success_count += 1
            await asyncio.sleep(2)
        await browser.close()

    print("\n" + "=" * 70)
    print(f"🎉 HOÀN TẤT! Đăng nhập thành công {success_count}/{len(accounts)} tài khoản.")
    print(f"📁 Phiên lưu tại: {sessions_dir.as_posix()}")
    print("=" * 70)
    return success_count


def get_available_sessions(sessions_dir: Path) -> list[Path]:
    """Tìm danh sách tất cả file session hợp lệ đã lưu trong sessions_dir."""
    if not sessions_dir.is_dir():
        return []
    return [
        f for f in sorted(sessions_dir.glob("*.json"))
        if f.is_file() and f.stat().st_size > 50
    ]
