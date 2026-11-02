# Backend

Backend dùng FastAPI. API handlers chỉ điều phối request/response; business logic nằm trong services và các module tools.

Local dùng `pnpm.cmd dev:backend` (reload) hoặc `pnpm.cmd start:backend` (không reload).
Hai lệnh dùng Uvicorn loop factory `app.core.runtime:create_event_loop`: Windows luôn dùng
Selector để psycopg async hoạt động cả khi không reload; browser subprocesses của Threads
vẫn chạy trên Proactor loop trong thread riêng. Backend health endpoint không đủ để kết
luận worker đang xử lý queue; khi kiểm tra vận hành cần xác minh advisory lock của worker.

