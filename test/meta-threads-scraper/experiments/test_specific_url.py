import asyncio
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from playwright.async_api import async_playwright
from modules.config import load_app_config
from modules.crawler import scrape_post_comments
from modules.ai_engine import format_comments_hierarchy, curate_post

TARGET_URL = "https://www.threads.com/share/QK5rqAx26/"

async def main():
    config = load_app_config()
    print("=" * 70)
    print(f"🎯 ĐANG KIỂM TRA CÀO TOÀN BỘ BÌNH LUẬN CHO LINK:")
    print(f"   {TARGET_URL}")
    print("=" * 70)

    session_path = REPO_ROOT / "sessions" / "acc_01.json"
    user_session_path = REPO_ROOT / "sessions" / "user_session.json"
    chosen_session = None
    if session_path.is_file():
        chosen_session = session_path
    elif user_session_path.is_file():
        chosen_session = user_session_path

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        c_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "extra_http_headers": {
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        }
        if chosen_session:
            print(f"🔑 Sử dụng phiên đăng nhập: {chosen_session.name}")
            c_kwargs["storage_state"] = str(chosen_session)
        else:
            print("🌐 Chạy ở chế độ Khách ẩn danh (Guest)")

        context = await browser.new_context(**c_kwargs)
        page = await context.new_page()

        print("\n⏳ Đang mở liên kết bài viết và giải mã redirect...")
        try:
            resp = await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ Goto timeout/warning: {e}")

        final_url = page.url
        print(f"🔗 URL thực tế sau chuyển hướng: {final_url}")

        # Lấy nội dung bài viết gốc
        post_title = await page.title()
        print(f"📌 Tiêu đề trang: {post_title}")

        # Trích xuất nội dung text bài viết gốc nếu có
        post_text = ""
        try:
            post_el = page.locator('div[data-pressable-container="true"]').first
            if await post_el.count():
                post_text = await post_el.inner_text()
        except Exception:
            pass
        if not post_text:
            post_text = post_title

        print("\n🔄 Bắt đầu cào toàn bộ bình luận (max_comments = -1)...")
        comments = await scrape_post_comments(
            page=page,
            post_url=final_url,
            max_comments=-1,  # Cào TOÀN BỘ bình luận
            enable_mouse_move=True
        )

        await browser.close()

    print("\n" + "=" * 70)
    print(f"📊 KẾT QUẢ CÀO BÌNH LUẬN:")
    print(f"   Tổng số bình luận thu thập được: {len(comments)}")
    print("=" * 70)

    if not comments:
        print("⚠️ Không tìm thấy bình luận nào (có thể bài viết không có bình luận, hoặc bị chuyển hướng/chặn).")
        return

    # Thống kê độ sâu
    depth_counts = {}
    for c in comments:
        d = c.get("depth", 1)
        depth_counts[d] = depth_counts.get(d, 0) + 1

    print("\n📈 Phân bố độ sâu bình luận:")
    for d in sorted(depth_counts.keys()):
        print(f"   - Cấp {d}: {depth_counts[d]} bình luận")

    # Mẫu JSON bình luận đầu tiên
    print("\n📝 Mẫu cấu trúc JSON của một vài bình luận tiêu biểu:")
    print(json.dumps(comments[:3], ensure_ascii=False, indent=2))

    # Cây hội thoại
    tree_str = format_comments_hierarchy(comments, max_chars=3000)
    print("\n🌳 CÂY HỘI THOẠI PHÂN CẤP (GỬI CHO AI):")
    print(tree_str)

    # Thử gọi Groq AI phân tích nếu có API Key
    groq_key = config.get("groq_api_key")
    if groq_key:
        print("\n🤖 ĐANG GỬI DỮ LIỆU ĐỂ GROQ AI THẨM ĐỊNH...")
        ai_res = curate_post(
            post_text=post_text,
            search_queries=["quán ăn", "địa điểm", "review"],
            comments=comments,
            model=config.get("groq", {}).get("model", "qwen/qwen3.8-27b"),
            api_key=groq_key,
        )
        if ai_res:
            print("\n✨ KẾT QUẢ AI PHÂN TÍCH:")
            print(json.dumps(ai_res, ensure_ascii=False, indent=2))
        else:
            print("⚠️ Groq AI không trả về kết quả JSON.")
    else:
        print("\nℹ️ Không tìm thấy GROQ_API_KEY trong .env để test bước gọi AI.")

if __name__ == "__main__":
    asyncio.run(main())
