# 🧵 Meta Threads Scraper & AI Chatbot Intelligence Pipeline

> **Dự án**: Thu thập dữ liệu bài viết & bình luận phân cấp từ Meta Threads (threads.com), tích hợp trợ lý **AI Chatbot** phân tích ý định tìm kiếm, quản lý **đa tài khoản xoay vòng (Round-Robin)**, cấu hình **bật/tắt Proxy độc lập cho từng account**, và tự động xuất dữ liệu kép dạng **JSON + Plain Text (TXT)** tối ưu sẵn cho các hệ thống AI/LLM bên ngoài.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

- 🤖 **AI Chatbot Intent Analysis (Groq AI)**: Tiếp nhận câu hỏi tự nhiên dài (ví dụ: *"tôi muốn tìm kiếm các địa điểm du lịch ít người biết"*), tự động hiểu ý định và sinh ra các từ khóa 2-3 chữ "chuẩn văn phong Threads", tránh triệt để lỗi tìm câu dài ra 0 kết quả của Threads.
- 💬 **Chế độ Chatbot tương tác (`python main.py chat`)**: Trò chuyện trực tiếp trên terminal như một trợ lý ảo, tự động phân tích và kích hoạt crawler theo thời gian thực.
- 👥 **Multi-Account Worker Pool**: Quản lý nhiều tài khoản Threads cùng lúc (3+ accounts), tự động xoay vòng (Round-Robin) giữa các tài khoản khi tìm kiếm và cào comment để san tải và chống rate-limit.
- 🔀 **Bật/Tắt Proxy riêng cho từng tài khoản**: Tùy chỉnh linh hoạt (ví dụ: Tài khoản 1 dùng IP mạng nhà trực tiếp, Tài khoản 2 & 3 đi qua Proxy) ngay trong `config.py`.
- 🔢 **Kiểm soát số lượng tài khoản**: Tùy chọn chỉ dùng 1 acc, 2 acc hoặc toàn bộ pool (`MAX_ACCOUNTS_TO_USE`, `ACTIVE_ACCOUNTS`).
- 🌲 **Deep Comment Tree Scraping**: Tự động click *"Xem thêm phản hồi"*, cuộn động vô hạn lấy TOÀN BỘ bình luận, tái tạo chính xác cây thảo luận phân cấp (`depth`, `reply_to_username`, `parent_id`, `like_count`).
- 🧹 **Khử trùng lặp tự động (Deduplication)**: Tự động lọc bỏ các bài viết trùng lặp giữa các từ khóa con trong cùng chủ đề.
- 📄 **Xuất song song 2 định dạng (JSON & TXT)**:
  - `threads_posts.json`: Dữ liệu có cấu trúc đầy đủ metadata.
  - `threads_posts.txt`: Cây hội thoại thụt dòng `└──` được sinh tự động bằng code thuần (0 tốn token AI, tốc độ 0.01s), cực kỳ tối ưu để nạp thẳng vào LLM/RAG bên ngoài (GPT-4, Claude, Gemini...).
- 🛡️ **Cơ chế chống Ban (Anti-Ban Throttling)**: Nghỉ ngẫu nhiên, mô phỏng cử động chuột người thật, chặn nạp media (Block Media) tăng tốc độ cào gấp 3 lần.
- ⚡ **Unified Management CLI (`main.py`)**: Một file điều khiển duy nhất cho toàn bộ quy trình (`run`, `chat`, `login`, `proxy`, `test`).

---

## 📁 Cấu Trúc Dự Án (Project Structure)

```text
meta-threads-scraper/
│
├── main.py                     # [Entrypoint trung tâm] CLI quản lý toàn bộ hệ thống
├── config.py                   # [Cấu hình chính] Số acc, proxy từng acc, delay, comment
├── .env                        # [Bảo mật] Lưu thông tin tài khoản Threads & Groq API Key
├── .env.example                # File mẫu cấu hình biến môi trường
├── accounts.json               # Cấu hình tài khoản phụ (nếu không khai báo trong .env)
├── proxies.txt                 # Danh sách các proxy sống được kiểm tra với Threads
├── requirements.txt            # Danh sách thư viện Python cần cài đặt
│
├── src/                        # Mã nguồn cốt lõi
│   ├── modules/                # Kiến trúc Module hóa thế hệ mới (V2)
│   │   ├── config.py           # Bộ nạp cấu hình thông minh (.env + config.py)
│   │   ├── auth.py             # Quản lý đăng nhập Playwright & tự động tắt popup Meta
│   │   ├── proxy.py            # Tải & kiểm tra proxy sống từ Proxifly CDN
│   │   ├── crawler.py          # WorkerPool luân phiên, cào bài viết & bóc tách cây comment
│   │   ├── ai_engine.py        # Chatbot Intent Engine, phân tích câu hỏi & sinh từ khóa
│   │   ├── storage.py          # Xuất dữ liệu JSON & dựng cây văn bản phân cấp TXT
│   │   └── pipeline.py         # Orchestrator điều phối toàn bộ chu trình cào dữ liệu
│   └── threads_parser/         # Thư viện core parser gốc
│
├── sessions/                   # Thư mục lưu Cookies/Storage của các tài khoản đã đăng nhập
│   ├── acc_01.json             # Phiên đăng nhập của tài khoản 1
│   ├── acc_02.json             # Phiên đăng nhập của tài khoản 2
│   └── acc_03.json             # Phiên đăng nhập của tài khoản 3
│
├── output/                     # Thư mục lưu kết quả cào dữ liệu
│   ├── threads_posts.json      # File JSON toàn bộ bài viết mới nhất
│   ├── threads_posts.txt       # File TXT phân cấp mới nhất (nạp thẳng cho AI ngoài)
│   └── runs/                   # Phân tầng lưu trữ theo ngày & đợt chạy
│       └── YYYY-MM-DD/
│           └── run_HH-MM-SS/
│               ├── summary.json        # Thống kê số bài, số comment, thời gian chạy
│               ├── posts.json          # Toàn bộ bài viết & comment (JSON)
│               └── posts.txt           # Toàn bộ bài viết & comment dạng cây (TXT)
│
├── scripts/                    # Các kịch bản tiện ích chạy độc lập
│   ├── auto_login.py           # Tự động đăng nhập hàng loạt tài khoản
│   ├── manual_login.py         # Đăng nhập thủ công bằng tay (khi cần nhập OTP/2FA)
│   └── manage_proxies.py       # Kiểm tra và làm mới proxy sống
│
└── tests/                      # Bộ kiểm thử tự động pytest (74 tests pass)
```

---

## 🚀 Hướng Dẫn Cài Đặt (Installation)

### 1. Yêu cầu hệ thống
- **Python**: Phiên bản 3.10 trở lên (khuyên dùng Python 3.11 hoặc 3.12).
- **Hệ điều hành**: Windows, macOS, hoặc Linux.

### 2. Cài đặt môi trường ảo & Thư viện
Mở Terminal / PowerShell tại thư mục dự án:

```bash
# 1. Tạo môi trường ảo (Virtual Environment)
python -m venv .venv

# 2. Kích hoạt môi trường ảo:
# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1
# Trên Linux/macOS:
source .venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 4. Cài đặt trình duyệt Playwright Chromium
playwright install chromium
```

---

## ⚙️ Cấu Hình Hệ Thống

### 1. Khai báo tài khoản trong file `.env`
Tạo file `.env` (hoặc chỉnh sửa từ `.env.example`). Điền thông tin 3 tài khoản của bạn:

```env
# 1. Groq AI API Key (Đăng ký miễn phí tại https://console.groq.com)
GROQ_API_KEY=gsk_your_groq_api_key_here

# 2. Danh sách các tài khoản Threads
# Tài khoản 1
THREADS_USERNAME_1=username_acc_1
THREADS_PASSWORD_1=password_acc_1

# Tài khoản 2
THREADS_USERNAME_2=username_acc_2
THREADS_PASSWORD_2=password_acc_2

# Tài khoản 3
THREADS_USERNAME_3=username_acc_3
THREADS_PASSWORD_3=password_acc_3
```

### 2. Đăng nhập lần đầu để lưu Session
Chạy lệnh sau một lần duy nhất. Trình duyệt Chrome sẽ tự động mở lên, đăng nhập lần lượt từng tài khoản và lưu phiên làm việc vào `sessions/acc_01.json`, `sessions/acc_02.json`, `sessions/acc_03.json`:

```bash
python main.py login --headed
```
*(Cờ `--headed` giúp hiển thị màn hình trình duyệt để nếu tài khoản có yêu cầu nhập mã OTP/Email/SMS thì bạn có thể gõ trực tiếp).*

---

## 🎮 Cách Sử Dụng Hệ Thống

### Cách 1: Chế độ Chatbot trò chuyện tự nhiên (Khuyên dùng)
Trò chuyện tương tác trực tiếp với trợ lý AI:

```bash
python main.py chat
```

**Ví dụ thực tế:**
```text
💬 Bạn: tôi muốn tìm kiếm các địa điểm du lịch ít người biết

🧠 [AI Chatbot Engine] Đang phân tích câu hỏi & ý định của bạn...
   🤖 Chatbot: "Mình đã chuẩn bị sẵn các từ khóa 'chill' nhất để bạn khám phá những góc nhỏ yên bình của Việt Nam nhé!"
   🎯 Ý định nhận diện: Tìm kiếm các địa điểm du lịch hoang sơ, ít người biết đến và có trải nghiệm chill.
   💡 Từ khóa Threads tối ưu: ['địa điểm chill', 'chỗ chơi vắng', 'du lịch ít người']

🌐 [Playwright Crawler] Khởi chạy cào an toàn tổng cộng 3 từ khóa...
   [1/3] [acc_01] Tìm kiếm: 'địa điểm chill'... -> Thu được 15 bài
   [2/3] [acc_02] Tìm kiếm: 'chỗ chơi vắng'... -> Thu được 12 bài
   [3/3] [acc_03] Tìm kiếm: 'du lịch ít người'... -> Thu được 14 bài

💬 [Deep Comment Scraping] Bắt đầu cào bình luận cho các bài viết tiêu biểu...
   [1/10] [acc_01] Đang đọc bình luận @travel_blogger (28 replies)... -> Thu được 28 bình luận
   [2/10] [acc_02] Đang đọc bình luận @checkin_vietnam (19 replies)... -> Thu được 19 bình luận

🎉 Hoàn thành cào bài! Đã lưu tự động:
   - File JSON: output/threads_posts.json
   - File TXT:  output/threads_posts.txt
```

### Cách 2: Truyền câu hỏi trực tiếp qua dòng lệnh
```bash
python main.py "quán cafe vintage có đàn piano acoustic ở Sài Gòn"
```

### Cách 3: Chạy tự động theo danh sách trong `config.py`
```bash
python main.py
```

### Cách 4: Quản lý Proxy tự động
```bash
# Tải và test 15 proxy sống kết nối được Threads, lưu vào proxies.txt:
python main.py proxy --limit 15

# Tự động quét và thay thế proxy chết cho các tài khoản:
python main.py proxy --check --auto-fix
```

### Cách 5: Chạy kiểm thử tự động
```bash
python main.py test
```

---

## 🎛️ Bảng Cấu Hình Chi Tiết (`config.py`)

File [config.py](config.py) là trung tâm điều khiển mọi hành vi của scraper. Bạn có thể mở file và chỉnh sửa trực tiếp:

| Biến Cấu Hình | Giá Trị Mặc Định | Ý Nghĩa & Hướng Dẫn |
| :--- | :---: | :--- |
| `SEARCH_QUERIES` | `["địa điểm hẹn hò..."]` | Danh sách câu hỏi tự nhiên hoặc chủ đề tìm kiếm. |
| `MAX_POSTS_PER_KEYWORD` | `30` | Số bài viết tối đa thu thập cho mỗi từ khóa con. |
| `AUTH_ENABLED` | `True` | `True`: Dùng tài khoản đã lưu trong `sessions/`. `False`: Chạy ẩn danh (Guest). |
| `MAX_ACCOUNTS_TO_USE` | `-1` | Số lượng tài khoản sử dụng (`-1`: Dùng tất cả tài khoản có sẵn trong `sessions/`; `1`, `2`: Chỉ dùng N tài khoản đầu). |
| `ACTIVE_ACCOUNTS` | `[]` | Chỉ định danh sách tài khoản cụ thể muốn chạy (ví dụ `["acc_01", "acc_03"]` để bỏ qua `acc_02`). |
| `PROXY_ENABLED` | `False` | `True`: Bật proxy mặc định. `False`: Kết nối trực tiếp (Direct IP mạng nhà). |
| `ACCOUNT_PROXY_TOGGLE` | `{"acc_01": False,...}` | **Bật/Tắt Proxy riêng cho từng tài khoản**: Đặt `True` (bắt buộc dùng Proxy) hoặc `False` (dùng Direct IP mạng nhà). |
| `COMMENTS_ENABLED` | `True` | Bật/Tắt tính năng cào sâu bình luận bên trong bài viết. |
| `MAX_POSTS_TO_SCRAPE_COMMENTS` | `10` | Số bài viết nhiều thảo luận nhất cần vào cào comment (`-1`: Cào tất cả). |
| `MAX_COMMENTS_PER_POST` | `25` | Số bình luận tối đa lấy trong 1 bài viết (`-1`: Cuộn và lấy **TOÀN BỘ** không giới hạn). |
| `MIN_REPLIES_THRESHOLD` | `2` | Chỉ cào những bài viết có từ X bình luận trở lên. |
| `MIN_DELAY_SECONDS` | `2.0` | Thời gian nghỉ ngẫu nhiên tối thiểu giữa các thao tác (giúp chống ban). |
| `MAX_DELAY_SECONDS` | `4.0` | Thời gian nghỉ ngẫu nhiên tối đa giữa các thao tác. |
| `BLOCK_MEDIA` | `True` | Chặn nạp hình ảnh/video nặng trên trình duyệt để **tăng tốc độ cào gấp 3 lần** (link media gốc vẫn được trích xuất đầy đủ vào file). |
| `ENABLE_AI_FILTERING` | `False` | Bật/Tắt AI Groq ở Bước 3. Đặt `False` để hệ thống xuất trực tiếp dữ liệu thô & có cấu trúc sang JSON + TXT bằng code thuần, tiết kiệm 100% token cho AI bên ngoài. |
| `KEYWORDS_PER_QUERY` | `2` | Số lượng từ khóa Threads 2-3 chữ AI Chatbot sinh ra từ câu hỏi tự nhiên của bạn. |

---

## 📊 Cấu Trúc Dữ Liệu Đầu Ra (Output Structure)

Sau mỗi lần chạy, dữ liệu được tự động đồng bộ ra thư mục `output/`:

### 1. File văn bản phân cấp trực quan: `output/threads_posts.txt`
Được thiết kế tối ưu nhất để **nạp thẳng vào Context Window của LLM/AI bên ngoài** hoặc đọc bằng mắt:

```text
=====================================================================================
DỮ LIỆU THREADS SCRAPER - BÀI VIẾT & CÂY BÌNH LUẬN (STRUCTURED TEXT)
Chủ đề tìm kiếm: tôi muốn tìm kiếm các địa điểm du lịch ít người biết
Tổng số bài viết: 10
Tổng số bình luận: 85
=====================================================================================

-------------------------------------------------------------------------------------
BÀI VIẾT #01 | Tác giả: @dulich_bui (ID: 3885034422723551327)
🔗 URL: https://www.threads.com/@dulich_bui/post/DXqajlCmiBf
⏱️ Đăng lúc: 2026-04-28T04:56:55Z | ❤️ 245 likes | 💬 14 replies | 🔁 38 reposts
🏷️ Từ khóa khớp: địa điểm chill, chỗ chơi vắng

[Nội dung bài viết]:
Cuối tuần muốn trốn khói bụi thành phố, mọi người gợi ý cho mình vài cung đường phượt hoặc cắm trại còn hoang sơ gần Sài Gòn với...

[Cây thảo luận & bình luận] (14 bình luận):
• [@phuot_thu] (Cấp 1) [❤️ 32]: Bạn thử đi hồ Trị An đoạn đập tràn xem, cắm trại qua đêm siêu chill và vắng người.
  └── [@nguyen_an] (Cấp 2, trả lời @phuot_thu) [❤️ 18]: Đoạn này nhớ dọn rác sạch sẽ nha b, đợt trước nhiều nhóm tới xả rác quá.
    └── [@dulich_bui] (Cấp 3, trả lời @nguyen_an) [❤️ 5]: Dạ chắc chắn rồi bạn ơi, mình luôn mang túi rác theo.
• [@lan_ngoc] (Cấp 1) [❤️ 15]: Đi núi Dinh ở Vũng Tàu thử đi bạn, suối Tiên trên đó vắng và nước trong vắt.
```

### 2. File dữ liệu có cấu trúc: `output/threads_posts.json`
Chứa đầy đủ metadata chuẩn cho các hệ thống phần mềm, cơ sở dữ liệu hoặc script tự động hóa:
- Thông tin bài viết: `post_id`, `url`, `username`, `text`, `published_at`, `like_count`, `reply_count`, `images`, `videos`, `search_keywords`...
- Cây bình luận: Mỗi comment gồm `id`, `username`, `text`, `like_count`, `depth`, `reply_to_username`, `parent_id`.

---

## 🛡️ Giấy Phép (License)

Dự án được phân phối dưới giấy phép mã nguồn mở **MIT License**. Bạn có toàn quyền sử dụng, sửa đổi và tích hợp vào các sản phẩm cá nhân hoặc thương mại.
