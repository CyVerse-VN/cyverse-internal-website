# ADR 005: Internal username authentication

## Status

Superseded by ADR 006

## Context

CyVerse cần tài khoản nội bộ được quản trị viên cấp, không có self-signup, email reset hoặc external OAuth trong v1.

## Decision

- FastAPI sở hữu user, password verification, authorization và revocable sessions trong PostgreSQL.
- Mật khẩu dùng Argon2id. Session dùng opaque random token; database chỉ lưu token hash.
- Next.js hoạt động như BFF, giữ raw token trong cookie `HttpOnly` và gọi backend từ server.
- Role v1 gồm chuỗi `admin` và `member`, được validate và kiểm tra trong backend thay vì database enum/check constraint. Admin đầu tiên được bootstrap bằng CLI.
- Model xác thực dùng `created_at`, `updated_at`, `deleted_at`; mọi lookup đăng nhập bỏ qua bản ghi đã xóa mềm.

## Consequences

Ứng dụng tự chịu trách nhiệm vận hành authentication schema, session revocation và migration. Đăng nhập sai không làm khóa tạm tài khoản. Supabase có thể vẫn cung cấp PostgreSQL managed nhưng Supabase Auth không được dùng cho luồng này.
