import asyncio
import json
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

async def test_extract_structured_comments(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}
        )
        page = await context.new_page()

        graphql_items = []
        async def on_response(res):
            lower = res.url.lower()
            if "graphql" in lower:
                try:
                    data = await res.json()
                    graphql_items.append(data)
                except Exception:
                    pass

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Inspect DOM: Look for comment items.
        # Threads usually uses divs with specific roles or data-pressable-container inside the main thread view
        dom_comments = await page.evaluate('''() => {
            const results = [];
            // Find all article elements or pressable containers
            const elements = document.querySelectorAll('div[data-pressable-container="true"]');
            elements.forEach((el, index) => {
                // Find username link (href starts with /@)
                const userLink = el.querySelector('a[href^="/@"]');
                const username = userLink ? userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0] : null;
                
                // Find all span text
                const textNodes = Array.from(el.querySelectorAll('span[dir="auto"]')).map(s => s.innerText.trim()).filter(Boolean);
                
                results.push({
                    index: index,
                    username: username,
                    text_nodes: textNodes,
                    full_text: el.innerText
                });
            });
            return results;
        }''')

        await browser.close()

    print(f"GraphQL items count: {len(graphql_items)}")
    print(f"DOM comments count: {len(dom_comments)}")

    # Check the first few DOM comments
    print("\n--- SAMPLE DOM COMMENTS ---")
    for i, c in enumerate(dom_comments[:8]):
        print(f"[{i}] User: {c['username']}")
        print(f"    Text nodes: {c['text_nodes']}")
        clean_full = " // ".join(c['full_text'].split("\n"))
        print(f"    Full: {clean_full[:120]}")

    with open("scratch/comment_structure.json", "w", encoding="utf-8") as f:
        json.dump({
            "dom_comments": dom_comments[:15],
            "graphql": graphql_items
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(test_extract_structured_comments("https://www.threads.com/@sep.gksquf._/post/DdUQ5M4E3IS"))
