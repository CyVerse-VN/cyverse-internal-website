#!/usr/bin/env python3
"""
Production Pipeline: Threads Scraper + Groq AI + Anti-Ban Throttling
Refactored Modular Architecture:
- config.py: Quản lý các hằng số cấu hình hệ thống
- src/modules/config: Quản lý biến môi trường .env và nạp config.py
- src/modules/auth: Quản lý đăng nhập & session
- src/modules/proxy: Kiểm tra và cấp phát proxy
- src/modules/crawler: Playwright worker pool, cào bài và comment
- src/modules/ai_engine: AI mở rộng từ khóa, lọc sơ bộ & thẩm định chi tiết
- src/modules/storage: Lưu trữ theo mốc thời gian runs/YYYY-MM-DD/run_HH-MM-SS/
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Xác định thư mục gốc của repository
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from .config import load_app_config
from .auth import get_available_sessions
from .ai_engine import analyze_user_intent, expand_search_query, pre_filter_posts, curate_post
from .crawler import WorkerPool, scrape_single_keyword, scrape_post_comments, format_post
from .storage import save_pipeline_run, get_current_timestamp


async def execute_pipeline(custom_query: str | None = None) -> None:
    start_time = time.time()
    config = load_app_config()

    # Xác định các câu tìm kiếm
    queries = [custom_query] if custom_query else config.get("search_queries", [])
    if not queries:
        print("❌ Không có câu tìm kiếm nào được cấu hình trong config.py!")
        return

    # Các tham số cào và anti-ban
    max_posts = config.get("max_posts_per_keyword", 30)
    anti_ban = config.get("anti_ban", {})
    min_delay = anti_ban.get("min_delay_seconds", 2.0)
    max_delay = anti_ban.get("max_delay_seconds", 4.0)
    mouse_move = anti_ban.get("random_mouse_movement", True)

    block_media = config.get("performance", {}).get("block_media", True)

    # Cấu hình AI Groq
    groq_cfg = config.get("groq", {})
    groq_model = groq_cfg.get("model", "qwen/qwen3.8-27b")
    ai_filter = groq_cfg.get("enable_ai_filtering", True)
    kws_per_query = groq_cfg.get("keywords_per_query", 1)
    groq_key = config.get("groq_api_key")

    # Cấu hình AI Gatekeeper (lọc trước khi cào comment)
    pre_filter_cfg = config.get("pre_filter", {})
    pre_filter_enabled = pre_filter_cfg.get("enabled", False)
    pre_filter_batch_size = pre_filter_cfg.get("batch_size", 15)
    pre_filter_strictness = pre_filter_cfg.get("strictness", "high")

    # Cấu hình bình luận (Comments)
    comments_cfg = config.get("comments", {})
    comments_enabled = comments_cfg.get("enabled", True)
    min_replies_threshold = comments_cfg.get("min_replies_threshold", 2)
    max_posts_to_scrape_comments = comments_cfg.get("max_posts_to_scrape", 10)
    max_comments_per_post = comments_cfg.get("max_comments_per_post", 25)

    # Quản lý phiên tài khoản & Proxy
    auth_cfg = config.get("auth", {})
    auth_enabled = auth_cfg.get("enabled", True)
    sessions_dir = REPO_ROOT / auth_cfg.get("sessions_dir", "sessions")
    session_files = get_available_sessions(sessions_dir) if auth_enabled else []

    # Lọc số lượng tài khoản theo cấu hình ACTIVE_ACCOUNTS hoặc MAX_ACCOUNTS_TO_USE
    active_filter = [a.lower() for a in config.get("active_accounts", []) if a]
    max_accs = config.get("max_accounts_to_use", -1)
    if auth_enabled and session_files:
        if active_filter:
            session_files = [s for s in session_files if s.stem.lower() in active_filter]
        elif max_accs > 0:
            session_files = session_files[:max_accs]

    accounts = config.get("accounts", [])
    proxy_cfg = config.get("proxy", {})
    global_proxy_enabled = proxy_cfg.get("enabled", False)
    account_proxy_toggle = config.get("account_proxy_toggle") or proxy_cfg.get("account_proxy_toggle", {})

    proxy_pool: list[str] = []
    proxy_file = REPO_ROOT / proxy_cfg.get("proxy_file", "proxies.txt")
    if proxy_file.is_file():
        try:
            proxy_pool = [l.strip() for l in proxy_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
        except Exception:
            pass

    active_proxy = random.choice(proxy_pool) if (global_proxy_enabled and proxy_pool) else None
    scrape_timestamp = get_current_timestamp()

    # Báo cáo khởi động
    if session_files:
        acc_str = f"Tài khoản Pool ({len(session_files)} acc: {', '.join(s.stem for s in session_files)})"
    else:
        acc_str = "Ẩn danh (Guest / Khách)"

    print("=" * 75)
    print("🚀 THREADS SCRAPER & AI PIPELINE (MODULAR V2)")
    print(f"📅 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Số lượng chủ đề tìm kiếm: {len(queries)}")
    print(f"🔑 Chế độ đăng nhập: {acc_str}")
    print(f"🌐 Proxy mạng chung: {'Bật' if global_proxy_enabled else 'Tắt (Kết nối trực tiếp)'}")
    if account_proxy_toggle:
        toggle_info = ", ".join(f"{k}: {'Proxy' if v else 'Direct'}" for k, v in account_proxy_toggle.items())
        print(f"🔀 Cấu hình Proxy từng Acc: {toggle_info}")
    print(f"⚡ Tối ưu tốc độ (Block Media): {'Bật (Chặn nạp media tăng tốc 3x)' if block_media else 'Tắt'}")
    print(f"🧠 AI Gatekeeper: {'Bật' if pre_filter_enabled else 'Tắt'} (Chế độ: {pre_filter_strictness})")
    print(f"💬 Cào bình luận: {'Bật' if comments_enabled else 'Tắt'} (Tối đa {max_posts_to_scrape_comments} bài, {max_comments_per_post} bình luận/bài)")
    print(f"🛡️ Cơ chế Anti-Ban: Delay ngẫu nhiên {min_delay}s - {max_delay}s, giả lập chuột người thật")
    print(f"🤖 AI Engine: Groq ({groq_model})")
    print("=" * 75)

    # 1. AI CHATBOT: PHÂN TÍCH Ý ĐỊNH NGƯỜI DÙNG & TỪ KHÓA TỐI ƯU
    all_target_keywords: dict[str, list[str]] = {}
    print("\n🧠 [AI Chatbot Engine] Đang phân tích câu hỏi & ý định của bạn...")
    for q in queries:
        intent_info = analyze_user_intent(q, model=groq_model, count=kws_per_query, api_key=groq_key)
        resp = intent_info.get("friendly_response", "")
        summary = intent_info.get("intent_summary", "")
        extracted_kws = intent_info.get("keywords", [])

        if resp:
            print(f"   🤖 Chatbot: \"{resp}\"")
        if summary and summary != q:
            print(f"   🎯 Ý định nhận diện: {summary}")
        print(f"   💡 Từ khóa Threads tối ưu: {extracted_kws}")

        # Nếu câu hỏi ban đầu là câu dài (> 3 từ), không search câu dài trên Threads mà chỉ search các từ khóa tối ưu
        words = q.strip().split()
        if len(words) <= 3:
            combined: list[str] = []
            for kw in [q] + extracted_kws:
                if kw not in combined:
                    combined.append(kw)
            all_target_keywords[q] = combined
        else:
            all_target_keywords[q] = extracted_kws if extracted_kws else [q]

    total_keywords_count = sum(len(kws) for kws in all_target_keywords.values())
    current_kw_idx = 0
    posts_by_id: dict[str, dict] = {}

    print(f"\n🌐 [Playwright Crawler] Khởi chạy cào an toàn tổng cộng {total_keywords_count} từ khóa...")

    # 2. KHỞI CHẠY PLAYWRIGHT & WORKER POOL
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        worker_pool = WorkerPool(browser)

        await worker_pool.initialize(
            session_files=session_files,
            accounts=accounts,
            block_media=block_media,
            fallback_proxy=active_proxy,
            auth_enabled=auth_enabled,
            account_proxy_toggle=account_proxy_toggle,
            proxy_pool=proxy_pool,
            global_proxy_enabled=global_proxy_enabled,
        )

        # 3. VÒNG LẶP CÀO BÀI THEO TỪ KHÓA (XOAY VÒNG WORKER)
        for topic, kws in all_target_keywords.items():
            print(f"\n📁 Chủ đề: '{topic}'")
            for kw in kws:
                current_kw_idx += 1
                worker = worker_pool.get_worker(current_kw_idx - 1)
                page = worker["page"]
                worker_tag = f"[{worker['id']}] " if len(worker_pool.workers) > 1 else ""
                t0 = time.time()
                print(f"   [{current_kw_idx}/{total_keywords_count}] {worker_tag}Tìm kiếm: '{kw}'...", end=" ", flush=True)

                raw_posts = await scrape_single_keyword(page, kw, limit=max_posts, enable_mouse_move=mouse_move)
                dur = round(time.time() - t0, 2)
                print(f"-> Thu được {len(raw_posts)} bài ({dur}s)")

                for post in raw_posts:
                    formatted = format_post(post, kw, scrape_timestamp)
                    key = formatted.get("post_id") or formatted.get("url")
                    if not key:
                        continue
                    if key in posts_by_id:
                        if kw not in posts_by_id[key]["search_keywords"]:
                            posts_by_id[key]["search_keywords"].append(kw)
                    else:
                        posts_by_id[key] = formatted

                # Nghỉ ngẫu nhiên giữa các từ khóa
                sleep_sec = random.uniform(min_delay, max_delay)
                await asyncio.sleep(sleep_sec)

        all_unique_posts = list(posts_by_id.values())

        # 4. AI GATEKEEPER: LỌC SƠ BỘ TRƯỚC KHI CÀO COMMENT
        promising_candidates = all_unique_posts
        if pre_filter_enabled and all_unique_posts:
            print(f"\n🧠 [AI Gatekeeper] Đang lọc sơ bộ {len(all_unique_posts)} bài viết theo chủ đề: {queries}...")
            promising_candidates, discarded = pre_filter_posts(
                all_unique_posts,
                queries,
                model=groq_model,
                batch_size=pre_filter_batch_size,
                strictness=pre_filter_strictness,
                api_key=groq_key,
            )
            print(f"   -> AI đã chọn {len(promising_candidates)}/{len(all_unique_posts)} bài viết phù hợp (loại {len(discarded)} bài rác).")

        # 5. CÀO SÂU BÌNH LUẬN (CHỈ CÁC BÀI ĐÃ QUA LỌC VÀ NHIỀU REPLIES)
        total_comments_scraped = 0
        if comments_enabled and promising_candidates:
            comment_candidates = [
                p for p in promising_candidates
                if (p.get("reply_count") or 0) >= min_replies_threshold and p.get("url")
            ]
            comment_candidates.sort(key=lambda x: x.get("reply_count") or 0, reverse=True)
            if max_posts_to_scrape_comments > 0:
                comment_candidates = comment_candidates[:max_posts_to_scrape_comments]

            if comment_candidates:
                print(f"\n💬 [Deep Comment Scraping] Bắt đầu cào bình luận cho {len(comment_candidates)} bài viết...")
                for idx, post in enumerate(comment_candidates, 1):
                    worker = worker_pool.get_worker(idx - 1)
                    page = worker["page"]
                    worker_tag = f"[{worker['id']}] " if len(worker_pool.workers) > 1 else ""
                    p_url = post["url"]
                    rep_cnt = post.get("reply_count") or 0
                    print(f"   [{idx}/{len(comment_candidates)}] {worker_tag}Đang đọc bình luận @{post.get('username')} ({rep_cnt} replies)...", end=" ", flush=True)

                    t_c0 = time.time()
                    post_comments = await scrape_post_comments(
                        page,
                        p_url,
                        max_comments=max_comments_per_post,
                        enable_mouse_move=mouse_move,
                    )
                    post["comments"] = post_comments
                    total_comments_scraped += len(post_comments)
                    dur = round(time.time() - t_c0, 2)
                    print(f"-> Thu được {len(post_comments)} bình luận ({dur}s)")

                    sleep_sec = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(sleep_sec)

        await worker_pool.close()
        await browser.close()

    total_scraped = len(posts_by_id)
    all_posts = list(posts_by_id.values())
    print(f"\n🎉 Hoàn thành cào bài! Tổng cộng: {total_scraped} bài viết duy nhất, {total_comments_scraped} bình luận.")

    # 6. THẨM ĐỊNH CHI TIẾT & TRÍCH XUẤT THỰC THỂ/ĐỊA ĐIỂM BẰNG GROQ AI
    curated_posts = []
    posts_to_curate = promising_candidates if pre_filter_enabled else all_posts
    if ai_filter and posts_to_curate:
        print(f"\n🤖 [AI Curation] Đang thẩm định chi tiết & trích xuất nội dung giá trị từ {len(posts_to_curate)} bài viết...")
        for post in posts_to_curate:
            text = post.get("text") or ""
            post_comments = post.get("comments") or []
            analysis = curate_post(text, queries, comments=post_comments, model=groq_model, api_key=groq_key)
            if analysis:
                post["ai_analysis"] = analysis
                if analysis.get("is_relevant"):
                    curated_posts.append(post)

        print(f"   -> AI đã chọn lọc: {len(curated_posts)}/{len(posts_to_curate)} bài viết thực sự đúng trọng tâm!")

    # 7. LƯU KẾT QUẢ VÀO THƯ MỤC RUNS & LATEST
    total_time = round(time.time() - start_time, 2)
    saved_files = save_pipeline_run(
        all_posts=all_posts,
        curated_posts=curated_posts,
        topics=queries,
        total_comments=total_comments_scraped,
        duration_seconds=total_time,
        output_cfg=config.get("output", {}),
        repo_root=REPO_ROOT,
    )

    # 8. BÁO CÁO KẾT QUẢ
    print("\n" + "=" * 75)
    print("📊 BÁO CÁO KẾT QUẢ CUỐI CÙNG")
    print("=" * 75)
    print(f"⏱️ Tổng thời gian chạy: {total_time} giây")
    print(f"📦 Tổng bài viết cào được: {total_scraped} bài")
    print(f"💬 Tổng số bình luận cào sâu: {total_comments_scraped} bình luận")
    print(f"⭐ Bài viết chất lượng được AI chọn lọc: {len(curated_posts)} bài")
    print(f"📁 Thư mục lưu đợt chạy này: {saved_files['run_dir'].resolve().as_posix()}")
    print(f"   - File tóm tắt: {saved_files['summary'].name}")
    print(f"   - File toàn bộ bài viết (JSON): {saved_files['posts'].name}")
    print(f"   - File văn bản phân cấp (TXT): {saved_files['posts_txt'].name}")
    if curated_posts:
        print(f"   - File địa điểm chọn lọc: {saved_files['curated'].name}")
    print(f"✨ File đồng bộ mới nhất (Latest):")
    print(f"   - JSON: {saved_files['latest_posts'].resolve().as_posix()}")
    print(f"   - TXT:  {saved_files['latest_txt'].resolve().as_posix()}")

    display_list = curated_posts if curated_posts else all_posts
    if display_list:
        print("\nTop bài viết tiêu biểu vừa phân tích:")
        for i, p in enumerate(display_list[:5], 1):
            clean_text = " ".join((p.get("text") or "").split())
            ai_data = p.get("ai_analysis") or {}
            topic = ai_data.get("topic") or "Thảo luận"
            summary = ai_data.get("summary") or clean_text[:120]
            places = [r.get("name") for r in ai_data.get("recommended_places") or [] if r.get("name")]
            print(f"  {i}. [{topic}]")
            print(f"     Tóm tắt: {summary}")
            if places:
                print(f"     📍 Địa điểm/quán: {', '.join(places[:4])}")
            comments_list = p.get("comments") or []
            print(f"     Tác giả: @{p['username']} | Lượt like: {p.get('like_count')} | Bình luận cào được: {len(comments_list)}")
            print(f"     URL: {p['url']}")

    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Threads Scraper + Groq AI Production Pipeline")
    parser.add_argument("query", nargs="?", default=None, help="Câu tìm kiếm tùy chọn (nếu không truyền sẽ đọc từ config.py)")
    parser.add_argument("--query", "-q", dest="query_flag", default=None, help="Câu tìm kiếm chỉ định")
    args = parser.parse_args()

    chosen_query = args.query_flag or args.query
    asyncio.run(execute_pipeline(custom_query=chosen_query))


if __name__ == "__main__":
    main()
