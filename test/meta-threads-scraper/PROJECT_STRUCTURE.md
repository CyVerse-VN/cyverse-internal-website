# CẤU TRÚC THƯ MỤC VÀ TÀI LIỆU DỰ ÁN (PROJECT STRUCTURE)

> **Dự án**: Meta Threads Scraper & AI Curation Pipeline  
> **Mục tiêu**: Thu thập dữ liệu bài viết & bình luận từ Meta Threads (threads.com/threads.net), quản lý proxy & phiên đăng nhập đa tài khoản, chống checkpoint/rate limit, tích hợp AI (Groq API / Qwen / Llama) để mở rộng từ khóa, lọc bài và thẩm định/trích xuất dữ liệu có cấu trúc.

---

## 1. SƠ ĐỒ CÂY THƯ MỤC TỔNG THỂ

```plaintext
meta-threads-scraper/
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # Quy trình CI tự động kiểm thử trên Python 3.11 & 3.13
│
├── examples/                      # File mẫu cấu hình dữ liệu đầu vào
│   ├── accounts.example.json      # Mẫu khai báo danh sách tài khoản Threads
│   ├── proxies.example.txt        # Mẫu danh sách proxy HTTP/HTTPS
│   └── users.example.json         # Mẫu danh sách username Threads để cào profile
│
├── experiments/                   # Thư mục thí nghiệm, R&D và script kiểm chứng kỹ thuật
│   ├── ai_threads_scraper.py      # Bản mẫu nguyên khối (monolith prototype) đầu tiên
│   ├── analyze_comment_structure.py # Phân tích cây DOM / cấu trúc JSON của bình luận Threads
│   ├── comment_structure.json     # Dữ liệu JSON mẫu phân tích cấu trúc bình luận
│   ├── diagnose_free_proxies.py   # Chẩn đoán kết nối và độ trễ proxy công cộng
│   ├── inspect_login_dom.py       # Kiểm tra các selector của form đăng nhập Threads
│   ├── inspect_output_comments.py # Script kiểm tra nhanh bình luận trong output JSON
│   ├── otp_code.py                # Thử nghiệm sinh mã 2FA TOTP tự động bằng pyotp
│   ├── post_debug.json            # Dữ liệu debug bài viết thô
│   ├── run_threads_search_experiment.py # Thử nghiệm cào tìm kiếm với các tham số khác nhau
│   ├── sample_post.json           # Dữ liệu mẫu một bài viết chuẩn hóa
│   ├── test_ai_with_comments.py   # Kiểm thử prompt AI phân tích bài viết kèm bình luận
│   ├── test_anonymous_post.py     # Kiểm tra khả năng lấy bài viết ở chế độ khách (Guest)
│   ├── test_batch_prefilter.py    # Kiểm thử tính năng AI lọc sơ bộ hàng loạt (Batch Pre-filter)
│   ├── test_clean_comments.py     # Thử nghiệm làm sạch văn bản và lọc nhiễu bình luận
│   ├── test_comment_depth.py      # Thử nghiệm cào bình luận đa tầng (nested replies)
│   ├── test_dynamic_query_filter.py # Kiểm tra bộ lọc bài viết linh hoạt theo truy vấn
│   ├── test_free_proxies.py       # Thử nghiệm tải và kiểm tra proxy miễn phí
│   ├── test_keyword_lengths.py    # Đo lường độ nhạy của Threads Search với độ dài từ khóa
│   ├── test_pagination_network.py # Thử nghiệm bắt gói tin mạng GraphQL/Relay khi cuộn trang
│   ├── test_parse_raw_http.py     # Thử nghiệm parse bài viết trực tiếp qua HTTP
│   ├── test_post_comments.py      # Thử nghiệm trích xuất bình luận bên trong bài viết
│   ├── test_post_ssr.py           # Thử nghiệm đọc dữ liệu Server-Side Rendering (SSR) nhúng
│   ├── test_raw_http.py           # Thử nghiệm request HTTP thuần (không cần trình duyệt)
│   ├── test_search_raw_http.py    # Thử nghiệm tìm kiếm bằng HTTP client trực tiếp
│   ├── test_speed.py              # Đo lường tốc độ cào giữa các chiến lược khác nhau
│   ├── test_universal_curation.py # Thử nghiệm prompt thẩm định nội dung tổng quát
│   ├── test_universal_filter.py   # Thử nghiệm AI Filter đa chủ đề
│   ├── test_user_exact_query.py   # Thử nghiệm tìm kiếm khớp chính xác chuỗi người dùng
│   └── *.png                      # Ảnh chụp màn hình kiểm chứng kết quả trong quá trình R&D
│
├── output/                        # Thư mục chứa dữ liệu kết quả cào & thẩm định
│   ├── runs/                      # Dữ liệu lưu trữ theo phiên chạy (YYYY-MM-DD/run_HH-MM-SS/)
│   │   └── YYYY-MM-DD/
│   │       └── run_HH-MM-SS/
│   │           ├── summary.json   # Báo cáo thống kê phiên chạy (thời gian, số bài, số comment)
│   │           ├── posts.json     # Toàn bộ dữ liệu bài viết & bình luận đã cào
│   │           └── curated_places.json # Dữ liệu bài viết/địa điểm đã qua AI thẩm định chất lượng
│   ├── search/                    # Kết quả cào của CLI threads-parser gốc (phân loại theo keyword/tag)
│   ├── curated_places.json        # Dữ liệu thẩm định AI của phiên chạy mới nhất
│   ├── threads_posts.json         # Toàn bộ bài viết của phiên chạy mới nhất
│   ├── test_report.md             # Báo cáo tổng hợp kết quả chạy thử nghiệm
│   └── .gitkeep                   # Giữ thư mục output trên git
│
├── scripts/                       # Các kịch bản tiện ích điều hành nhanh
│   ├── auto_login.py              # Tự động đăng nhập hàng loạt tài khoản từ .env/accounts.json
│   ├── manual_login.py            # Mở trình duyệt có giao diện để người dùng tự đăng nhập thủ công
│   └── manage_proxies.py          # Kiểm tra proxy của tài khoản và tải proxy sống từ Proxifly CDN
│
├── sessions/                      # Lưu trữ phiên đăng nhập (Cookies, LocalStorage) dạng JSON
│   └── acc_01.json                # Phiên đăng nhập Playwright đã lưu của tài khoản 01
│
├── src/                           # Mã nguồn chính của dự án
│   ├── login_accounts.py          # Module đăng nhập tự động tích hợp xác thực 2FA TOTP (threads-parser)
│   │
│   ├── modules/                   # Hệ thống Pipeline & Kiến trúc Modular hóa hiện đại
│   │   ├── __init__.py            # Khởi tạo package modules
│   │   ├── config.py              # Nạp biến môi trường .env, nạp config.py & quản lý cấu hình
│   │   ├── auth.py                # Quản lý phiên đăng nhập, nạp session, tự động tắt popup Meta
│   │   ├── proxy.py               # Lấy proxy từ jsDelivr/Proxifly CDN, format proxy cho Playwright
│   │   ├── crawler.py             # Playwright WorkerPool, cào bài viết theo từ khóa, cào bình luận
│   │   ├── ai_engine.py           # Kết nối Groq AI (mở rộng từ khóa 2-3 chữ, tiền lọc, thẩm định bài)
│   │   ├── storage.py             # Quản lý lưu trữ kết quả theo mốc thời gian runs/ và file mới nhất
│   │   └── pipeline.py            # Orchestrator điều phối toàn bộ chu trình cào -> AI -> lưu trữ
│   │
│   └── threads_parser/            # Thư viện lõi gốc (Engine cào profile/search và CLI threads-parser)
│       ├── __init__.py            # Khởi tạo package threads_parser
│       ├── __main__.py            # Entry point khi chạy `python -m threads_parser`
│       ├── accounts.py            # Khai báo AccountConfig, quản lý thông tin tài khoản và context
│       ├── browser.py             # Quản lý vòng đời trình duyệt Playwright, stealth script, tắt cookie
│       ├── cli.py                 # Xử lý tham số dòng lệnh cho lệnh `threads-parser`
│       ├── errors.py              # Định nghĩa các Exception tùy biến (TargetProfileError, ProxyAccessError)
│       ├── media.py               # Tải hình ảnh/video về máy với cơ chế retry và đặt tên an toàn
│       ├── parser.py              # Phân tích cú pháp dữ liệu HTML, JSON-LD, GraphQL Relay của Threads
│       ├── proxies.py             # Xử lý xoay vòng proxy, nạp danh sách proxy từ file
│       ├── quarantine.py          # Cơ chế cách ly (quarantine) các proxy bị lỗi/chặn tạm thời
│       ├── runner.py              # Điều phối tác vụ cào profile/search, kiểm soát số lượng bài viết
│       ├── search.py              # Trích xuất danh sách bài viết từ trang tìm kiếm (Top & Recent)
│       ├── storage.py             # Lưu trữ dữ liệu bài viết và quản lý trùng lặp (deduplication)
│       └── traffic.py             # Giám sát lưu lượng mạng, băng thông tiêu thụ và số lượng request
│
├── tests/                         # Bộ kiểm thử tự động (Pytest)
│   ├── test_accounts.py           # Kiểm thử tính hợp lệ của tài khoản, nạp session và TOTP
│   ├── test_cli_traffic.py        # Kiểm thử tích hợp CLI và theo dõi traffic mạng
│   ├── test_login_accounts.py     # Kiểm thử luồng đăng nhập và xử lý lỗi đăng nhập
│   ├── test_media_filter.py       # Kiểm thử bộ lọc định dạng ảnh/video khi tải về
│   ├── test_modules.py            # Kiểm thử các module cốt lõi (config, ai_engine, proxy, storage)
│   ├── test_parser_boundaries.py  # Kiểm thử các trường hợp biên của parser với HTML/JSON bị thiếu dữ liệu
│   ├── test_proxies.py            # Kiểm thử chuẩn hóa proxy và xoay vòng proxy
│   ├── test_quarantine.py         # Kiểm thử cơ chế cách ly và giải phóng proxy lỗi
│   ├── test_runtime_dependencies.py # Kiểm tra tính sẵn sàng của các thư viện phụ thuộc
│   ├── test_storage.py            # Kiểm thử ghi/đọc dữ liệu bài viết và cấu trúc thư mục
│   └── test_traffic.py            # Kiểm thử bộ đếm dung lượng mạng và phân tích trạng thái HTTP
│
├── .env                           # File cấu hình biến môi trường bảo mật (API Key, mật khẩu, proxy cá nhân)
├── .env.example                   # File mẫu hướng dẫn khai báo biến môi trường an toàn
├── .gitignore                     # Danh sách file/thư mục loại trừ khỏi quản lý phiên bản Git
├── accounts.json                  # Cấu hình danh sách tài khoản Threads và proxy gán riêng cho từng acc
├── config.py                      # Cấu hình hằng số trung tâm (từ khóa tìm kiếm, delay chống ban, comment, AI)
├── LICENSE                        # Giấy phép mã nguồn mở (MIT License)
├── main.py                        # Điểm khởi chạy trung tâm (Unified CLI) quản lý toàn bộ hệ thống
├── proxies.txt                    # Danh sách các proxy hoạt động tốt đã được kiểm tra và lọc
├── pyproject.toml                 # Khai báo metadata dự án, build system và console entrypoint
├── README.md                      # Tài liệu hướng dẫn sử dụng chi tiết bằng tiếng Anh
└── requirements.txt               # Danh sách các thư viện Python cần cài đặt
```

---

## 2. CHI TIẾT TỪNG FILE & MỤC ĐÍCH SỬ DỤNG

### 2.1. Thư mục gốc (Root Directory)

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `main.py` | **Trung tâm điều khiển duy nhất (Unified Management CLI)** của toàn bộ dự án. Cung cấp các lệnh: `python main.py` (chạy pipeline cào + AI), `python main.py login` (đăng nhập tài khoản), `python main.py proxy` (làm mới/kiểm tra proxy sống), và `python main.py test` (chạy toàn bộ bộ test). |
| `config.py` | **File cấu hình hằng số hoạt động chính** của hệ thống: từ khóa tìm kiếm (`SEARCH_QUERIES`), số bài viết tối đa (`MAX_POSTS_PER_KEYWORD`), cấu hình AI pre-filter, thông số cào bình luận (`COMMENTS_ENABLED`, `MAX_COMMENTS_PER_POST`), cơ chế nghỉ ngẫu nhiên chống ban (`MIN_DELAY_SECONDS`, `MAX_DELAY_SECONDS`), và đường dẫn lưu trữ. Có comment `#` chi tiết, dễ dàng chỉnh sửa. |
| `.env` | **Lưu trữ các thông tin bí mật/nhạy cảm**: thông tin tài khoản đăng nhập Threads (`THREADS_USERNAME`, `THREADS_PASSWORD`), khóa `GROQ_API_KEY` gọi LLM, proxy cá nhân. Tuyệt đối không commit lên git. |
| `.env.example` | File mẫu cung cấp hướng dẫn cách khai báo các biến môi trường cho `.env`. |
| `accounts.json` | File cấu hình danh sách nhiều tài khoản Threads cho trường hợp chạy đa tài khoản/đa proxy (`accounts-file`). |
| `proxies.txt` | Chứa danh sách các proxy HTTP/HTTPS sống đã được hệ thống kiểm tra với Threads và sẵn sàng cho crawler sử dụng. |
| `pyproject.toml` | Cấu hình cài đặt package theo chuẩn PEP 518/621, định nghĩa lệnh terminal `threads-parser` trỏ đến `src/threads_parser/cli.py`. |
| `requirements.txt` | Liệt kê các thư viện phụ thuộc chính: `playwright`, `httpx`, `pyotp`, `pytest`. |
| `README.md` | Tài liệu giới thiệu tổng quan dự án, hướng dẫn cài đặt, cú pháp lệnh CLI, và các tính năng chính bằng tiếng Anh. |
| `LICENSE` | Giấy phép bản quyền mã nguồn mở MIT. |
| `.gitignore` | Quy định các file/thư mục không đưa vào Git (như `.env`, `.venv/`, `sessions/`, `output/runs/`, `__pycache__/`). |

---

### 2.2. Thư mục `src/modules/` (Kiến trúc Pipeline & Nghiệp vụ Nâng cao)

Thư mục này đại diện cho kiến trúc cải tiến dạng module (Modular Architecture), tối ưu hóa việc tích hợp giữa **Playwright Scraper + Groq LLM Engine**:

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `__init__.py` | Đánh dấu thư mục `modules` là một Python package. |
| `config.py` | Nạp biến môi trường từ `.env` và hợp nhất với các hằng số cấu hình từ `config.py` và `accounts.json`. Cung cấp hàm `load_app_config()` an toàn. |
| `auth.py` | Quản lý phiên đăng nhập: tự động đăng nhập tài khoản Threads, kiểm tra và nạp cookies/session từ thư mục `sessions/`, tự động tắt các popup của Meta ("Lưu thông tin đăng nhập", "Để sau"). |
| `proxy.py` | Quản lý proxy thông minh: tải proxy miễn phí mới nhất từ Proxifly/jsDelivr CDN, kiểm tra kết nối proxy trực tiếp với Threads, và chuyển đổi URL proxy sang định dạng Playwright hỗ trợ. |
| `crawler.py` | Trình cào dữ liệu tối ưu: quản lý `WorkerPool` trình duyệt Playwright, chặn tải ảnh/video/font để tăng tốc độ gấp 3 lần, mô phỏng di chuột người thật (`simulate_human_mouse`), cào bài viết theo từ khóa và cào bình luận chi tiết. |
| `ai_engine.py` | Tích hợp Groq Cloud API: mở rộng từ khóa tìm kiếm thành các cụm 2-3 chữ phù hợp thuật toán Threads (`expand_search_query`), AI tiền lọc bài viết liên quan (`pre_filter_posts`), và thẩm định/trích xuất thông tin chi tiết (`curate_post`). |
| `storage.py` | Lưu trữ dữ liệu chuẩn hóa: tạo cấu trúc thư mục theo thời gian `output/runs/YYYY-MM-DD/run_HH-MM-SS/`, xuất file báo cáo `summary.json`, toàn bộ bài `posts.json`, bài thẩm định `curated_places.json`, và cập nhật file mới nhất ở thư mục gốc `output/`. |
| `pipeline.py` | **Bộ điều phối (Orchestrator)** kết nối toàn bộ các module: đọc cấu hình -> mở rộng từ khóa -> nạp session -> cào bài viết song song -> lọc AI -> cào bình luận -> thẩm định thông tin -> lưu trữ báo cáo. |

---

### 2.3. Thư mục `src/threads_parser/` (Engine Cào Lõi & CLI Gốc)

Thư mục này chứa core scraper gốc của `meta-threads-scraper`, cung cấp công cụ dòng lệnh `threads-parser`:

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `__init__.py` | Khai báo package và phiên bản của parser. |
| `__main__.py` | Cho phép chạy module trực tiếp từ terminal qua lệnh `python -m threads_parser`. |
| `accounts.py` | Định nghĩa lớp dữ liệu `AccountConfig`, nạp tài khoản từ JSON, quản lý trạng thái tài khoản và khởi tạo Playwright context độc lập cho từng tài khoản. |
| `browser.py` | Quản lý vòng đời Playwright browser, chèn stealth script che giấu tự động hóa, thu thập các thẻ `<script type="application/json">` nhúng trên Threads, và xử lý banner chấp thuận Cookie. |
| `cli.py` | Phân tích cú pháp các cờ lệnh dòng lệnh của `threads-parser` (như `--search`, `--search-mode`, `--users-file`, `--incremental`, `--proxy`, `--max-posts`). |
| `errors.py` | Khai báo các ngoại lệ đặc thù như `TargetProfileError` (lỗi khi cào profile) và `ProxyAccessError` (lỗi kết nối proxy). |
| `media.py` | Tự động tải hình ảnh và video từ bài viết Threads về đĩa cứng, có cơ chế đặt tên file theo hash an toàn và retry khi rớt mạng. |
| `parser.py` | Bóc tách dữ liệu bài viết từ nhiều nguồn: GraphQL response, Relay store, JSON-LD schema, hoặc HTML DOM; chuẩn hóa thông tin lượt thích, chia sẻ, nội dung, tác giả. |
| `proxies.py` | Đọc danh sách proxy từ file văn bản, phân giải định dạng URL `http://user:pass@host:port` và thực hiện xoay vòng proxy cho các worker. |
| `quarantine.py` | Cơ chế "cách ly" proxy: khi một proxy bị lỗi timeout hoặc bị Threads chặn, nó sẽ bị đưa vào danh sách quarantine trong một khoảng thời gian nhất định trước khi được thử lại. |
| `runner.py` | Điều phối quá trình cào: phân bổ profile/từ khóa cho các worker, kiểm soát giới hạn bài viết, xử lý cập nhật bài viết mới (`incremental`) và retry khi đổi tài khoản. |
| `search.py` | Xây dựng URL tìm kiếm theo từ khóa/hashtag (`keyword`/`tag`) và chế độ sắp xếp (`top`/`recent`), cuộn trang và thu thập danh sách bài viết từ kết quả tìm kiếm. |
| `storage.py` | Quản lý ghi dữ liệu bài viết ra thư mục `output/`, kiểm tra trùng lặp bài viết (`deduplication`) để tránh cào lại các bài đã lưu. |
| `traffic.py` | Giám sát và ghi nhận lưu lượng mạng tiêu thụ (số request, byte gửi/nhận, HTTP status codes) theo từng tài khoản hoặc domain. |

---

### 2.4. Thư mục `src/` (File độc lập)

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `login_accounts.py` | Tiện ích hỗ trợ đăng nhập tài khoản Threads hàng loạt có hỗ trợ **mã xác thực 2 bước (TOTP/2FA)** thông qua thư viện `pyotp`. |

---

### 2.5. Thư mục `scripts/` (Kịch bản Quản trị)

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `auto_login.py` | Kịch bản chạy nhanh tự động đăng nhập các tài khoản được cấu hình trong `.env` hoặc `accounts.json` và lưu phiên vào thư mục `sessions/`. |
| `manual_login.py` | Mở trình duyệt Chrome có giao diện thật (`headless=False`) để người dùng tự tay đăng nhập vào Threads (bằng mật khẩu, mã OTP điện thoại, hoặc QR code Instagram). Sau khi vào trang chủ, script tự bắt lấy cookie và lưu vào `sessions/user_session.json`. |
| `manage_proxies.py` | CLI kiểm tra tình trạng kết nối của proxy với Threads. Hỗ trợ chế độ `--check` (kiểm tra proxy của các account) và tự động kéo proxy mới từ Proxifly CDN nếu proxy cũ bị hỏng. |

---

### 2.6. Thư mục `sessions/` (Lưu trữ Phiên Đăng nhập)

| Tên File / Thư mục | Mục Đích & Chức Năng |
| :--- | :--- |
| `acc_01.json` | File trạng thái lưu trữ Cookies và LocalStorage của tài khoản Threads số 01. Nhờ file này, Playwright mở trình duyệt là đã ở trạng thái đăng nhập sẵn, không cần gửi lại thông tin đăng nhập mỗi lần chạy. |
| `user_session.json` | File phiên lưu trữ khi người dùng đăng nhập bằng phương thức thủ công qua `manual_login.py`. |

---

### 2.7. Thư mục `examples/` (Tệp Tin Cấu Hình Mẫu)

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `accounts.example.json` | Mẫu cấu hình danh sách tài khoản định dạng JSON, gồm: `id`, `username`, `password`, `proxy`, `totp_secret`, `rate_limit`. |
| `proxies.example.txt` | Mẫu danh sách các địa chỉ proxy (mỗi dòng một proxy dạng `http://ip:port` hoặc `http://user:pass@ip:port`). |
| `users.example.json` | Mẫu danh sách các username Threads cần cào bài viết hàng loạt. |

---

### 2.8. Thư mục `output/` (Dữ liệu Kết Quả Cào & Thẩm Định)

| Tên File / Thư mục | Mục Đích & Chức Năng |
| :--- | :--- |
| `runs/` | Thư mục tổ chức kết quả theo từng mốc thời gian chạy: `runs/YYYY-MM-DD/run_HH-MM-SS/`. Giúp lưu vết lịch sử cào không bao giờ bị ghi đè. |
| `runs/.../summary.json` | Tóm tắt kết quả chạy: thời gian bắt đầu, tổng thời lượng chạy, các chủ đề đã tìm kiếm, tổng số bài viết cào được, tổng số bình luận, và số bài được AI thẩm định. |
| `runs/.../posts.json` | Danh sách đầy đủ toàn bộ các bài viết và bình luận chi tiết thu thập được trong phiên chạy đó. |
| `runs/.../curated_places.json` | Danh sách các bài viết đã được AI phân tích, đánh giá điểm chất lượng, trích xuất địa điểm, ưu/nhược điểm và tóm tắt khuyến nghị. |
| `search/` | Kết quả xuất ra từ CLI gốc `threads-parser`, được phân loại theo từ khóa và chế độ tìm kiếm. |
| `threads_posts.json` | Bản sao tiện lợi của toàn bộ bài viết từ phiên chạy gần nhất (đặt ở thư mục gốc output để dễ truy cập). |
| `curated_places.json` | Bản sao tiện lợi của danh sách địa điểm/bài viết AI thẩm định từ phiên chạy gần nhất. |
| `test_report.md` | Báo cáo chi tiết dạng Markdown ghi nhận kết quả và đánh giá chất lượng cào thử nghiệm. |
| `.gitkeep` | File rỗng giúp Git duy trì thư mục `output/` trên repository mà không cần commit dữ liệu cào. |

---

### 2.9. Thư mục `tests/` (Bộ Kiểm Thử Tự Động - Pytest)

Bộ kiểm thử đảm bảo toàn bộ hệ thống hoạt động ổn định và không phát sinh hồi quy khi thay đổi mã nguồn:

| Tên File Test | Đối Tượng & Mục Đích Kiểm Thử |
| :--- | :--- |
| `test_accounts.py` | Kiểm tra việc đọc file cấu hình tài khoản, xác thực schema dữ liệu tài khoản và tích hợp mã TOTP 2FA. |
| `test_cli_traffic.py` | Kiểm thử các cờ lệnh của CLI và khả năng xuất báo cáo traffic theo dõi băng thông mạng. |
| `test_login_accounts.py` | Kiểm thử logic đăng nhập tự động, xử lý ngoại lệ khi sai mật khẩu hoặc lỗi mạng. |
| `test_media_filter.py` | Kiểm tra logic lọc link hình ảnh, video và cơ chế bỏ qua tài nguyên không hợp lệ. |
| `test_modules.py` | Kiểm thử các module mới của pipeline: đọc file cấu hình an toàn, format proxy, gọi AI engine khi thiếu key hoặc có key, và lưu trữ báo cáo. |
| `test_parser_boundaries.py` | Kiểm thử độ bền của parser khi dữ liệu Threads trả về bị thiếu trường (title, replies, media, user profile). |
| `test_proxies.py` | Kiểm thử phân giải cú pháp URL proxy, xoay vòng proxy trong danh sách và tích hợp với HTTP client. |
| `test_quarantine.py` | Kiểm tra tính năng đưa proxy hỏng vào danh sách cách ly và tự phục hồi khi hết thời gian phạt. |
| `test_runtime_dependencies.py` | Kiểm tra môi trường thực thi đã cài đặt đủ các dependency bắt buộc chưa (Playwright, Httpx, Pytest). |
| `test_storage.py` | Kiểm tra khả năng lưu bài viết vào JSON, khử trùng lặp ID bài viết và khởi tạo thư mục. |
| `test_traffic.py` | Kiểm thử bộ đếm dung lượng (TrafficMonitor) tính toán chính xác số bytes truyền tải và phân loại status HTTP. |

---

### 2.10. Thư mục `experiments/` (Thử Nghiệm & Nguyên Mẫu R&D)

Thư mục này đóng vai trò như phòng thí nghiệm kỹ thuật của dự án. Trước khi một tính năng được đưa vào `src/modules/`, nó được thử nghiệm tại đây:

- **Các script tối ưu hóa tìm kiếm**: `test_keyword_lengths.py`, `test_dynamic_query_filter.py`, `test_user_exact_query.py` (chứng minh thuật toán Threads chỉ hoạt động tốt với từ khóa ngắn 2-3 chữ).
- **Các script phân tích cấu trúc**: `analyze_comment_structure.py`, `inspect_login_dom.py`, `inspect_output_comments.py`, `test_comment_depth.py`.
- **Các script kiểm tra giao thức mạng & tốc độ**: `test_raw_http.py`, `test_search_raw_http.py`, `test_pagination_network.py`, `test_speed.py`, `diagnose_free_proxies.py`.
- **Các script thử nghiệm AI**: `test_ai_with_comments.py`, `test_batch_prefilter.py`, `test_universal_curation.py`, `test_universal_filter.py`.
- **Các file ảnh minh họa và JSON fixture**: Dùng làm dữ liệu đầu vào chuẩn để đối chiếu khi chạy thử nghiệm độc lập.

---

### 2.11. Thư mục `.github/` (CI/CD)

| Tên File | Mục Đích & Chức Năng |
| :--- | :--- |
| `.github/workflows/ci.yml` | Workflow GitHub Actions tự động kích hoạt khi có `push` hoặc `pull request`. Chạy trên môi trường Ubuntu với cả **Python 3.11** và **Python 3.13**, cài đặt dependency, biên dịch bytecode (`compileall`) và thực thi toàn bộ bộ test `pytest`. |

---

## 3. LUỒNG HOẠT ĐỘNG TỔNG QUAN CỦA HỆ THỐNG (WORKFLOW)

Khi người dùng thực thi lệnh:
```bash
python main.py "địa điểm hẹn hò lãng mạn ở Sài Gòn"
```

Chu trình dữ liệu sẽ diễn ra tuần tự qua các thành phần:

```mermaid
flowchart TD
    A[main.py: CLI Entry] --> B[modules/config: Nạp .env & config.py]
    B --> C[modules/ai_engine: Mở rộng từ khóa thành cụm 2-3 chữ]
    C --> D[modules/auth: Nạp Cookies/Session từ sessions/]
    D --> E[modules/crawler: Playwright WorkerPool cào bài viết theo từ khóa]
    E --> F{Bật AI Pre-filter?}
    F -- Có --> G[modules/ai_engine: AI lọc sơ bộ bài viết tiềm năng]
    F -- Không --> H[modules/crawler: Cào bình luận sâu của các bài nhiều tương tác]
    G --> H
    H --> I[modules/ai_engine: Thẩm định & trích xuất dữ liệu chi tiết]
    I --> J[modules/storage: Lưu trữ vào output/runs/ và file latest]
```
