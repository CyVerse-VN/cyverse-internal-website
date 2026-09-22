# ADR 006: Stateless access and refresh tokens

## Status

Accepted

## Context

CyVerse chỉ cần cơ chế access token và refresh token đơn giản cho tài khoản nội bộ. Việc lưu từng phiên trong `auth_sessions` làm tăng schema, truy vấn và vòng đời thu hồi mà sản phẩm hiện tại không cần.

## Decision

- FastAPI phát hành JWT ký bằng `HS256`: access token mặc định 15 phút và refresh token mặc định 30 ngày.
- Next.js BFF lưu hai token trong cookie `HttpOnly`, `SameSite=Lax`; JavaScript phía client không được đọc token.
- Next.js Proxy làm mới token khi cookie access token hết hạn. Backend chỉ chấp nhận access token ở Bearer header và chỉ chấp nhận refresh token tại `/auth/refresh`.
- Database không lưu token. `users.token_version` được đưa vào JWT và được tăng khi đổi mật khẩu hoặc khóa tài khoản để vô hiệu hóa toàn bộ token cũ.
- Mật khẩu tiếp tục được băm bằng Argon2id trước khi lưu.

## Consequences

Không còn bảng `auth_sessions` và không thể thu hồi riêng token của một thiết bị. Logout chỉ xóa cookie hiện tại. Refresh token bị đánh cắp còn hiệu lực đến khi hết hạn, tài khoản bị khóa hoặc mật khẩu được đổi. Secret JWT phải được quản lý như secret server-side và thay đổi giá trị mặc định trước khi chạy production.
