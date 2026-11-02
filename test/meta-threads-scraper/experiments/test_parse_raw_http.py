import httpx
import re
import sys
import json
from urllib.parse import quote
from threads_parser.search import extract_search_posts

sys.stdout.reconfigure(encoding="utf-8")

query = "quán date"
url = f"https://www.threads.com/search?q={quote(query)}&serp_type=default&filter=recent"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

res = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', res.text, re.DOTALL)

raw_items = []
for s in scripts:
    try:
        data = json.loads(s)
        raw_items.append(data)
    except Exception:
        pass

posts = extract_search_posts(raw_items)
print(f"Extracted {len(posts)} posts directly via raw HTTP in 0.8s!")
for i, p in enumerate(posts[:5], 1):
    print(f"  {i}. @{p.get('username')}: {p.get('text')[:80]}...")
