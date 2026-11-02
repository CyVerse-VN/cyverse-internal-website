# Quản lý Rate Limit AI (Gemini & Groq)

Tài liệu này lưu trữ thông số giới hạn lưu lượng (Rate Limits) chính thức của các model **Google Gemini** và **Groq**, cùng công thức điều phối tần suất gọi (pacing) để bảo vệ hệ thống tránh bị lỗi `HTTP 429 Too Many Requests` hoặc bị khóa/ban API key khi treo tool hoặc cào dữ liệu liên tục.

Mã nguồn định nghĩa và tính toán tự động: [`apps/backend/src/app/core/ai_rate_limits.py`](file:///d:/Projects/cyverse/cyverse-internal-website/apps/backend/src/app/core/ai_rate_limits.py).

---

## 1. Bảng thông số Rate Limit chính thức

### Google Gemini / Gemma Models

| Model | Phân loại (Category) | RPM (Requests/phút) | TPM (Tokens/phút) | RPD (Requests/ngày) |
| :--- | :--- | :--- | :--- | :--- |
| **Gemma 4 26B** | Other models | 30 | 16,000 (16K) | 14,400 (14.4K) |
| **Gemma 4 31B** | Other models | 30 | 16,000 (16K) | 14,400 (14.4K) |

---

### Groq Models

| MODEL ID | RPM | RPD | TPM | TPD | ASH (Audio s/h) | ASD (Audio s/d) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `canopylabs/orpheus-arabic-saudi` | 10 | 100 | 1.2K (1,200) | 3.6K (3,600) | — | — |
| `canopylabs/orpheus-v1-english` | 10 | 100 | 1.2K (1,200) | 3.6K (3,600) | — | — |
| `meta-llama/llama-prompt-guard-2-22m` | 30 | 14.4K (14,400) | 15K (15,000) | 500K (500,000) | — | — |
| `meta-llama/llama-prompt-guard-2-86m` | 30 | 14.4K (14,400) | 15K (15,000) | 500K (500,000) | — | — |
| `openai/gpt-oss-120b` | 30 | 1K (1,000) | 8K (8,000) | 200K (200,000) | — | — |
| `openai/gpt-oss-20b` | 30 | 1K (1,000) | 8K (8,000) | 200K (200,000) | — | — |
| `openai/gpt-oss-safeguard-20b` | 3 | 1K (1,000) | 2K (2,000) | 200K (200,000) | — | — |
| `qwen/qwen3.8-27b` | 30 | 1K (1,000) | 8K (8,000) | 200K (200,000) | — | — |
| `whisper-large-v3` | 20 | 2K (2,000) | — | — | 7.2K (2 giờ) | 28.8K (8 giờ) |
| `whisper-large-v3-turbo` | 20 | 2K (2,000) | — | — | 7.2K (2 giờ) | 28.8K (8 giờ) |

*Ghi chú các thuật ngữ:*
- **RPM**: Requests Per Minute (Số yêu cầu tối đa mỗi phút).
- **RPD**: Requests Per Day (Số yêu cầu tối đa mỗi ngày).
- **TPM**: Tokens Per Minute (Số lượng token tối đa mỗi phút).
- **TPD**: Tokens Per Day (Số lượng token tối đa mỗi ngày).
- **ASH**: Audio Seconds per Hour (Thời lượng audio tính bằng giây tối đa mỗi giờ).
- **ASD**: Audio Seconds per Day (Thời lượng audio tính bằng giây tối đa mỗi ngày).

---

## 2. Nguyên tắc tính toán tránh bị Rate Limit Ban

Để đảm bảo hệ thống chạy mượt mà, không bị nhà cung cấp phạt HTTP 429 hoặc khóa quyền truy cập:

### A. Ngưỡng sử dụng an toàn (Safety Utilization Buffer: 80%)
Hệ thống không bao giờ gọi sát 100% trần hạn mức. Thay vào đó, áp dụng hệ số sử dụng an toàn **80%** (`utilization = 0.80`), giữ lại 20% biên độ an toàn cho độ trễ mạng và sai số đồng hồ (clock drift).

$$\text{Safe RPM} = \text{RPM} \times 0.80$$

### B. Công thức tính thời gian chờ giữa 2 yêu cầu liên tiếp (Request Interval)
Khoảng cách tối thiểu (tính bằng giây) giữa 2 lần gọi API cùng một model:

$$\text{Interval (giây)} = \frac{60}{\text{Safe RPM}} + \text{margin\_seconds}$$

*(Với `margin_seconds = 0.15s`)*

**Bảng tính thời gian giãn cách thực tế cho các nhóm model:**
- **Nhóm RPM = 30** (`qwen/qwen3.8-27b`, `openai/gpt-oss-20b`, `Gemma 4 26B/31B`):
  $$\text{Interval} = \frac{60}{30 \times 0.8} + 0.15 = 2.5 + 0.15 = \mathbf{2.65\text{ giây}}$$
  *(Đây chính là lý do công cụ cào dữ liệu Threads cài đặt mặc định `min_delay_seconds: 2.0` và `max_delay_seconds: 4.0` — hoàn toàn nằm trong vùng an toàn tuyệt đối).*

- **Nhóm RPM = 20** (`whisper-large-v3`, `whisper-large-v3-turbo`):
  $$\text{Interval} = \frac{60}{20 \times 0.8} + 0.15 = 3.75 + 0.15 = \mathbf{3.90\text{ giây}}$$

- **Nhóm RPM = 10** (`canopylabs/orpheus-*`):
  $$\text{Interval} = \frac{60}{10 \times 0.8} + 0.15 = 7.5 + 0.15 = \mathbf{7.65\text{ giây}}$$

- **Nhóm RPM = 3** (`openai/gpt-oss-safeguard-20b`):
  $$\text{Interval} = \frac{60}{3 \times 0.8} + 0.15 = 25.0 + 0.15 = \mathbf{25.15\text{ giây}}$$

---

## 3. Quản lý Token Per Minute (TPM) và Giới hạn ngày (RPD/TPD)

1. **Kiểm soát TPM**:
   - Model `qwen/qwen3.8-27b` và `openai/gpt-oss-20b` có giới hạn TPM là 8,000.
   - Khi chạy phân tích keyword hoặc trích xuất dữ liệu, cấu hình `max_tokens` của mỗi prompt được giới hạn từ **1,200 – 1,800 tokens**.
   - Với khoảng cách 2.65s giữa các request, trong 1 phút tối đa chỉ phát sinh ~20 requests $\times$ 300 token trung bình = ~6,000 tokens (dưới mức an toàn 6,400 TPM = $8,000 \times 80\%$).

2. **Kiểm soát RPD (Hạn mức ngày)**:
   - Khi treo tool cào dữ liệu qua đêm hoặc chạy ngầm lâu dài, cần lưu ý hạn mức RPD:
     - `qwen/qwen3.8-27b`: 1,000 requests/ngày.
     - `Gemma 4 26B/31B`: 14,400 requests/ngày.
     - `canopylabs/orpheus-*`: 100 requests/ngày.
   - Nếu một tác vụ phân tích keyword cần nhiều hơn 1,000 lần gọi/ngày, hệ thống sẽ tự động chuyển đổi sang Gemma hoặc luân phiên các model fallback trong danh sách routing.
