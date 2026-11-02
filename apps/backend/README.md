# Backend

## Internal authentication setup

Đặt `DATABASE_URL` thành connection string PostgreSQL-compatible TiDB Cloud với database `cyverse_internal` và cấu hình `AUTH_JWT_SECRET`. URL mẫu trong `.env.example` chỉ chứa placeholder; phải thay bằng thông tin từ TiDB Cloud. Backend và Alembic dùng chung URL qua psycopg 3, mặc định xác minh TLS. Xem [database setup](../../docs/database.md).

Chạy migration và tạo admin đầu tiên trên database đích đã được phép khởi tạo:

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

To run the local backend without automatic reload, use `pnpm.cmd start:backend`.
Both entry points explicitly select a psycopg-compatible event loop on Windows.

FastAPI tự chạy AI Research queue consumer theo `research_config.embedded_worker` (mặc định `True`),
nên local development và deployment không cần một worker process riêng.

Chạy các lệnh trên từ thư mục root của repository. Có thể dùng `pnpm bootstrap` để cài cả frontend và backend trong một lệnh.

Cấu hình secret và hạ tầng local nằm trong `.env`; danh sách biến mẫu nằm trong `.env.example`. Backend luôn resolve file này theo thư mục `apps/backend`, không phụ thuộc current working directory. Các thông số vận hành AI Research (provider, model, endpoint, giới hạn, timeout, ranking và queue) được quản lý tập trung, có type và validation tại `src/app/tools/research/config.py`; thay đổi file này cần restart backend.

`DATABASE_URL`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `RESEARCH_SEMANTIC_SCHOLAR_API_KEY` và `RESEARCH_OPENALEX_API_KEY` là secret phía server; không sao chép chúng sang frontend hoặc commit giá trị thật.
`AUTH_JWT_SECRET` cũng là secret phía server, phải có ít nhất 32 ký tự và phải khác giá trị mẫu khi chạy production.

API mặc định chạy tại `http://localhost:8000`; health check ở `/api/v1/health`.

Backend yêu cầu Python 3.13.15 theo baseline tại `docs/technology-baseline.md`.

## Threads Scraper

Tool Threads dùng chung `apps/backend/.env`, hỗ trợ login/session, tìm kiếm, bình luận,
Groq và API job nền. Cài browser bằng `pnpm.cmd threads:install`, đăng nhập bằng
`pnpm.cmd threads:login acc_01`. Consumer embedded hỗ trợ Windows/Uvicorn reload;
đặt `THREADS_EMBEDDED_WORKER=true` để chạy cùng backend. Có thể tách worker bằng
`THREADS_EMBEDDED_WORKER=false` và lệnh `pnpm.cmd threads:worker`.
Xem [hướng dẫn đầy đủ](../../docs/tools/threads.md).
