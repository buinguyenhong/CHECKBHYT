# Project: CheckBHYT LAN WebApp

## 1. Định hướng dự án

CheckBHYT hiện được định hướng là **LAN WebApp nội bộ bệnh viện** phục vụ đối soát dữ liệu BHYT sau khi hệ thống HIS/EMR/BHYT đã xuất và gửi XML lên cổng BHYT.

Ứng dụng không trực tiếp tạo XML và không trực tiếp gửi XML. Vai trò chính của hệ thống là:

- Lấy danh sách hồ sơ đáng lẽ phải gửi từ SQL Server HIS.
- Đọc danh sách hồ sơ đã gửi/đã được cổng hoặc phần mềm BHYT ghi nhận từ file `listbh.xlsx`.
- Đọc file lỗi chi tiết từ cổng BHYT, thường là `HoSoLoiChiTiet.xlsx`, sau khi các ca cần gửi lại đã được reset và hệ thống gửi XML bên ngoài gửi lại.
- Đối soát theo khóa nghiệp vụ `MA_LK`.
- Phân loại hồ sơ thành đã gửi, lỗi chi tiết, hoặc chưa gửi thành công.
- Lưu trạng thái xử lý vào SQLite nội bộ của webapp.
- Cho phòng IT và các khoa lâm sàng phối hợp xử lý lỗi theo trạng thái.
- Sinh câu lệnh SQL reset cờ xuất dữ liệu để hệ thống gửi XML bên ngoài gửi lại.
- Xuất báo cáo Excel phục vụ kiểm tra và lưu trữ.

Bản desktop PySide6 cũ vẫn còn trong repo để tham chiếu nghiệp vụ:

- `main.py`
- `main02022026.py`
- `KiemTraGuiBHYT.spec`

Tuy nhiên hướng phát triển chính từ hiện tại là:

- `web_app/main.py`
- `web_app/run.py`
- `web_app/services/*`
- `web_app/templates/*`
- `LaunchWebBHYT.py`

## 2. Mô hình triển khai thực tế

Webapp được thiết kế để chạy trong **mạng LAN local, không phụ thuộc internet khi vận hành hằng ngày**.

Mô hình máy chủ dự kiến:

- Một máy Windows đặt trong bệnh viện.
- Máy có 2 card mạng:
  - Card mạng local/LAN bệnh viện: dùng cho các khoa truy cập webapp và kết nối SQL Server HIS.
  - Card mạng internet: dùng khi cần cài đặt thư viện, cập nhật mã nguồn, hoặc hỗ trợ từ xa nếu được phép.
- Khi vận hành chính thức, các máy khoa truy cập qua địa chỉ LAN, ví dụ `http://<IP_LAN_MAY_CHU>:8000`.
- Dữ liệu nghiệp vụ và file upload nằm nội bộ trên máy chủ.
- Không cần client cài phần mềm, chỉ cần trình duyệt trong mạng LAN.

Điểm cần cấu hình ở tầng hạ tầng:

- Máy chủ phải ping/kết nối được SQL Server HIS qua LAN.
- Firewall Windows phải mở port webapp, mặc định `8000`, cho mạng nội bộ.
- Các máy khoa chỉ cần truy cập IP LAN của máy chủ, không dùng IP internet.
- Nếu máy có nhiều card mạng, cần xác định đúng IP LAN để thông báo cho các khoa.
- Không public webapp ra internet nếu chưa bổ sung bảo mật tương ứng.

## 3. Công nghệ sử dụng

Backend webapp:

- Python 3.10+; khuyến nghị Python 3.13.x.
- FastAPI.
- Uvicorn.
- SQLAlchemy.
- SQLite để lưu trạng thái nội bộ webapp.
- pandas, openpyxl để xử lý Excel.
- pyodbc để kết nối SQL Server HIS.
- Jinja2 templates cho giao diện HTML.

Desktop/launcher:

- `LaunchWebBHYT.py`: launcher Tkinter để cài dependency, chọn thư mục, chọn port, khởi động/dừng server nền.
- PySide6 vẫn tồn tại cho bản desktop cũ, không phải hướng phát triển chính.
- PyInstaller có thể dùng khi cần đóng gói công cụ phụ trợ.

File quan trọng:

- `requirements.txt`: danh sách thư viện.
- `INSTALL_WEB.md`: hướng dẫn triển khai webapp.
- `web_app/run.py`: entry point chạy server LAN.
- `web_app/main.py`: FastAPI app, routes, API, scheduler, seed dữ liệu mặc định, tích hợp trực tiếp XML Validator chạy nền qua BackgroundTasks, API tải Client RPA Runner.
- `web_app/database.py`: SQLite engine/session.
- `web_app/models.py`: models dữ liệu nội bộ.
- `web_app/auth.py`: đăng nhập và phân quyền.
- `web_app/services/his_service.py`: kết nối SQL HIS, cache, chuẩn hóa SQL, sinh reset SQL.
- `web_app/services/excel_service.py`: đọc `listbh.xlsx`, `HoSoLoiChiTiet.xlsx`.
- `web_app/services/compare_service.py`: logic đối soát và lưu trạng thái.
- `web_app/services/portal_automation.py`: module Playwright RPA tự động hóa Cổng BHYT chạy trên Server.
- `client_runner/`: bộ công cụ RPA Runner chạy trực tiếp trên máy trạm Client PC (`client_agent.py`, `Cai_Dat_May_Tram.bat`, `Chay_RPA_May_Tram.bat`).
- `web_app/xml_validator/`: thư mục chứa mô-đun đối soát và kiểm tra cấu trúc hồ sơ XML BHYT (in-process).
  - `xml_parser.py`: Đọc tệp XML, giải mã Container XML ký số và gom nhóm theo MA_LK.
  - `rule_engine.py`: Chứa 26 quy tắc nghiệp vụ BHYT kiểm tra lỗi.
  - `report_generator.py`: Sinh báo cáo tổng hợp lỗi Excel và JSON kết quả.
- `web_app/templates/admin.html`: giao diện phòng IT (bao gồm Tự động hóa Client RPA / Server RPA và Tab kiểm tra XML BHYT).
- `web_app/templates/department.html`: giao diện khoa lâm sàng.
- `web_app/templates/login.html`: đăng nhập.


File sinh trong runtime:

- `web_app/app_state.db` hoặc `app_state.db` tùy thư mục chạy: SQLite lưu trạng thái.
- `web_app/uploaded_files/` hoặc `uploaded_files/`: file Excel upload và file export.
- `web_app/cache_sql/` hoặc `cache_sql/`: cache dữ liệu SQL HIS.
- `launcher_config.json`: cấu hình launcher.

Lưu ý: do một số đường dẫn hiện dùng relative path, nên nên chạy bằng `python web_app/run.py` hoặc launcher để `run.py` tự chuyển working directory vào `web_app`.

## 4. Tài khoản và phân quyền

Webapp hiện có 2 vai trò:

- `admin`: phòng IT/quản trị hệ thống.
- `user`: tài khoản khoa/phòng lâm sàng.

Tài khoản admin mặc định được tạo khi app chạy lần đầu:

- Username: `admin`
- Password: `adminBHYT2026`

Việc cần làm khi triển khai thật:

- Đăng nhập admin lần đầu.
- Tạo tài khoản riêng cho từng khoa.
- Map chính xác `department_name` với tên khoa trả về từ stored procedure HIS, vì khoa chỉ thấy hồ sơ có `Record.ten_khoa == User.department_name`.
- Nên bổ sung chức năng đổi mật khẩu admin mặc định hoặc đổi trực tiếp trong DB trước khi dùng chính thức.

## 5. Nguồn dữ liệu đầu vào

### 5.1. SQL Server HIS

Webapp lấy danh sách hồ sơ đáng lẽ phải gửi bằng 2 stored procedure:

- Ngoại trú:
  - `dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NgoaiTru_Optimized`
- Nội trú:
  - `dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NoiTru_Optimized`

Tham số truyền vào:

- `@TuNgay`
- `@DenNgay`

Định dạng ngày truyền vào SQL: `yyyyMMdd`, ví dụ `20260527`.

Cột bắt buộc từ SP ngoại trú:

- `TenBenhNhan`
- `SoBHYT`
- `Column4`
- `SoPhieuThanhToanNgoaiTru`
- `NgayRa`
- `Tongcong`: Tổng số tiền chi phí của ca bệnh.
- `QuyBHYT_ChiTra`: Tổng số tiền quỹ BHYT chi trả cho ca bệnh.

Cột bắt buộc từ SP nội trú:

- `TenBenhNhan`
- `SoBHYT`
- `SoPhieu_BA`
- `khoadieutri`
- `NgayRa`
- `Tongcong`: Tổng số tiền chi phí của ca bệnh.
- `QuyBHYT_ChiTra`: Tổng số tiền quỹ BHYT chi trả cho ca bệnh.

### 5.2. File danh sách đã gửi BHYT

File upload trên tab admin: `listbh.xlsx`.

Cột mặc định:

- `Mã liên kết`: mã liên kết hồ sơ.
- `Ngày ra`: ngày ra để lọc theo khoảng đối soát.

Khi đọc file, hệ thống chuẩn hóa thành:

- `MA_LK`
- `_ngay`

Ý nghĩa nghiệp vụ: file này đại diện cho danh sách hồ sơ đã gửi hoặc đã được cổng/phần mềm BHYT ghi nhận.

### 5.3. File lỗi chi tiết BHYT

File upload trên tab admin: `HoSoLoiChiTiet.xlsx`.

Cột bắt buộc:

- `MA_LK`

Cột tùy chọn:

- `MALOI`
- `MOTALOI`
- `Ngày ra`

Nếu thiếu `MALOI` hoặc `MOTALOI`, hệ thống tự tạo cột rỗng.

Ý nghĩa nghiệp vụ: đây là danh sách hồ sơ cổng BHYT trả lỗi sau khi hệ thống bên ngoài đã gửi hồ sơ lên cổng. Trong quy trình chuẩn, file này thường xuất hiện sau bước đối soát `listbh`, reset các ca chưa đẩy, và gửi lại.

## 6. Chuẩn hóa dữ liệu nghiệp vụ

Khóa chính xuyên suốt hệ thống là `MA_LK`.

Quy tắc chuẩn hóa `MA_LK`:

- Nếu null/NaN thì đưa về chuỗi rỗng.
- Ép sang chuỗi.
- `strip()` khoảng trắng đầu cuối.
- Thay `_CC` bằng `/CC`.

Ngoại trú:

- `Loại ca` = `Ngoại trú`
- `MA_LK` = `Column4`
- `Họ tên` = `TenBenhNhan`
- `Mã thẻ` = `SoBHYT`
- `Tên khoa` = `Khám bệnh`
- `Mã y tế` = `SoPhieuThanhToanNgoaiTru`
- `Ngày ra viện` = `NgayRa`

Nội trú:

- `Loại ca` = `Nội trú`
- `MA_LK` = `SoPhieu_BA`
- Nếu `SoPhieu_BA` bắt đầu bằng `A`, bỏ chữ `A` đầu trước khi so sánh/reset.
- `Họ tên` = `TenBenhNhan`
- `Mã thẻ` = `SoBHYT`
- `Tên khoa` = `khoadieutri`
- `Mã y tế` = rỗng
- `Ngày ra viện` = `NgayRa`

Sau khi ghép ngoại trú và nội trú:

- Bỏ dòng không có `MA_LK`.
- Chuẩn hóa lại `MA_LK`.
- Bỏ trùng theo `MA_LK`, giữ dòng đầu tiên.

## 7. Mô hình dữ liệu SQLite nội bộ

SQLite lưu trạng thái vận hành của webapp, không thay thế SQL Server HIS.

Các bảng chính:

- `users`: tài khoản admin/khoa.
- `app_config`: cấu hình kết nối SQL Server HIS, SP, tự đồng bộ, và thông tin đăng nhập tự động hóa Cổng BHYT (`portal_url`, `portal_ma_cskcb`, `portal_username`, `portal_password`).
- `records`: hồ sơ đối soát và trạng thái xử lý hiện tại (gồm `ma_lk`, `ho_ten`, `ma_the`, `ten_khoa`, `loai_ca`, `ngay_ra_vien`, `tong_tien`, `tien_bhyt`, `maloi`, `motaloi`, `type_group`, `status`, `note`, `unlock_status`).
- `record_logs`: nhật ký lịch sử thay đổi trạng thái/ghi chú từng ca.
- `error_definitions`: danh mục hướng dẫn lỗi theo `MALOI` và từ khóa trong `MOTALOI`.
- `error_history_archive`: cơ sở dữ liệu lưu trữ vĩnh viễn tất cả các dòng lỗi từng phát sinh qua các đợt đối soát (lưu `ma_lk`, `ho_ten`, `ma_the`, `ten_khoa`, `loai_ca`, `tong_tien`, `tien_bhyt`, `maloi`, `motaloi`, `thang_doi_soat`, `status`, `first_detected_at`, `resolved_at`, `resolved_by`, `note_history`).

> **Quy tắc tổng hợp tài chính theo tháng:** Khi tính tổng chi phí (`tong_tien`) và tiền BHYT chi trả (`tien_bhyt`), hệ thống luôn gom nhóm và tính dựa trên **số ca bệnh duy nhất (`MA_LK`)**, không tính lặp theo dòng lỗi (một ca bệnh có thể phát sinh nhiều dòng lỗi khác nhau nhưng số tiền chỉ được tính một lần cho ca bệnh đó).

Trạng thái `Record.status`:

- `PENDING`: đang chờ xử lý.
- `WAITING_REVIEW`: khoa đã nhập ghi chú/sửa lỗi và gửi IT duyệt.
- `WAITING_RESEND`: IT đã sinh/copy SQL reset, đang chờ hệ thống bên ngoài gửi XML lại.
- `RESOLVED`: lần đối soát sau đã thấy hồ sơ xuất hiện trong `listbh`, hoặc IT chủ động xác nhận hoàn tất thủ công.

Nhóm `Record.type_group`:

- `FAIL`: có trong SQL HIS nhưng chưa có trong danh sách bảo hiểm đã gửi (`listbh`) và cũng chưa có trong danh sách lỗi chi tiết (`HoSoLoiChiTiet.xlsx`).
- `LOI`: có lỗi chi tiết từ `HoSoLoiChiTiet.xlsx`.

Trạng thái mở khóa HIS:

- `NORMAL`: bình thường.
- `UNLOCKED`: IT đã trả về khoa/mở khóa để khoa sửa.

## 8. Quy trình đang thực thi hiện tại trong code

Đây là quy trình thực tế hiện đang chạy theo code trong `web_app/main.py` và `web_app/services/*`.

### 8.1. Khởi động hệ thống

1. IT chạy:

```powershell
python web_app/run.py
```

2. `run.py`:

- Chuyển working directory vào `web_app`.
- Đọc port từ `--port` hoặc biến môi trường `BHYT_PORT`, mặc định `8000`.
- In IP LAN dò được.
- Chạy Uvicorn với `host="0.0.0.0"`.

3. `web_app/main.py` khi import:

- Tạo bảng SQLite nếu chưa có.
- Tự migrate nhẹ một số cột mới trong `app_config` và `records`.
- Seed admin mặc định nếu chưa có.
- Seed cấu hình mặc định nếu chưa có.
- Seed danh mục lỗi mẫu nếu chưa có.
- Khởi động scheduler tự đồng bộ khi FastAPI startup.

### 8.2. Đăng nhập và điều hướng

1. Người dùng truy cập `/`.
2. Nếu chưa có cookie session, chuyển về `/login`.
3. Sau khi login:

- Nếu role `admin`, chuyển `/admin`.
- Nếu role `user`, chuyển `/department`.

Hiện session cookie lưu username trong cookie `checkbh_session`.

### 8.3. Cấu hình HIS

Phòng IT vào tab admin `Đồng bộ & Đối soát`:

1. Chọn ODBC driver.
2. Nhập server SQL HIS.
3. Nhập database.
4. Chọn `Windows Auth` hoặc `SQL Auth`.
5. Nhập user/password nếu dùng SQL Auth.
6. Nhập SP ngoại trú/nội trú nếu khác mặc định.
7. Bấm `Lưu cấu hình`.
8. Bấm `Test kết nối SQL Server`.

API liên quan:

- `GET /api/config`
- `POST /api/config`
- `GET /api/config/drivers`
- `POST /api/config/test-connection`

Password HIS hiện được lưu dạng XOR/base64 trong SQLite. Đây chỉ là che giấu cơ bản, chưa phải mã hóa mạnh.

### 8.4. Upload file đối soát

Admin upload:

- `listbh.xlsx` qua `POST /api/upload/listbh`.
- `HoSoLoiChiTiet.xlsx` qua `POST /api/upload/loi`.

Hiện file được lưu cố định:

- `uploaded_files/listbh.xlsx`
- `uploaded_files/HoSoLoiChiTiet.xlsx`

Nếu upload lại, file cũ bị ghi đè.

Khi upload file lỗi, hệ thống còn cố gắng ghép ngay vào ngày đối soát gần nhất đang có trong SQLite và chuyển các record tương ứng sang nhóm `LOI`.

### 8.4.1. Module Tự động hóa Cổng BHYT Bán tự động (Playwright RPA)

Hệ thống tích hợp module RPA (`web_app/services/portal_automation.py`) dựa trên Playwright để tự động hóa 2 luồng độc lập:

1. **Luồng B (Đối soát B - Danh sách đã gửi)**:
   - Tự động mở trình duyệt Chromium, tự điền Mã CSKCB, Tên đăng nhập, Mật khẩu. Người dùng chỉ cần gõ mã Captcha (hoặc tự động bỏ qua nếu session cookie `portal_storage_state.json` còn hiệu lực).
   - Điều hướng tới `Hồ sơ XML -> Danh sách đề nghị thanh toán`.
   - Chọn trạng thái `Đã đề nghị thanh toán`, bấm `Tìm kiếm`.
   - Kích hoạt `Xuất Excel`, lưu tự động về `uploaded_files/listbh.xlsx`.
   - Tự động kích hoạt đối soát B với CSDL HIS để tìm các ca FAIL và sinh câu lệnh SQL reset.

2. **Luồng C (Đối soát C - Danh sách lỗi chi tiết)**:
   - Tự động điều hướng tới `Hồ sơ XML -> Quyết định 3176/QĐ-BYT -> Kết quả gửi hồ sơ XML`.
   - Lọc theo khoảng ngày và hiển thị 100 bản ghi/trang, lọc các gói có lỗi.
   - Duyệt qua từng trang, click mở chi tiết từng gói lỗi và xuất file Excel lỗi chi tiết về thư mục tạm `uploaded_files/temp_errors/`.
   - Tự động gom toàn bộ các file Excel thành 1 file duy nhất `uploaded_files/HoSoLoiChiTiet.xlsx` theo đúng cấu trúc chuẩn.
   - Tự động kích hoạt đối soát C (kèm file lỗi chi tiết) với CSDL HIS để phân loại lỗi, phân khoa phòng và lưu trữ vĩnh viễn vào `error_history_archive`.

API liên quan:
- `POST /api/automation/flow-b`
- `POST /api/automation/flow-c`
- `GET /api/automation/logs`

### 8.5. Chạy đồng bộ và đối soát thủ công

Admin chọn `Từ ngày`, `Đến ngày`, bấm kích hoạt đồng bộ.

API hiện dùng:

- `POST /api/sync/start`
- Frontend poll `GET /api/sync/status`.

Luồng nền `run_sync_in_background()`:

1. Đọc cấu hình HIS từ SQLite.
2. Giải mã password HIS.
3. Gọi `his_service.fetch_his_data(cfg, from_date, to_date)`.
4. `fetch_his_data()` dùng cache SQL nếu có.
5. Nếu không có cache hoặc cache thiếu range, gọi 2 stored procedure HIS.
6. Chuẩn hóa thành dataframe `df_sql`.
7. Đọc `uploaded_files/listbh.xlsx` nếu có.
8. Lọc `listbh` theo khoảng ngày.
9. Chỉ đọc `uploaded_files/HoSoLoiChiTiet.xlsx` nếu IT bật tùy chọn dùng file lỗi trong lần đối soát đó.
10. Nếu không bật tùy chọn file lỗi, hệ thống bỏ qua file lỗi dù file đang tồn tại trên máy chủ để tránh dùng nhầm file cũ.
11. Gọi `compare_service.process_comparison()`.
12. Lưu hoặc cập nhật records vào SQLite.
13. Cập nhật progress/log cho UI.

Ngày đối soát lưu vào record hiện là `datetime.date.today()`, tức ngày chạy đối soát, không phải `from_date` hoặc `to_date`.

### 8.6. Logic phân loại trong đối soát

Với từng hồ sơ trong `df_sql`:

1. Chuẩn hóa `MA_LK`.
2. Kiểm tra `MA_LK` có trong danh sách `listbh` đã lọc không.
3. Kiểm tra `MA_LK` có trong file lỗi chi tiết không.

Nếu `MA_LK` có trong `listbh`:

- Đếm vào `sent`.
- Tự động chuyển tất cả record cũ cùng `MA_LK` sang `RESOLVED`.
- Reset `his_unlock_status` về `NORMAL`.
- Ghi log hệ thống.

Nếu `MA_LK` không có trong `listbh` và không có trong file lỗi:

- Tạo/cập nhật record nhóm `FAIL`.
- Trạng thái mặc định `PENDING`.
- Nhóm này dành cho IT xử lý/reset.

Nếu `MA_LK` không có trong `listbh` nhưng có trong file lỗi:

- Tạo/cập nhật record nhóm `LOI`.
- Mỗi dòng lỗi chi tiết có thể tạo một record riêng theo `MA_LK + MALOI + MOTALOI`.
- Trạng thái mặc định `PENDING`.
- Hệ thống tự học danh mục lỗi mới nếu gặp `MALOI`/keyword chưa có.

### 8.7. Quy trình xử lý của khoa

Khoa đăng nhập `/department`.

API lấy dữ liệu:

- `GET /api/records/dept?status=...`

Khoa chỉ thấy:

- `Record.ten_khoa == user.department_name`
- `Record.type_group == "LOI"`

Khoa xử lý:

1. Xem lỗi, nguyên nhân gợi ý, hướng dẫn xử lý.
2. Sửa dữ liệu trên HIS theo quy trình nội bộ.
3. Nhập ghi chú.
4. Bấm lưu/gắn cờ gửi IT.
5. API `POST /api/records/{record_id}/flag` đổi trạng thái sang `WAITING_REVIEW`.

Khoa không trực tiếp chạy SQL reset trên webapp.

### 8.8. Quy trình xử lý của IT

IT có các luồng chính:

Danh sách FAIL:

- `GET /api/records/admin/fail`
- IT xem các ca `FAIL` chưa `RESOLVED`.
- Có thể sinh SQL reset hàng loạt theo loại ca qua `POST /api/records/admin/fail/reset?loai=...`.
- Code chuyển các record FAIL đó sang `WAITING_RESEND` sau khi sinh SQL.
- Câu SQL trả về để IT copy chạy ngoài SSMS.
- Chỉ khi lần đối soát sau thấy `MA_LK` xuất hiện trong `listbh`, hệ thống mới tự chuyển sang `RESOLVED`.

Trả hồ sơ về khoa (mở khóa/khóa lại bệnh án hàng loạt):

- `GET /api/admin/dept-unlock-preview?department_name=...`
- IT xem trước các ca lỗi (`LOI`) của khoa kèm cờ `requires_his_reset` (xác định ca nào cần can thiệp mở khóa HIS, ca nào khoa tự sửa được).
- `POST /api/admin/bulk-unlock`
- IT chọn khoa và loại thao tác (`UNLOCK` hoặc `CLOSE`).
- Hệ thống sinh SQL cập nhật trạng thái bệnh án nội trú (`BenhAn.TrangThai = 'DaXuatVien'` khi mở khóa hoặc `DaThanhToan` khi khóa lại) và đổi trạng thái hồ sơ thành `UNLOCKED` hoặc `NORMAL`. IT copy script chạy trên SSMS.

Mở khóa/trả khoa:

- `POST /api/records/{id}/toggle-his-unlock`
- Nếu action `UNLOCK`, record chuyển `his_unlock_status = "UNLOCKED"` và sinh SQL đưa `BenhAn.TrangThai` về `DaXuatVien` để khoa sửa.
- Nếu action `CLOSE`, record chuyển về `NORMAL` và sinh SQL đưa `BenhAn.TrangThai` về `DaThanhToan` để khóa lại sau khi khoa sửa.
- Script này hiện áp dụng cho ca `Nội trú` theo `BenhAn.SoBenhAn`. Đây là script mở/khóa bệnh án, không phải script reset cờ xuất XML.

Đánh dấu xử lý thủ công:

- `POST /api/records/{record_id}/admin-resolve`
- IT có hai tùy chọn qua tham số `action`:
  - `edit`: Chỉ lưu ghi chú xử lý của IT (giữ nguyên trạng thái hồ sơ).
  - `resolve` (mặc định): Lưu ghi chú và đổi trạng thái hồ sơ sang `RESOLVED`.

### 8.9. Scheduler tự đồng bộ

Khi app startup, scheduler chạy nền:

- Kiểm tra mỗi 30 giây.
- Nếu `auto_sync_enabled = true` và giờ/phút hiện tại trùng `auto_sync_time`, tự chạy đồng bộ.
- Range tự động hiện là 3 ngày gần nhất: từ hôm nay trừ 3 ngày đến hôm nay.
- Sau khi chạy, sleep 65 giây để tránh chạy lặp trong cùng phút.

### 8.10. Xuất báo cáo

Hệ thống hỗ trợ các loại export Excel:

- `GET /api/export/sql_list`: Xuất toàn bộ danh sách nạp từ HIS SQL ở ngày đối soát gần nhất.
- `GET /api/export/fail`: Xuất danh sách ca FAIL chưa giải quyết (hỗ trợ các tham số `from_date`, `to_date` để lọc theo ngày ra viện và cờ `include_resolved` để quyết định có xuất ca đã duyệt hay không).
- `GET /api/export/loi`: Xuất danh sách tất cả các ca lỗi (`LOI`) chưa giải quyết trong hệ thống.
- `GET /api/export/dept/loi`: Khoa lâm sàng xuất danh sách lỗi chưa giải quyết của riêng khoa mình theo tháng.

## 9. Quy trình nghiệp vụ chuẩn đề xuất khi vận hành hằng ngày

Đây là quy trình đề xuất để vận hành đúng và giảm lệch dữ liệu.

### 9.1. Chuẩn bị đầu ngày hoặc đầu ca

1. Kiểm tra máy chủ webapp đang chạy.
2. Xác nhận các khoa truy cập được địa chỉ LAN.
3. IT đăng nhập admin.
4. Kiểm tra cấu hình SQL HIS nếu có thay đổi server/database/SP.
5. Nếu có thay đổi cấu hình HIS, bấm `Xóa Cache SQL` trước khi đối soát.

### 9.2. Đối soát danh sách đã gửi và tìm ca chưa đẩy

1. Lấy file danh sách đã gửi BHYT từ cổng/phần mềm BHYT.
2. Đảm bảo file có cột `Mã liên kết` và `Ngày ra`.
3. Upload vào webapp dưới dạng `listbh.xlsx`.
4. Chọn đúng khoảng ngày cần đối soát.
5. Chạy `Đồng bộ & Đối soát CSDL HIS`.
6. Webapp lấy dữ liệu từ SQL Server HIS theo đúng khoảng ngày đã chọn.
7. Webapp so sánh danh sách SQL HIS với `listbh.xlsx` theo `MA_LK`.
8. Các ca có trong SQL HIS nhưng chưa có trong `listbh.xlsx` và chưa có trong danh sách lỗi được đưa vào nhóm `FAIL`.
9. IT kiểm tra nhóm `FAIL` và sinh SQL reset HIS để hệ thống gửi XML bên ngoài đẩy lại dữ liệu.
10. Sau khi reset và hệ thống bên ngoài gửi lại, IT lấy lại kết quả từ cổng/phần mềm BHYT:
   - Nếu ca đã được ghi nhận gửi thành công, cập nhật/upload lại `listbh.xlsx` rồi chạy đối soát lại.
   - Nếu cổng trả lỗi chi tiết, lúc này mới upload/import `HoSoLoiChiTiet.xlsx` để phân loại nhóm `LOI`.
11. Chờ progress hoàn tất 100%.
12. Kiểm tra KPI:
   - Tổng ca SQL.
   - Đã gửi BHYT.
   - Danh sách lỗi.
   - Danh sách FAIL.
   - IT đã duyệt.

### 9.3. Xử lý nhóm FAIL

Nhóm `FAIL` là hồ sơ có trong SQL HIS nhưng chưa có trong danh sách bảo hiểm đã gửi (`listbh`) và cũng chưa có trong danh sách lỗi chi tiết (`HoSoLoiChiTiet.xlsx`).

Quy trình:

1. IT mở tab `Danh sách FAIL`.
2. Kiểm tra các ca theo ngày ra viện xa nhất trước.
3. Chọn reset ngoại trú/nội trú phù hợp.
4. Copy SQL reset do webapp sinh.
5. Chạy SQL trong SSMS hoặc công cụ được bệnh viện cho phép.
6. Đợi hệ thống gửi XML bên ngoài gửi lại.
7. Lấy lại `listbh.xlsx` mới từ cổng/phần mềm BHYT.
8. Upload lại `listbh.xlsx`.
9. Chạy đối soát lại để hệ thống tự chuyển ca đã gửi thành `RESOLVED`.

Sau khi IT sinh SQL reset, webapp chuyển ca sang `WAITING_RESEND`. Ca chỉ hoàn tất khi lần đối soát sau thấy `MA_LK` đã có trong `listbh`, hoặc khi IT chủ động xác nhận hoàn tất thủ công.

### 9.4. Xử lý nhóm LỖI chi tiết

Nhóm `LOI` là hồ sơ có trong file lỗi chi tiết BHYT.

Quy trình:

1. Khoa đăng nhập tài khoản của khoa.
2. Xem danh sách lỗi thuộc khoa.
3. Đọc nguyên nhân/hướng dẫn từ danh mục lỗi nếu có.
4. Sửa dữ liệu trên HIS.
5. Nếu lỗi cần mở khóa bệnh án trước khi sửa, IT bấm mở khóa để sinh script đưa `BenhAn.TrangThai` về `DaXuatVien`, copy chạy trên SSMS, sau đó khoa sửa dữ liệu trên HIS.
6. Khoa nhập ghi chú đã xử lý.
7. Khoa gửi IT duyệt, record chuyển `WAITING_REVIEW`.
8. IT kiểm tra lại.
9. Nếu trước đó đã mở khóa, IT bấm khóa lại để sinh script đưa `BenhAn.TrangThai` về `DaThanhToan`, copy chạy trên SSMS.
10. IT duyệt và lấy SQL reset cờ xuất nếu cần gửi XML lại.
11. Hệ thống gửi XML bên ngoài gửi lại.
12. IT upload lại file danh sách đã gửi/file lỗi mới và chạy đối soát lại.
13. Nếu ca đã xuất hiện trong `listbh`, hệ thống tự chuyển các record cùng `MA_LK` sang `RESOLVED`.

Script mở khóa bệnh án nội trú có dạng:

```sql
-- MO KHOA BENH AN CHO KHOA SUA
SELECT ba.SoBenhAn, ba.TrangThai, ba.NgayRaVien
FROM BenhAn ba
WHERE ba.SoBenhAn IN (
    '26.002711/CC'
);

UPDATE ba
SET TrangThai = 'DaXuatVien'
FROM BenhAn ba
WHERE ba.SoBenhAn IN (
    '26.002711/CC'
);
```

Script khóa lại sau khi khoa sửa có dạng:

```sql
-- KHOA LAI BENH AN SAU KHI KHOA SUA XONG
UPDATE ba
SET TrangThai = 'DaThanhToan'
FROM BenhAn ba
WHERE ba.SoBenhAn IN (
    '26.002711/CC'
);
```

### 9.5. Cuối ngày

1. Export `sql_list.xlsx`, `DANH_SACH_FAIL.xlsx`, `DANH_SACH_KEM_LOI.xlsx` nếu cần lưu hồ sơ.
2. Kiểm tra số lượng `PENDING` và `WAITING_REVIEW`.
3. Gửi danh sách còn tồn cho các khoa/IT.
4. Backup `app_state.db` nếu cần lưu lịch sử xử lý.

## 10. Logic reset SQL

Reset không gửi XML. Reset chỉ đặt lại cờ xuất dữ liệu để hệ thống khác gửi XML lại.

Các cờ reset:

- `Export=0`
- `Export1=0`
- `Export_CV130=0`

Ngoại trú:

```sql
UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM TiepNhan tn
JOIN XacNhanChiPhi xn ON xn.TiepNhan_Id = tn.TiepNhan_Id
WHERE tn.SoTiepNhan IN (
    ...
);
```

Nội trú:

```sql
UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM BenhAn ba
JOIN XacNhanChiPhi xn ON xn.BenhAn_Id = ba.BenhAn_Id
WHERE ba.SoBenhAn IN (
    ...
);
```

Trong webapp, loại ca lấy từ `Record.loai_ca`, không còn tách bằng `MA_LK.startswith("TN.")` ở UI như bản desktop. Tuy vậy quy tắc dữ liệu ban đầu vẫn cần nhất quán: ngoại trú thường có mã `TN.*`, nội trú là số bệnh án đã bỏ `A` đầu nếu có.

## 11. Cache SQL

Cache hiện nằm trong:

- `cache_sql/index.json`
- `cache_sql/sql_list_<TuNgay>.pkl`

Logic hiện tại:

- Cache theo `TuNgay`.
- Nếu `TuNgay` và `DenNgay` khớp cache, dùng lại.
- Nếu `DenNgay` lớn hơn cache cũ, chỉ gọi SQL phần ngày còn thiếu rồi ghép.
- Nếu cache không dùng được, gọi full range.

Timeout SQL hiện tại:

- `BHYT_SQL_CONNECT_TIMEOUT`: timeout khi kết nối SQL Server, mặc định `60` giây.
- `BHYT_SQL_QUERY_TIMEOUT`: timeout khi chạy truy vấn/stored procedure/reset SQL qua pyodbc, mặc định `0`.
- Giá trị `0` nghĩa là không giới hạn timeout truy vấn ở phía pyodbc, phù hợp khi chạy dữ liệu dài như 1 tháng.
- Nếu bệnh viện muốn giới hạn lại, có thể set biến môi trường `BHYT_SQL_QUERY_TIMEOUT`, ví dụ `1800` cho 30 phút.

Rủi ro:

- Cache chưa phân biệt server/database/SP/user.
- Đổi cấu hình HIS mà không clear cache có thể dùng nhầm dữ liệu.
- Không giới hạn query timeout giúp tránh dừng giữa chừng, nhưng nếu SP bị treo thật thì job có thể chạy rất lâu; cần theo dõi log/progress và tối ưu SP/index phía SQL Server nếu thường xuyên quá chậm.

Hướng xử lý nên làm:

- Tạo cache key bằng hash gồm:
  - server
  - database
  - auth/user
  - SP ngoại trú
  - SP nội trú
  - `TuNgay`
  - `DenNgay`
  - version schema
- Hiển thị rõ cache đang dùng cho cấu hình nào.
- Tự clear hoặc bỏ qua cache khi cấu hình HIS thay đổi.

## 12. Rà soát lỗi và rủi ro hiện tại

### 12.1. Bảo mật đăng nhập

Hiện session cookie lưu trực tiếp username, chưa ký/chưa mã hóa.

Nên cải thiện:

- Dùng signed session hoặc JWT nội bộ có secret.
- Set `SameSite=Lax`.
- Nếu dùng HTTPS nội bộ thì set thêm `Secure`.
- Thêm chức năng đổi mật khẩu.
- Bắt đổi mật khẩu admin mặc định khi chạy lần đầu.

### 12.2. Mật khẩu SQL HIS

Hiện password HIS được XOR/base64 bằng key hard-code.

Nên cải thiện:

- Dùng Windows Credential Manager, DPAPI, hoặc tối thiểu mã hóa bằng khóa ngoài source code.
- Cho phép không lưu password, nhập khi chạy nếu bệnh viện yêu cầu.

### 12.3. Sinh SQL bằng ghép chuỗi

`build_reset_sql()` đưa `MA_LK` trực tiếp vào SQL.

Nên cải thiện:

- Escape dấu `'` trong mã.
- Khi chạy trực tiếp, dùng parameterized query hoặc bảng tạm.
- Validate `loai_ca` chỉ nhận `Ngoại trú`/`Nội trú`.
- Validate stored procedure name theo whitelist hoặc pattern an toàn.

### 12.4. Đánh dấu RESOLVED quá sớm

Một số API reset/approve hiện chuyển record sang `RESOLVED` ngay khi IT lấy SQL reset.

Nên kiểm tra lại nghiệp vụ:

- Nếu `RESOLVED` nghĩa là "đã xử lý trên webapp", code hiện phù hợp.
- Nếu `RESOLVED` nghĩa là "đã được cổng BHYT ghi nhận gửi thành công", nên thêm trạng thái trung gian.

Đề xuất trạng thái mới:

- `PENDING`
- `WAITING_DEPARTMENT`
- `WAITING_REVIEW`
- `RESET_READY`
- `RESET_SQL_COPIED`
- `WAITING_RESEND`
- `RESOLVED`

### 12.5. File upload ghi đè

Hiện upload `listbh.xlsx` và `HoSoLoiChiTiet.xlsx` ghi đè file cũ.

Nên cải thiện:

- Lưu file theo timestamp.
- Lưu metadata: người upload, thời điểm upload, số dòng, range ngày.
- Cho phép chọn bộ file dùng cho một lần đối soát.

### 12.6. Ngày đối soát

Record hiện lưu `ngay_doi_soat = today()`.

Điều này phù hợp để biết ngày chạy hệ thống, nhưng chưa đủ nếu cần truy vết theo range nghiệp vụ.

Nên thêm:

- `tu_ngay`
- `den_ngay`
- `sync_run_id`
- `source_file_id`

### 12.7. Lọc dữ liệu theo khoa

Khoa chỉ thấy lỗi nếu `Record.ten_khoa` khớp tuyệt đối `User.department_name`.

Rủi ro:

- HIS trả `Khoa Sản`, admin tạo `Sản` thì khoa không thấy dữ liệu.
- Có khoảng trắng/ký tự khác biệt.

Nên cải thiện:

- Thêm bảng mapping khoa HIS -> tài khoản khoa.
- Chuẩn hóa tên khoa.
- UI cho admin chọn từ danh sách khoa thực tế đã phát hiện.

### 12.8. Scheduler tự đồng bộ

Scheduler hiện chạy theo giờ cấu hình và lấy 3 ngày gần nhất.

Rủi ro:

- Nếu thời điểm đó file `listbh.xlsx` chưa được cập nhật, kết quả đối soát sẽ sai.
- Nếu job chạy lâu, trạng thái progress global có thể gây nhầm với job thủ công.

Nên cải thiện:

- Tạo bảng `sync_runs`.
- Mỗi lần đồng bộ có ID, logs riêng, trạng thái riêng.
- Scheduler chỉ chạy khi file nguồn mới hơn lần chạy trước.
- Có cấu hình range tự động.

### 12.9. Đường dẫn runtime

Một số path hiện là relative.

Nên cải thiện:

- Tính đường dẫn theo `BASE_DIR = Path(__file__).resolve().parent`.
- Đặt SQLite, upload, cache cố định dưới `web_app/data/`, `web_app/uploaded_files/`, `web_app/cache_sql/`.

### 12.10. Frontend khó bảo trì

HTML/CSS/JS đang inline trong template lớn.

Nên cải thiện:

- Tách JS ra `static/js/admin.js`, `static/js/department.js`.
- Tách CSS ra `static/css/*.css`.
- Chuẩn hóa component table, modal, toast.

## 13. Hướng tối ưu hóa nghiệp vụ

### 13.1. Thêm vòng đời xử lý rõ ràng

Mục tiêu: không nhầm giữa "đã copy SQL reset" và "đã gửi BHYT thành công".

Đề xuất:

- `PENDING`: mới phát hiện lỗi/fail.
- `IN_PROGRESS`: đang được khoa/IT xử lý.
- `WAITING_REVIEW`: khoa gửi IT duyệt.
- `RESET_DONE`: IT đã reset cờ xuất.
- `WAITING_RESEND`: chờ hệ thống gửi XML bên ngoài gửi lại.
- `RESOLVED`: đã thấy lại trong `listbh`.

### 13.2. Tạo lần đồng bộ độc lập

Thêm bảng `sync_runs`:

- id
- from_date
- to_date
- started_at
- finished_at
- triggered_by
- listbh_file
- loi_file
- total_sql
- total_sent
- total_loi
- total_fail
- status
- log

Lợi ích:

- Truy vết được mỗi lần đối soát.
- Export đúng theo lần chạy.
- Không phụ thuộc "ngày gần nhất có dữ liệu".

### 13.3. Quản lý file nguồn

Thêm bảng `uploaded_files`:

- file_type
- original_name
- stored_name
- uploaded_by
- uploaded_at
- row_count
- hash

Lợi ích:

- Biết lần đối soát dùng file nào.
- Tránh ghi đè mất dấu vết.
- Phát hiện upload nhầm file cũ.

### 13.4. Mapping khoa phòng

Thêm bảng `department_mappings`:

- his_department_name
- app_department_name
- user_id hoặc department_id
- active

Lợi ích:

- Khoa thấy đúng dữ liệu.
- Không phụ thuộc khớp chuỗi tuyệt đối.
- Dễ xử lý trường hợp một khoa có nhiều tên trong HIS.

### 13.5. Báo cáo lệch hai chiều

Hiện trọng tâm là:

- Có trong SQL nhưng không có trong BHYT.

Nên thêm:

- Có trong BHYT nhưng không có trong SQL.
- Có trong file lỗi nhưng không có trong SQL range đang chạy.
- Có trong file lỗi nhưng đã xuất hiện trong list đã gửi.

### 13.6. Tự cảnh báo dữ liệu đầu vào bất thường

Nên kiểm tra sau upload:

- Thiếu cột bắt buộc.
- Số dòng bằng 0.
- Tỷ lệ `MA_LK` rỗng.
- Khoảng ngày trong file không giao với range đối soát.
- File lỗi có nhiều `MA_LK` không nằm trong SQL.
- Dữ liệu ngày parse lỗi.

### 13.7. Dashboard theo trách nhiệm

Admin:

- Tổng lỗi theo khoa.
- Top mã lỗi nhiều nhất.
- Lỗi quá hạn theo ngày ra viện.
- Số ca đã reset nhưng chưa gửi lại.

Khoa:

- Việc cần xử lý hôm nay.
- Việc đã gửi IT duyệt.
- Việc bị IT trả lại.
- Hướng dẫn lỗi theo từng dòng.

## 14. Quy trình triển khai LAN đề xuất

### 14.1. Cài đặt lần đầu trên máy chủ

1. Cài Python.
2. Cài ODBC Driver 17/18 for SQL Server.
3. Clone/copy source vào máy chủ.
4. Tạo `.venv`.
5. Cài thư viện:

```powershell
pip install -r requirements.txt
```

6. Chạy thử:

```powershell
python web_app/run.py --port 8000
```

7. Truy cập từ chính máy chủ:

```text
http://localhost:8000
```

8. Truy cập từ máy khoa:

```text
http://<IP_LAN_MAY_CHU>:8000
```

### 14.2. Cấu hình mạng

1. Xác định IP LAN của card mạng bệnh viện.
2. Mở inbound firewall port `8000` cho private/domain network.
3. Không mở port này ra internet.
4. Nếu máy có internet và LAN đồng thời, ưu tiên thông báo địa chỉ IP thuộc LAN bệnh viện cho các khoa.
5. Kiểm tra từ máy khoa bằng trình duyệt.

### 14.3. Chạy nền

Khuyến nghị dùng một trong hai cách:

- Task Scheduler chạy `python web_app/run.py`.
- NSSM tạo Windows Service.

Nếu dùng launcher:

- Chạy `LaunchWebBHYT.py`.
- Chọn thư mục dự án.
- Chọn port.
- Start server background.

## 15. Các endpoint chính

Trang:

- `GET /`
- `GET /login`
- `GET /admin`
- `GET /department`

Auth:

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

Config:

- `GET /api/config`
- `POST /api/config`
- `GET /api/config/drivers`
- `POST /api/config/test-connection`
- `POST /api/config/clear-cache`

Upload/đối soát:

- `POST /api/upload/listbh`
- `POST /api/upload/loi`
- `GET /api/records/compare`
- `POST /api/sync/start`
- `GET /api/sync/status`

Khoa:

- `GET /api/records/dept`
- `GET /api/records/dept/stats`
- `GET /api/export/dept/loi`

Admin xử lý:

- `GET /api/records/admin/fail`
- `POST /api/records/{record_id}/admin-resolve`
- `POST /api/records/admin/fail/reset`
- `POST /api/records/{id}/toggle-his-unlock`
- `GET /api/admin/dept-unlock-preview`
- `POST /api/admin/bulk-unlock`

Báo cáo & Xuất file:

- `GET /api/records/kpi`
- `GET /api/reports/departments`
- `GET /api/export/sql_list`
- `GET /api/export/fail`
- `GET /api/export/loi`

Lưu trữ Lịch sử Lỗi Vĩnh viễn:

- `GET /api/archive/errors`
- `GET /api/archive/months`
- `GET /api/archive/stats`
- `GET /api/export/archive/errors`

Quản trị:

- `GET /api/users`
- `POST /api/users`
- `DELETE /api/users/{user_id}`
- `GET /api/error-definitions`
- `POST /api/error-definitions`
- `DELETE /api/error-definitions/{id}`

## 16. Checklist kiểm tra quy trình với người dùng nghiệp vụ

Cần xác nhận lại các điểm sau trước khi tinh chỉnh code sâu:

1. `RESOLVED` có nên chỉ dựa vào việc đã thấy hồ sơ gửi thành công trong `listbh`, hay IT vẫn được phép xác nhận thủ công trong một số trường hợp?
2. Trạng thái `WAITING_RESEND` đã đủ cho giai đoạn sau reset/chờ gửi lại chưa, hay cần tách thêm `RESET_SQL_COPIED` và `RESET_DONE`?
3. Khoa có cần quyền yêu cầu IT mở khóa HIS trực tiếp từ màn hình khoa không?
4. File lỗi `HoSoLoiChiTiet.xlsx` có thể có nhiều dòng cùng `MA_LK` không, và mỗi dòng có cần thành một việc riêng không?
5. Một khoa trong HIS có thể có nhiều tên khác nhau không?
6. Ngoại trú luôn map về `Khám bệnh` có đúng thực tế không?
7. Scheduler tự động nên chạy theo 3 ngày gần nhất hay theo range cố định khác?
8. Có cần lưu lịch sử nhiều lần upload file hay chỉ cần file mới nhất?
9. Có cần báo cáo lệch ngược "có trong BHYT nhưng không có trong SQL" không?
10. Có cần chạy reset trực tiếp từ webapp hay chỉ sinh SQL để IT copy chạy SSMS?

## 17. Ưu tiên phát triển tiếp theo

Ưu tiên cao:

1. Sửa tài liệu và quy trình vận hành theo webapp.
2. Thêm trạng thái trung gian để không `RESOLVED` quá sớm.
3. Tăng bảo mật session và bắt đổi mật khẩu admin mặc định.
4. Cải thiện cache key theo cấu hình HIS.
5. Chuẩn hóa path runtime theo `BASE_DIR`.
6. Escape/validate SQL reset.
7. Thêm mapping khoa phòng.

Ưu tiên trung bình:

1. Tạo bảng `sync_runs`.
2. Lưu lịch sử upload file.
3. Báo cáo lệch hai chiều.
4. Dashboard theo mã lỗi/khoa/quá hạn.
5. Tách JS/CSS khỏi template.

Ưu tiên sau:

1. Test tự động cho services nghiệp vụ.
2. Đóng gói launcher/webapp thành bộ cài nội bộ.
3. Thêm backup/restore SQLite.
4. Thêm audit log đầy đủ hơn cho thao tác admin.

## 18. Ghi chú cho agent hoặc lập trình viên mới

Nếu sửa webapp, đọc theo thứ tự:

1. `AGENT_CHANGELOG.md` để nắm thay đổi qua các phiên làm việc và ghi log sau khi sửa.
2. `web_app/models.py` để hiểu dữ liệu.
3. `web_app/services/his_service.py` để hiểu SQL HIS và reset.
4. `web_app/services/excel_service.py` để hiểu file Excel.
5. `web_app/services/compare_service.py` để hiểu phân loại nghiệp vụ.
6. `web_app/main.py` để hiểu API và scheduler.
7. `web_app/templates/admin.html` và `department.html` để hiểu thao tác người dùng.

Nguyên tắc quan trọng:

- Không sửa `dist/` hoặc `build/` trừ khi đang đóng gói.
- Không commit `app_state.db`, cache, file upload, file Excel thật.
- Không thay đổi logic `MA_LK` nếu chưa xác nhận nghiệp vụ.
- Khi thay đổi trạng thái xử lý, phải xem cả màn hình admin, khoa, export, KPI và scheduler.
- Khi đổi logic đối soát, nên có test mẫu cho `compare_service.process_comparison()`.
- Sau mỗi thay đổi có ý nghĩa, phải cập nhật `AGENT_CHANGELOG.md` để phiên làm việc sau hiểu bối cảnh.
