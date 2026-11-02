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

async def test_search(url, block_media=True):
    print(f"\n=======================================================")
    print(f"Testing URL: {url}")
    print(f"Block media: {block_media}")
    
    async with async_playwright() as p:
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
        if block_media:
            await context.route(
                "**/*",
                lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_()
            )
        page = await context.new_page()

        raw_items = []
        graphql_urls = []

        async def on_response(res):
            lower = res.url.lower()
            if "graphql" in lower:
                graphql_urls.append(res.url)
            if "graphql" in lower or ("threads." in lower and any(k in lower for k in ("api", "query", "search"))):
                content_type = res.headers.get("content-type", "").lower()
                if "json" in content_type or "graphql" in lower:
                    try:
                        data = await res.json()
                        if isinstance(data, (dict, list)):
                            raw_items.append(data)
                    except Exception as e:
                        pass

        page.on("response", on_response)

        try:
            resp = await page.goto(url, wait_until="networkidle", timeout=20000)
            print(f"Final Page URL: {page.url} (Status: {resp.status if resp else 'N/A'})")
        except Exception as e:
            print(f"Goto error/timeout: {e}")

        await dismiss_cookie_banner(page)
        
        # Check text on page or take screenshot
        title = await page.title()
        print(f"Page Title: {title}")

        # Check DOM elements
        posts_in_dom = await page.evaluate('''() => {
            const containers = document.querySelectorAll('div[data-pressable-container="true"]');
            return containers.length;
        }''')
        print(f"DOM containers found: {posts_in_dom}")

        # Check raw items from responses
        print(f"GraphQL responses captured: {len(graphql_urls)}")
        print(f"Total raw items captured: {len(raw_items)}")

        # Collect script JSON
        script_items = await collect_script_json(page)
        print(f"Script JSON items collected: {len(script_items)}")
        raw_items.extend(script_items)

        extracted = extract_search_posts(raw_items)
        print(f"Extracted search posts: {len(extracted)}")
        if extracted:
            for i, post in enumerate(extracted[:3], 1):
                txt = (post.get("text") or "").replace("\n", " ")[:80]
                print(f"  {i}. @{post.get('username')}: {txt}")
        else:
            # Let's save HTML or inspect why 0 posts
            content_snippet = (await page.content())[:1000]
            # check if page shows "No results" or similar
            no_results = await page.evaluate('''() => {
                const bodyText = document.body.innerText;
                return bodyText.slice(0, 500);
            }''')
            print(f"Body text preview:\n{no_results}")

        await browser.close()

async def main():
    kw = "địa điểm hẹn hò lãng mạn ở Sài Gòn"
    # Case 1: Pipeline URL currently used (threads.com with filter=recent)
    u1 = f"https://www.threads.com/search?q={quote(kw)}&serp_type=default&filter=recent"
    await test_search(u1, block_media=True)

    # Case 2: threads.net without filter=recent (Default Top search)
    u2 = f"https://www.threads.net/search?q={quote(kw)}"
    await test_search(u2, block_media=True)

    # Case 3: threads.net with filter=recent
    u3 = f"https://www.threads.net/search?q={quote(kw)}&serp_type=default&filter=recent"
    await test_search(u3, block_media=True)

if __name__ == "__main__":
    asyncio.run(main())
