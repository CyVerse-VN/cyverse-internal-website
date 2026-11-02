#!/usr/bin/env python3
"""
Threads Login Helper: Hỗ trợ đăng nhập thủ công 1 lần duy nhất để lưu Session Cookies.
Trình duyệt sẽ mở giao diện thật (headless=False) để bạn tự đăng nhập an toàn,
sau đó script tự động lưu cookies/session vào file sessions/user_session.json.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

repo_root = Path(__file__).resolve().parent.parent
sessions_dir = repo_root / "sessions"
session_file = sessions_dir / "user_session.json"

async def manual_login():
    sessions_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("🔐 THREADS LOGIN HELPER (LƯU PHIÊN ĐĂNG NHẬP)")
    print("=" * 70)
    print("1. Một cửa sổ trình duyệt Chrome sẽ mở ra.")
    print("2. Vui lòng đăng nhập tài khoản Threads/Instagram của bạn (bằng pass, OTP hoặc QR).")
    print("3. Sau khi đăng nhập thành công vào trang chủ Threads, hệ thống sẽ tự động")
    print("   lưu session vào 'sessions/user_session.json' và đóng trình duyệt.")
    print("=" * 70)
    print("\n⏳ Đang mở trình duyệt...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )
        page = await context.new_page()
        await page.goto("https://www.threads.com/login", wait_until="domcontentloaded")

        print("👉 Trình duyệt đã sẵn sàng! Mời bạn thao tác đăng nhập trên cửa sổ Chrome vừa mở...")

        # Chờ người dùng đăng nhập thành công
        # Dấu hiệu thành công: có cookie 'sessionid' hoặc url không còn là login/challenge
        logged_in = False
        for _ in range(300):  # Chờ tối đa 5 phút (300 giây)
            await asyncio.sleep(1)
            cookies = await context.cookies()
            has_session = any(c.get("name") in ("sessionid", "sessionid_ss") and c.get("value") for c in cookies)
            current_url = page.url.lower()

            if has_session and not any(k in current_url for k in ("/login", "/challenge", "/checkpoint")):
                logged_in = True
                break

        if logged_in:
            print("\n🎉 ĐĂNG NHẬP THÀNH CÔNG!")
            await asyncio.sleep(2)  # Đợi cookie ổn định
            await context.storage_state(path=str(session_file))
            print(f"💾 Đã lưu phiên đăng nhập an toàn vào: {session_file.resolve().as_posix()}")
            print("🚀 Từ bây giờ, bạn có thể bật 'AUTH_ENABLED = True' trong config.py để pipeline cào bằng tài khoản này.")
        else:
            print("\n⚠️ Hết thời gian chờ hoặc chưa hoàn tất đăng nhập. Phiên chưa được lưu.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(manual_login())
