# Deployment

## Authentication configuration

- Frontend dùng `BACKEND_API_URL` server-only, bao gồm prefix `/api/v1`.
- Chạy Alembic migration trước khi phát hành backend có authentication schema mới.
- Bootstrap admin đầu tiên sau migration bằng `cyverse-create-admin`; mật khẩu được nhập qua prompt ẩn.
- Tạo `AUTH_JWT_SECRET` ngẫu nhiên riêng cho từng môi trường và lưu trong secret manager.

Cấu hình container và triển khai được quản lý trong `infra`. Các workflow CI/CD sẽ nằm trong `.github/workflows`.

## Ranh giới biến môi trường

Frontend và backend là hai deployment unit độc lập:

- Frontend dùng `apps/web/.env.example` làm hợp đồng cấu hình. Khi deploy, khai báo `BACKEND_API_URL` và `APP_URL` trong frontend service.
- Backend dùng `apps/backend/.env.example` làm hợp đồng cấu hình. Khi deploy, khai báo các biến này trong backend service hoặc secret manager.
- Không upload file `.env` local và không commit secret.
- `NEXT_PUBLIC_*` là dữ liệu công khai được bundle cho trình duyệt. Mọi database credential, Supabase key phía server và OpenRouter key chỉ được khai báo cho backend.

## Biến frontend

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `BACKEND_API_URL` | Có | URL backend server-only, bao gồm prefix `/api/v1`. |
| `APP_URL` | Có | URL canonical của frontend. |

## Biến backend

| Biến | Bắt buộc | Mô tả |
| --- | --- | --- |
| `APP_ENV` | Có | Tên môi trường, ví dụ `development`, `staging` hoặc `production`. |
| `APP_NAME` | Có | Tên hiển thị của FastAPI application. |
| `API_V1_PREFIX` | Có | Prefix route API, mặc định `/api/v1`. |
| `DATABASE_URL` | Có khi dùng database | PostgreSQL SQLAlchemy URL dùng driver `psycopg`. |
| `AUTH_JWT_SECRET` | Có | Secret ngẫu nhiên tối thiểu 32 ký tự để ký access/refresh token. Không dùng giá trị mẫu trong production. |
| `AUTH_JWT_ISSUER` | Có | Issuer bắt buộc trong JWT, mặc định `cyverse-backend`. |
| `AUTH_JWT_AUDIENCE` | Có | Audience bắt buộc trong JWT, mặc định `cyverse-internal-web`. |
| `AUTH_ACCESS_TOKEN_MINUTES` | Có | Thời hạn access token theo phút, mặc định `15`. |
| `AUTH_REFRESH_TOKEN_DAYS` | Có | Thời hạn refresh token theo ngày, mặc định `30`. |
| `SUPABASE_POOLER_REGION` | Khi Supabase chạy trên mạng IPv4 | AWS region dùng để chuyển direct URL sang Session Pooler port `5432`. |
| `SUPABASE_URL` | Khi bật Supabase | URL project Supabase. |
| `SUPABASE_KEY` | Khi bật Supabase | Key phía server; lưu trong secret manager. |
| `OPENROUTER_API_KEY` | Khi bật OpenRouter | API key phía server; lưu trong secret manager. |
| `GROQ_API_KEY` | Khi AI Research dùng Groq | API key phía server; lưu trong secret manager. |
| `RESEARCH_SEMANTIC_SCHOLAR_API_KEY` | Không | API key source phía server; giúp tăng quota khi được cấp. |
| `RESEARCH_OPENALEX_API_KEY` | Không | API key source phía server; chỉ khai báo khi tài khoản OpenAlex yêu cầu. |

## AI Research queue consumer

AI Research queue consumer chạy trực tiếp trong FastAPI lifespan khi
`research_config.embedded_worker=True`, do đó deployment chỉ cần một backend Web Service. Không cần tạo
Background Worker riêng. Consumer giữ PostgreSQL advisory lock và tự thử lại khi process khác đang
giữ lock hoặc khi database tạm thời mất kết nối.

Để giữ mô hình deploy đơn giản và predictable, chạy một Render Web Service instance với một Uvicorn
worker. Khi backend shutdown có kiểm soát, task nền được cancel và run dở dang được đưa lại vào FIFO
queue ngay. Stale recovery theo lease vẫn xử lý trường hợp process crash không kịp cleanup. Database
migration phải chạy trước khi phát hành backend mới.

Environment chỉ giữ secret AI (`GROQ_API_KEY`, `OPENROUTER_API_KEY`,
`RESEARCH_SEMANTIC_SCHOLAR_API_KEY`, `RESEARCH_OPENALEX_API_KEY`). Provider/model, endpoint,
timeout/retry, default/maximum, ranking, poll interval, restart interval và lease được quản lý bằng
typed config tại `apps/backend/src/app/tools/research/config.py`. Thay đổi config này cần build/redeploy
hoặc restart backend. Có thể đặt `research_config.embedded_worker=False` trong file config cho process
chỉ phục vụ API.

Render Web Service dùng start command duy nhất:

```text
uv run --project apps/backend uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
