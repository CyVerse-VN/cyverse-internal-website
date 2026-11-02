# Jobs and scheduling

Threads Scraper dùng queue `tool_runs` hiện có, consumer riêng có advisory lock và
timeout. Consumer chạy trong API lifespan hoặc `python -m app.workers.threads` khi tắt
`THREADS_EMBEDDED_WORKER`. Job queued giữ nguyên khi restart; job running bị gián đoạn
chuyển failed để người dùng chủ động chạy lại; checkpoints bài/bình luận đã lưu vẫn còn.
Đóng frontend không hủy job. Consumer còn xử lý TXT archive/cleanup bền vững trong
database, retry cloud lỗi bằng exponential backoff. Delete active job yêu cầu cancel trước,
xóa Cloudinary trước khi hard-delete database. Xem [Threads tool](tools/threads.md).

Dispatcher nhận yêu cầu chạy nền, worker processor gọi handler phù hợp, và repository lưu vòng đời job. Scheduler chỉ xác định tác vụ đến hạn rồi dispatch job.

NotebookLM import có consumer riêng chạy trong FastAPI lifespan, dùng PostgreSQL advisory lock khác Research để chỉ một consumer xử lý queue này. Mỗi import liên kết một `tool_run`; job được phục hồi sau restart khi chưa bắt đầu upload. Khi kết quả upload không xác định, hệ thống dừng job với `UPLOAD_OUTCOME_UNKNOWN` để người dùng kiểm tra notebook trước khi thử lại.

Phiên Google của mỗi import được mã hóa trong bản ghi job để worker có thể xử lý sau khi request kết thúc. Job hoàn thành hoặc thất bại sẽ xóa bản mã phiên. Nếu phiên Google hết hạn trong lúc chờ hoặc `AUTH_JWT_SECRET` thay đổi, worker đánh dấu job thất bại và người dùng phải kết nối lại từ extension.

