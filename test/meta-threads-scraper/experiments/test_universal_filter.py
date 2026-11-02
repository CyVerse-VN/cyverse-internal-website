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

# 4 bài viết mẫu với các thể loại khác nhau:
sample_posts = [
    {
        "index": 1,
        "text": "Ai có hóng vụ drama idol T. tối qua trên livestream không? Thấy bảo bên nhãn hàng đã hủy hợp đồng rồi, thực hư thế nào vậy mn vào kể tôi nghe với 🍿"
    },
    {
        "index": 2,
        "text": "Tổng hợp 5 quán cafe rooftop ngắm hoàng hôn cực chill ở quận 1 và quận 3 cho các cặp đôi đi date cuối tuần nè."
    },
    {
        "index": 3,
        "text": "Mình chuẩn bị phỏng vấn Senior Backend Engineer tuần tới, anh em cho mình hỏi dạo này các cty hay hỏi sâu về System Design hay Concurrency hơn vậy?"
    },
    {
        "index": 4,
        "text": "Thanh lý son môi MAC mới quẹt 1 lần giá 250k freeship toàn quốc, ai lấy ib mình nha."
    }
]

def dynamic_pre_filter(query: str, strictness: str = "high"):
    system_prompt = f"""Bạn là bộ lọc sơ loại thông minh (AI Gatekeeper) cho hệ thống tìm kiếm Threads.
Chủ đề tìm kiếm của người dùng: "{query}"
Mức độ kiểm duyệt (strictness): {strictness}

Nhiệm vụ: Duyệt qua danh sách bài viết trên Threads và xác định bài viết nào PHÙ HỢP VỚI CHỦ ĐỀ NGƯỜI DÙNG để giữ lại cào bình luận sâu.
Tuyệt đối KHÔNG áp đặt định kiến chủ đề (ví dụ: không được mặc định loại bỏ bài drama, tâm sự hay bài kỹ thuật nếu người dùng đang tìm kiếm chủ đề đó).

TIÊU CHÍ ĐÁNH GIÁ:
1. CHẤP NHẬN (is_promising = true):
   - Bài viết TRỰC TIẾP chia sẻ thông tin, review, bàn luận, diễn biến, ý kiến hoặc kinh nghiệm về đúng chủ đề người dùng đang tìm.
   - HOẶC bài viết là CÂU HỎI, XIN Ý KIẾN, KHẢO SÁT, HÓNG BIẾN xoay quanh chủ đề này (vì các bình luận bên dưới sẽ chứa thông tin giải đáp và đóng góp giá trị từ cộng đồng).
2. LOẠI BỎ (is_promising = false):
   - Bài viết LẠC ĐỀ, không liên quan đến chủ đề người dùng đang tìm kiếm.
   - Bài viết chứa từ khóa trùng lặp nhưng ngữ cảnh hoàn toàn khác (ví dụ: tìm drama nhưng là bài bán hàng mượn trend; tìm địa điểm nhưng là bài tâm sự không nhắc địa điểm).
   - Bài viết bán hàng, spam, quảng cáo rác không phục vụ chủ đề.

Định dạng trả về: DUY NHẤT 1 mảng JSON các object:
[
  {{"index": 1, "is_promising": true, "reason": "Lý do ngắn gọn 5-10 từ"}}
]"""

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(sample_posts, ensure_ascii=False)}
        ],
        "temperature": 0.1,
        "max_tokens": 400
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=12)
    if res.status_code == 200:
        content = res.json()["choices"][0]["message"]["content"]
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    return f"Error {res.status_code}: {res.text}"

print("=== TEST CASE 1: Người dùng tìm DRAMA SHOWBIZ ===")
res1 = dynamic_pre_filter("drama hóng phốt showbiz idol")
print(json.dumps(res1, ensure_ascii=False, indent=2))

print("\n=== TEST CASE 2: Người dùng tìm ĐỊA ĐIỂM CAFE / HẸN HÒ ===")
res2 = dynamic_pre_filter("quán cafe rooftop hẹn hò cuối tuần")
print(json.dumps(res2, ensure_ascii=False, indent=2))

print("\n=== TEST CASE 3: Người dùng tìm PHỎNG VẤN IT / BACKEND ===")
res3 = dynamic_pre_filter("kinh nghiệm phỏng vấn backend engineer system design")
print(json.dumps(res3, ensure_ascii=False, indent=2))
