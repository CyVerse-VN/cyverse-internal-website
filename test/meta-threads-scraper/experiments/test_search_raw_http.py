import httpx
import re
import sys
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")

query = "quán date"
url = f"https://www.threads.com/search?q={quote(query)}&serp_type=default&filter=recent"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

try:
    res = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
    print(f"Status Code: {res.status_code}")
    print(f"Content Length: {len(res.text)} bytes")
    scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
    print(f"Found {len(scripts)} application/json scripts in search raw HTML.")
    
    # Check if searchResults or search posts are present
    has_results = "searchResults" in res.text or "search_results" in res.text or "thread_items" in res.text
    print(f"Contains search results data: {has_results}")
except Exception as e:
    print(f"Error: {e}")
