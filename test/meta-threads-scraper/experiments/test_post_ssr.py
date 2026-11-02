import httpx
import re
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.threads.com/@himmelame/post/DeZ3gpLkyp1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

res = httpx.get(url, headers=headers, follow_redirects=True, timeout=10)
scripts = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', res.text, re.DOTALL)

found_texts = []
for s in scripts:
    if "Điện Biên Phủ" in s or "Bánh bao" in s:
        try:
            data = json.loads(s)
            found_texts.append(s[:200])
        except Exception:
            pass

print(f"Found {len(found_texts)} matching script payloads in post SSR HTML!")
