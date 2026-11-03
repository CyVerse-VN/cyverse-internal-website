# Threads Scraper Tool

## Discovery post triage (đang phát triển)

Travel có thể chọn `discovery_mode="evidence_poi"` để thử Query Planning và Groq
post triage. Đây mới là nền tảng chọn bài: chưa có trích xuất POI có evidence,
entity resolution hoặc xác minh, nên không xem kết quả là danh sách địa điểm đã xác nhận.
Mặc định vẫn là `legacy`. Discovery giữ keyword thủ công làm seed, giới hạn số query
bằng `discovery_max_queries` (mặc định 10, tối đa 20) và comment bằng
`discovery_comment_budget` (mặc định 20, tối đa 100); giới hạn `max_comment_posts`
dương vẫn được áp dụng nếu nhỏ hơn. `discovery_query_planning=false` tắt lập kế hoạch.
Triage cần Groq ngay cả khi tắt lập kế hoạch. Các metadata `discovery_plan`, `triage`
và `comment_collection_status` được lưu trong snapshot của session, theo cùng quyền
truy cập và vòng đời xóa/hủy hiện tại. `not_attempted` không có nghĩa bài không có comment.
Trọng số ranking ban đầu là heuristic và chưa được hiệu chuẩn bằng benchmark.

JSON export có ba mức khi tải: `basic` (mặc định: bài và bình luận), `standard`
(thêm metadata và thống kê), `full` (thêm source data). Mức xuất không thay đổi dữ
liệu trong database. `standard` và `full` chứa run ID, request, trạng thái và `result`.
`result.search_attempts` ghi kết quả từng keyword/mode; mọi lượt tìm kiếm lỗi sẽ làm job
thất bại, thay vì hoàn thành với kết quả rỗng. Bài và bình luận giữ `source_data` từ record
nguồn khi có thể, `collected_at`, và `source_data_status`. Source record loại các trường xác
thực phổ biến mà không giới hạn kích thước từng record; đây không phải bản sao toàn bộ network response.
Comment DOM có `source=dom`; parent có thể được suy luận (`parent_inferred`). Dữ liệu cũ
không có metadata này và được đánh dấu `unknown`. Các bài không qua AI pre-filter vẫn được
giữ trong kết quả với `filter_selected=false`; chỉ bài được chọn được xử lý comments/AI.

Trong Threads Scraper và Travel & Places, lựa chọn **Exclude posts from previous sessions**
mặc định tắt. Khi bật (`check_duplicate=true`), worker bỏ qua bài có cùng post ID đã lưu
trong các session không bị hủy của cùng user; không xóa hoặc thay đổi các session trước.
Kết quả có thể ít bài hơn, kể cả khi tìm kiếm trả về đủ bài. Khi tắt, các bài cũ vẫn có thể
được thu thập lại; bài trùng ID hoặc URL trong cùng một lượt vẫn được gộp. `duplicate_count`
gồm cả số bài bị bỏ giữa các session và số bài được gộp trong cùng lượt; `search_attempts`
ghi riêng hai loại cho lượt chạy mới.

Các thiết lập cũ trong browser được đọc lại nhưng `check_duplicate` được đặt về `false`
một lần khi chuyển sang phiên bản preference mới. Sau đó lựa chọn do người dùng thay đổi
được ghi nhớ cho các lượt tiếp theo. Các job đã tạo giữ nguyên request và không bị thay đổi.
Log INFO và lỗi ghi ra stdout: xem terminal khi chạy local hoặc mục Logs của backend trên
Render; log có thể chứa query và URL bài.
Khi bật chống trùng giữa session và có dữ liệu cũ, crawler có thể xem tới bốn lần số bài
yêu cầu (tối đa 100 kết quả mỗi keyword/mode) để tìm bài mới; số bài mới được thêm vẫn
không vượt mức đã chọn. Không bảo đảm tìm đủ nếu nguồn có nhiều bài trùng hoặc dừng tải.
Mỗi keyword được phân bổ tuần tự theo vòng giữa các account; chế độ top/recent của cùng
keyword dùng cùng account. Không chạy các account song song để hạn chế RAM. Khi session
thiếu, hết hạn hoặc bị chuyển về đăng nhập, worker thử đăng nhập lại một lần nếu account
có username/password; session mới được lưu vào file và database. Nếu Threads yêu cầu
challenge không thể xử lý tự động, hãy đăng nhập thủ công và import lại session.

Không còn upload TXT lên Cloudinary; JSON vẫn lưu trong database và có thể tải TXT theo
yêu cầu. Các TXT đã lưu trước đây không bị xóa tự động; khi xóa session, worker vẫn xóa
các cloud asset cũ trước khi xóa database.
Giới hạn capture của trình duyệt vẫn có thể bỏ sót response; record nguồn đã thu thập
được không còn bị bỏ chỉ vì vượt 32 KB. Dataset lớn có thể vượt bộ nhớ hoặc quota database.

Backend tích hợp luồng trong `test/meta-threads-scraper`: mở rộng từ khóa bằng Groq,
tìm bài Threads, khử trùng lặp, lọc sơ bộ, lấy bình luận phân cấp và thẩm định nội dung.
Code runtime nằm hoàn toàn trong `apps/backend/src/app/tools/threads`, không import hay
chạy script từ thư mục `test`. Giao diện tại `/tools/threads`, truy cập từ sidebar sau khi đăng nhập.

## Giao diện và cấu hình collection

Giao diện cung cấp thanh chuyển đổi tab kiểu ChatGPT (Segmented Pill Toggle) giữa hai chế độ làm việc riêng biệt:
1. **Threads Scraper**: Cào và tổng hợp bài viết theo câu hỏi hoặc chủ đề tự do.
2. **Travel & Places (Du lịch & Địa điểm)**: Tối ưu cho việc khám phá các quán ăn, quán cafe, điểm check-in và du lịch.
   - Hỗ trợ chọn nhanh thành phố/địa phương và loại hình (Quán ăn ít người biết, Cafe view chill, Điểm check-in độc lạ, Ăn đêm & dạo phố, Ngắm hoàng hôn, Dã ngoại,...).
   - **Phân tích từ khóa AI (Analyze keywords)**: AI đọc topic/prompt của người dùng và tạo sẵn bộ từ khóa liên quan được phân chia theo các nhóm trực quan. Người dùng có thể chọn lọc, bỏ bớt hoặc thêm bớt các từ khóa trước khi bắt đầu cào dữ liệu.
   - Loại tìm kiếm hỗ trợ: Phổ biến (`top`), Mới nhất (`recent`), hoặc Cả hai (`both` - crawler cào tuần tự cả top và recent cho từng từ khóa).
   - Hiển thị kết quả linh hoạt: Tab **Bản tin bài viết** (Cards địa điểm hiển thị địa chỉ, ghi chú đặc trưng trích xuất bởi AI) và Tab **Curation View** (Phân tích chuyên sâu).
   - Lịch sử session của tab Threads Scraper và Travel & Places được phân tách riêng biệt (`request.mode == "travel"` vs `"scraper"`).

Khi bật expand ở tab Scraper, AI tạo tối đa 1–5 từ khóa theo lựa chọn. API vẫn hỗ trợ `keywords` riêng; giao diện gửi danh sách rỗng và dùng ô nhập chung. Phần comments có bật/tắt, giới hạn mỗi bài hoặc chế độ lấy tất cả theo giới hạn vận hành của crawler. AI pre-filter có mức none/medium/high; `curate` là tùy chọn riêng của API, mặc định tắt.

Mục "Cài đặt nâng cao" (Advanced settings) cho phép tùy chỉnh thời gian chạy tối đa (`run_timeout_seconds`, đặt `-1` để chạy đến khi xong hoặc từ 60s–86400s), thời gian tìm kiếm mỗi từ khóa (`search_timeout_seconds`, 15s–600s), độ trễ (`min_delay_seconds`, `max_delay_seconds`), số bài lấy bình luận (`max_comment_posts`, tối đa 500 bài), số phản hồi tối thiểu (`min_replies`), số tài khoản xoay vòng (`max_accounts`) và proxy (`use_proxy`). Các giá trị được kiểm tra ở frontend và backend; preference hợp lệ được nhớ trong browser.

Chọn **Until done** ở thời gian chạy sẽ bỏ giới hạn thời gian toàn job và thời gian tìm
kiếm từng keyword; có thể chọn lại giới hạn keyword riêng. Chế độ này không bảo đảm lấy
toàn bộ dữ liệu: giới hạn số bài/bình luận, số vòng cuộn, kiểm tra feed ngừng tải và
timeout tải trang vẫn được áp dụng. Job vẫn có thể dừng do lỗi, bị hủy hoặc service bị
restart/sleep. API dùng `-1` cho từng timeout không giới hạn; timeout tìm kiếm có giới hạn
nhận từ 15 đến 600 giây.

### Hàng đợi Session (FIFO Queue)
Khi một session đang chạy (`running`), người dùng có thể tạo thêm nhiều session khác. Các session mới sẽ tự động lưu vào hệ thống dưới trạng thái `queued` (chờ xử lý) và xếp thứ tự trong hàng đợi (`#1`, `#2`,...). Worker xử lý tuần tự từng session theo nguyên tắc FIFO (First-In, First-Out), đảm bảo an toàn tài nguyên và không bị xung đột trình duyệt.

Crawler chờ có search response hợp lệ trước khi kết luận không có bài; trang còn loading không được ghi thành collection rỗng thành công. Nếu hết giới hạn chờ mà chưa có payload search, job trả `THREADS_SEARCH_UNAVAILABLE`. Trang bình luận lạnh cũng có khoảng chờ ban đầu trước khi dừng vì không có dữ liệu mới.

Search cuộn vùng có thể cuộn thực tế tại giữa feed, theo dõi vị trí/chiều cao trang và `searchResults.page_info.has_next_page`; metadata network mới ưu tiên hơn SSR ban đầu. Không dừng chỉ vì vài lượt chưa có bài mới khi vẫn đang đi qua danh sách đã tải hoặc layout còn thay đổi. Mỗi từ khóa có budget `THREADS_SEARCH_TIMEOUT_SECONDS` (mặc định 120s) và giới hạn an toàn 200 lượt. Khi chưa đủ bài do hết kết quả, phân trang ngừng tải hoặc hết budget, result giữ bài đã lấy kèm warning nêu số lượng/lý do; không âm thầm báo đủ chỉ tiêu. `max_posts_per_keyword` là tối đa bài duy nhất cho mỗi từ khóa, không bảo đảm Threads có đủ bài. Khử trùng giữa các từ khóa vẫn chạy ngay cả khi tắt AI pre-filter.

Session mới mặc định public, mọi user đã đăng nhập có thể xem metadata, dữ liệu và tải file. Private chỉ owner/admin truy cập. Chỉ owner/admin đổi visibility, hủy và xóa session. Session cũ giữ private sau migration; không tự công khai dữ liệu đã có.

Sau khi tạo collection, URL `/tools/threads/{id}` giữ liên kết tới job, cho phép reload hoặc quay lại từ lịch sử. Trang hiển thị stage/progress, hủy job, lọc posts theo nội dung, chỉ xem curated posts và xuất JSON/TXT. Lịch sử nằm bên trái; lịch sử và cấu hình thu gọn độc lập, nhớ trạng thái trong browser. Khi tạo/chọn session, cấu hình tự thu gọn. Web chỉ hiển thị bài viết; comments đọc qua link Threads hoặc file export. Visibility chỉ chỉnh trong session; form không có lựa chọn visibility hoặc dùng lại cấu hình. Frontend gọi Next.js same-origin API `/api/threads/*`; token được giữ trong HttpOnly cookie và chỉ Next.js server chuyển Bearer token sang backend.

## Cấu hình dùng chung

Mọi biến môi trường nằm trong `apps/backend/.env`; xem template
`apps/backend/.env.example`. `GROQ_API_KEY` dùng chung với các tính năng backend hiện có.
Không cần `.env`, `config.py` hoặc `accounts.json` riêng cho scraper.

Ba biến backend-only `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
chỉ cần để xóa asset Cloudinary cũ. Không upload TXT mới.

```dotenv
THREADS_ENABLED=true
THREADS_EMBEDDED_WORKER=true
THREADS_ANONYMOUS=false
THREADS_ACCOUNTS='[{"id":"acc_01","username":"user1","password":"***","enabled":true},{"id":"acc_02","username":"user2","password":"***","enabled":true},{"id":"acc_03","username":"user3","password":"***","enabled":true}]'
THREADS_SESSIONS_DIR=.local/threads/sessions
THREADS_GROQ_MODEL=qwen/qwen3.8-27b
```

`THREADS_ACCOUNTS` là JSON array, cấu hình danh sách tài khoản (ví dụ 3 tài khoản `acc_01`, `acc_02`, `acc_03`). Các trường:

| Trường | Ý nghĩa |
| --- | --- |
| `id` | ID nội bộ chỉ gồm chữ cái, số, `_`, `-` (ví dụ `acc_01`, `acc_02`, `acc_03`). |
| `username`, `password` | Dùng bởi lệnh login tự động ở local; có thể bỏ trống khi đã có session. |
| `totp_secret` | Tùy chọn; sinh mã TOTP khi tài khoản bật 2FA. |
| `proxy` | Tùy chọn: `http://user:pass@host:port` hoặc `socks5://host:port`; bỏ trống để kết nối trực tiếp. |
| `enabled` | Bật/tắt tài khoản trong pool; mặc định `true`. |

---

## Quản lý Session tập trung (threads_sessions.json)

Để thuận tiện quản lý nhiều tài khoản (ví dụ 3 tài khoản `acc_01`, `acc_02`, `acc_03`) mà không phải tải từng file riêng lẻ, hệ thống hỗ trợ gom chung toàn bộ session vào **1 tệp JSON duy nhất** tên là:

```text
threads_sessions.json
```

### 1. Cấu trúc tệp `threads_sessions.json`
Tệp có thể ở dạng đối tượng chuẩn chứa trường `sessions` hoặc map trực tiếp theo `account_id`:

```json
{
  "version": 1,
  "updated_at": "2026-11-03T00:00:00Z",
  "sessions": {
    "acc_01": {
      "cookies": [
        {
          "name": "sessionid",
          "value": "...",
          "domain": ".threads.com",
          "path": "/",
          "expires": 1824977570.57,
          "httpOnly": true,
          "secure": true
        }
      ],
      "origins": []
    },
    "acc_02": {
      "cookies": [...],
      "origins": []
    },
    "acc_03": {
      "cookies": [...],
      "origins": []
    }
  }
}
```

> **Lưu ý:** Hệ thống cũng tương thích ngược hoàn toàn với việc import từng tệp riêng lẻ (ví dụ `acc_01.json`), hoặc tệp JSON mảng `[{"id": "acc_01", "cookies": [...]}, ...]`.

---

### 2. Cơ chế hoạt động giữa Local và Web (Render / Cloud)

* **Ở Local:**
  * Mặc định, backend đọc trực tiếp tệp tổng hợp `threads_sessions.json` hoặc các tệp `acc_01.json`, `acc_02.json`, `acc_03.json` đặt trong thư mục `apps/backend/.local/threads/sessions/`.
  * Nếu bạn chạy lệnh tạo session tự động ở local (`pnpm.cmd threads:login acc_01`), file sẽ được tạo hoặc cập nhật tại đây.
* **Khi triển khai lên Web (Render):**
  * Do ổ cứng container trên Render là tạm thời (ephemeral disk) và sẽ bị xóa khi restart hoặc redeploy, toàn bộ session được lưu bền vững vào bảng cơ sở dữ liệu PostgreSQL `threads_account_sessions`.
  * **Cách kích hoạt trên Web:** Admin chỉ cần truy cập trang **Cài đặt** (`/settings/account`) -> mục **Threads Sessions (Admin)** và tải lên 1 tệp duy nhất `threads_sessions.json`.
  * Backend sẽ tự động phân tách, kiểm tra tính hợp lệ của từng tài khoản, lưu vào PostgreSQL và ghi đồng thời ra đĩa container cho Playwright crawler.
  * Mỗi khi container Render khởi động lại hoặc scale instance mới, hàm `restore_sessions_from_db()` sẽ tự động đồng bộ session từ PostgreSQL ra đĩa container.

---

### 3. Phân quyền Admin & Dùng chung phiên

* **Chỉ Admin mới có quyền Import:**
  * Endpoint API `POST /api/v1/tools/threads/sessions/batch` và `POST /api/v1/tools/threads/accounts/{id}/session` được bảo vệ bằng middleware `require_admin`. Người dùng thông thường (role `member`) sẽ nhận mã lỗi `403 Forbidden`.
  * Nút tải lên / xuất tệp session chỉ xuất hiện trong trang Cài đặt của Admin.
* **Mọi thành viên dùng chung:**
  * Toàn bộ thành viên trong nhóm đều dùng chung các session đang kích hoạt mà Admin đã import khi chạy tác vụ cào dữ liệu (hệ thống tự động xoay vòng qua các tài khoản hợp lệ).

---

### 4. Kiểm tra và cảnh báo hết hạn Session

* **Tự động nhận diện hết hạn:**
  * Backend tự động phân tích trường `expires` trong cookie `sessionid` của Threads/Instagram.
  * API `/api/v1/tools/threads/accounts` trả về cờ `is_expired` và thời điểm hết hạn `expires_at` (ISO format).
* **Hiển thị trực quan cho người dùng:**
  * **Trang Cài đặt (Admin):** Hiển thị nhãn **Active** (kèm ngày hết hạn), **Expired** (Hết hạn), hoặc **No Session** (Chưa có session). Cung cấp nút **Export JSON** để tải tệp `threads_sessions.json` về và nút **Import JSON (Bundle)** để cập nhật.
  * **Trang Scraper / Travel Form:** Khi có bất kỳ tài khoản nào bị hết hạn session, hệ thống hiển thị thanh cảnh báo đỏ:
    > *⚠️ Tài khoản (acc_01) có phiên đăng nhập đã hết hạn. Vui lòng liên hệ Admin để cập nhật lại session JSON trong Cài đặt.*
  * Nếu tất cả tài khoản đều chưa có session hoặc hết hạn, nút bắt đầu cào sẽ được khóa lại kèm thông báo hướng dẫn liên hệ Admin.

---

### 5. Cơ chế Chạy linh hoạt & Tự động bỏ qua (Skip) tài khoản lỗi

* **Không bắt buộc tất cả tài khoản phải có session:**
  * Hệ thống chỉ yêu cầu tối thiểu **1 tài khoản** có session hoạt động (`active_count >= 1`).
  * Ví dụ: Nếu cấu hình 3 tài khoản nhưng chỉ có `acc_01` và `acc_02` có session (hoặc `acc_03` chưa đăng nhập), hệ thống sẽ tự động dùng 2 tài khoản sẵn có và bỏ qua tài khoản chưa sẵn sàng. Nút cào dữ liệu vẫn mở và hoạt động bình thường.
* **Tự động chuyển tài khoản khi gặp sự cố lúc cào:**
  * Trong quá trình cào bài hoặc lấy bình luận, nếu một tài khoản bất ngờ bị Threads điều hướng về trang đăng nhập hoặc yêu cầu challenge/checkpoint:
  * Crawler sẽ tự động loại bỏ tài khoản lỗi ra khỏi danh sách xoay vòng, ghi nhận thông báo cảnh báo (warning) và tiếp tục thực hiện cào dữ liệu với các tài khoản khỏe mạnh còn lại.
  * Tác vụ cào chỉ bị dừng nếu **tất cả** các tài khoản đều bị mất phiên và không còn tài khoản nào dùng được.

---

## Cài Chromium và đăng nhập tài khoản local

Chạy từ repository root:

```powershell
uv sync --project apps/backend --extra dev
pnpm.cmd threads:install
pnpm.cmd threads:login acc_01
```

Lệnh login tự nhập username/password từ `.env`; nếu có `totp_secret`, lệnh sẽ nhập mã
TOTP. Browser mặc định có cửa sổ để người vận hành xử lý xác thực bổ sung. Có thể dùng
`--headless` khi không cần tương tác, hoặc `--manual` để tự đăng nhập hoàn toàn:

```powershell
pnpm.cmd threads:login acc_01 --manual
pnpm.cmd threads:login acc_01 --headless --timeout 120
```

Sau khi có đủ session cho 3 tài khoản ở local, bạn có thể:
1. Vào trang Cài đặt trên Web (`/settings/account`) dưới quyền Admin.
2. Bấm **Export JSON** hoặc gom 3 session vào tệp `threads_sessions.json`.
3. Bấm **Import JSON (Bundle)** để kích hoạt tất cả trên Web.

## Worker và Windows

Mặc định consumer chạy trong FastAPI lifespan khi `THREADS_ENABLED=true` và
`THREADS_EMBEDDED_WORKER=true`. Có thể tách worker bằng cách đặt
`THREADS_EMBEDDED_WORKER=false` và chạy:

```powershell
pnpm.cmd threads:worker
```

Trên Windows, worker giữ database I/O trên Selector event loop và chạy Playwright trên
Proactor event loop trong thread riêng. Progress/cancellation được chuyển về database
loop; timeout hoặc shutdown đóng browser trước khi thread kết thúc. Vì vậy có thể dùng
consumer embedded cùng `pnpm.cmd dev:backend`, hoặc tách worker theo lệnh trên. Không
chạy psycopg async trên Proactor loop. Cấu hình local dùng `THREADS_EMBEDDED_WORKER=true`.
Lệnh `pnpm.cmd start:backend` chạy API/embedded worker không reload với loop factory
`app.core.runtime:create_event_loop`, tránh Uvicorn mặc định chọn Proactor trên Windows.

Worker dùng PostgreSQL advisory lock riêng, xử lý FIFO từng job để hạn chế số browser
đồng thời. API và worker phải cùng database, cấu hình và session files. Sau restart, job
đang chạy chuyển `failed/WORKER_INTERRUPTED`; dữ liệu đã checkpoint vẫn còn, job đang chờ
vẫn được xử lý. Đóng tab, trình duyệt hoặc frontend không hủy job; backend/worker phải tiếp
tục chạy. Không tự chạy lại job đã cào một phần để tránh thêm request và chi phí AI.
Consumer xử lý xóa asset Cloudinary cũ với exponential backoff 30 giây đến 1 giờ.

## API

Các endpoint dùng Bearer access token hiện có. Public đọc được bởi user đã đăng nhập;
private chỉ owner/admin đọc. Thao tác quản lý luôn giới hạn owner/admin. Không đủ quyền
trả `404`, kể cả export và thao tác trên public session.

| Method | Path | Chức năng |
| --- | --- | --- |
| `GET` | `/api/v1/tools/threads/config` | Defaults, limits, enabled, accounts_ready và ai_available; không trả credentials hoặc account IDs. |
| `POST` | `/api/v1/tools/threads/runs` | Tạo job và trả `202`; hỗ trợ `Idempotency-Key`. |
| `GET` | `/api/v1/tools/threads/runs?limit=20&offset=0` | Danh sách job được phép xem. |
| `GET` | `/api/v1/tools/threads/runs/{id}` | Request, trạng thái, stage, progress, lỗi và kết quả. |
| `POST` | `/api/v1/tools/threads/runs/{id}/cancel` | Hủy queued job hoặc yêu cầu dừng running job. |
| `PATCH` | `/api/v1/tools/threads/runs/{id}` | Đổi `visibility` thành public/private. |
| `DELETE` | `/api/v1/tools/threads/runs/{id}` | Trả `202`, yêu cầu dừng và xóa vĩnh viễn cloud/database. |
| `GET` | `/api/v1/tools/threads/runs/{id}/export?format=json&detail=basic` | Tải JSON mức `basic`, `standard` hoặc `full`; mặc định `basic`. |
| `GET` | `/api/v1/tools/threads/runs/{id}/export?format=txt` | Toàn bộ session theo `threads-text-v2`, có ID và quan hệ cha–con. |

Request ví dụ:

```json
{
  "query": "Find quiet cafes for reading in Saigon",
  "visibility": "public",
  "max_posts_per_keyword": 15,
  "search_type": "recent",
  "include_comments": true,
  "max_comment_posts": 10,
  "max_comments_per_post": 25,
  "min_replies": 2,
  "expand_query": true,
  "pre_filter": true,
  "curate": true
}
```

`keywords` tùy chọn, tối đa 5 cụm, mỗi cụm 1–100 ký tự. Khi truyền `keywords`, backend bỏ
bước mở rộng từ khóa. API cho tối đa 100 bài/từ khóa, 50 bài lấy bình luận và 500 bình
luận/bài khi đặt giới hạn dương. `max_comment_posts <= 0` chọn mọi bài đủ điều kiện;
`max_comments_per_post <= 0` lấy theo chế độ không giới hạn số đếm nhưng vẫn dừng sau
35 vòng hoặc 3 vòng không có dữ liệu mới. Không bảo đảm lấy đủ mọi bình luận trên Threads.
Muốn chạy hoàn toàn không có AI, truyền `expand_query=false`, `pre_filter=false`,
`curate=false`; đồng thời truyền `keywords` hoặc dùng query tối đa 100 ký tự.

Stage: `queued`, `planning`, `searching`, `filtering`, `comments`, `curating`, `saving`, rồi
`completed`, `failed` hoặc `cancelled`. Progress từ 0 đến 1. Kết quả gồm `posts`,
`curated_post_ids`, `total_comments`, `keywords`, `duration_seconds`, `warnings`. Bài được
giữ kèm `search_keywords`, media URLs, counters, bình luận và `ai_analysis` nếu bật.
Response còn có owner (ID/display name), visibility, thời gian tạo/bắt đầu/kết thúc,
post/comment counts, `can_manage`, `archive_status`, lỗi storage an toàn và
`deletion_requested`. List chỉ tải metadata/counts, `result=null`.

Groq được gọi bằng HTTP async; JSON response được kiểm tra bằng Pydantic. Lỗi AI làm job
thất bại rõ ràng; không âm thầm trả kết quả chưa thẩm định. Dùng cùng idempotency key và
request sẽ trả lại job cũ; đổi input hoặc dùng key của tool khác trả `409`.

## Lưu trữ, bảo mật và vận hành

Request/lifecycle lưu trong `tool_runs`. Migration `20261101_0006` thêm `threads_results`
(summary một collection), `threads_posts` (snapshot từng bài) và `threads_comments`
(snapshot bình luận, giữ parent ID). Migration `20261101_0007` thêm metadata chia sẻ,
counts và trạng thái archive/cleanup bền vững. Bản ghi session được tạo ngay khi queue.
Checkpoint được ghi sau mỗi từ khóa và mỗi batch pre-filter, giữ cả bài không được chọn.
Bài và ID được commit trước khi lấy comments.
Cứ mỗi khi chạy xong một từ khóa, hệ thống tự động lưu (commit) snapshot dữ liệu các bài viết thu được vào PostgreSQL. Cơ chế này đảm bảo dữ liệu không bị mất sạch nếu gặp lỗi kết nối hoặc gián đoạn giữa chừng. Tính năng xuất file (JSON và TXT) chỉ mở khóa cho người dùng khi phiên cào đã dừng hoặc hoàn tất (`completed`, `failed`), giúp tối ưu tài nguyên lưu trữ và đảm bảo file xuất ra có đầy đủ tổng hợp toàn bộ bài viết đã cào.

### Cơ chế Hủy và Xóa Session (Dừng ngay & Xóa sạch dữ liệu)

1. **Hủy session (`cancel`)**:
   - Khi người dùng bấm hủy, cờ `cancel_requested` được bật ngay lập tức. Monitor task ngắt crawler, đóng trình duyệt Playwright và giải phóng tài nguyên.
   - Toàn bộ bài viết (`ThreadsPostRecord`) và bình luận (`ThreadsCommentRecord`) đã thu thập dở dang sẽ bị xóa sạch khỏi database (`snapshot.posts.clear()`).
   - Các chỉ số được đưa về 0 (`post_count = 0`, `comment_count = 0`, `snapshot_ready = False`), không upload file txt lên Cloudinary.
   - Các bài viết của phiên bị hủy bị loại bỏ khỏi `get_existing_post_ids` để không ảnh hưởng đến bộ lọc trùng lặp cho các phiên cào kế tiếp.
   - API `/export` từ chối xuất file đối với session đã hủy (`SESSION_CANCELLED`).
   - Giao diện hiển thị thông báo rõ ràng rằng phiên đã được hủy và toàn bộ dữ liệu đã được dừng và xóa sạch.

2. **Xóa session (`delete`)**:
   - Khi người dùng bấm xóa, hệ thống lập tức yêu cầu dừng nếu session đang chạy hoặc trong hàng đợi.
   - Xóa sạch dữ liệu bài viết/bình luận trong database.
   - Worker dọn dẹp artifact (`ThreadsArtifacts.run_once`) kiểm tra và xóa vĩnh viễn file text archive trên Cloudinary (nếu đã từng tải lên).
   - Tiến hành xóa vĩnh viễn bản ghi `ToolRun` cùng toàn bộ bản ghi liên quan qua cơ chế cascade delete trong cơ sở dữ liệu.

Các Cloudinary ID cũ được giữ để cleanup khi xóa session. Không có upload TXT mới.
Download TXT được dựng từ snapshot PostgreSQL theo yêu cầu; nội dung không tin cậy nằm
trong các dòng literal có tiền tố `|`.

Không tải media về disk, không tự lấy public proxy, không đưa credentials, proxy hoặc
session vào request/result API.

Session files là credentials: chỉ cấp quyền đọc cho tiến trình backend/worker và giữ
trên persistent storage khi deploy. Trên Linux, cài Chromium cùng system dependencies
trong build image (`uv run python -m playwright install --with-deps chromium`). Không
trỏ worker development vào database production. `THREADS_RUN_TIMEOUT_SECONDS` mặc định
1800 giây; delay giữa các lượt cào nằm trong `THREADS_MIN_DELAY_SECONDS` và
`THREADS_MAX_DELAY_SECONDS`.

Parser được port từ mẫu scraper và giữ MIT notice trong module. Playwright đã có qua
NotebookLM và được khai báo direct dependency vì tool import trực tiếp; PyOTP phục vụ
TOTP, tránh tự triển khai thuật toán xác thực. Đã đối chiếu metadata/license từ
[Playwright](https://pypi.org/project/playwright/) và [PyOTP](https://pypi.org/project/PyOTP/),
và kiểm tra advisory theo phiên bản qua OSV khi tích hợp. Model có thể đổi bằng
`THREADS_GROQ_MODEL`; danh mục chính thức tại [Groq models](https://console.groq.com/docs/models).


## Nội dung HTML và định dạng TXT

Bài viết lấy caption từ JSON, ngày đăng ở trường `published_at` riêng. Fallback đọc bình
luận từ DOM từng ghép mọi `span[dir="auto"]`, có thể dính timestamp hoặc nút Translate.
Extractor mới duyệt text nodes, bỏ controls/time và container con, rồi lọc fragment UI riêng;
không xóa ngày hoặc chữ Translate trong caption có cấu trúc. Snapshot DOM cũ có cả tiền tố
ngày và hậu tố Translate được làm sạch khi đọc/export, không ghi đè raw snapshot.
Web không render bình luận hoặc phần AI analysis trong post cards.

TXT `threads-text-v2` có session/request metadata, collection summary, post ID/URL/timestamp,
metrics, media URLs, literal post text và toàn bộ AI analysis. Mỗi comment có ID, parent ID,
source depth, tree depth, source type, like count và reply-to username. Renderer nhóm comment
con dưới cha, giữ nguyên parent ngoài collection, đánh dấu quan hệ không xác định hoặc chu kỳ,
và không tự đoán cha cho DOM fallback. Từng dòng nội dung có tiền tố `|`, không bị nhầm với
metadata/dấu kết thúc khi nội dung chứa tên section hoặc instruction. JSONB vẫn là dữ liệu
có cấu trúc chính; TXT dùng để đọc và gửi AI, không bảo đảm đã thu thập toàn bộ comments nguồn.


---

## Threads Discovery Engine V2 (Social POI Discovery)

Trong chế độ Travel & Places (`mode="travel"`), hệ thống hỗ trợ Discovery Engine V2 (`discovery_mode="evidence_poi"`) để khám phá và định danh địa điểm (POI) từ nội dung và thảo luận cộng đồng trên Threads. Chế độ cào dữ liệu cũ (`discovery_mode="legacy"`) vẫn được giữ nguyên mặc định.

### 1. Luồng xử lý và kiến trúc

```text
Natural Language Query -> [1] Query Planner (Multi-perspective)
                       -> [2] Threads Search (Top/Recent tracking angle)
                       -> [3] Post Deduplication
                       -> [4] AI Post Triage & Ranking (Multi-signal)
                       -> [5] Adaptive Comment Crawling (Discussion potential)
                       -> [6] Comment Cleaning & Context Reconstruction
                       -> [7] Evidence-grounded POI Extraction (Span-level)
                       -> [8] Entity Resolution & Provenance Preservation
                       -> [9] POI Candidates Storage & Verification Status
```

### 2. Các thành phần chính

- **Multi-perspective Query Planning (`query_planner.py`)**:
  - Phân tích yêu cầu theo: Core topic, Geographic scope, Desired attributes, Exclusions.
  - Sinh từ khóa theo các góc nhìn: Demand-driven (`demand`, người dùng hỏi gợi ý), Experience-driven (`experience`, chia sẻ quán ruột/núp hẻm), Khu vực (`neighborhood`), và Topic (`topic_specific`).
  - Bảo toàn từ khóa thủ công (`use_manual_keywords=true`) làm seed đầu tiên, không ghi đè hoặc loại bỏ từ khóa tiếng Việt có dấu. Loại bỏ các truy vấn phủ định không mong muốn.
  - Ghi nhận `angle` cho từng lượt tìm kiếm trong `result.search_attempts`.

- **AI Post Triage & Routing (`triage.py`, `ranking.py`)**:
  - Đánh giá đa tín hiệu: `geo_match` (`yes`, `no`, `uncertain`), `topic_relevance` (0-1), `direct_poi_score` (0-4), `discussion_poi_score` (0-4), `promotion_risk` (0-4).
  - Định tuyến bài viết:
    - `DIRECT_POI`: Bài viết chia sẻ địa điểm cụ thể.
    - `DISCUSSION_POI`: Bài viết hỏi đáp/thảo luận có tiềm năng chứa gợi ý trong bình luận.
    - `BOTH`: Vừa có POI trực tiếp vừa có thảo luận giá trị.
    - `EXCLUDED`: Sai phạm vi địa lý rõ ràng, không liên quan hoặc nguy cơ quảng cáo/spam cao.
    - `UNCLASSIFIED`: Giữ nguyên dữ liệu khi triage không khả dụng, không tự ý loại trừ.
  - Xếp hạng cào bình luận dựa trên tiềm năng thảo luận (`discussion_poi_score`), không dựa thuần túy vào `reply_count` để tránh đẩy bài viral lạc đề lên đầu.

- **Comment Cleaning & Context Reconstruction (`comment_processing.py`)**:
  - Chuẩn hóa Unicode NFC, loại bỏ văn bản giao diện (nút Translate, nhãn thời gian UI).
  - Khử trùng lặp giữa bản ghi DOM fallback và bình luận có cấu trúc.
  - Xây dựng cây hội thoại `(Post context + Parent comment + Child replies)`.
  - Đánh dấu `context_incomplete=true` khi thiếu ngữ cảnh cha hoặc bình luận mồ côi. Chunking theo cụm hội thoại trong giới hạn token thay vì cắt cụt thô bạo.

- **Evidence-grounded POI Extraction (`poi_extractor.py`, `evidence_validator.py`)**:
  - Trích xuất `POIMention` (tên, khu vực, địa chỉ, bằng chứng) và `POIClaim` (loại thông tin: món ăn, giá cả, không gian, cảnh báo, đóng cửa).
  - Bắt buộc kiểm tra bằng chứng (`find_evidence_span`): `evidence_text` phải tồn tại trong văn bản nguồn. Xác định vị trí offset chính xác (`start_offset`, `end_offset`).
  - Không chấp nhận địa chỉ hoặc tên quán do AI tự suy đoán. Thuộc tính không có trong nguồn được đưa về `null`.
  - Cảnh báo đóng cửa (`closure`) hoặc trải nghiệm xấu được lưu thành claim cảnh báo, không bị bỏ qua.

- **Entity Resolution & Provenance (`poi_resolver.py`)**:
  - Chuẩn hóa tên và so khớp tương đồng (Fuzzy Matching).
  - Phân biệt chi nhánh (Branch discrimination): Các chi nhánh khác quận/khu vực không bị gộp sai.
  - Bảo toàn toàn bộ mentions và claims nguồn.
  - Đánh giá trạng thái xác minh:
    - `candidate`: Đã tìm được địa điểm ứng viên, cần kiểm chứng.
    - `verified`: Đã có từ 2 nguồn độc lập trở lên và có thông tin địa lý rõ ràng.
    - `unresolved`: Chưa đủ thông tin nhận diện.
    - `rejected`: Địa điểm sai hoặc không hợp lệ.

- **Lưu trữ cơ sở dữ liệu (`models/threads.py`, Migration `20261103_0010`)**:
  - Bảng `threads_poi_candidates`: Lưu canonical POI, địa chỉ, phân loại, trạng thái xác minh.
  - Bảng `threads_poi_mentions`: Lưu từng lần xuất hiện của POI kèm liên kết bài viết/bình luận nguồn và evidence span.
  - Bảng `threads_poi_claims`: Lưu các thuộc tính, nhận xét, đánh giá kèm quote bằng chứng.
  - Tự động xóa sạch qua cascade khi session bị hủy hoặc xóa.

- **Analytics & Retrieval Feedback (`feedback.py`)**:
  - Đo lường Query Yield, Unique Post Yield, POI Mention Yield, Verified POI Yield và Grounding Rate theo từng query.
