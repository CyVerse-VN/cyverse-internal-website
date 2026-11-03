# API contracts

## Threads Scraper

Các endpoint `/api/v1/tools/threads/runs` yêu cầu Bearer token. Session mới mặc định public
cho user đã đăng nhập; private chỉ owner/admin xem. `POST` nhận `visibility` và tạo job `202`,
`GET` liệt kê (`limit`, `offset`), `GET /{id}` đọc metadata/trạng thái/kết quả từng phần,
`POST /{id}/cancel` yêu cầu hủy, `PATCH /{id}` đổi visibility, `DELETE /{id}` trả `202` và
yêu cầu xóa cloud rồi hard-delete database. Mọi mutation chỉ owner/admin. Response có
`deletion_requested` trong lúc cleanup; sau khi xóa xong trả `404`.
`check_duplicate` mặc định `false`; `true` bỏ qua post ID đã có trong session không bị
hủy của cùng owner. Dù giá trị nào, kết quả trùng ID hoặc URL trong cùng lượt được gộp.
`GET /{id}/export?format=json&detail=basic|standard|full` tải JSON theo mức đã chọn;
mặc định `basic`. `format=txt` tải TXT theo yêu cầu chứa dữ liệu session,
metadata, ID và quan hệ cha–con của bình luận. API không còn hỗ trợ `format=md`.
Tạo job hỗ trợ `Idempotency-Key`; các tham số account, proxy, đường dẫn và credentials
chỉ được cấu hình server-side. Xem [request/response và setup Threads](tools/threads.md).

`GET /api/v1/tools/threads/config` trả defaults, limits và các boolean readiness an toàn,
gồm `cloudinary_ready`. Cloudinary credentials và delivery URLs không xuất hiện trong API.
`POST /api/v1/tools/threads/keywords` nhận `prompt` chủ đề hoặc địa điểm và trả danh sách từ khóa phân tích bởi AI chia theo từng nhóm trực quan.
List runs chỉ trả summary (`result=null`); detail/export tải snapshots. Frontend dùng các
same-origin routes `/api/threads/config`, `/api/threads/keywords`, `/api/threads/runs`, `/api/threads/runs/{id}`,
`/{id}/cancel` và `/{id}/export`, giữ nguyên mã lỗi và download headers của backend.

## Authentication and user administration

Access token được gửi trong `Authorization: Bearer <token>` giữa Next.js server và FastAPI. Refresh token chỉ được gửi trong body của endpoint refresh.

| Method | Path | Mô tả |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Nhận username/password; trả access token, refresh token, expiry và safe user DTO. |
| `POST` | `/api/v1/auth/refresh` | Nhận refresh token hợp lệ; trả cặp access/refresh token mới. |
| `GET` | `/api/v1/auth/me` | Trả user hiện tại. |
| `PATCH` | `/api/v1/auth/me` | Cập nhật display name, team và `notebooklm_email` ưu tiên của chính user; không cho phép tự đổi username, role hoặc trạng thái. |
| `POST` | `/api/v1/auth/me/change-password` | Xác minh mật khẩu hiện tại, đổi mật khẩu bằng Argon2id, vô hiệu hóa token cũ và trả cặp token mới cho phiên hiện tại. |
| `GET` | `/api/v1/admin/users` | Tìm kiếm và phân trang user; yêu cầu admin; response có `current_user_id` để UI nhận biết tài khoản đang thao tác mà không cần gọi `/auth/me` lần nữa. |
| `POST` | `/api/v1/admin/users` | Tạo user, có thể đặt email NotebookLM ưu tiên; yêu cầu admin. |
| `PATCH` | `/api/v1/admin/users/{id}` | Cập nhật hồ sơ, email NotebookLM ưu tiên, role hoặc trạng thái; yêu cầu admin. |
| `POST` | `/api/v1/admin/users/{id}/reset-password` | Đặt mật khẩu và vô hiệu hóa token cũ; yêu cầu admin. |

Safe user DTO không chứa password hash, token hoặc `token_version`.

Username dài 3–64 ký tự, không chứa khoảng trắng và chỉ gồm chữ cái ASCII, chữ số, dấu chấm (`.`), gạch dưới (`_`) hoặc gạch ngang (`-`). Backend lưu username ở dạng lowercase.

Các API public của backend được đặt dưới prefix `/api/v1`. Schema request và response dùng Pydantic và được quản lý trong `app/schemas` hoặc module tool tương ứng.

## AI Research Tool

Mọi endpoint dưới đây yêu cầu Bearer access token.

| Method | Path | Mô tả |
| --- | --- | --- |
| `GET` | `/api/v1/tools/research/config` | Trả defaults, enums, limits và config schema version. |
| `POST` | `/api/v1/tools/research/sessions` | Tạo public/private session queued; hỗ trợ `Idempotency-Key`. |
| `GET` | `/api/v1/tools/research/sessions` | Danh sách public và private session được phép xem theo cursor. |
| `GET` | `/api/v1/tools/research/sessions/{id}` | Detail, queue position, events, warnings/error và final papers. |
| `PATCH` | `/api/v1/tools/research/sessions/{id}` | Owner/admin đổi visibility hoặc title. |
| `DELETE` | `/api/v1/tools/research/sessions/{id}` | Owner/admin xóa mềm session; run active được yêu cầu hủy trước. |
| `POST` | `/api/v1/tools/research/sessions/{id}/cancel` | Owner/admin yêu cầu hủy queued/running session. |

Paper không có API pagination hoặc server-side filter; detail trả tối đa 50 record. Truy cập session
không đủ quyền trả `404` để tránh làm lộ private identifier.

## NotebookLM paper import

Các endpoint sau yêu cầu Bearer access token. Mỗi người chỉ chọn email Google đang đăng nhập trong trình duyệt của mình. Backend xác minh email thực qua NotebookLM trước khi liệt kê sổ hoặc tạo import. Import detail chỉ owner/admin được xem.

| Method | Path | Mô tả |
| --- | --- | --- |
| `POST` | `/api/v1/tools/notebooklm/accounts/discover` | Nhận cookie Google từ extension và trả danh sách `{email,authuser}` đã được NotebookLM xác minh. |
| `POST` | `/api/v1/tools/notebooklm/notebooks` | Nhận `cookies`, `account_email`; trả `{account_email,items:[{id,title}]}` từ email đã chọn. |
| `POST` | `/api/v1/tools/notebooklm/imports` | Nhận `cookies`, `account_email`, `notebook_id`, `source="google_scholar"`, paper seed và `Idempotency-Key`; xác minh email và notebook rồi trả job `202`. |
| `GET` | `/api/v1/tools/notebooklm/imports/{id}` | Trả trạng thái, stage, source ID hoặc `{code,message}` khi thất bại. |

Extension lấy cookie mới mỗi lần dùng, không lưu cookie Google trong extension storage. Worker chỉ giữ phiên được mã hóa trong job đang chờ/chạy và xóa khi job hoàn thành hoặc thất bại. Email ưu tiên trong hồ sơ chỉ là lựa chọn; backend luôn xác minh email với phiên Google khi thực hiện thao tác. Xem [hướng dẫn NotebookLM](notebooklm-setup.md).

Paper seed gồm `title`, `authors`, `year`, `doi`, `arxiv_id`, `landing_url`, `pdf_url`. Trường ngoài title có thể rỗng/null. Nếu có PDF URL, worker không tìm lại; nếu không, resolver dùng metadata và trả `LOW_CONFIDENCE_MATCH` khi thiếu bằng chứng. PDF chỉ được lưu tạm lúc upload. Sau khi bắt đầu upload, job gián đoạn mà chưa có source ID sẽ thất bại với `UPLOAD_OUTCOME_UNKNOWN` để tránh tự động tạo source trùng.
