# Database

## Authentication schema

- `users` lưu username duy nhất, password hash, hồ sơ hiển thị, role dạng string, trạng thái và timestamps.
- `users.token_version` được tăng khi khóa tài khoản hoặc đổi mật khẩu để vô hiệu hóa toàn bộ token cũ mà không cần lưu từng session.
- Access token và refresh token là JWT đã ký, không được lưu trong database. Bảng `auth_sessions` được xóa ở migration `20260912_0002`.
- User dùng `created_at`, `updated_at`, `deleted_at`; repository mặc định bỏ qua bản ghi có `deleted_at`.
- Database lưu `role` như chuỗi thông thường. Danh sách role hợp lệ và authorization được kiểm tra trong backend code.
- Không xóa vĩnh viễn user từ giao diện quản trị; dùng `is_active` để giữ tính toàn vẹn tham chiếu.

Chạy migration từ repository root:

```bash
uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head
```

Database được truy cập qua lớp session và repositories. Mọi thay đổi schema phải có migration Alembic tương ứng.

## AI Research schema

- `tool_runs` lưu owner, FIFO status, stage, progress, cancellation, worker lease và lỗi an toàn.
- `tool_run_events` lưu timeline stage để frontend khôi phục tiến trình sau reconnect.
- `research_sessions` lưu query, public/private visibility, effective settings, warning và số liệu tổng hợp.
- `research_papers` chỉ lưu paper cuối pipeline đã có Vietnamese summary và 1–3 why-read bullets.

Không lưu source response, raw candidate, abstract, prompt/response LLM hoặc ranking trung gian.
