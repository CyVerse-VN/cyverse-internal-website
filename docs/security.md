# Security

## Internal authentication

- Tài khoản dùng `username` chuẩn hóa chữ thường và mật khẩu băm bằng Argon2id.
- Mật khẩu được chấp nhận từ 8 đến 128 ký tự.
- Trình duyệt lưu access token và refresh token trong cookie `HttpOnly`, `SameSite=Lax`; token không được đưa vào client JavaScript hoặc browser storage.
- Access token JWT có thời hạn mặc định 15 phút; refresh token JWT có thời hạn mặc định 30 ngày. Backend cố định thuật toán `HS256` và bắt buộc các claim `iss`, `aud`, `sub`, `iat`, `nbf`, `exp`, `type`, `ver`, `jti`.
- Secret ký JWT phải có ít nhất 32 ký tự và phải được thay bằng giá trị ngẫu nhiên riêng trong production.
- Token không được lưu trong database. Logout xóa cookie tại Next.js; khóa tài khoản hoặc đổi mật khẩu tăng `users.token_version` để vô hiệu hóa toàn bộ token cũ.
- Vì refresh token là stateless, một token bị đánh cắp vẫn có hiệu lực đến khi hết hạn, tài khoản bị khóa hoặc mật khẩu được đổi. Hệ thống không hỗ trợ thu hồi riêng từng thiết bị.
- Đăng nhập sai trả cùng một thông báo chung và không khóa tạm tài khoản.
- Quyền `admin` luôn được kiểm tra tại API. Khóa tài khoản hoặc đặt lại mật khẩu sẽ vô hiệu hóa token hiện tại.
- Role được lưu dạng string; Pydantic và authorization service chịu trách nhiệm chấp nhận `admin`/`member` và từ chối giá trị khác.
- User có `deleted_at` không còn hợp lệ cho đăng nhập hay truy cập API.
- Không ghi log mật khẩu, raw token, password hash hoặc payload nhạy cảm.

Không lưu secret trong repository. Xác thực, phân quyền và các hàm mật mã được tập trung trong `app/auth` và `app/core/security.py`.
