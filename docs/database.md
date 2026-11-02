# Database

## TiDB Cloud PostgreSQL setup

Ứng dụng dùng **PostgreSQL-compatible TiDB Cloud**, database `cyverse_internal`, port `5432`. Lấy thông tin từ **Connect** của instance và đặt `DATABASE_URL` trong `apps/backend/.env` hoặc secret environment của backend:

```env
DATABASE_URL=postgresql://INSTANCE.postgres:REPLACE_WITH_URL_ENCODED_PASSWORD@INSTANCE.gateway01.us-east-1.prod.aws.pg.tidbcloud.com:5432/cyverse_internal?sslmode=verify-full
```

- URL trên chỉ là mẫu; thay toàn bộ placeholder và percent-encode ký tự đặc biệt trong mật khẩu. Không đưa TXT link hoặc `mailto:` vào URL.
- `DATABASE_URL` là bắt buộc, không có kết nối database mặc định. Backend và Alembic cùng chuẩn hóa `postgresql://` thành `postgresql+psycopg://`, giữ nguyên username, host, port và database.
- Endpoint `.pg.tidbcloud.com` mặc định dùng `sslmode=verify-full`, kiểm tra CA và hostname. Backend tự đặt `sslrootcert` thành CA bundle của certifi để Windows và Linux dùng cùng tập CA. Nếu có CA riêng, thêm `sslrootcert` với đường dẫn PEM đã URL-encode; không tắt TLS.
- Chỉ backend giữ thông tin kết nối; không đưa vào frontend, log, tài liệu hoặc Git. `.env.example` chỉ chứa placeholder.
- SQLAlchemy async sessions phục vụ request và workers; Alembic dùng sync engine với cùng driver psycopg 3. Không cần thêm driver hoặc dịch vụ authentication của nhà cung cấp database.

Database `cyverse_internal` phải tồn tại trước khi chạy migration. Trên database được phép khởi tạo, chạy từ repository root:

```powershell
pnpm.cmd db:migrate
pnpm.cmd db:status
pnpm.cmd admin:create
```

Migration giữ nguyên lịch sử schema, tạo application tables trong database đích. Đổi URL không sao chép dữ liệu; việc chuyển dữ liệu có sẵn cần quy trình export/import riêng và phải được phép truy cập dữ liệu nguồn/đích. Không sửa hoặc xóa các bảng hệ thống do TiDB Cloud quản lý.

Kiểm tra tự động dùng URL database test riêng và mock repositories; không kết nối cloud. Có thể kiểm tra SQL migration mà không mở kết nối bằng:

```powershell
uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head --sql
```

Trước khi vận hành trên instance đích, xác minh schema/migrations, CRUD và transactions, JSONB, `SELECT ... FOR UPDATE` và PostgreSQL advisory locks dùng bởi workers. Kiểm tra offline không thay thế kiểm tra tích hợp trên database được phép sử dụng.

Tài liệu: [TiDB PostgreSQL quick start](https://docs.pingcap.com/tidbcloud/pg-quickstart/), [PostgreSQL compatibility](https://docs.pingcap.com/tidbcloud/postgresql-compatibility/) và [psycopg/libpq TLS](https://www.postgresql.org/docs/18/libpq-ssl.html).

## Authentication schema

- `users` lưu username duy nhất, password hash, hồ sơ hiển thị, role dạng string, trạng thái và timestamps.
- `users.token_version` được tăng khi khóa tài khoản hoặc đổi mật khẩu để vô hiệu hóa toàn bộ token cũ mà không cần lưu từng session.
- Access token và refresh token là JWT đã ký, không được lưu trong database. Bảng `auth_sessions` được xóa ở migration `20260912_0002`.
- User dùng `created_at`, `updated_at`, `deleted_at`; repository mặc định bỏ qua bản ghi có `deleted_at`.
- Database lưu `role` như chuỗi thông thường. Danh sách role hợp lệ và authorization được kiểm tra trong backend code.
- Không xóa vĩnh viễn user từ giao diện quản trị; dùng `is_active` để giữ tính toàn vẹn tham chiếu.

Chạy migration từ repository root:

```bash
uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head
```

Database được truy cập qua lớp session và repositories. Mọi thay đổi schema phải có migration Alembic tương ứng.

## Threads schema

- `tool_runs` lưu request, owner, trạng thái và tiến trình collection.
- `threads_results.run_id` là primary key và foreign key tới job; JSONB summary giữ keywords,
  curated IDs, warnings và thống kê.
- `threads_posts` lưu source post ID, thứ tự và JSONB snapshot đã validation, gồm counters,
  text, media URLs và AI analysis. Unique theo `(run_id, post_id)` và `(run_id, position)`.
- `threads_comments` liên kết snapshot post, lưu source comment ID, parent comment ID, thứ tự
  và JSONB nội dung; parent ID được giữ dù bình luận cha nằm ngoài giới hạn collection.

Migration `20261101_0006` tạo bảng và indexes. `20261101_0007` thêm visibility, snapshot
readiness, counts, Cloudinary public ID/status, retry và deletion marker vào `threads_results`.
Session được tạo ngay lúc queue; selected posts được checkpoint trước comments, rồi commit
sau từng bài lấy bình luận/AI analysis. Lỗi/hủy/restart giữ dữ liệu từng phần. Session mới
public; session cũ giữ private. API list không tải toàn bộ snapshot. Delete chỉ hard-delete
`tool_runs` cùng các snapshot/events sau khi cloud cleanup thành công (hoặc chưa từng thử
upload). Xem [Threads tool](tools/threads.md).

## AI Research schema

- `tool_runs` lưu owner, FIFO status, stage, progress, cancellation, worker lease và lỗi an toàn.
- `tool_run_events` lưu timeline stage để frontend khôi phục tiến trình sau reconnect.
- `research_sessions` lưu query, public/private visibility, effective settings, warning và số liệu tổng hợp.
- `research_papers` chỉ lưu paper cuối pipeline đã có Vietnamese summary và 1–3 why-read bullets.

Không lưu source response, raw candidate, abstract, prompt/response LLM hoặc ranking trung gian.


Migration `20261102_0008` đổi `markdown_status/public_id/uploaded_at` thành các cột
`archive_status/public_id/uploaded_at` và thêm `legacy_archive_public_id`. Session cũ được
đưa về pending để ghi TXT rồi xóa file Markdown cũ; giữ cả hai reference nếu cloud lỗi.
