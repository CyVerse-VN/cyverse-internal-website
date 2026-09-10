# Technology baseline

Đây là baseline phiên bản chuẩn của dự án. Khi nâng cấp một thành phần, cần cập nhật tài liệu này, manifest liên quan và lockfile trong cùng thay đổi.

| Thành phần | Phiên bản chuẩn | Ghi chú |
| --- | --- | --- |
| Node.js | 24 LTS | Không dùng Node 26 Current. |
| pnpm | 12.x | Package manager cho monorepo; commit `pnpm-lock.yaml`. |
| Next.js | Từ 16.3.3, trong line 16.x | Dùng bản security-patched và không tự động nâng sang major 17. |
| React | 19.2.x | Đồng bộ với Next.js 16. |
| TypeScript | 5.x | Next.js 16 yêu cầu TypeScript từ 5.1. |
| Tailwind CSS | 4.x | Baseline styling cho frontend mới. |
| Python | 3.13.15 | Ưu tiên compatibility của hệ sinh thái AI/data thay vì Python 3.14. |
| FastAPI | 0.141.x | Giữ trong line minor 0.141. |
| Pydantic | 2.x | Dùng native với FastAPI hiện tại. |
| SQLAlchemy | 2.0.x | ORM và database toolkit của backend. |
| Alembic | 1.19.x | Quản lý database migrations. |
| PostgreSQL | Supabase managed | Không pin phiên bản PostgreSQL server trong repository. |
| Python package manager | uv | Dùng để tạo môi trường, resolve và lock dependency. |
| Python DB driver | psycopg 3.x | Kết hợp với SQLAlchemy. |
| Testing backend | pytest | Unit test và integration test. |
| Lint/format backend | Ruff | Dùng chung cho format và lint. |
| Testing frontend | Vitest + Playwright | Unit/component test và end-to-end test. |
| Lint frontend | ESLint | Chạy ESLint trực tiếp; Next.js 16 không còn `next lint`. |

## Quy tắc pin phiên bản

- Runtime được pin bằng `.node-version` và `.python-version`.
- Manifest chỉ cho phép nâng cấp trong line đã duyệt: Next.js 16, React 19.2, FastAPI 0.141, SQLAlchemy 2.0 và Alembic 1.19.
- `pnpm-lock.yaml` và `uv.lock` phải được tạo bằng đúng runtime/package manager baseline và commit vào repository.
- Không chỉnh lockfile thủ công.

