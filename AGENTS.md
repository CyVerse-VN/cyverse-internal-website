# Repository guidelines

- Giữ frontend trong `apps/web` và backend trong `apps/backend`.
- Tách business logic khỏi API handlers và UI components.
- Không commit secret; cập nhật `.env.example` khi thêm biến môi trường.
- Bổ sung test cùng khu vực chức năng được thay đổi.
- Cập nhật tài liệu kiến trúc khi thay đổi ranh giới module hoặc luồng dữ liệu.

