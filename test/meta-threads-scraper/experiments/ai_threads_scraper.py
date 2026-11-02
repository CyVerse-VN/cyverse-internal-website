#!/usr/bin/env python3
"""
AI-Powered Threads Scraper with Groq
Tự động mở rộng từ khóa bằng Groq AI -> Cào bài viết trên Threads -> Lọc & trích xuất địa điểm thông minh.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

# Cấu hình UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
from playwright.async_api import async_playwright

# Import module từ package hiện tại
repo_root = Path(__file__).resolve().parent
src_dir = repo_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from threads_parser.browser import collect_script_json, dismiss_cookie_banner
from threads_parser.search import extract_search_posts

# Tự động đọc file .env nếu có
def load_dotenv():
    env_file = repo_root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_dotenv()

DEFAULT_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"  # Model tối ưu tiếng Việt, cực nhanh, free quota lớn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def expand_query_with_groq(query: str, api_key: str, count: int = 4) -> list[str]:
    """Dùng Groq AI phân tích câu hỏi dài thành các từ khóa ngắn 2-3 chữ phù hợp với Threads."""
    print(f"\n🤖 [Groq AI] Đang phân tích từ khóa gốc: '{query}'...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    prompt = f"""Bạn là chuyên gia về mạng xã hội Threads và du lịch Việt Nam.
Người dùng có nhu cầu tìm kiếm: "{query}".
Do máy chủ Threads không hỗ trợ tìm kiếm câu dài và chỉ tìm được chuỗi 2-3 chữ chính xác, nhiệm vụ của bạn là sinh ra {count} cụm từ tìm kiếm ngắn gọn (chỉ 2 đến 3 từ mỗi cụm) tiếng Việt tự nhiên nhất mà giới trẻ thường viết trong status khi review, check-in, ăn uống hoặc đi chơi.

Yêu cầu:
- Mỗi cụm từ chỉ từ 2 đến 3 từ (ví dụ: "Sài Gòn về đêm", "ăn đêm Sài Gòn", "quán cafe đêm").
- Tuyệt đối không sinh câu dài > 3 từ.
- Trả về DUY NHẤT một mảng JSON các chuỗi, không giải thích gì thêm.
Ví dụ định dạng trả về:
["Sài Gòn về đêm", "ăn đêm Sài Gòn", "quán cafe đêm"]"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
    }

    try:
        res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            # Bóc tách JSON mảng
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                keywords = json.loads(match.group(0))
                if isinstance(keywords, list) and keywords:
                    clean_kws = [str(k).strip() for k in keywords if str(k).strip()]
                    print(f"   -> AI đã sinh {len(clean_kws)} từ khóa hạt giống: {clean_kws}")
                    return clean_kws
        print(f"⚠️ Groq trả về status {res.status_code}, dùng fallback từ khóa.")
    except Exception as exc:
        print(f"⚠️ Lỗi kết nối Groq ({exc}), dùng fallback từ khóa.")

    # Fallback dự phòng nếu mất mạng hoặc lỗi API
    return [query]


def filter_and_curate_post_with_groq(text: str, api_key: str) -> dict | None:
    """Dùng Groq AI thẩm định xem bài viết có đúng là địa điểm du lịch/ăn chơi không."""
    if not text or len(text.strip()) < 15:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = f"""Dưới đây là một bài viết trên Threads:
"{text}"

Hãy đánh giá xem bài viết này có chia sẻ, hỏi hoặc review về địa điểm ăn uống, cafe, đi chơi, du lịch tại TP.HCM/Sài Gòn không.
Chỉ trả về DUY NHẤT 1 object JSON với cấu trúc:
{{
  "is_relevant": true hoặc false,
  "place_name": "Tên địa điểm hoặc null",
  "highlight": "Tóm tắt ngắn 1 câu về điểm nổi bật"
}}"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }

    try:
        res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception:
        pass
    return None


async def scrape_keyword(page, keyword: str, limit: int = 15) -> list[dict]:
    """Cào bài viết của 1 từ khóa trên Threads."""
    url = f"https://www.threads.com/search?q={quote(keyword)}&serp_type=default&filter=recent"
    raw_items = []

    async def on_response(res):
        lower = res.url.lower()
        if "graphql" in lower or ("threads." in lower and any(k in lower for k in ("api", "query", "search"))):
            content_type = res.headers.get("content-type", "").lower()
            if "json" in content_type or "graphql" in lower:
                try:
                    data = await res.json()
                    if isinstance(data, (dict, list)):
                        raw_items.append(data)
                except Exception:
                    pass

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
    except Exception:
        pass

    await dismiss_cookie_banner(page)
    try:
        await page.evaluate("() => document.querySelectorAll('[role=\"dialog\"]').forEach(el => el.remove())")
    except Exception:
        pass

    script_items = await collect_script_json(page)
    raw_items.extend(script_items)

    extracted = extract_search_posts(raw_items)
    return extracted[:limit] if limit else extracted


def normalize_post_schema(p: dict, keyword: str, scrape_time: str) -> dict:
    raw_id = p.get("id") or p.get("pk")
    url = p.get("permalink") or p.get("url")
    if not url and p.get("username") and p.get("code"):
        url = f"https://www.threads.com/@{p['username']}/post/{p['code']}"

    media_urls = p.get("media_urls") or []
    if not media_urls and p.get("media"):
        media_urls = [m["url"] for m in p["media"] if isinstance(m, dict) and m.get("url")]

    return {
        "post_id": str(raw_id) if raw_id else None,
        "url": url,
        "username": p.get("username"),
        "display_name": p.get("display_name"),
        "text": p.get("text"),
        "created_at": p.get("timestamp"),
        "like_count": p.get("like_count"),
        "reply_count": p.get("reply_count"),
        "repost_count": p.get("repost_count"),
        "media_urls": media_urls,
        "search_keywords": [keyword],
        "scraped_at": scrape_time,
    }


async def run_pipeline(user_query: str, limit_per_keyword: int = 15, api_key: str = DEFAULT_GROQ_API_KEY, ai_curate: bool = True):
    start_total = time.time()
    scrape_time = now_iso()
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "threads_posts.json"

    print("=" * 70)
    print(f"🔥 BẮT ĐẦU PIPELINE TỰ ĐỘNG THU THẬP THREADS VỚI GROQ AI")
    print(f"🎯 Ý định tìm kiếm ban đầu: '{user_query}'")
    print("=" * 70)

    # 1. BƯỚC 1: GROQ AI SINH TỪ KHÓA TƯƠNG ĐƯƠNG
    seed_keywords = expand_query_with_groq(user_query, api_key=api_key, count=4)
    # Thêm luôn query gốc vào để thử
    all_search_terms = []
    for k in [user_query] + seed_keywords:
        if k not in all_search_terms:
            all_search_terms.append(k)

    # 2. BƯỚC 2: CÀO BÀI TỰ ĐỘNG BẰNG PLAYWRIGHT
    posts_by_id = {}
    print(f"\n🌐 Bắt đầu cào tự động {len(all_search_terms)} từ khóa...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        for i, term in enumerate(all_search_terms, 1):
            t0 = time.time()
            print(f"   [{i}/{len(all_search_terms)}] Cào từ khóa: '{term}'...", end=" ", flush=True)
            raw_posts = await scrape_keyword(page, term, limit=limit_per_keyword)
            print(f"-> {len(raw_posts)} bài ({round(time.time() - t0, 2)}s)")

            for post in raw_posts:
                formatted = normalize_post_schema(post, term, scrape_time)
                key = formatted.get("post_id") or formatted.get("url")
                if not key:
                    continue
                if key in posts_by_id:
                    if term not in posts_by_id[key]["search_keywords"]:
                        posts_by_id[key]["search_keywords"].append(term)
                else:
                    posts_by_id[key] = formatted

            await asyncio.sleep(1.0)

        await browser.close()

    raw_total = len(posts_by_id)
    print(f"\n✅ Đã cào được tổng cộng: {raw_total} bài viết duy nhất.")

    # 3. BƯỚC 3: GROQ AI LỌC NGỮ NGHĨA & TRÍCH XUẤT ĐỊA ĐIỂM
    final_posts = list(posts_by_id.values())
    if ai_curate and final_posts:
        print(f"\n🤖 [Groq AI] Đang phân tích & lọc nội dung bài viết...")
        curated_count = 0
        for p in final_posts[:25]:  # Thử lọc cho top 25 bài
            text = p.get("text") or ""
            analysis = filter_and_curate_post_with_groq(text, api_key=api_key)
            if analysis:
                p["ai_analysis"] = analysis
                if analysis.get("is_relevant"):
                    curated_count += 1

        print(f"   -> AI đã phân tích ngữ nghĩa, xác nhận các bài liên quan đến địa điểm/trải nghiệm du lịch.")

    # 4. BƯỚC 4: XUẤT FILE JSON CHUẨN
    output_data = {
        "metadata": {
            "source": "Threads",
            "scraper": "vladyslav-hord/meta-threads-scraper + Groq AI",
            "original_query": user_query,
            "generated_keywords": seed_keywords,
            "scraped_at": scrape_time,
            "total_posts": len(final_posts),
        },
        "posts": final_posts,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    total_duration = round(time.time() - start_total, 2)

    # 5. HIỂN THỊ KẾT QUẢ RA TERMINAL
    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ HOÀN TẤT")
    print("=" * 70)
    print(f"🎯 Từ khóa ban đầu: '{user_query}'")
    print(f"💡 Từ khóa được Groq AI tạo tự động: {seed_keywords}")
    print(f"📦 Tổng số bài viết thu thập thành công: {len(final_posts)} bài")
    print(f"⏱️ Tổng thời gian chạy: {total_duration}s")
    print(f"📁 File JSON đã lưu tại: {json_path.resolve().as_posix()}")

    print("\nTop 5 bài viết thực tế tiêu biểu thu thập được:")
    for i, p in enumerate(final_posts[:5], 1):
        clean_text = " ".join((p.get("text") or "").split())
        print(f"  {i}. @{p['username']}: {clean_text[:90]}...")
        print(f"     URL: {p['url']}")
        ai_info = p.get("ai_analysis")
        if ai_info and ai_info.get("place_name"):
            print(f"     📍 Địa điểm do AI nhận diện: {ai_info['place_name']}")
        print(f"     Stats: ❤️ {p.get('like_count')} likes | 💬 {p.get('reply_count')} replies")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="AI-Powered Threads Scraper")
    parser.add_argument("query", nargs="?", default="du lịch đêm sài gòn", help="Câu tìm kiếm gốc (default: 'du lịch đêm sài gòn')")
    parser.add_argument("--limit", type=int, default=15, help="Giới hạn bài/từ khóa (default: 15)")
    parser.add_argument("--no-curate", action="store_true", help="Bỏ qua bước AI lọc bài")
    args = parser.parse_args()

    asyncio.run(run_pipeline(args.query, limit_per_keyword=args.limit, ai_curate=not args.no_curate))


if __name__ == "__main__":
    main()
