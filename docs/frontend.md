# Frontend

Frontend dùng Next.js App Router (Next.js 16, React 19) kết hợp Tailwind CSS v4.

## Cấu trúc thư mục

- **Routes**: Nằm trong `src/app`.
- **UI Components**: Các component nền tảng chuẩn **shadcn/ui** (dựa trên Radix UI primitives và Lucide icons) đặt tại `src/components/ui/`.
- **Layout & Shared UI**: Đặt tại `src/components/layout/` và `src/components/shared/`.
- **Feature Logic**: Logic theo miền nghiệp vụ nằm trong `src/features/`.
- **Utilities**: Hàm dùng chung như `cn()` đặt trong `src/lib/utils.ts`.

## Hệ thống thư viện UI

### Đợt 1: Đã cài đặt và đang sử dụng (Cốt lõi & Gọn nhẹ)

| Nhóm | Thư viện | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Styling** | `tailwindcss` (v4), `@tailwindcss/postcss` | Nền tảng utility styling, CSS variables, transitions. |
| **UI Components** | `shadcn/ui` (Radix UI primitives) | Button, Badge, Card, Dialog, DropdownMenu, Avatar, Skeleton. |
| **Icons** | `lucide-react` | Bộ icon SVG vector sắc nét, đồng bộ cho toàn bộ website. |
| **Theme** | `next-themes` | Hỗ trợ Dark Mode / Light Mode / System không bị FOUC. |
| **Toast** | `sonner` | Toast notification gọn nhẹ (`toast.success()`, `toast.error()`). |
| **Form & Validation** | `react-hook-form`, `zod`, `@hookform/resolvers` | Quản lý form hiệu năng cao, validate schema kiểu dữ liệu type-safe. |

### Đợt 2: Lộ trình cài đặt khi phát triển tính năng tương ứng (Khi cần)

Để đảm bảo quy tắc giữ ứng dụng luôn gọn nhẹ và chỉ cài package khi có ca sử dụng thực tế, các thư viện sau được ghi nhận để bổ sung theo nhu cầu tính năng:

| Thư viện | Khi nào cài | Mục đích |
| :--- | :--- | :--- |
| **`recharts`** | Khi phát triển màn hình Analytics / Model Metrics | Trực quan hóa số lượng tác vụ deepfake, thống kê độ chính xác mô hình AI. |
| **`@tanstack/react-table`** | Khi bảng dữ liệu cần sorting/filtering phức tạp | Xử lý dữ liệu bảng nâng cao phía Client (dataset lớn, ẩn hiện cột tùy biến). |
| **`date-fns`** | Khi cần DateRangePicker hoặc so sánh thời gian | Xử lý format ngày tháng dạng tương đối ("2 giờ trước") và chọn khoảng ngày. |
| **`motion`** *(framer-motion)* | Cân nhắc kỹ | Chỉ cài khi cần hiệu ứng kéo thả (drag & drop) hoặc chuyển cảnh layout cực phức tạp. |



