import httpx
import re
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.threads.com/@himmelame/post/DeZ3gpLkyp1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

try:
    res = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
    print(f"Status Code: {res.status_code}")
    print(f"Content Length: {len(res.text)} bytes")
    
    # Check if text or comments are in the HTML
    has_post_text = "Bánh bao" in res.text
    has_author = "himmelame" in res.text
    has_comment_text = "Điện Biên Phủ" in res.text
    print(f"Contains author: {has_author}")
    print(f"Contains post text snippet: {has_post_text}")
    print(f"Contains comment snippet: {has_comment_text}")

    # Check for script json tags
    scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', res.text, re.DOTALL)
    print(f"Found {len(scripts)} application/json scripts in raw HTML.")
    
except Exception as e:
    print(f"Error: {e}")
