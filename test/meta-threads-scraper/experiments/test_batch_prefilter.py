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

# Sample posts from real Threads crawl
test_posts = [
    {"index": 1, "text": "Chia tay rồi ai đúng ai sai cũng không còn quan trọng ... nhưng nếu bạn muốn biết hãy nhìn vào nyc của cô ấy. Họ vội vã đi tìm 1 cuộc tình mới hay đang cắm đầu vào công việc"},
    {"index": 2, "text": "Dating Threads\nVài nét về gu của mình:\n- ưa nhìn, tóc dài, trầm tính... ai hợp ib làm quen nha"},
    {"index": 3, "text": "Cuối tuần này mình đi date với crush, mọi người có quán nào xinh xinh, đồ ăn ngon, không gian lãng mạn ở Sài Gòn recommend mình với ạ 🥹"},
    {"index": 4, "text": "Chỉ 3xx/pax chắc đây là quán date lí tưởng nhất mà mình nghĩ tới luôn í =))) decor n xinh xinh mà n tình tình, đi riết full cso của bên này luôn"},
    {"index": 5, "text": "Hôm nay đi date mà bạn nam để mình trả tiền nước, thấy cấn cấn mn ơi... mn nghĩ sao về việc chia tiền date đầu tiên?"},
    {"index": 6, "text": "Quán cổ lựa cho buổi date của chúng tôi... Vừa ấm cúng vừa ngon miệng tại Quận 1"},
    {"index": 7, "text": "Cần pass lại đầm hoa mặc đi date mới 99% size S, freeship SG mn ơi"}
]

user_query = "địa điểm hẹn hò lãng mạn ở Sài Gòn"

system_prompt = f"""Bạn là bộ lọc sơ loại thông minh (Gatekeeper AI).
Yêu cầu tìm kiếm của người dùng: "{user_query}"

Nhiệm vụ: Duyệt qua danh sách bài viết trên Threads và đánh giá xem bài viết đó có ĐÁNG ĐỂ CÀO BÌNH LUẬN (hoặc chứa thông tin địa điểm) không.
- TIÊU CHÍ CHẤP NHẬN (is_promising = true):
  1. Bài viết chia sẻ / review / giới thiệu trực tiếp quán ăn, cafe, địa điểm đi chơi, hẹn hò, du lịch.
  2. HOẶC bài viết là CÂU HỎI xin gợi ý / recommend địa điểm (vì phần bình luận bên dưới sẽ chứa rất nhiều địa điểm do cộng đồng gợi ý).
- TIÊU CHÍ LOẠI BỎ (is_promising = false):
  1. Bài tâm sự tình cảm, drama yêu đương, triết lý chia tay, tranh cãi ai trả tiền date...
  2. Bài tìm người yêu, matchmaking, tuyển gấu, tự giới thiệu bản thân...
  3. Bài bán hàng online, pass đồ, phòng trọ, quảng cáo không liên quan.

Trả về DUY NHẤT 1 mảng JSON các object theo định dạng:
[
  {{"index": 1, "is_promising": true/false, "reason": "Lý do ngắn gọn 5-10 từ"}}
]"""

payload = {
    "model": "qwen/qwen3.8-27b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(test_posts, ensure_ascii=False)}
    ],
    "temperature": 0.1
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
print("Status:", res.status_code)
content = res.json()["choices"][0]["message"]["content"]
print("Response:\n", content)
