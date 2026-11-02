import asyncio
import json
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

async def inspect_post_comments(url: str):
    print(f"Loading post: {url}")
    graphql_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"}
        )
        page = await context.new_page()

        async def on_response(res):
            lower = res.url.lower()
            if "graphql" in lower or "api" in lower or "query" in lower:
                try:
                    data = await res.json()
                    graphql_responses.append({"url": res.url, "data": data})
                except Exception:
                    pass

        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # Also inspect DOM elements
        # Threads comments often have data-pressable-container or role="article" or specific spans
        articles = await page.eval_on_selector_all(
            "article, [data-pressable-container='true'], div[data-virtualized-root='true']",
            "elements => elements.map(e => e.innerText)"
        )

        content = await page.content()
        await browser.close()

    print(f"Captured {len(graphql_responses)} GraphQL/API responses.")
    print(f"Captured {len(articles)} article/container elements from DOM.")

    # Check for text in GraphQL responses
    all_json_texts = []
    def extract_strings(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "text" and isinstance(v, str):
                    all_json_texts.append(v)
                else:
                    extract_strings(v)
        elif isinstance(obj, list):
            for item in obj:
                extract_strings(item)

    for item in graphql_responses:
        extract_strings(item["data"])

    print(f"Extracted {len(all_json_texts)} text fields from GraphQL payloads:")
    for i, t in enumerate(all_json_texts[:15], 1):
        print(f"  [{i}] {t[:120]}")

    print("\nExtracted DOM texts (First 5):")
    for i, a in enumerate(articles[:5], 1):
        clean = " // ".join(a.split("\n"))
        print(f"  DOM [{i}] {clean[:150]}")

    with open("scratch/post_debug.json", "w", encoding="utf-8") as f:
        json.dump({
            "graphql_count": len(graphql_responses),
            "texts": all_json_texts,
            "dom_articles": articles[:10]
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(inspect_post_comments("https://www.threads.com/@sep.gksquf._/post/DdUQ5M4E3IS"))
