# Deployment

Cấu hình container và triển khai được quản lý trong `infra`. Các workflow CI/CD sẽ nằm trong `.github/workflows`.

## Ranh giới biến môi trường

Frontend và backend là hai deployment unit độc lập:

- Frontend dùng `apps/web/.env.example` làm hợp đồng cấu hình. Khi deploy, khai báo `NEXT_PUBLIC_API_URL` trong frontend service.
- Backend dùng `apps/backend/.env.example` làm hợp đồng cấu hình. Khi deploy, khai báo các biến này trong backend service hoặc secret manager.
- Không upload file `.env` local và không commit secret.
- `NEXT_PUBLIC_*` là dữ liệu công khai được bundle cho trình duyệt. Mọi database credential, Supabase key phía server và OpenRouter key chỉ được khai báo cho backend.

## Biến frontend

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Có | URL public của backend, bao gồm prefix `/api/v1`. |

## Biến backend

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `APP_ENV` | Có | Tên môi trường, ví dụ `development`, `staging` hoặc `production`. |
| `APP_NAME` | Có | Tên hiển thị của FastAPI application. |
| `API_V1_PREFIX` | Có | Prefix route API, mặc định `/api/v1`. |
| `DATABASE_URL` | Có khi dùng database | PostgreSQL SQLAlchemy URL dùng driver `psycopg`. |
| `SUPABASE_URL` | Khi bật Supabase | URL project Supabase. |
| `SUPABASE_KEY` | Khi bật Supabase | Key phía server; lưu trong secret manager. |
| `OPENROUTER_API_KEY` | Khi bật OpenRouter | API key phía server; lưu trong secret manager. |
