# CyVerse Internal Tools

Monorepo cho các công cụ nội bộ của CyVerse.

## Yêu cầu

- Node.js 24.21.0 (xem `.node-version`)
- Corepack, đi kèm Node.js.
- `uv` để quản lý Python và dependency backend. Nếu chưa có, cài theo [hướng dẫn chính thức của uv](https://docs.astral.sh/uv/getting-started/installation/).

Không cần cài pnpm hoặc Python thủ công. Corepack sẽ dùng pnpm 12.4.0 đã pin trong `package.json`; `uv` sẽ dùng Python 3.13.15 đã pin trong `.python-version`.

## Cài đặt từ bản clone mới

Trên Windows PowerShell:

```powershell
corepack enable
pnpm.cmd bootstrap
```

Trên macOS/Linux:

```bash
corepack enable
pnpm bootstrap
```

Lệnh bootstrap:

- Tạo `apps/web/.env.local` từ `apps/web/.env.example` nếu file local chưa tồn tại.
- Tạo `apps/backend/.env` từ `apps/backend/.env.example` nếu file local chưa tồn tại.
- Cài frontend theo `pnpm-lock.yaml`.
- Tạo `apps/backend/.venv` và cài backend theo `apps/backend/uv.lock`.

Bootstrap không ghi đè file môi trường đã có. Sau khi bootstrap, điền giá trị local trong hai file trên khi cần kết nối database hoặc dịch vụ ngoài.

## Cấu hình đăng nhập nội bộ

Backend cần PostgreSQL đang chạy và database đã tồn tại. Cập nhật `apps/backend/.env`:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:<POSTGRES_PASSWORD>@localhost:5432/cyverse
AUTH_JWT_SECRET=<AT_LEAST_32_RANDOM_CHARACTERS>
```

Nếu dùng Supabase trên mạng chỉ có IPv4, giữ direct `DATABASE_URL` lấy từ nút **Connect** của project và thêm region của Session Pooler:

```env
SUPABASE_POOLER_REGION=ap-southeast-2
```

Backend sẽ tự chuyển direct endpoint sang Supabase Session Pooler port `5432`, thêm `sslmode=require`, đồng thời giữ nguyên database password.

Không commit mật khẩu PostgreSQL hoặc file `.env`. Frontend gọi backend qua Server Actions; cập nhật `apps/web/.env.local`:

```env
BACKEND_API_URL=http://localhost:8000/api/v1
APP_URL=http://localhost:3000
```

Chạy migration từ thư mục root:

```powershell
pnpm.cmd db:migrate
```

Kiểm tra revision hiện tại khi cần:

```powershell
pnpm.cmd db:status
```

### Tạo admin đầu tiên

Chỉ dùng lệnh này khi hệ thống chưa có admin đang hoạt động:

```powershell
pnpm.cmd admin:create --username admin --display-name "CyVerse Admin" --team "Platform"
```

CLI yêu cầu nhập và xác nhận mật khẩu bằng prompt ẩn. Mật khẩu phải dài từ 8 đến 128 ký tự; không ghi mật khẩu trực tiếp vào câu lệnh, README hoặc shell history. Sau khi có admin đầu tiên, admin có thể tạo tài khoản `member` hoặc `admin` tại `/admin/users`.

Trên macOS/Linux, dùng cùng câu lệnh nhưng thay `pnpm.cmd` bằng `pnpm`.

## Chạy backend và frontend local

Mở hai terminal tại thư mục root.

Terminal 1 — backend:

```powershell
pnpm.cmd dev:backend
```

Backend tự khởi động AI Research queue consumer trong FastAPI; không cần chạy thêm worker process.

Terminal 2 — frontend:

```powershell
pnpm.cmd dev:web
```

Trên macOS/Linux, dùng `pnpm dev:backend` và `pnpm dev:web`. Dùng `pnpm.cmd` trên Windows giúp tránh lỗi PowerShell `running scripts is disabled` mà không cần thay đổi execution policy của máy.

- Frontend: `http://localhost:3000`.
- Backend: `http://localhost:8000`.
- API documentation: `http://localhost:8000/docs`.
- Health check: `http://localhost:8000/api/v1/health`.
- Login: `http://localhost:3000/login`.

Đăng nhập bằng tài khoản đã tạo qua `admin:create`. Session được lưu trong cookie `HttpOnly` trong 30 ngày và không xuất hiện trong browser storage.

## Các lệnh kiểm tra

Chạy từ thư mục root:

```powershell
pnpm.cmd lint:backend
pnpm.cmd test:backend
pnpm.cmd lint:web
pnpm.cmd test:web
pnpm.cmd build:web
```

## Thành phần

- `apps/web`: frontend Next.js.
- `apps/backend`: API FastAPI, background workers và scheduler.
- `docs`: tài liệu sản phẩm và kỹ thuật.
- `infra`: cấu hình triển khai.
- `scripts`: script dùng ở cấp repository.

Xem hướng dẫn riêng tại `apps/web/README.md` và `apps/backend/README.md`.

Baseline runtime, framework và tooling được ghi tại `docs/technology-baseline.md`.
