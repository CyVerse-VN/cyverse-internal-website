# Backend

API FastAPI theo kiến trúc modular monolith.

```bash
uv sync --project apps/backend --extra dev
pnpm dev:backend
```

Chạy các lệnh trên từ thư mục root của repository. Có thể dùng `pnpm bootstrap` để cài cả frontend và backend trong một lệnh.

Cấu hình local nằm trong `.env`; danh sách biến và giá trị mẫu nằm trong `.env.example`. Backend luôn resolve file này theo thư mục `apps/backend`, không phụ thuộc current working directory.

`SUPABASE_KEY` và `OPENROUTER_API_KEY` là secret phía server; không sao chép chúng sang frontend hoặc commit giá trị thật.

API mặc định chạy tại `http://localhost:8000`; health check ở `/api/v1/health`.

Backend yêu cầu Python 3.13.15 theo baseline tại `docs/technology-baseline.md`.
