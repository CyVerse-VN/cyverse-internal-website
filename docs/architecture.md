# Kiến trúc

## Authentication data flow

Browser gửi form đến Next.js Server Action. Next.js gọi FastAPI bằng `BACKEND_API_URL`, lưu access token và refresh token đã ký trong hai cookie `HttpOnly`, rồi gửi access token cho backend bằng Bearer header ở các request server-side. Khi access token hết hạn, Next.js Proxy dùng refresh token để lấy cặp token mới trước khi render route. FastAPI xác minh chữ ký, loại token, hạn dùng và `token_version`, sau đó tải user hiện tại để thực hiện authorization theo role. Browser không gọi trực tiếp authentication API và JavaScript phía client không đọc được token.

Account Settings dùng endpoint self-service riêng: user chỉ được cập nhật display name/team và đổi mật khẩu của chính mình. Username, role và trạng thái vẫn do administrator quản lý. Khi đổi mật khẩu, backend tăng `token_version` để vô hiệu hóa các token cũ rồi phát cặp token mới cho phiên đang thao tác.

Hệ thống là monorepo gồm frontend Next.js và backend FastAPI theo hướng modular monolith. Các tác vụ dài được chuyển sang background jobs; scheduler chịu trách nhiệm kích hoạt các job định kỳ.

## AI Research data flow

Browser gọi Next.js same-origin route vì access token nằm trong HttpOnly cookie. Route Handler thêm
Bearer token và gọi FastAPI. API tạo durable `tool_run`/`research_session` rồi trả queued state ngay.
Queue consumer được FastAPI lifespan khởi động cùng backend. Consumer giữ PostgreSQL advisory lock
toàn cục, claim FIFO session, persist từng stage và chỉ commit final papers sau enrichment. Browser
poll detail trong lúc active nên có thể reload mà không mất queue position hoặc progress. Việc chạy
consumer trong API process giúp deployment chỉ cần một Web Service; database lease/stale recovery
vẫn bảo vệ các run bị gián đoạn khi backend restart.
