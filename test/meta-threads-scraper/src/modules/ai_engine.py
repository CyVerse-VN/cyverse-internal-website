from __future__ import annotations

import json
import os
import re
from typing import Any
import httpx

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def analyze_user_intent(
    user_query: str,
    model: str = "qwen/qwen3.8-27b",
    count: int = 3,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Phân tích câu hỏi tự nhiên / hội thoại của người dùng theo phong cách Chatbot:
    1. Hiểu ý định tìm kiếm sâu xa của người dùng (User Intent).
    2. Sinh ra danh sách từ khóa 2-3 chữ tối ưu tuyệt đối cho Threads (vì Threads nhạy cảm với chuỗi, search câu dài sẽ ra 0 bài).
    3. Trả về phản hồi tự nhiên, thân thiện như một trợ lý AI.
    """
    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key:
        clean_words = user_query.strip().split()
        kw = " ".join(clean_words[:3]) if len(clean_words) > 3 else user_query.strip()
        return {
            "intent_summary": user_query,
            "friendly_response": f"Tôi sẽ hỗ trợ tìm kiếm bài viết về '{kw}' trên Threads giúp bạn!",
            "keywords": [kw],
        }

    system_prompt = f"""Bạn là Trợ lý AI Tìm kiếm Threads thông minh (Threads Social Listening Chatbot).
Nhiệm vụ của bạn là nhận vào câu hỏi/yêu cầu tự nhiên của người dùng, phân tích ý định và sinh ra đúng {count} cụm từ khóa tìm kiếm (search terms) tiếng Việt CỰC KỲ NGẮN (chỉ 2 đến 3 từ mỗi cụm) có lượng bài viết thảo luận/review thực tế cao nhất trên Threads Việt Nam.

QUY TẮC CỐT LÕI VỀ THUẬT TOÁN THREADS:
1. Độ dài từ khóa: BẮT BUỘC chỉ từ 2 đến 3 từ mỗi cụm (tối đa 4 từ nếu là cụm từ cố định như "hidden gem", "điểm du lịch"). Tuyệt đối không sinh câu dài vì Threads khớp chuỗi chính xác, tìm câu dài sẽ ra 0 kết quả!
2. Nắm bắt đúng văn phong tự nhiên người dùng Threads:
   - "du lịch ít người biết / hoang sơ" ➔ "địa điểm chill", "chỗ chơi vắng", "du lịch ít người", "hidden gem"
   - "quán hẹn hò lãng mạn" ➔ "quán date", "quán lãng mạn", "cafe view đẹp"
   - "tìm việc / phỏng vấn" ➔ "kinh nghiệm phỏng vấn", "review công ty", "tìm việc"
3. Tạo phản hồi chatbot thân thiện, ấm áp và tự nhiên (1-2 câu).

Trả về DUY NHẤT một JSON object chuẩn:
{{
  "intent_summary": "Tóm tắt ngắn gọn ý định cốt lõi của người dùng (1 câu)",
  "friendly_response": "Lời phản hồi thân thiện, nhiệt tình của AI chatbot (1-2 câu)",
  "keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"]
}}"""

    user_prompt = f"""Người dùng hỏi: "{user_query}"
Hãy phân tích ý định và sinh ra đúng {count} từ khóa 2-3 chữ phù hợp nhất trên Threads."""

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 300,
    }

    try:
        res = httpx.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                kws = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
                if kws:
                    return {
                        "intent_summary": data.get("intent_summary") or user_query,
                        "friendly_response": data.get("friendly_response") or "Tôi sẽ tìm kiếm giúp bạn!",
                        "keywords": kws[:count],
                    }
    except Exception as exc:
        print(f"⚠️ Lỗi phân tích ý định Chatbot AI ({exc})")

    words = user_query.strip().split()
    fallback_kw = " ".join(words[:3]) if len(words) > 3 else user_query.strip()
    return {
        "intent_summary": user_query,
        "friendly_response": "Tôi sẽ hỗ trợ bạn tìm kiếm ngay bây giờ!",
        "keywords": [fallback_kw],
    }


def expand_search_query(
    user_query: str,
    model: str = "qwen/qwen3.8-27b",
    count: int = 2,
    api_key: str | None = None,
) -> list[str]:
    """Tương thích ngược: Lấy danh sách từ khóa tối ưu từ hàm phân tích ý định."""
    res = analyze_user_intent(user_query, model=model, count=count, api_key=api_key)
    return res.get("keywords") or [user_query]


def pre_filter_posts(
    posts: list[dict[str, Any]],
    search_queries: list[str],
    model: str = "qwen/qwen3.8-27b",
    batch_size: int = 15,
    strictness: str = "high",
    api_key: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    AI Gatekeeper: Lọc sơ bộ danh sách bài viết dựa trên câu lệnh tìm kiếm TRƯỚC KHI cào bình luận.
    Loại bỏ các bài viết rác, giữ lại các bài chia sẻ kinh nghiệm hoặc câu hỏi thảo luận liên quan.
    """
    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key or not posts:
        return posts, []

    kept_posts: list[dict[str, Any]] = []
    discarded_posts: list[dict[str, Any]] = []
    queries_summary = "; ".join(search_queries)

    strictness_desc = (
        "Giữ lại bài viết trực tiếp chứa thông tin hoặc câu hỏi/thảo luận đúng chủ đề tìm kiếm."
        if strictness == "high"
        else "Nới lỏng: Giữ lại bài viết có liên quan trực tiếp hoặc gián tiếp đến chủ đề tìm kiếm."
    )

    system_prompt = f"""Bạn là AI Gatekeeper lọc bài viết mạng xã hội Threads.
Nhiệm vụ của bạn là nhận vào danh sách bài viết và chủ đề tìm kiếm của người dùng, đánh giá xem từng bài viết có TIỀM NĂNG liên quan đến chủ đề người dùng tìm kiếm hay không.

CHỦ ĐỀ TÌM KIẾM CỦA NGƯỜI DÙNG: "{queries_summary}"
MỨC ĐỘ KHẮT KHE: {strictness} ({strictness_desc})

QUY TẮC ĐÁNH GIÁ:
1. GIỮ LẠI (keep = true):
   - Bài viết chia sẻ thông tin, review, kinh nghiệm, địa điểm hoặc chủ đề người dùng đang tìm.
   - Bài viết đặt câu hỏi, thăm dò ý kiến để cộng đồng vào bình luận về chủ đề đó.
2. LOẠI BỎ (keep = false):
   - Bài viết hoàn toàn không liên quan, spam bán hàng không dính dáng, than thở vu vơ.

Định dạng trả về: DUY NHẤT một mảng JSON các object theo định dạng:
[
  {{"id": "id_bai_viet", "keep": true/false, "reason": "lý do ngắn gọn"}}
]"""

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    for i in range(0, len(posts), batch_size):
        batch = posts[i : i + batch_size]
        posts_payload = [
            {
                "id": p.get("post_id") or p.get("url") or f"idx_{idx}",
                "text": (p.get("text") or "")[:350],
                "username": p.get("username"),
            }
            for idx, p in enumerate(batch)
        ]

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(posts_payload, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }

        try:
            res = httpx.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                content = res.json()["choices"][0]["message"]["content"].strip()
                match = re.search(r"\[.*\]", content, re.DOTALL)
                if match:
                    evaluations = {item.get("id"): item for item in json.loads(match.group(0))}
                    for p in batch:
                        pid = p.get("post_id") or p.get("url")
                        decision = evaluations.get(pid, {})
                        if decision.get("keep", True):
                            p["pre_filter_reason"] = decision.get("reason", "Phù hợp chủ đề")
                            kept_posts.append(p)
                        else:
                            p["pre_filter_reason"] = decision.get("reason", "Không liên quan")
                            discarded_posts.append(p)
                    continue
        except Exception:
            pass

        kept_posts.extend(batch)

    return kept_posts, discarded_posts


def format_comments_hierarchy(comments: list[dict[str, Any]], max_chars: int = 4000) -> str:
    """
    Format danh sách bình luận theo cấu trúc phân cấp (cây hội thoại) cho AI phân tích.
    Hiển thị rõ cấp độ, người bình luận, người được phản hồi và lượt thích.
    """
    if not comments:
        return ""

    lines: list[str] = []
    total_len = 0
    for c in comments:
        uname = c.get("username", "user")
        text = str(c.get("text", "")).strip()
        if not text:
            continue

        depth = int(c.get("depth", 1) or 1)
        reply_to = c.get("reply_to_username")
        likes = c.get("like_count", 0) or 0
        like_str = f" [❤️ {likes}]" if likes > 0 else ""

        indent = "  " * max(0, depth - 1)
        if depth > 1 and reply_to:
            line = f"{indent}└── [@{uname}] (Cấp {depth}, trả lời @{reply_to}): {text}{like_str}"
        else:
            line = f"• [@{uname}] (Cấp 1): {text}{like_str}"

        if total_len + len(line) > max_chars:
            lines.append("... (và một số bình luận tiếp theo)")
            break

        lines.append(line)
        total_len += len(line)

    return "\n".join(lines)


def curate_post(
    post_text: str,
    search_queries: list[str],
    comments: list[dict[str, Any]] | None = None,
    model: str = "qwen/qwen3.8-27b",
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """
    Thẩm định sâu nội dung bài viết và trích xuất thực thể, địa điểm, chủ đề giá trị bằng Groq AI.
    Tận dụng toàn bộ ngữ cảnh bình luận phân cấp của cộng đồng.
    """
    key = api_key or os.getenv("GROQ_API_KEY", "")
    if not key or not post_text.strip():
        return None

    queries_str = "; ".join(search_queries)
    comments_context = ""
    if comments:
        formatted_tree = format_comments_hierarchy(comments, max_chars=4000)
        if formatted_tree:
            comments_context = (
                "\n\nCÁC BÌNH LUẬN & ĐỐI THOẠI CỦA CỘNG ĐỒNG (THEO PHÂN CẤP CÂY THẢO LUẬN):\n"
                f"{formatted_tree}"
            )

    system_prompt = f"""Bạn là trợ lý AI chuyên thẩm định và chuẩn hóa dữ liệu mạng xã hội Threads.
Nhiệm vụ: Đọc bài viết (kèm toàn bộ các bình luận và phản hồi từ cộng đồng) và trích xuất thông tin hữu ích liên quan đến chủ đề: "{queries_str}".

HƯỚNG DẪN ĐẶC BIỆT KHI PHÂN TÍCH BÌNH LUẬN:
1. Bình luận được tổ chức theo cấp độ phân nhánh hội thoại:
   - Cấp 1: Bình luận gốc trả lời bài viết (thường là gợi ý, review ban đầu).
   - Cấp 2, 3...: Phản hồi, tranh luận hoặc đính chính ý kiến cấp trước đó.
2. Hãy chú ý đối chiếu các phản hồi: nếu một địa điểm/ý kiến bị nhiều người bên dưới phản bác (như 'quán dở', 'chặt chém', 'đóng cửa rồi', 'phục vụ tệ'), hãy cân nhắc loại bỏ hoặc ghi chú lại cảnh báo.

Hãy trả về duy nhất một JSON object theo đúng định dạng sau:
{{
  "is_relevant": true/false,
  "confidence_score": 0.0 đến 1.0,
  "topic": "Tiêu đề ngắn gọn mô tả nội dung",
  "summary": "Tóm tắt ngắn gọn nội dung giá trị nhất trong 2-3 câu (kết hợp cả bài viết và các ý kiến bình luận giá trị)",
  "recommended_places": [
    {{"name": "Tên địa điểm/quán/dịch vụ", "category": "Loại hình", "address_or_area": "Khu vực", "note": "Ghi chú từ bình luận (nếu có)"}}
  ],
  "key_entities": ["từ khóa 1", "từ khóa 2"],
  "sentiment": "positive / neutral / negative"
}}"""

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Bài viết Threads:\n{post_text}\n{comments_context}"},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }

    try:
        res = httpx.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"].strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception:
        pass

    return None
