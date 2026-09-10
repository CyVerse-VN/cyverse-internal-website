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

## Chạy local

Mở hai terminal tại thư mục root:

```bash
pnpm dev:web
```

```bash
pnpm dev:backend
```

Nếu PowerShell báo `running scripts is disabled`, dùng `pnpm.cmd dev:web` và `pnpm.cmd dev:backend`. Không cần thay đổi execution policy của máy.

- Frontend: `http://localhost:3000`.
- Backend: `http://localhost:8000`.
- Health check: `http://localhost:8000/api/v1/health`.

## Thành phần

- `apps/web`: frontend Next.js.
- `apps/backend`: API FastAPI, background workers và scheduler.
- `docs`: tài liệu sản phẩm và kỹ thuật.
- `infra`: cấu hình triển khai.
- `scripts`: script dùng ở cấp repository.

Xem hướng dẫn riêng tại `apps/web/README.md` và `apps/backend/README.md`.

Baseline runtime, framework và tooling được ghi tại `docs/technology-baseline.md`.
