import asyncio
import json
import sys
from urllib.parse import quote
from playwright.async_api import async_playwright
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo_root = Path(".").resolve()
sys.path.insert(0, str(repo_root / "src"))

from threads_parser.browser import collect_script_json, dismiss_cookie_banner
from threads_parser.search import extract_search_posts

async def test_input_search():
    async with async_playwright() as p:
        # Launch with headless=False or headless=True
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            }
        )
        page = await context.new_page()

        # Try various keywords
        test_keywords = [
            "địa điểm hẹn hò lãng mạn ở Sài Gòn",
            "địa điểm hẹn hò sài gòn",
            "địa điểm hẹn hò",
            "quán date",
            "hẹn hò"
        ]

        for kw in test_keywords:
            url = f"https://www.threads.com/search?q={quote(kw)}"
            raw_items = []

            async def on_response(res):
                lower = res.url.lower()
                if "graphql" in lower:
                    try:
                        data = await res.json()
                        if isinstance(data, (dict, list)):
                            raw_items.append(data)
                    except Exception:
                        pass

            page.on("response", on_response)
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception:
                pass

            await dismiss_cookie_banner(page)
            script_items = await collect_script_json(page)
            raw_items.extend(script_items)
            extracted = extract_search_posts(raw_items)
            
            # Check body text
            body_text = await page.evaluate("() => document.body.innerText.slice(0, 200)")
            has_no_results = "Không có kết quả nào" in body_text or "No results" in body_text
            
            print(f"Keyword: '{kw}'")
            print(f"  -> Extracted posts: {len(extracted)}")
            print(f"  -> Has 'No results': {has_no_results}")
            if extracted:
                print(f"  -> Sample: {extracted[0].get('text', '')[:60]}...")
            print("-" * 50)
            
            # Remove response listener for next loop
            page.remove_listener("response", on_response)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_input_search())
