# API contracts

## Authentication and user administration

Access token được gửi trong `Authorization: Bearer <token>` giữa Next.js server và FastAPI. Refresh token chỉ được gửi trong body của endpoint refresh.

| Method | Path | Mô tả |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Nhận username/password; trả access token, refresh token, expiry và safe user DTO. |
| `POST` | `/api/v1/auth/refresh` | Nhận refresh token hợp lệ; trả cặp access/refresh token mới. |
| `GET` | `/api/v1/auth/me` | Trả user hiện tại. |
| `PATCH` | `/api/v1/auth/me` | Cập nhật display name và team của chính user; không cho phép tự đổi username, role hoặc trạng thái. |
| `POST` | `/api/v1/auth/me/change-password` | Xác minh mật khẩu hiện tại, đổi mật khẩu bằng Argon2id, vô hiệu hóa token cũ và trả cặp token mới cho phiên hiện tại. |
| `GET` | `/api/v1/admin/users` | Tìm kiếm và phân trang user; yêu cầu admin; response có `current_user_id` để UI nhận biết tài khoản đang thao tác mà không cần gọi `/auth/me` lần nữa. |
| `POST` | `/api/v1/admin/users` | Tạo user; yêu cầu admin. |
| `PATCH` | `/api/v1/admin/users/{id}` | Cập nhật hồ sơ, role hoặc trạng thái; yêu cầu admin. |
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
