"""
=============================================================================
CẤU HÌNH HỆ THỐNG THREADS SCRAPER & AI CURATION
=============================================================================
File này chứa toàn bộ các hằng số cấu hình của hệ thống.
Bạn có thể dễ dàng chỉnh sửa trực tiếp các giá trị bên dưới để điều khiển
hành vi cào dữ liệu, tài khoản, proxy, thời gian nghỉ và tích hợp AI.
=============================================================================
"""

from __future__ import annotations
from typing import Any

# =============================================================================
# 1. TÌM KIẾM & THU THẬP DỮ LIỆU (SEARCH & CRAWLING)
# =============================================================================

# Danh sách các chủ đề / câu lệnh tự nhiên bạn muốn tìm kiếm trên Threads.
# Hệ thống AI sẽ tự động phân tích câu này và sinh ra các từ khóa 2-3 chữ
# tối ưu nhất với thuật toán tìm kiếm của Threads (ví dụ: "quán date", "cafe đẹp").
SEARCH_QUERIES: list[str] = [
    "địa điểm hẹn hò lãng mạn ở Sài Gòn",
]

# Số lượng bài viết tối đa cần lấy cho mỗi từ khóa con (mặc định: 30 bài)
MAX_POSTS_PER_KEYWORD: int = 30


# =============================================================================
# 2. HIỆU NĂNG & TỐC ĐỘ (PERFORMANCE)
# =============================================================================

# Tối ưu hóa tốc độ cào bài viết và bình luận:
# - True: Tăng tốc gấp 3 lần bằng cách chặn trình duyệt nạp ảnh, video và font nặng.
#         (Lưu ý: Link ảnh/video gốc vẫn được trích xuất và lưu đầy đủ vào file JSON).
# - False: Tải toàn bộ media như người dùng duyệt web thông thường.
BLOCK_MEDIA: bool = True


# =============================================================================
# 3. XÁC THỰC & PHIÊN ĐĂNG NHẬP (AUTHENTICATION & SESSIONS)
# =============================================================================

# Bật/Tắt chế độ sử dụng tài khoản đăng nhập Threads:
# - True: Tự động sử dụng phiên đăng nhập (Cookies/Storage) từ thư mục sessions/
#         (giúp tìm kiếm câu dài không giới hạn, cào sâu bình luận mà không bị chặn).
# - False: Chế độ khách ẩn danh (Guest mode).
AUTH_ENABLED: bool = True

# Điều chỉnh số lượng tài khoản sử dụng trong phiên cào:
# - Đặt số dương (ví dụ: 1, 2): Chỉ lấy đúng N tài khoản đầu tiên để cào.
# - Đặt -1: Sử dụng TẤT CẢ tài khoản có sẵn trong sessions/ (mặc định: dùng cả 3 acc).
MAX_ACCOUNTS_TO_USE: int = -1

# Chỉ định danh sách cụ thể các tài khoản muốn chạy (ghi đè MAX_ACCOUNTS_TO_USE nếu có):
# Ví dụ: ["acc_01", "acc_02"] -> chỉ chạy 2 acc này, bỏ qua acc_03.
# Để trống [] nếu muốn tự động lấy theo MAX_ACCOUNTS_TO_USE.
ACTIVE_ACCOUNTS: list[str] = []

# File session lưu cookies khi người dùng đăng nhập thủ công qua `python main.py login --manual`
SESSION_FILE: str = "sessions/user_session.json"

# Thư mục chứa session của các tài khoản (mặc định: sessions/acc_01.json, ...)
SESSIONS_DIR: str = "sessions"


# =============================================================================
# 4. CẤU HÌNH PROXY & BẬT/TẮT CHO TỪNG TÀI KHOẢN (PER-ACCOUNT PROXY)
# =============================================================================

# Bật/Tắt sử dụng Proxy chung (dành cho các tài khoản không cấu hình riêng bên dưới):
# - False: Mặc định kết nối trực tiếp (Direct IP mạng gia đình).
# - True: Mặc định bật proxy từ PROXY_FILE.
PROXY_ENABLED: bool = False

# Đường dẫn file danh sách proxy sống (mỗi dòng một proxy URL: http://user:pass@host:port)
PROXY_FILE: str = "proxies.txt"

# BẬT / TẮT PROXY RIÊNG BIỆT CHO TỪNG TÀI KHOẢN:
# Cấu hình linh hoạt:
# - True: Tài khoản này BẮT BUỘC dùng Proxy (lấy proxy cấp phát từ proxies.txt hoặc accounts.json).
# - False: Tài khoản này KẾT NỐI TRỰC TIẾP (Direct IP mạng nhà, không qua proxy).
# (Nếu tài khoản nào không được liệt kê ở đây, nó sẽ nhận giá trị của PROXY_ENABLED ở trên).
ACCOUNT_PROXY_TOGGLE: dict[str, bool] = {
    "acc_01": False,  # Tài khoản 1: Kết nối trực tiếp (Direct IP mạng nhà)
    "acc_02": False,  # Tài khoản 2: Đặt True nếu muốn bật proxy, False là mạng nhà
    "acc_03": False,  # Tài khoản 3: Đặt True nếu muốn bật proxy, False là mạng nhà
}


# =============================================================================
# 5. AI TIỀN LỌC BÀI VIẾT (AI GATEKEEPER PRE-FILTER)
# =============================================================================

# Đánh giá tiêu đề/nội dung bài viết dựa trên câu lệnh tìm kiếm TRƯỚC KHI cào bình luận
# - True: Bật AI đối chiếu nội dung bài viết với SEARCH_QUERIES để loại bài rác sớm.
# - False: Tắt (chọn bài cào comment thuần túy dựa trên số lượt replies).
PRE_FILTER_ENABLED: bool = False

# Số lượng bài viết gửi cho AI thẩm định cùng 1 lượt trong 1 request (batch size)
PRE_FILTER_BATCH_SIZE: int = 15

# Mức độ nghiêm ngặt của AI khi lọc bài:
# - "high": Chỉ giữ bài đúng trọng tâm hoặc câu hỏi sát nhất với chủ đề tìm kiếm.
# - "medium": Nới lỏng cho các bài thảo luận có liên quan gián tiếp.
PRE_FILTER_STRICTNESS: str = "high"


# =============================================================================
# 6. CÀO BÌNH LUẬN CHI TIẾT (COMMENTS & REPLIES)
# =============================================================================

# Bật/Tắt cào bình luận bên trong bài viết để lấy thêm thông tin review/đánh giá
COMMENTS_ENABLED: bool = True

# Số lượng bài viết tối đa cần vào cào bình luận (khuyên dùng 5-10 để chạy nhanh; -1: tất cả)
MAX_POSTS_TO_SCRAPE_COMMENTS: int = 10

# Số lượng bình luận tối đa lấy trong 1 bài viết:
# - Đặt số dương (ví dụ: 25, 50): Lấy tối đa số lượng này rồi dừng lại.
# - Đặt -1 hoặc 0: Lấy TOÀN BỘ bình luận không giới hạn (tự động cuộn động và bấm 'Xem thêm phản hồi' cho đến khi hết bài).
MAX_COMMENTS_PER_POST: int = 25

# Ngưỡng bình luận tối thiểu: Chỉ cào bài viết có từ X bình luận trở lên (tránh bài ít tương tác)
MIN_REPLIES_THRESHOLD: int = 2


# =============================================================================
# 7. CƠ CHẾ CHỐNG SPAM & CHỐNG RATE LIMIT (ANTI-BAN & HUMAN SIMULATION)
# =============================================================================

# Thời gian nghỉ ngẫu nhiên tối thiểu giữa các thao tác cuộn / chuyển trang (giây)
MIN_DELAY_SECONDS: float = 2.0

# Thời gian nghỉ ngẫu nhiên tối đa giữa các thao tác cuộn / chuyển trang (giây)
MAX_DELAY_SECONDS: float = 4.0

# Mô phỏng cử động chuột ngẫu nhiên như người dùng thật để vượt qua cơ chế bot detection
RANDOM_MOUSE_MOVEMENT: bool = True


# =============================================================================
# 8. CẤU HÌNH GROQ AI (AI MODEL & EXTRACTION)
# =============================================================================

# Tên mô hình AI sử dụng trên Groq Cloud (ví dụ: "qwen/qwen3.8-27b", "llama-3.3-70b-versatile")
GROQ_MODEL: str = "qwen/qwen3.8-27b"

# Bật/Tắt AI thẩm định bước 3 (đặt False để xuất dữ liệu sạch dạng JSON & TXT bằng code thuần cho AI ngoài xử lý)
ENABLE_AI_FILTERING: bool = False

# Số lượng từ khóa Threads 2-3 chữ AI Chatbot sinh ra từ câu hỏi tự nhiên của người dùng (khuyên dùng: 2 - 3)
KEYWORDS_PER_QUERY: int = 2


# =============================================================================
# 9. ĐƯỜNG DẪN KẾT QUẢ ĐẦU RA (OUTPUT DIRECTORIES & FILES)
# =============================================================================

# Thư mục gốc lưu trữ toàn bộ dữ liệu đầu ra
BASE_OUTPUT_DIR: str = "output"

# Thư mục lưu dữ liệu theo từng phiên chạy (output/runs/YYYY-MM-DD/run_HH-MM-SS/)
RUNS_OUTPUT_DIR: str = "output/runs"

# File tổng hợp toàn bộ bài viết của lần cào gần nhất (để tiện truy cập nhanh)
LATEST_POSTS_FILE: str = "output/threads_posts.json"

# File văn bản .txt phân cấp trực quan bằng code thuần (dành cho người đọc hoặc nạp thẳng vào AI ngoài)
LATEST_TXT_FILE: str = "output/threads_posts.txt"

# File tổng hợp dữ liệu đã qua AI thẩm định chất lượng của lần cào gần nhất (nếu bật AI)
LATEST_CURATED_FILE: str = "output/curated_places.json"


# =============================================================================
# HÀM XUẤT CẤU HÌNH (HELPER EXPORT)
# =============================================================================

def to_dict() -> dict[str, Any]:
    """Chuyển đổi toàn bộ các hằng số cấu hình thành dictionary chuẩn."""
    return {
        "search_queries": SEARCH_QUERIES,
        "max_posts_per_keyword": MAX_POSTS_PER_KEYWORD,
        "performance": {
            "block_media": BLOCK_MEDIA,
        },
        "auth": {
            "enabled": AUTH_ENABLED,
            "session_file": SESSION_FILE,
            "sessions_dir": SESSIONS_DIR,
        },
        "proxy": {
            "enabled": PROXY_ENABLED,
            "proxy_file": PROXY_FILE,
        },
        "pre_filter": {
            "enabled": PRE_FILTER_ENABLED,
            "batch_size": PRE_FILTER_BATCH_SIZE,
            "strictness": PRE_FILTER_STRICTNESS,
        },
        "comments": {
            "enabled": COMMENTS_ENABLED,
            "max_posts_to_scrape": MAX_POSTS_TO_SCRAPE_COMMENTS,
            "max_comments_per_post": MAX_COMMENTS_PER_POST,
            "min_replies_threshold": MIN_REPLIES_THRESHOLD,
        },
        "anti_ban": {
            "min_delay_seconds": MIN_DELAY_SECONDS,
            "max_delay_seconds": MAX_DELAY_SECONDS,
            "random_mouse_movement": RANDOM_MOUSE_MOVEMENT,
        },
        "groq": {
            "model": GROQ_MODEL,
            "enable_ai_filtering": ENABLE_AI_FILTERING,
            "keywords_per_query": KEYWORDS_PER_QUERY,
        },
        "output": {
            "base_dir": BASE_OUTPUT_DIR,
            "runs_dir": RUNS_OUTPUT_DIR,
            "json_file": LATEST_POSTS_FILE,
            "curated_file": LATEST_CURATED_FILE,
        },
    }
