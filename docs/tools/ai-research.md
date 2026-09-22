# AI Research Tool

AI Research Tool là một hàng đợi tìm paper dùng chung cho toàn bộ member CyVerse. Mỗi query tạo
một session độc lập, mặc định public. Public session được mọi user đã đăng nhập xem; private session
chỉ owner và admin truy cập. Owner/admin có thể đổi visibility và hủy session đang queued/running.

## Pipeline

Queue consumer chạy trong FastAPI lifespan và xử lý đúng một research session tại một thời điểm theo
FIFO: planning, retrieval từ Semantic Scholar/arXiv/OpenAlex, deduplication, filtering,
deterministic ranking, AI reranking, diversity, Vietnamese enrichment và final persistence. Các
nguồn chạy đồng thời bên trong một session nhưng vẫn tuân thủ retry/rate limit riêng.
Retry dùng khoảng chờ tối thiểu riêng cho từng source. AI reranking chạy theo batch nhỏ, kiểm tra đủ
paper ID và retry output sai contract trước khi chuyển model fallback; enrichment cũng từ chối cả batch
nếu thiếu paper hoặc summary/`why_read_vi` không phải tiếng Việt có dấu.

Candidate, abstract, source payload, rejected record, prompt và stage ranking chỉ tồn tại trong bộ
nhớ. Database chỉ nhận final paper trong cùng transaction đánh dấu run hoàn tất. Nếu một nguồn lỗi,
pipeline có thể hoàn thành với warning; nếu không còn paper đã được enrichment hợp lệ, run thất bại
và không lưu paper.

Mỗi final paper có summary tiếng Việt và từ một đến ba mục `why_read_vi`, với
`analysis_basis=abstract`. `pdf_url` chỉ chứa direct PDF; UI fallback sang `landing_url` khi cần.

## Cấu hình user

Mặc định dùng ba nguồn, ba năm gần nhất, 50 raw paper mỗi nguồn và tối đa 20 final paper. User có thể
chọn source, time range, publication type, language, open access, yêu cầu abstract, raw cap và result
limit. Backend giới hạn 100 raw paper mỗi nguồn, 300 tổng và 50 final paper. Các model, weight,
timeout, retry và rate limit được quản lý bằng typed config tại
`apps/backend/src/app/tools/research/config.py`; API key vẫn chỉ lấy từ backend environment.

Frontend lưu preference cục bộ theo config schema version. Session, tiến trình và paper là dữ liệu
server-side và vẫn tồn tại khi đóng hoặc reload trang.

Session rail hiển thị menu quản lý khi hover/focus. Owner/admin có thể đổi title hoặc xóa mềm session;
session active được yêu cầu hủy trước khi ẩn khỏi lịch sử. Time range có preset theo từng năm bắt đầu
đến năm hiện tại, bên cạnh lựa chọn all years và custom range.
