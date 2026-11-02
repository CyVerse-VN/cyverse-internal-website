import os
import httpx
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

def get_env_key():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("GROQ_API_KEY")

api_key = get_env_key()

test_posts = [
    {"index": 1, "text": "Chia tay rồi ai đúng ai sai cũng không còn quan trọng ... nhưng nếu bạn muốn biết hãy nhìn vào nyc của cô ấy."},
    {"index": 2, "text": "Cuối tuần này mình đi date với crush, mọi người có quán nào xinh xinh, đồ ăn ngon ở Sài Gòn recommend mình với ạ 🥹"},
    {"index": 3, "text": "Cần pass lại đầm hoa mặc đi date mới 99% size S, freeship SG mn ơi"}
]

def test_query_filter(query):
    system_prompt = f"""Bạn là bộ lọc sơ loại thông minh (AI Gatekeeper).
Yêu cầu tìm kiếm của người dùng: "{query}"

Nhiệm vụ: Duyệt qua danh sách bài viết trên Threads và đánh giá xem bài viết đó có PHÙ HỢP VỚI YÊU CẦU TÌM KIẾM CỦA NGƯỜI DÙNG để đáng cào bình luận hay không.
- TIÊU CHÍ CHẤP NHẬN (is_promising = true):
  1. Bài viết trực tiếp đề cập, chia sẻ thông tin, review hoặc thảo luận đúng chủ đề người dùng đang tìm kiếm.
  2. HOẶC bài viết là CÂU HỎI / XIN Ý KIẾN xoay quanh chủ đề này (vì các bình luận bên dưới sẽ chứa thông tin giải đáp trực tiếp cho chủ đề).
- TIÊU CHÍ LOẠI BỎ (is_promising = false):
  1. Bài viết lạc đề, không phục vụ cho mục tiêu tìm kiếm của người dùng.
  2. Bài viết chứa từ khóa trùng hợp nhưng nội dung thuộc về chủ đề khác (ví dụ tìm địa điểm nhưng bài viết là bán hàng, tâm sự không liên quan).
  3. Tin spam, rác, bot.

Trả về DUY NHẤT 1 mảng JSON:
[
  {{"index": 1, "is_promising": true/false, "reason": "Lý do ngắn gọn 5-10 từ"}}
]"""

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(test_posts, ensure_ascii=False)}
        ],
        "temperature": 0.1,
        "max_tokens": 400
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
    if res.status_code != 200:
        return f"Error {res.status_code}: {res.text}"
    return res.json()["choices"][0]["message"]["content"]

print("--- Test 1: Query = 'địa điểm hẹn hò Sài Gòn' ---")
print(test_query_filter("địa điểm hẹn hò Sài Gòn"))

print("\n--- Test 2: Query = 'tâm sự chia tay tình cảm' ---")
print(test_query_filter("tâm sự chia tay tình cảm"))
