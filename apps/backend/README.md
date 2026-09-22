# Backend

## Internal authentication setup

Sau khi cấu hình `DATABASE_URL` và `AUTH_JWT_SECRET`, chạy migration và tạo admin đầu tiên:

```bash
uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head
uv run --project apps/backend cyverse-create-admin --username admin --display-name "CyVerse Admin" --team "Platform"
```

CLI yêu cầu nhập và xác nhận mật khẩu bằng prompt ẩn. Sau khi có admin đầu tiên, quản lý tài khoản tại `/admin/users` trên frontend.

API FastAPI theo kiến trúc modular monolith.

```bash
uv sync --project apps/backend --extra dev
pnpm dev:backend
```

FastAPI tự chạy AI Research queue consumer theo `research_config.embedded_worker` (mặc định `True`),
nên local development và deployment không cần một worker process riêng.

Chạy các lệnh trên từ thư mục root của repository. Có thể dùng `pnpm bootstrap` để cài cả frontend và backend trong một lệnh.

Cấu hình secret và hạ tầng local nằm trong `.env`; danh sách biến mẫu nằm trong `.env.example`. Backend luôn resolve file này theo thư mục `apps/backend`, không phụ thuộc current working directory. Các thông số vận hành AI Research (provider, model, endpoint, giới hạn, timeout, ranking và queue) được quản lý tập trung, có type và validation tại `src/app/tools/research/config.py`; thay đổi file này cần restart backend.

`SUPABASE_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `RESEARCH_SEMANTIC_SCHOLAR_API_KEY` và `RESEARCH_OPENALEX_API_KEY` là secret phía server; không sao chép chúng sang frontend hoặc commit giá trị thật.
`AUTH_JWT_SECRET` cũng là secret phía server, phải có ít nhất 32 ký tự và phải khác giá trị mẫu khi chạy production.

API mặc định chạy tại `http://localhost:8000`; health check ở `/api/v1/health`.

Backend yêu cầu Python 3.13.15 theo baseline tại `docs/technology-baseline.md`.
