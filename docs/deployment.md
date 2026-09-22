# Deployment Guide

Tài liệu hướng dẫn triển khai toàn diện hệ sinh thái CyVerse Internal Tools với kiến trúc phân tán:
- **Frontend (`apps/web`)**: Triển khai trên **Vercel** (Next.js 16+ Turbopack).
- **Backend (`apps/backend`)**: Triển khai trên **Render** (FastAPI, Python 3.13, Uvicorn, uv).
- **Database**: PostgreSQL (Render PostgreSQL, Supabase, Neon hoặc AWS RDS).

---

## 1. Tổng quan kiến trúc và luồng dữ liệu

```
[ Trình duyệt người dùng ]
        │
        ├── (1) Giao diện & Next.js Server Actions / API Routes
        ▼
[ Vercel: Next.js Web App ] (apps/web)
        │
        │ (2) Server-to-Server HTTPS Fetch (BACKEND_API_URL)
        ▼
[ Render: FastAPI Backend ] (apps/backend)
        │
        ├── (3) Database Queries (DATABASE_URL qua psycopg3)
        ▼
[ PostgreSQL Database ] (Supabase / Render Postgres)
```

- **Authentication & Cookies**: Next.js Server Actions thực hiện đăng nhập với Backend và quản lý `access_token` cùng `refresh_token` trong Cookie bảo mật (`HttpOnly`, `SameSite=Lax`, `Secure` trên HTTPS).
- **Server-to-Server Communication**: Frontend gọi Backend hoàn toàn qua server Next.js bằng `BACKEND_API_URL`. Trình duyệt không trực tiếp gọi API Backend ngoại trừ khi được mở rộng.
- **CORS Protection**: Backend được trang bị `CORSMiddleware` với danh sách origin hợp lệ (`CORS_ORIGINS`) và biểu thức chính quy (`CORS_ORIGIN_REGEX`) để hỗ trợ domain chính thức cũng như các Vercel preview deployment (`*.vercel.app`).

---

## 2. Hướng dẫn triển khai Backend lên Render

Có 2 phương thức triển khai trên Render:

### Cách 1: Sử dụng Render Blueprint (`render.yaml`) — Khuyến nghị

Kho lưu trữ đã tích hợp sẵn file [render.yaml](file:///d:/MyProject/CyVerse/cyverse-internal-website/render.yaml) ở thư mục gốc:

1. Đăng nhập vào [Render Dashboard](https://dashboard.render.com/).
2. Nhấn nút **New +** > Chọn **Blueprint**.
3. Kết nối với GitHub repository của bạn (`cyverse-internal-website`).
4. Render sẽ tự động phát hiện `render.yaml` và nạp dịch vụ `cyverse-backend`:
   - Runtime: **Docker** (sử dụng [Dockerfile.backend](file:///d:/MyProject/CyVerse/cyverse-internal-website/infra/docker/Dockerfile.backend)).
   - Tự động sinh `AUTH_JWT_SECRET` ngẫu nhiên đạt chuẩn bảo mật >= 32 ký tự.
   - Tự động chạy migration database (`alembic upgrade head`) khi container khởi động (hoàn toàn tương thích gói Free tier của Render).
5. Điền các biến môi trường chưa đồng bộ (ví dụ: `DATABASE_URL`, `CORS_ORIGINS`, các API key AI).
6. Nhấn **Apply** để bắt đầu build và deploy.

---

### Cách 2: Tạo Web Service thủ công trên Render

Nếu muốn tự cấu hình trên giao diện Render Dashboard:

1. Nhấn **New +** > Chọn **Web Service**.
2. Kết nối với repository Git.
3. Cấu hình cơ bản:
   - **Name**: `cyverse-backend`
   - **Region**: `Singapore` (hoặc khu vực gần bạn nhất).
   - **Branch**: `main` (hoặc branch bạn muốn deploy).
   - **Root Directory**: Để trống (mặc định là root của repository).
4. Chọn một trong hai Runtime:

#### Phương án Docker (Tối ưu và đồng nhất môi trường nhất - Khuyến nghị cho Free tier):
- **Environment**: `Docker`
- **Dockerfile Path**: `infra/docker/Dockerfile.backend`
- **Docker Build Context Directory**: `.`
- *(Gói Free không cần điền Pre-Deploy Command vì Dockerfile đã tự động chạy migration khi khởi động)*.

#### Phương án Python Native (Không dùng Docker):
- **Environment**: `Python`
- **Build Command**:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv sync --frozen --project apps/backend --no-dev
  ```
- **Start Command**:
  ```bash
  export PATH="$HOME/.local/bin:$PATH" && uv run --project apps/backend uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Pre-Deploy Command**:
  ```bash
  export PATH="$HOME/.local/bin:$PATH" && uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head
  ```

5. Cấu hình **Health Check Path**:
   - Nhập: `/api/v1/health` (hoặc `/health`). Render sẽ kiểm tra định kỳ để đảm bảo service luôn hoạt động.

---

### Bảng biến môi trường Backend trên Render

Khai báo trong mục **Environment Variables** của Web Service trên Render:

| Tên biến | Bắt buộc | Giá trị mẫu / Hướng dẫn |
| --- | --- | --- |
| `APP_ENV` | Có | `production` |
| `APP_NAME` | Có | `CyVerse Internal Tools API` |
| `API_V1_PREFIX` | Có | `/api/v1` |
| `DATABASE_URL` | Có | Connection string PostgreSQL (ví dụ: `postgresql+psycopg://user:pass@host:5432/dbname`). Nếu dùng URL dạng `postgresql://`, hệ thống sẽ tự động chuyển sang driver `psycopg`. |
| `AUTH_JWT_SECRET` | Có | Chuỗi ngẫu nhiên bí mật tối thiểu **32 ký tự** (Render Blueprint tự động sinh bằng `generateValue: true`). Không sử dụng giá trị mẫu trong production. |
| `AUTH_JWT_ISSUER` | Có | `cyverse-backend` |
| `AUTH_JWT_AUDIENCE` | Có | `cyverse-internal-web` |
| `AUTH_ACCESS_TOKEN_MINUTES` | Có | `15` |
| `AUTH_REFRESH_TOKEN_DAYS` | Có | `30` |
| `CORS_ORIGINS` | Có | Danh sách domain frontend được phép truy cập, phân cách bằng dấu phẩy: `https://<ten-ung-dung>.vercel.app,http://localhost:3000` |
| `CORS_ORIGIN_REGEX` | Tùy chọn | `^https:\/\/.*\.vercel\.app$` (Cho phép tất cả Vercel preview branch deployments kết nối). |
| `SUPABASE_POOLER_REGION` | Khi dùng Supabase IPv4 | Ví dụ `ap-southeast-2` (Render mạng IPv4 cần pooler port 5432). |
| `SUPABASE_URL` | Khi bật Supabase | URL project Supabase. |
| `SUPABASE_KEY` | Khi bật Supabase | Secret key server-side của Supabase. |
| `GROQ_API_KEY` | Khi dùng Groq AI | API key phía server. |
| `OPENROUTER_API_KEY` | Khi dùng OpenRouter | API key phía server. |
| `GEMINI_API_KEY` | Khi dùng Google Gemini | API key phía server. |
| `RESEARCH_SEMANTIC_SCHOLAR_API_KEY` | Tùy chọn | Tăng hạn mức tra cứu AI Research. |
| `RESEARCH_OPENALEX_API_KEY` | Tùy chọn | API key OpenAlex nếu cần. |

---

### Khởi tạo tài khoản Quản trị viên (Admin) đầu tiên trên Render

Sau khi backend deploy thành công và chạy xong database migration:

1. Vào Render Dashboard > Chọn Web Service `cyverse-backend`.
2. Chọn tab **Shell**.
3. Chạy lệnh:
   - Với Docker:
     ```bash
     cyverse-create-admin
     ```
   - Với Native Python:
     ```bash
     uv run --project apps/backend cyverse-create-admin
     ```
4. Điền các thông tin:
   - `Username`: Tên đăng nhập (ví dụ `admin`)
   - `Display Name`: Tên hiển thị (ví dụ `System Administrator`)
   - `Password`: Nhập mật khẩu bí mật (mật khẩu sẽ được hash bảo mật bằng Argon2id).

---

## 3. Hướng dẫn triển khai Frontend lên Vercel

Frontend là ứng dụng Next.js nằm trong `apps/web`.

### Bước 1: Import dự án vào Vercel

1. Đăng nhập vào [Vercel Dashboard](https://vercel.com/).
2. Nhấn nút **Add New...** > Chọn **Project**.
3. Chọn GitHub repository `cyverse-internal-website`.

### Bước 2: Cấu hình Project Settings

Trong màn hình thiết lập dự án:
- **Framework Preset**: Chọn `Next.js`.
- **Root Directory**: Nhấn **Edit** và chọn `apps/web`.
- **Build Command**: Để mặc định (`next build`) hoặc `pnpm build`.
- **Output Directory**: Để mặc định (`.next`).
- **Install Command**: Để mặc định (`pnpm install`).

> [!NOTE]
> Vercel sẽ tự động phát hiện monorepo pnpm, sử dụng [pnpm-workspace.yaml](file:///d:/MyProject/CyVerse/cyverse-internal-website/pnpm-workspace.yaml) và [pnpm-lock.yaml](file:///d:/MyProject/CyVerse/cyverse-internal-website/pnpm-lock.yaml) tại thư mục gốc để quản lý và cache dependencies một cách tối ưu.

### Bước 3: Cấu hình Biến Môi Trường trên Vercel

Thêm các biến môi trường sau trong phần **Environment Variables**:

| Tên biến | Bắt buộc | Mô tả & Giá trị |
| --- | --- | --- |
| `BACKEND_API_URL` | **Có** | URL dịch vụ Render backend đã deploy, **phải bao gồm suffix `/api/v1`**.<br>Ví dụ: `https://cyverse-backend.onrender.com/api/v1` |
| `APP_URL` | Có | Domain canonical của frontend Vercel.<br>Ví dụ: `https://cyverse-web.vercel.app` (hoặc custom domain của bạn). |

> [!IMPORTANT]
> `BACKEND_API_URL` và `APP_URL` là biến server-side, **tuyệt đối không** thêm tiền tố `NEXT_PUBLIC_` để tránh lộ thông tin nội bộ ra trình duyệt client.

### Bước 4: Nhấn Deploy

Nhấn nút **Deploy**. Vercel sẽ build và cung cấp domain chính thức (dạng `https://<ten-du-an>.vercel.app`).

---

## 4. Cập nhật CORS sau khi có Domain Vercel

Sau khi Vercel deploy xong và bạn nhận được domain chính thức (ví dụ: `https://cyverse-web.vercel.app`):

1. Quay lại Render Dashboard > Chọn service `cyverse-backend` > **Environment**.
2. Thêm hoặc cập nhật biến `CORS_ORIGINS`:
   ```text
   https://cyverse-web.vercel.app
   ```
   *(Nếu có nhiều domain, phân tách bằng dấu phẩy, ví dụ: `https://cyverse-web.vercel.app,https://mycustomdomain.com`)*.
3. Đảm bảo `CORS_ORIGIN_REGEX` được đặt thành:
   ```text
   ^https:\/\/.*\.vercel\.app$
   ```
   Biểu thức này sẽ tự động chấp nhận tất cả các bản xem trước (preview deployments) của Vercel khi bạn tạo Pull Request.
4. Render sẽ tự động redeploy với cấu hình mới.

---

## 5. Danh mục kiểm tra sau triển khai (Verification Checklist)

- [ ] **Render Backend Health**: Truy cập `https://<backend>.onrender.com/health` và `https://<backend>.onrender.com/api/v1/health`, kiểm tra nhận được `{"status":"ok"}`.
- [ ] **Render API Docs**: Truy cập `https://<backend>.onrender.com/docs` để kiểm tra OpenAPI Swagger UI.
- [ ] **Alembic Database Migration**: Kiểm tra bảng `users`, `research_sessions` đã tồn tại trong database PostgreSQL.
- [ ] **Admin Account**: Đã chạy lệnh `cyverse-create-admin` trên Render Shell để tạo tài khoản admin đầu tiên.
- [ ] **Vercel Frontend Login**: Truy cập `https://<frontend>.vercel.app/login`, đăng nhập bằng tài khoản admin vừa tạo và kiểm tra chuyển hướng vào `/dashboard`.
- [ ] **AI Research Workspace**: Tạo phiên nghiên cứu mới trong `/tools/research` để kiểm tra kết nối API và queue consumer nền.
