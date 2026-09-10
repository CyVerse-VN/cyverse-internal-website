# Web

Frontend Next.js dùng App Router.

```bash
pnpm bootstrap
pnpm dev:web
```

Chạy các lệnh trên từ root repository. Cấu hình local nằm trong `.env.local`; danh sách biến và giá trị mẫu nằm trong `.env.example`.

Chỉ biến có prefix `NEXT_PUBLIC_` được phép xuất hiện ở đây. Các giá trị này có thể được đưa xuống trình duyệt và không được chứa secret.

Ứng dụng mặc định chạy tại `http://localhost:3000`.

Frontend yêu cầu Node.js 24.21.0 và pnpm 12.x theo baseline tại `docs/technology-baseline.md`.
