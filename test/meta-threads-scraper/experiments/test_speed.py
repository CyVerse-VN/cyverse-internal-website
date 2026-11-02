import asyncio
import time
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def test_speed(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Block images and media
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

        t0 = time.time()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        try:
            await page.wait_for_selector('div[data-pressable-container="true"]', timeout=5000)
        except Exception:
            pass

        dur = round(time.time() - t0, 2)
        print(f"Page loaded without media in: {dur}s (vs 6-8s before)")

        count = await page.eval_on_selector_all('div[data-pressable-container="true"]', "els => els.length")
        print(f"Comments containers found: {count}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_speed("https://www.threads.com/@himmelame/post/DeZ3gpLkyp1"))
