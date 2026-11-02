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

def dynamic_curate_post(text: str, user_queries: list[str], comments: list[dict] = None):
    query_context = ", ".join([f'"{q}"' for q in user_queries])
    system_prompt = f"""Bạn là trợ lý AI chuyên phân tích, thẩm định chất lượng và trích xuất dữ liệu giá trị từ mạng xã hội Threads.
Mục tiêu phân tích: Đánh giá bài viết dựa trên nhu cầu tìm kiếm của người dùng: [{query_context}]

Nhiệm vụ:
1. Đánh giá xem bài viết có cung cấp thông tin/thảo luận hữu ích đúng chủ đề không ("is_relevant": true/false).
2. Tóm tắt nội dung chính và các chi tiết đáng chú ý.
3. Trích xuất các thực thể chính (tên địa điểm, thương hiệu, sản phẩm, nhân vật, sự kiện...) được nhắc tới.
4. Trích xuất các gợi ý hoặc ý kiến đóng góp giá trị từ bình luận của cộng đồng.

Trả về DUY NHẤT 1 object JSON:
{{
  "is_relevant": true,
  "topic": "Chủ đề chính",
  "summary": "Tóm tắt ngắn gọn 1 câu",
  "key_entities": ["Tên thực thể, tên địa điểm, tên sản phẩm hoặc nhân vật chính"],
  "insights_from_comments": [
    {{
      "point": "Ý kiến đóng góp hoặc gợi ý",
      "author": "username"
    }}
  ],
  "recommended_places": [
    {{
      "name": "Tên địa điểm/quán nếu có (hoặc null nếu không phải chủ đề địa điểm)",
      "district_or_address": "Địa chỉ/quận nếu có",
      "feature": "Đặc điểm nổi bật nếu có"
    }}
  ]
}}"""

    prompt_content = f'Bài viết Threads:\n"{text}"'
    if comments:
        lines = [f"- @{c.get('username', 'user')}: {c.get('text', '')}" for c in comments[:10]]
        prompt_content += "\n\nBình luận cộng đồng:\n" + "\n".join(lines)

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_content}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
    if res.status_code == 200:
        content = res.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    return f"Error {res.status_code}: {res.text}"

# Test 1: Drama
p1_text = "Ai có hóng vụ drama idol T. tối qua trên livestream không? Thấy bảo bên nhãn hàng X đã hủy hợp đồng rồi."
p1_comments = [
    {"username": "netizen99", "text": "Hủy thật rồi bạn ơi, bên fanpage X vừa xóa hết ảnh đại diện có mặt T rồi."},
    {"username": "hongbien", "text": "Clip gốc 30 phút trên tiktok vẫn còn kìa mn"}
]
print("--- TEST CURATE: Drama ---")
print(json.dumps(dynamic_curate_post(p1_text, ["drama showbiz idol"], p1_comments), ensure_ascii=False, indent=2))

# Test 2: Cafe / Du lịch
p2_text = "Cuối tuần đi date ở Sài Gòn thì ghé đâu mn? Mình thích không gian yên tĩnh ngắm thành phố."
p2_comments = [
    {"username": "saigonese", "text": "Bạn thử Blank Lounge ở Landmark 81 xem, ngắm view tầng cao cực đỉnh."},
    {"username": "coffeelover", "text": "Ghé Twilight Rooftop bên quận Bình Thạnh nha, nhạc acoustic êm dịu lắm."}
]
print("\n--- TEST CURATE: Cafe / Date ---")
print(json.dumps(dynamic_curate_post(p2_text, ["địa điểm hẹn hò lãng mạn ở Sài Gòn"], p2_comments), ensure_ascii=False, indent=2))
