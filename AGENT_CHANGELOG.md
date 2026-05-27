# Agent Change Log - CheckBHYT

File này dùng để các agent và lập trình viên đọc nhanh bối cảnh thay đổi qua nhiều phiên làm việc.

Mỗi khi sửa code, sửa tài liệu, đổi nghiệp vụ, đổi cấu hình triển khai, hoặc phát hiện rủi ro quan trọng, agent phải thêm một mục mới vào đầu phần "Nhật ký thay đổi".

## Quy tắc ghi log cho agent

Khi kết thúc một thay đổi, thêm entry theo mẫu:

```markdown
## YYYY-MM-DD HH:mm - Tên agent/người sửa

### Mục tiêu
- Việc cần xử lý.

### Thay đổi
- File đã sửa và nội dung chính.

### Nghiệp vụ ảnh hưởng
- Luồng nghiệp vụ nào bị ảnh hưởng.
- Định nghĩa/trạng thái nào thay đổi.

### Kiểm tra
- Lệnh/test đã chạy.
- Kết quả.

### Lưu ý cho phiên sau
- Việc còn dang dở.
- Quyết định cần người dùng xác nhận.
- Rủi ro cần theo dõi.
```

Nguyên tắc:

- Ghi ngắn gọn nhưng đủ để agent khác hiểu tại sao sửa.
- Luôn nêu rõ file quan trọng đã đụng tới.
- Nếu thay đổi nghiệp vụ, ghi rõ tác động đến `FAIL`, `LOI`, `WAITING_RESEND`, `RESOLVED`, reset HIS, hoặc quy trình upload file.
- Nếu không chạy được app/test, ghi rõ lý do.
- Không ghi thông tin nhạy cảm như password SQL, IP thật, dữ liệu bệnh nhân thật.

## Quy ước nghiệp vụ hiện tại

- Hướng phát triển chính là LAN WebApp, không phải desktop PySide6.
- `listbh.xlsx` là danh sách hồ sơ đã gửi/được cổng BHYT ghi nhận.
- `HoSoLoiChiTiet.xlsx` là file lỗi chi tiết, thường chỉ import sau khi reset ca chưa đẩy và hệ thống ngoài gửi lại.
- `FAIL` là ca có trong SQL HIS nhưng chưa có trong `listbh.xlsx` và cũng chưa có trong `HoSoLoiChiTiet.xlsx`.
- `LOI` là ca có lỗi chi tiết từ `HoSoLoiChiTiet.xlsx`.
- `WAITING_RESEND` là trạng thái sau khi IT đã sinh/copy SQL reset, đang chờ hệ thống ngoài gửi XML lại.
- `RESOLVED` nên ưu tiên hiểu là đã thấy hồ sơ xuất hiện trong `listbh.xlsx` ở lần đối soát sau, hoặc IT xác nhận thủ công trong trường hợp đặc biệt.
- Script reset cờ xuất XML khác với script mở/khóa bệnh án.
- Script mở khóa bệnh án nội trú:
  - `UNLOCK`: `BenhAn.TrangThai = 'DaXuatVien'`.
  - `CLOSE`: `BenhAn.TrangThai = 'DaThanhToan'`.

## Nhật ký thay đổi

## 2026-05-27 - Codex

### Mục tiêu
- Sửa lỗi KPI "Tổng ca SQL" hiển thị bằng số ca `FAIL`.

### Thay đổi
- `web_app/models.py`: thêm các cột KPI lần đối soát gần nhất vào `AppConfig`.
- `web_app/main.py`:
  - Thêm migration SQLite cho các cột KPI mới.
  - Thêm `save_last_kpis()` để lưu `total/sent/fail/loi` sau mỗi lần đối soát thủ công, đối soát nền, và scheduler.
  - `GET /api/records/kpi` ưu tiên đọc KPI đã lưu thay vì `count(records)`.

### Nghiệp vụ ảnh hưởng
- `Tổng ca SQL` giờ là tổng số dòng SQL HIS trả về sau chuẩn hóa trong lần đối soát gần nhất.
- Không còn phụ thuộc vào số record `FAIL`/`LOI` đang lưu trong SQLite.

### Kiểm tra
- Cần chạy `py_compile` và smoke test KPI.

### Lưu ý cho phiên sau
- `records` hiện vẫn không lưu toàn bộ ca SQL đã gửi thành công; nếu cần export `sql_list.xlsx` đầy đủ thì nên lưu snapshot riêng hoặc bảng `sync_runs/sync_records`.

## 2026-05-27 - Codex

### Mục tiêu
- Tránh timeout khi truy vấn dữ liệu SQL HIS range dài như 1 tháng.
- Làm rõ Bước 3 trên giao diện admin dù chưa có ca `FAIL`.

### Thay đổi
- `web_app/services/his_service.py`:
  - Thêm `SQL_CONNECT_TIMEOUT_SECONDS`, mặc định 60 giây.
  - Thêm `SQL_QUERY_TIMEOUT_SECONDS`, mặc định 0 nghĩa là không giới hạn query timeout pyodbc.
  - Set timeout cho connection/cursor khi test connection, chạy stored procedure và chạy SQL update.
- `web_app/templates/admin.html`:
  - Bước 3 luôn hiển thị.
  - Nút reset bị disable khi chưa có `FAIL`.
  - Hiển thị hint số ca `FAIL` sau đối soát.
- `Project.md`: ghi lại biến môi trường timeout và rủi ro khi query chạy quá lâu.

### Nghiệp vụ ảnh hưởng
- Chạy đối soát range dài ít bị ngắt bởi pyodbc query timeout.
- Quy trình UI rõ hơn: người dùng luôn thấy bước tạo SQL reset HIS, nhưng chỉ thao tác được khi có `FAIL`.

### Kiểm tra
- Cần chạy `py_compile` sau thay đổi.

### Lưu ý cho phiên sau
- Nếu SQL Server/SP bị treo thật, query timeout 0 sẽ chờ rất lâu. Cần cân nhắc thêm nút hủy job hoặc cấu hình timeout trên UI.

## 2026-05-27 - Codex

### Mục tiêu
- Tạo file nhật ký để các agent khác đọc hiểu bối cảnh thay đổi qua nhiều phiên làm việc.
- Đặt quy ước bắt buộc agent phải ghi lại thay đổi sau mỗi lần sửa.

### Thay đổi
- Thêm `AGENT_CHANGELOG.md`.
- Ghi quy tắc format log, quy ước nghiệp vụ hiện tại, và các thay đổi quan trọng đã thực hiện trong phiên này.

### Nghiệp vụ ảnh hưởng
- Không thay đổi logic runtime.
- Tăng khả năng bàn giao giữa các phiên làm việc/agent.

### Kiểm tra
- Không cần chạy test vì chỉ thêm tài liệu.

### Lưu ý cho phiên sau
- Khi agent sửa code hoặc nghiệp vụ, phải thêm entry mới lên đầu phần "Nhật ký thay đổi".

## 2026-05-27 - Codex

### Mục tiêu
- Sửa quy trình webapp theo nghiệp vụ mới: đối soát `listbh.xlsx` trước, tìm `FAIL`, reset HIS, sau đó mới import file lỗi chi tiết nếu cổng trả lỗi.

### Thay đổi
- `Project.md`: viết lại theo hướng LAN WebApp là sản phẩm chính.
- `web_app/main.py`: thêm cờ `include_errors`; mặc định không dùng `HoSoLoiChiTiet.xlsx` khi đối soát ban đầu.
- `web_app/templates/admin.html`: chỉnh UI thành các bước:
  - Bước 1 tải `listbh.xlsx`.
  - Bước 2 đối soát SQL HIS với `listbh`.
  - Bước 3 sinh SQL reset HIS cho ca `FAIL`.
  - Bước 4 mới tải file lỗi sau khi gửi lại.
- `web_app/services/compare_service.py`: nếu ca đã có lỗi chi tiết thì đóng nhóm `FAIL` cũ và tạo/giữ nhóm `LOI`.
- `web_app/templates/department.html`: thêm trạng thái `WAITING_RESEND`.

### Nghiệp vụ ảnh hưởng
- `FAIL` được định nghĩa là ca có trong SQL HIS nhưng chưa có trong `listbh.xlsx` và chưa có trong file lỗi chi tiết.
- File lỗi chi tiết chỉ được dùng khi IT chủ động bật tùy chọn đối soát kèm lỗi.
- Sau reset, ca chuyển `WAITING_RESEND`, chưa chuyển ngay `RESOLVED`.

### Kiểm tra
- Chạy `python -m py_compile` cho backend webapp.
- Chạy smoke test SQLite in-memory cho luồng `FAIL -> LOI -> RESOLVED`.

### Lưu ý cho phiên sau
- Cần cài dependency bằng `pip install -r requirements.txt` trước khi chạy webapp thực tế, vì Python hệ thống hiện thiếu `fastapi`.

## 2026-05-27 - Codex

### Mục tiêu
- Bổ sung script mở/khóa bệnh án cho nhóm lỗi chi tiết cần IT trả hồ sơ về khoa sửa.

### Thay đổi
- `web_app/services/his_service.py`: thêm `build_benhan_unlock_sql(keys, action_type)`.
- `web_app/main.py`: `POST /api/records/{id}/toggle-his-unlock` sinh script:
  - `UNLOCK`: đưa `BenhAn.TrangThai` về `DaXuatVien`.
  - `CLOSE`: đưa `BenhAn.TrangThai` về `DaThanhToan`.
- `web_app/templates/admin.html`: nút mở khóa và khóa lại đều mở modal SQL để IT copy chạy SSMS.
- `Project.md`: cập nhật quy trình lỗi chi tiết và phân biệt script mở/khóa bệnh án với script reset cờ xuất XML.

### Nghiệp vụ ảnh hưởng
- Mở khóa bệnh án hiện áp dụng cho ca `Nội trú` theo `BenhAn.SoBenhAn`.
- Đây là script trạng thái bệnh án, không phải script reset cờ gửi XML.

### Kiểm tra
- Chạy `python -m py_compile`.
- Test sinh script mẫu cho `UNLOCK` và `CLOSE`.

### Lưu ý cho phiên sau
- Nếu cần hỗ trợ ngoại trú cho mở/khóa tương tự, phải xác nhận bảng/cột trạng thái tương ứng trước khi code.

## 2026-05-27 - Codex

### Mục tiêu
- Sửa lỗi nhánh báo thiếu dependency trong `web_app/run.py`.

### Thay đổi
- `web_app/run.py`: chuyển thông báo thiếu thư viện sang ASCII để tránh crash encoding trên Windows console CP1252.

### Nghiệp vụ ảnh hưởng
- Không ảnh hưởng nghiệp vụ.

### Kiểm tra
- Chạy thử `python web_app/run.py --port 8011` khi thiếu `fastapi`; chương trình in đúng hướng dẫn cài dependency.

### Lưu ý cho phiên sau
- Sau khi tạo `.venv` và cài `requirements.txt`, nên chạy lại app để kiểm tra UI bằng trình duyệt.
