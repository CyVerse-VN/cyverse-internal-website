import asyncio
import json
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def test_anonymous_post_reading(post_url: str):
    print(f"\n=======================================================")
    print(f"Kiểm tra đọc chi tiết bài viết KHÔNG ĐĂNG NHẬP (Anonymous):")
    print(f"URL: {post_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}
        )
        page = await context.new_page()

        # Block media for speed
        await context.route(
            "**/*",
            lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_()
        )

        try:
            await page.goto(post_url, wait_until="networkidle", timeout=20000)
        except Exception:
            pass

        # Close cookie dialog
        try:
            await page.evaluate('''() => {
                document.querySelectorAll('[role="dialog"]').forEach(el => el.remove());
                const cookieBtn = document.querySelector('button');
            }''')
        except Exception:
            pass

        # 1. Đọc bài viết gốc
        post_data = await page.evaluate('''() => {
            const containers = document.querySelectorAll('div[data-pressable-container="true"]');
            if (!containers.length) return null;
            const mainPost = containers[0];
            const author = mainPost.querySelector('a[href^="/@"]')?.innerText || "";
            const spans = Array.from(mainPost.querySelectorAll('span[dir="auto"]')).map(s => s.innerText.trim());
            return {
                author,
                text: spans.join("\\n")
            };
        }''')
        print(f"\n1. Thông tin bài viết gốc:")
        if post_data:
            print(f"   Tác giả: @{post_data.get('author')}")
            print(f"   Nội dung: {post_data.get('text')[:150]}...")
        else:
            print("   Không tìm thấy container bài viết!")

        # 2. Đọc bình luận ban đầu
        initial_comments = await page.evaluate('''() => {
            const containers = document.querySelectorAll('div[data-pressable-container="true"]');
            const list = [];
            for (let i = 1; i < containers.length; i++) {
                const el = containers[i];
                const author = el.querySelector('a[href^="/@"]')?.innerText || "";
                const text = Array.from(el.querySelectorAll('span[dir="auto"]')).map(s => s.innerText.trim()).filter(Boolean).join(" ");
                if (text) list.push({ author, text });
            }
            return list;
        }''')
        print(f"\n2. Số bình luận nạp sẵn ban đầu: {len(initial_comments)}")
        for i, c in enumerate(initial_comments[:3], 1):
            print(f"   Comment {i} (@{c.get('author')}): {c.get('text')[:80]}")

        # 3. Cuộn chuột để nạp thêm bình luận (Infinite scroll mà không cần login)
        print(f"\n3. Thử cuộn trang (Scroll) để nạp thêm bình luận mà không cần login:")
        for scroll_idx in range(1, 4):
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(1.5)
            # Tự động gỡ modal login nếu có bật lên
            await page.evaluate("() => document.querySelectorAll('[role=\"dialog\"]').forEach(el => el.remove())")
            
            total_now = await page.evaluate('''() => {
                return document.querySelectorAll('div[data-pressable-container="true"]').length - 1;
            }''')
            print(f"   Lần cuộn {scroll_idx}: Hiện có {total_now} bình luận trên trang.")

        await browser.close()

if __name__ == "__main__":
    # Test post 1: Post xin gợi ý quán ăn sau concert
    asyncio.run(test_anonymous_post_reading("https://www.threads.com/@sep.gksquf._/post/DdUQ5M4E3IS"))
