# Kết nối NotebookLM cá nhân từ extension

Mỗi tài khoản CyVerse (admin hoặc member) có một email NotebookLM ưu tiên. Email này có thể sửa ở **Website → Account Settings** hoặc chọn từ danh sách email Google ngay trong popup extension. Email trong hồ sơ chỉ là lựa chọn; backend xác minh lại email với phiên Google thật mỗi khi liệt kê sổ hoặc thêm paper.

## Thao tác trên giao diện

1. Đăng nhập Google và mở `https://notebooklm.google.com/` trên cùng trình duyệt và Chrome profile đang cài extension. Nếu muốn dùng email khác, đăng nhập thêm email đó vào Google/NotebookLM.
2. Mở popup extension, đăng nhập CyVerse bằng bất kỳ role nào. Bấm **Find signed-in Google accounts**, chọn email NotebookLM, rồi bấm **Use this account**. Popup kiểm tra số sổ có thể truy cập. Khi đổi email, lặp lại thao tác này; cũng có thể sửa email ưu tiên trên trang **Account Settings**, sau đó extension sẽ dùng email đó nếu phiên Google tương ứng đang đăng nhập.
3. Trên Google Scholar, bấm **Add to NotebookLM** dưới paper, chọn sổ rồi bấm **Add paper**. Extension lấy phiên Google mới nhất, backend kiểm tra email và quyền truy cập sổ, tìm/tải PDF và upload PDF vào NotebookLM. Theo dõi trạng thái trong hộp thoại đến khi hoàn tất.
4. Nếu phiên Google hết hạn, mở NotebookLM để đăng nhập lại, bấm **Find signed-in Google accounts** trong popup và chọn lại email. Không cần chạy lệnh đăng nhập trên server.

## Vận hành

Deploy migration Alembic `20261001_0005` cùng backend mới, rồi cài lại hoặc cập nhật extension để Chrome cấp quyền `cookies` cho `*.google.com`. Server vẫn cần `AUTH_JWT_SECRET` ổn định giữa các lần khởi động: khóa này dùng để mã hóa phiên tạm trong job; đổi khóa khi job còn chờ sẽ làm các job đó thất bại. Không cần `NOTEBOOKLM_AUTH_JSON` hoặc profile NotebookLM trên server. Cấu hình API extension bằng `VITE_API_URL` trỏ tới backend HTTPS khi triển khai.

Extension chỉ đọc các cookie xác thực Google cần cho NotebookLM, không lưu chúng trong browser storage. Backend nhận cookie qua API có xác thực, dùng để xác minh email và liệt kê sổ. Khi tạo import, phiên được mã hóa trong database cho worker và xóa khi job hoàn tất hoặc thất bại. Chỉ dùng hệ thống qua HTTPS ngoài môi trường local; bảo vệ database, log và khóa JWT như dữ liệu nhạy cảm.

NotebookLM cá nhân chưa có API upload công khai tương đương NotebookLM Enterprise. Adapter hiện dùng `notebooklm-py`, dựa vào giao diện không chính thức của Google; khi Google thay đổi cơ chế đăng nhập hoặc upload có thể cần cập nhật SDK. Không thể xác nhận upload thật nếu chưa thử bằng tài khoản Google và sổ thử nghiệm của người dùng. NotebookLM Enterprise có API `notebooks.sources.uploadFile` chính thức nếu tổ chức chuyển sang dịch vụ đó.
