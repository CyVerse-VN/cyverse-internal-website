from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_current_timestamp() -> str:
    """Trả về timestamp chuẩn ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def format_posts_to_text(posts: list[dict[str, Any]], topics: list[str] | None = None) -> str:
    """
    Format toàn bộ bài viết và bình luận theo cây phân cấp trực quan vào file .txt.
    Xử lý tự động 100% bằng code thuần Python (không cần AI, tốc độ tức thì, 0 tốn token),
    chuẩn định dạng tối ưu để nạp thẳng vào các mô hình LLM/AI bên ngoài hoặc người đọc trực tiếp.
    """
    lines: list[str] = []
    lines.append("=" * 85)
    lines.append("DỮ LIỆU THREADS SCRAPER - BÀI VIẾT & CÂY BÌNH LUẬN (STRUCTURED TEXT)")
    if topics:
        lines.append(f"Chủ đề tìm kiếm: {', '.join(topics)}")
    lines.append(f"Tổng số bài viết: {len(posts)}")
    total_comments = sum(len(p.get("comments") or []) for p in posts)
    lines.append(f"Tổng số bình luận: {total_comments}")
    lines.append("=" * 85 + "\n")

    for idx, post in enumerate(posts, 1):
        uname = post.get("username") or "unknown"
        url = post.get("url") or ""
        post_id = post.get("post_id") or ""
        likes = post.get("like_count", 0) or 0
        replies = post.get("reply_count", 0) or 0
        reposts = post.get("repost_count", 0) or 0
        text = (post.get("text") or "").strip()
        pub_at = post.get("published_at") or ""
        kws = ", ".join(post.get("search_keywords") or [])

        lines.append("-" * 85)
        lines.append(f"BÀI VIẾT #{idx:02d} | Tác giả: @{uname} (ID: {post_id})")
        lines.append(f"🔗 URL: {url}")
        lines.append(f"⏱️ Đăng lúc: {pub_at} | ❤️ {likes} likes | 💬 {replies} replies | 🔁 {reposts} reposts")
        if kws:
            lines.append(f"🏷️ Từ khóa khớp: {kws}")
        lines.append(f"\n[Nội dung bài viết]:\n{text if text else '(Bài viết không có văn bản)'}\n")

        comments = post.get("comments") or []
        if comments:
            lines.append(f"[Cây thảo luận & bình luận] ({len(comments)} bình luận):")
            for c in comments:
                c_uname = c.get("username", "user")
                c_text = str(c.get("text", "")).strip()
                if not c_text:
                    continue
                depth = int(c.get("depth", 1) or 1)
                reply_to = c.get("reply_to_username")
                c_likes = c.get("like_count", 0) or 0
                like_str = f" [❤️ {c_likes}]" if c_likes > 0 else ""

                indent = "  " * max(0, depth - 1)
                if depth > 1 and reply_to:
                    lines.append(f"{indent}└── [@{c_uname}] (Cấp {depth}, trả lời @{reply_to}){like_str}: {c_text}")
                else:
                    lines.append(f"• [@{c_uname}] (Cấp 1){like_str}: {c_text}")
            lines.append("")
        else:
            lines.append("[Bình luận]: Không có bình luận nào.\n")

    return "\n".join(lines)


def save_pipeline_run(
    all_posts: list[dict[str, Any]],
    curated_posts: list[dict[str, Any]],
    topics: list[str],
    total_comments: int,
    duration_seconds: float,
    output_cfg: dict[str, Any],
    repo_root: Path,
) -> dict[str, Path]:
    """
    Lưu trữ kết quả theo cấu trúc thư mục rõ ràng:
    1. Thư mục theo mốc thời gian: output/runs/YYYY-MM-DD/run_HH-MM-SS/
       - summary.json: Thông số chạy, thời gian, chủ đề tìm kiếm
       - posts.json: Toàn bộ bài viết và bình luận (JSON)
       - posts.txt: Toàn bộ bài viết và bình luận (Văn bản phân cấp cho AI ngoài)
       - curated_places.json: Dữ liệu đã qua AI thẩm định chất lượng (nếu bật AI)
    2. File tổng hợp mới nhất (Latest Convenience Files):
       - output/threads_posts.json
       - output/threads_posts.txt
       - output/curated_places.json
    """
    base_dir = repo_root / output_cfg.get("base_dir", "output")
    runs_dir = repo_root / output_cfg.get("runs_dir", "output/runs")

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("run_%H-%M-%S")
    current_run_dir = runs_dir / date_str / time_str
    current_run_dir.mkdir(parents=True, exist_ok=True)

    timestamp_iso = get_current_timestamp()

    # 1. Summary Report
    summary_data = {
        "metadata": {
            "source": "Meta Threads",
            "executed_at": timestamp_iso,
            "duration_seconds": round(duration_seconds, 2),
            "topics": topics,
            "stats": {
                "total_posts": len(all_posts),
                "total_comments": total_comments,
                "curated_posts_count": len(curated_posts),
            },
        }
    }
    summary_file = current_run_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    # 2. Toàn bộ bài viết và bình luận (JSON)
    full_export = {
        "metadata": {
            "source": "Threads",
            "topics": topics,
            "scraped_at": timestamp_iso,
            "total_posts": len(all_posts),
            "total_comments": total_comments,
        },
        "posts": all_posts,
    }
    run_posts_file = current_run_dir / "posts.json"
    with open(run_posts_file, "w", encoding="utf-8") as f:
        json.dump(full_export, f, ensure_ascii=False, indent=2)

    # 3. Xuất file TXT phân cấp (Pure Code - Rất thân thiện với AI bên ngoài)
    txt_content = format_posts_to_text(all_posts, topics=topics)
    run_txt_file = current_run_dir / "posts.txt"
    run_txt_file.write_text(txt_content, encoding="utf-8")

    # 4. File Curated (Địa điểm/thực thể AI đã chọn lọc nếu có)
    curated_export = {
        "metadata": {
            "source": "Threads AI Curated",
            "topics": topics,
            "curated_at": timestamp_iso,
            "total_curated_items": len(curated_posts),
        },
        "curated_results": curated_posts,
    }
    run_curated_file = current_run_dir / "curated_places.json"
    with open(run_curated_file, "w", encoding="utf-8") as f:
        json.dump(curated_export, f, ensure_ascii=False, indent=2)

    # 5. Đồng bộ file mới nhất (Latest) ở thư mục output/
    latest_json_path = repo_root / output_cfg.get("json_file", "output/threads_posts.json")
    latest_txt_path = repo_root / output_cfg.get("txt_file", "output/threads_posts.txt")
    latest_curated_path = repo_root / output_cfg.get("curated_file", "output/curated_places.json")

    latest_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(full_export, f, ensure_ascii=False, indent=2)

    latest_txt_path.parent.mkdir(parents=True, exist_ok=True)
    latest_txt_path.write_text(txt_content, encoding="utf-8")

    if curated_posts:
        latest_curated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(latest_curated_path, "w", encoding="utf-8") as f:
            json.dump(curated_export, f, ensure_ascii=False, indent=2)

    return {
        "run_dir": current_run_dir,
        "summary": summary_file,
        "posts": run_posts_file,
        "posts_txt": run_txt_file,
        "curated": run_curated_file,
        "latest_posts": latest_json_path,
        "latest_txt": latest_txt_path,
        "latest_curated": latest_curated_path,
    }
