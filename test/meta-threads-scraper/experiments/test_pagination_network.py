import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def inspect_comment_pagination():
    url = "https://www.threads.com/@tduwc.c_/post/DeN6Iy5CaZ1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        graphql_calls = []
        page.on("response", lambda r: graphql_calls.append(r.url) if "graphql" in r.url else None)
        
        await page.goto(url, wait_until="networkidle", timeout=20000)
        initial_calls = len(graphql_calls)
        print(f"GraphQL calls on initial load: {initial_calls}")
        
        # Scroll down
        for i in range(3):
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)
        
        print(f"GraphQL calls after scrolling: {len(graphql_calls) - initial_calls}")
        
        # Check if there is a button like "Xem thêm câu trả lời" / "View replies"
        buttons = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('div[role="button"], button')).map(b => b.innerText.trim()).filter(Boolean);
        }''')
        print("Buttons found on post page:", buttons)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_comment_pagination())
