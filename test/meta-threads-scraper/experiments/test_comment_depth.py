import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

# Test post có nhiều bình luận (62 replies): https://www.threads.com/@tduwc.c_/post/DeN6Iy5CaZ1
async def test_depth():
    url = "https://www.threads.com/@tduwc.c_/post/DeN6Iy5CaZ1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=20000)
        
        # Thử scroll 5 lần
        for i in range(5):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(1)
            # Remove dialogs
            await page.evaluate("() => document.querySelectorAll('[role=\"dialog\"]').forEach(e => e.remove())")
        
        count = await page.evaluate("() => document.querySelectorAll('div[data-pressable-container=\"true\"]').length - 1")
        print(f"Post 62 replies -> Scraped: {count} comments without login")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_depth())
