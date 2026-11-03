# Kiến trúc

## Database data flow

FastAPI API, background workers và CLI truy cập database `cyverse_internal` trên PostgreSQL-compatible TiDB Cloud qua SQLAlchemy và psycopg 3. `apps/backend/src/app/core/config.py` xác thực và chuẩn hóa `DATABASE_URL` dùng chung cho async session và Alembic sync engine; endpoint TiDB mặc định dùng TLS với kiểm tra hostname và CA từ certifi. Repositories giữ trách nhiệm truy vấn, frontend chỉ gọi backend API. Xem [database setup](database.md).

## Authentication data flow

Browser gửi form đến Next.js Server Action. Next.js gọi FastAPI bằng `BACKEND_API_URL`, lưu access token và refresh token đã ký trong hai cookie `HttpOnly`, rồi gửi access token cho backend bằng Bearer header ở các request server-side. Khi access token hết hạn, Next.js Proxy dùng refresh token để lấy cặp token mới trước khi render route. FastAPI xác minh chữ ký, loại token, hạn dùng và `token_version`, sau đó tải user hiện tại để thực hiện authorization theo role. Browser không gọi trực tiếp authentication API và JavaScript phía client không đọc được token.

Account Settings dùng endpoint self-service riêng: user chỉ được cập nhật display name/team và đổi mật khẩu của chính mình. Username, role và trạng thái vẫn do administrator quản lý. Khi đổi mật khẩu, backend tăng `token_version` để vô hiệu hóa các token cũ rồi phát cặp token mới cho phiên đang thao tác.

Hệ thống là monorepo gồm frontend Next.js và backend FastAPI theo hướng modular monolith. Các tác vụ dài được chuyển sang background jobs; scheduler chịu trách nhiệm kích hoạt các job định kỳ.

## Threads Scraper data flow

Browser → Next.js authenticated proxy → `ThreadsService`/`ThreadsRepository` → `tool_runs` queue →
`ThreadsWorker` → registered `ThreadsTool` → pipeline → Playwright account contexts và
Groq adapter. Worker persist stage vào `tool_runs`, checkpoint selected posts trước comments,
rồi cập nhật snapshots sau từng bài lấy comments/AI analysis trong
`threads_results`/`threads_posts`/`threads_comments`. Session mới mặc định public cho user
đã đăng nhập; private chỉ owner/admin đọc; mọi mutation chỉ owner/admin. JSON/TXT
download kiểm tra cùng quyền. Consumer giữ hàng đợi archive/cleanup: một raw TXT
asset authenticated trên Cloudinary cho mỗi session sau khi job dừng, retry độc lập khi
cloud lỗi. Delete dừng pipeline, xóa cloud rồi hard-delete database bằng cascade. Consumer
có advisory lock riêng, có thể chạy trong API
lifespan hoặc qua CLI. JSON export chứa run metadata và result; mỗi bài/bình luận có thể
chứa source record đã loại các trường xác thực phổ biến, cùng metadata
thu thập. Không lưu toàn bộ network response. Worker khôi phục account sessions trước khi
nhận job. Cấu hình dùng chung `apps/backend/.env`; browser sessions nằm trong
backend `.local/threads/sessions`. Xem [Threads tool](tools/threads.md).

## AI Research data flow

Browser gọi Next.js same-origin route vì access token nằm trong HttpOnly cookie. Route Handler thêm
Bearer token và gọi FastAPI. API tạo durable `tool_run`/`research_session` rồi trả queued state ngay.
Queue consumer được FastAPI lifespan khởi động cùng backend. Consumer giữ PostgreSQL advisory lock
toàn cục, claim FIFO session, persist từng stage và chỉ commit final papers sau enrichment. Browser
poll detail trong lúc active nên có thể reload mà không mất queue position hoặc progress. Việc chạy
consumer trong API process giúp deployment chỉ cần một Web Service; database lease/stale recovery
vẫn bảo vệ các run bị gián đoạn khi backend restart.
