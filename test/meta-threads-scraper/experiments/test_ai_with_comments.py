import os
import json
import httpx
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def get_env_key():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("GROQ_API_KEY")

api_key = get_env_key()

post_text = "Mọi người ơi, cho mình xin recommend quán ăn đêm ở Sài Gòn với ạ 🥹 Tụi mình đi concert ngày 17/10 nên dự định sau concert mới đi ăn chắc phải tầm khuya 12h-1h sáng trở đi ý ạ"
comments = [
    {"username": "tva.0912", "text": "Ốc Linh- Tôn Đản Q4\nCháo sườn, bánh đúc - Lê Quang Định\nmấy quán phở dọc đường Trường Sơn (gần sân bay)\nMCdonalds Điện Biên Phủ\nOtama Ramen- Trường Sa\nMiến trộn chợ Bà Chiểu\nBún bò Vạn Kiếp (Mệ ơi Mệ ơi gì đó)"},
    {"username": "trunnielee", "text": "Matsuya vạn tuế, mở 24/7 cho các vợ."},
    {"username": "sep.gksquf._", "text": "31 Hải Triều (phở tái lăn) với 39/39 Nguyễn Cảnh Chân bún Thái trà Thái"}
]

comment_str = "\n".join([f"- @{c['username']}: {c['text']}" for c in comments])
prompt = f"Bài viết chính:\n\"{post_text}\"\n\nBình luận của cộng đồng bên dưới:\n{comment_str}"

system_prompt = """Bạn là chuyên gia thẩm định dữ liệu du lịch & ẩm thực TP.HCM.
Nhiệm vụ: Phân tích bài viết trên Threads và các bình luận bên dưới để trích xuất danh sách các địa điểm ăn uống, vui chơi, cafe hoặc du lịch Sài Gòn được gợi ý.

Trả về DUY NHẤT 1 object JSON với định dạng:
{
  "is_relevant": true,
  "category": "ăn uống" | "cafe" | "đi chơi đêm" | "hẹn hò" | "khác",
  "summary": "Tóm tắt ngắn gọn 1 câu về nội dung hỏi/chia sẻ",
  "recommended_places": [
    {
      "name": "Tên quán hoặc địa điểm",
      "district_or_address": "Địa chỉ hoặc Quận (nếu có)",
      "dish_or_feature": "Món ăn hoặc đặc điểm (nếu có)",
      "recommended_by": "username người gợi ý"
    }
  ]
}"""

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
payload = {
    "model": "qwen/qwen3.8-27b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.2
}

res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
print("Status:", res.status_code)
content = res.json()["choices"][0]["message"]["content"]
print("AI Response:\n", content)
