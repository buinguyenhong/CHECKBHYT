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

## 2026-06-27 - Antigravity (Tính năng: Thêm khoảng thời gian vào tên file Excel xuất ra)

### Mục tiêu
- Khi xuất báo cáo danh sách lỗi (`LOI`) hoặc danh sách fail (`FAIL`), tự động thêm thông tin khoảng thời gian đối soát (từ ngày... đến ngày...) vào tên file tải xuống (ví dụ: `DANH_SACH_KEM_LOI_0106_2706.xlsx`), đồng bộ giữa mốc thời gian chọn ở mục đối soát dữ liệu trên UI và tên file xuất ra.

### Thay đổi
- `web_app/templates/admin.html`:
  - Cập nhật hàm `exportLoiData()` truyền thêm `from_date` và `to_date` lấy từ ô nhập liệu `sync_from` và `sync_to` tương tự ca FAIL.
  - Cập nhật nút Tải file danh sách kèm lỗi gọi `exportLoiData()` thay vì `exportData()`.
- `web_app/main.py`:
  - Cập nhật API `export_loi_list` nhận tham số `from_date` và `to_date` để lọc và định dạng tên file.
  - Cập nhật API `export_department_loi` sử dụng mốc thời gian tĩnh nguyên tháng được chọn thay vì quét động danh sách records để tên file ổn định (ví dụ chọn tháng 6 sẽ ra `0106_3006` cố định).
- `main.py` (Desktop GUI client):
  - Cập nhật hàm `export_fail` và `export_loi` tự động quét danh sách để định dạng tên file lưu mặc định trong Save File Dialog chứa suffix khoảng thời gian.

### Nghiệp vụ ảnh hưởng
- Người dùng tải báo cáo về có tên file trực quan chứa đúng mốc thời gian đã chọn đối soát ở giao diện Admin (ví dụ: `DANH_SACH_KEM_LOI_0106_2606.xlsx`), tránh bị lệch ngày khi ngày ra viện của ca đầu tiên không trùng ngày bắt đầu đối soát.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho các file Python.

## 2026-06-27 - Antigravity (Tính năng: Tách biệt lỗi thầu thuốc sang sheet Excel riêng khi xuất danh sách lỗi)

### Mục tiêu
- Khi xuất báo cáo/danh sách lỗi BHYT, tự động tách các lỗi liên quan đến Thông tin thầu (`TT_THAU`) và Mã thuốc (`MA_THUOC`) sang một sheet riêng biệt tên là "Lỗi thầu thuốc", các lỗi còn lại nằm ở sheet "Lỗi chung". Điều này giúp bộ phận Dược và quản lý danh mục xử lý lỗi nhanh hơn.

### Thay đổi
- `web_app/main.py`:
  - Cập nhật API `export_department_loi` (`GET /api/export/dept/loi`) và API `export_loi_list` (`GET /api/export/loi`): sử dụng `pd.ExcelWriter` phân tách dòng dữ liệu dựa trên từ khóa `TT_THAU` hoặc `MA_THUOC` trong cột mã lỗi hoặc mô tả lỗi, ghi vào hai sheet riêng biệt ("Lỗi chung" và "Lỗi thầu thuốc").
- `main.py` (Desktop GUI client):
  - Cập nhật hàm `export_loi` thực hiện phân tách lỗi thầu/thuốc tương tự thông qua kiểm tra linh hoạt tên cột.

### Nghiệp vụ ảnh hưởng
- File Excel báo cáo lỗi xuất ra từ hệ thống (cả giao diện khoa phòng và giao diện admin) sẽ có 2 sheet giúp phân luồng xử lý lỗi khoa lâm sàng và khoa dược/vật tư y tế rõ ràng.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py` và `main.py`.

## 2026-06-27 - Antigravity (Tính năng: Bổ sung danh mục hướng dẫn xử lý lỗi và Tối ưu hóa so khớp mã lỗi)

### Mục tiêu
- Bổ sung các mẫu lỗi thường gặp và hướng dẫn xử lý chi tiết (14 lỗi nghiệp vụ) từ tài liệu người dùng cung cấp vào danh mục lỗi mẫu (`ErrorDefinition`).
- Chuẩn hóa định dạng cột mã lỗi (`error_code`) dưới dạng mô tả ngắn gọn trực quan (ví dụ: `XML 7 (Giấy ra viện)`, `XML 3 (Dịch vụ kỹ thuật)`).
- Tối ưu hóa logic so khớp mã lỗi ở Backend (bulk unlock, preview, auto-collect) để hoạt động chính xác với định dạng mã lỗi descriptive mới.

### Thay đổi
- `web_app/main.py`:
  - Cập nhật danh sách lỗi mẫu `sample_errors` bổ sung đầy đủ các lỗi về logic thời gian, liên kết dữ liệu, tài chính danh mục và bỏ trống các trường bắt buộc.
  - Viết lại hàm khởi tạo danh mục lỗi thành dạng **idempotent seed**: tự động rà soát, đồng bộ và cập nhật mô tả/thông tin hướng dẫn cho danh sách lỗi cũ, đồng thời chèn mới nếu chưa có.
  - Sửa lỗi import thiếu `SessionLocal` ở block dọn dẹp dữ liệu trùng lặp trên startup.
  - Cập nhật hàm `bulk_unlock` và `dept_unlock_preview` thực hiện so khớp mã lỗi mềm dẻo (loại bỏ khoảng trắng, ký tự đặc biệt và chữ hoa/thường) giữa `Record.maloi` (ví dụ `XML7`) và `ErrorDefinition.error_code` (ví dụ `XML 7 (Giấy ra viện)`).
- `web_app/services/compare_service.py`:
  - Cập nhật hàm `process_comparison` tại luồng tự động thu thập mẫu lỗi mới (auto-collect): thực hiện so khớp mềm dẻo mã lỗi đầu vào với danh sách `ErrorDefinition` trong DB để tránh chèn trùng lặp hướng dẫn lỗi.

### Nghiệp vụ ảnh hưởng
- Người dùng lâm sàng và IT xem danh mục hướng dẫn lỗi chi tiết hơn với định dạng mã lỗi rõ ràng (có chú thích loại file XML tương ứng).
- Chức năng "Trả hồ sơ khoa" (bulk unlock) tự động nhận dạng chính xác các ca lỗi nội trú cần mở khóa theo danh mục hướng dẫn mới cập nhật.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công.
- Thực hiện chạy thử tiến trình khởi động WebApp để xác nhận danh mục lỗi mẫu được seed thành công 17 lỗi và định dạng chuẩn hóa khớp chính xác.

## 2026-06-26 - Antigravity (Sửa lỗi: Loại bỏ lỗi trùng lặp khi đối soát BHYT)

### Mục tiêu
- Khắc phục tình trạng các lỗi trùng lặp (cùng mã liên kết, mã lỗi, mô tả lỗi) xuất hiện nhiều lần hoặc bị nhân đôi trong cơ sở dữ liệu và hiển thị trên giao diện do sự khác biệt nhỏ về khoảng trắng, xuống dòng, chữ hoa/chữ thường trong file Excel đầu vào và cách so khớp chính xác trong SQLite.

### Thay đổi
- `web_app/services/compare_service.py`:
  - Thêm hàm `deduplicate_database_records(db: Session)` để tự động quét, nhóm và loại bỏ các bản ghi lỗi trùng lặp trong cơ sở dữ liệu (ưu tiên giữ lại bản ghi có trạng thái `PENDING` hoặc có ngày cập nhật mới nhất, đồng thời chuyển ghi chú cũ sang bản ghi được giữ lại).
  - Chuẩn hóa mã liên kết `ma_lk` (bằng cách chuyển thành chữ in hoa và rút gọn qua `chuan_hoa_ma_lk`) trên toàn bộ các nguồn dữ liệu đối soát.
  - Chuẩn hóa mã lỗi `maloi` (chữ in hoa) và mô tả lỗi `motaloi` (dọn dẹp khoảng trắng thừa, tab, xuống dòng qua hàm `clean_error_desc`).
  - Lọc trùng ngay từ danh sách lỗi của cùng một hồ sơ từ file Excel đầu vào (`error_map`).
  - Thay đổi logic đối soát lỗi chi tiết: Tải toàn bộ bản ghi lỗi `LOI` hiện có của bệnh nhân lên bộ nhớ và thực hiện so khớp mềm dẻo (không phân biệt chữ hoa/thường và khoảng trắng thừa) để cập nhật thay vì tạo bản ghi mới trùng lặp.
  - Gọi hàm `deduplicate_database_records(db)` ở đầu tiến trình đối soát `process_comparison`.
- `web_app/main.py`:
  - Tự động gọi `deduplicate_database_records(db)` khi ứng dụng khởi chạy (`Base.metadata.create_all`) để làm sạch toàn bộ dữ liệu trùng lặp lịch sử trong SQLite.

### Nghiệp vụ ảnh hưởng
- Không còn tình trạng một ca bệnh hiển thị nhiều lỗi giống hệt nhau trên màn hình của khoa và quản trị admin.
- Cơ sở dữ liệu SQLite được làm sạch và lưu trữ chuẩn hóa hơn.
- Logic đồng bộ chạy ổn định và chính xác kể cả khi file Excel báo lỗi chứa dòng trùng lặp hoặc viết hoa/thường khác biệt.

### Kiểm tra
- Viết script test trong `scratch/test_deduplication.py` tạo cơ sở dữ liệu mẫu chứa các bản ghi lỗi trùng lặp khác nhau về khoảng trắng, xuống dòng, chữ hoa thường và trạng thái. Chạy thành công xác nhận các bản ghi trùng bị xóa hoàn toàn, bản ghi giữ lại được chuyển đổi trạng thái chính xác và thông tin ghi chú được bảo toàn.
- Chạy biên dịch kiểm tra lỗi cú pháp (compile check) thành công.

## 2026-06-22 - buinguyenhong (Tính năng: Tách biệt sửa/duyệt ca FAIL và nâng cấp xuất Excel ca FAIL)

### Mục tiêu
- Hỗ trợ IT cập nhật ghi chú cho ca FAIL mà không cần đánh dấu hoàn tất (RESOLVED) ngay lập tức.
- Nâng cấp chức năng xuất Excel ca FAIL để hỗ trợ bộ lọc khoảng ngày ra viện, hiển thị rõ ràng trạng thái và ghi chú xử lý.

### Thay đổi
- `web_app/main.py`:
  - Cập nhật API `resolve_fail_record` (`POST /api/records/{record_id}/admin-resolve`) hỗ trợ tham số `action`. Nếu `action == "edit"`, hệ thống chỉ cập nhật ghi chú (chuyển log `EDIT_NOTE`), không chuyển trạng thái sang `RESOLVED`.
  - Cập nhật API `export_fail_list` (`GET /api/export/fail`) hỗ trợ tham số `include_resolved` (mặc định `True`), sắp xếp theo ngày ra viện tăng dần, xuất thêm cột "Trạng thái" (được Việt hóa trực quan) và ghi chú xử lý của IT.
- `web_app/templates/admin.html`:
  - Trong Modal Sửa/Duyệt ca FAIL: Tách nút "Lưu & Đánh dấu xử lý" thành 2 nút riêng biệt là "Lưu Ghi Chú (Vẫn hiển thị)" và "Duyệt & Hoàn Tất (Không hiển thị lại)".
  - Trong danh sách ca FAIL (Tab 3): Thêm nút "Xuất Excel ca FAIL" liên kết với chức năng lọc theo khoảng ngày ra viện (`from_date` và `to_date`).

### Nghiệp vụ ảnh hưởng
- IT có thể tạm lưu thông tin xử lý/ghi chú cho các ca FAIL chưa hoàn tất mà không sợ ca đó bị biến mất khỏi danh sách chờ xử lý.
- Dễ dàng xuất báo cáo Excel cho riêng danh sách ca FAIL có bộ lọc thời gian và thông tin chi tiết về trạng thái/ghi chú xử lý để báo cáo lãnh đạo hoặc các khoa phòng.

## 2026-06-15 - Antigravity (Sửa lỗi: Loại bỏ lỗi đã xử lý khỏi các file xuất Excel)

### Mục tiêu
- Sửa lỗi xuất danh sách kèm lỗi xuất cả các ca đã xử lý rồi (RESOLVED).

### Thay đổi
- `web_app/main.py`:
  - Cập nhật API `export_department_loi` (`GET /api/export/dept/loi`) lọc bỏ các ca lỗi đã xử lý (`status != "RESOLVED"`), giúp file xuất ra cho khoa chỉ hiển thị các ca lỗi thực sự chưa được khắc phục.

### Nghiệp vụ ảnh hưởng
- File Excel xuất danh sách lỗi của khoa phòng (`LOI_BHYT_*.xlsx`) chỉ chứa các ca lỗi đang cần xử lý, không bị lẫn các ca đã xử lý thành công.

## 2026-06-11 - Antigravity (Sửa lỗi: Thống kê và Hiển thị danh sách Lỗi trên Admin)

### Mục tiêu
- Sửa lỗi các khoa có danh sách lỗi nhưng giao diện admin hiển thị số ca lỗi bằng 0 (danh sách lỗi trống) và không thể xem/tải danh sách lỗi khi chạy đối soát không kèm file HoSoLoiChiTiet.
- Sửa lỗi preview trả hồ sơ khoa trống khi các ca lỗi chưa được định nghĩa requires_his_reset=True.

### Thay đổi
- `web_app/main.py`:
  - **KPIs động**: Cập nhật `get_global_kpis` tính trực tiếp số ca lỗi (`type_group="LOI"`) và ca FAIL (`type_group="FAIL"`) chưa xử lý từ DB, thay vì lấy thống kê của riêng lần đối soát cuối.
  - **Báo cáo động**: Cập nhật `get_department_breakdown` đếm tất cả ca lỗi đang hoạt động thay vì lọc theo `ngay_doi_soat` của lần đối soát cuối.
  - **Xuất Excel động**: Cập nhật `export_loi_list` xuất toàn bộ ca lỗi chưa giải quyết (`status != "RESOLVED"`) trong DB.
  - **Xem trước đầy đủ**: Cập nhật `preview_department_unlock` trả về toàn bộ ca LOI chưa giải quyết của khoa kèm cờ `requires_his_reset` thay vì lọc cứng bỏ qua ca không cần mở khóa.
- `web_app/templates/admin.html`:
  - Cập nhật JS `previewDeptUnlock` hiển thị toàn bộ ca lỗi của khoa, phân biệt ca cần mở khóa HIS với ca "Khoa tự sửa" (hiển thị badge trực quan), cập nhật cách tính số lượng nội trú/ngoại trú trên summary.

### Nghiệp vụ ảnh hưởng
- Admin luôn nhìn thấy chính xác tổng số lỗi đang tồn đọng trên Dashboard và báo cáo chi tiết khoa phòng.
- File export `DANH_SACH_KEM_LOI.xlsx` chứa đầy đủ các ca lỗi chưa giải quyết thay vì bị trống khi lần đối soát cuối không nạp file lỗi.
- IT có thể kiểm tra toàn bộ danh sách lỗi của khoa phòng tại tab "Trả hồ sơ khoa" và biết rõ ca nào tự sửa, ca nào cần IT can thiệp chạy SQL.

### Kiểm tra
- Chạy `py_compile` thành công cho `main.py`.

## 2026-06-10 - Antigravity (Bổ sung: Trả hồ sơ khoa hàng loạt)

### Mục tiêu
- Thêm công cụ sinh script trả hồ sơ về khoa (mở khóa bệnh án) hàng loạt theo khoa.
- IT chọn khoa → sinh SQL đưa BenhAn.TrangThai về DaXuatVien → khoa sửa → IT khóa lại.

### Thay đổi
- `web_app/main.py`:
  - **Thêm** `POST /api/admin/bulk-unlock` — sinh script mở khóa/khóa lại bệnh án hàng loạt theo khoa. Chỉ lấy ca LOI chưa RESOLVED khớp ErrorDefinition có `requires_his_reset=True`.
  - **Thêm** `GET /api/admin/dept-unlock-preview` — xem trước danh sách ca cần trả hồ sơ.
- `web_app/templates/admin.html`:
  - **Thay tab 4** "Chờ Duyệt (Khoa Gửi)" → "Trả hồ sơ khoa".
  - UI mới: dropdown chọn khoa, nút Xem trước / Mở khóa / Khóa lại, bảng preview.
  - Bỏ JS functions: `fetchReviewRecords()`, `approveAndReset()`.
  - Thêm JS functions: `loadUnlockDeptList()`, `previewDeptUnlock()`, `bulkDeptUnlock()`.

### Nghiệp vụ ảnh hưởng
- IT không còn chờ khoa gửi duyệt qua webapp. IT chủ động chọn khoa và sinh script.
- Chỉ ca nội trú mới cần mở khóa bệnh án. Ca ngoại trú được ghi chú nhưng không sinh script.
- Luồng mới: Khoa liên hệ IT → IT mở tab "Trả hồ sơ khoa" → chọn khoa → UNLOCK → copy SQL chạy SSMS → khoa sửa trên HIS → IT CLOSE.

### Kiểm tra
- `py_compile` thành công cho `main.py`.
- Cần smoke test trên trình duyệt.

### Lưu ý cho phiên sau
- API `POST /api/records/{id}/approve` đã bị xóa ở phiên trước. `toggleHisUnlock()` (single record) vẫn được giữ lại cho backward compatibility.
- ErrorDefinition phải có `requires_his_reset=True` cho các mã lỗi cần trả hồ sơ, nếu không tab này sẽ không tìm thấy ca nào.



### Mục tiêu
- Đơn giản hóa logic xử lý hồ sơ và trạng thái tại giao diện khoa lâm sàng.
- Bỏ quy trình khoa gửi duyệt IT qua webapp; thay bằng liên hệ trực tiếp.
- Thêm màn hình thống kê theo tháng cho khoa.

### Thay đổi
- `web_app/models.py`: cập nhật comment trạng thái, bỏ `WAITING_REVIEW`.
- `web_app/main.py`:
  - **Xóa** `POST /api/records/{record_id}/flag` (khoa gắn cờ gửi IT duyệt).
  - **Xóa** `GET /api/records/admin/review` (IT xem danh sách chờ duyệt).
  - **Xóa** `POST /api/records/{record_id}/approve` (IT duyệt và sinh SQL reset).
  - Cập nhật `GET /api/records/dept`: thêm lọc tháng, gom PENDING+WAITING_RESEND thành "Chưa xử lý".
  - **Thêm** `GET /api/records/dept/stats?month=YYYY-MM` (thống kê theo tháng cho khoa).
  - **Thêm** `GET /api/export/dept/loi?month=YYYY-MM` (xuất Excel lỗi theo khoa/tháng).
- `web_app/templates/department.html`:
  - Viết lại hoàn toàn giao diện khoa.
  - Bỏ nút hành động, modal ghi chú. Giao diện khoa chỉ đọc.
  - Đổi hướng dẫn: "liên hệ trực tiếp phòng IT".
  - Chỉ còn 2 trạng thái hiển thị: Chưa xử lý / Đã xử lý.
  - Màu sắc theo ngày ra viện: đỏ ≥7 ngày, cam 5-6 ngày, xanh cho RESOLVED.
  - KPI cards: Tổng lỗi, Chưa xử lý, Đã xử lý, Quá 7 ngày.
  - Thêm tab "Thống kê tháng" với: 5 stat cards, progress bar, nút xuất Excel.
  - Bỏ badge mở khóa HIS khỏi giao diện khoa.
- `admin.html`: không cần sửa — không có reference trực tiếp tới WAITING_REVIEW/review/approve.

### Nghiệp vụ ảnh hưởng
- `WAITING_REVIEW` bị loại bỏ khỏi hệ thống. Records hiện có trạng thái này vẫn nằm trong DB nhưng sẽ được auto-resolve khi đối soát lại nếu MA_LK có trong listbh.
- Khoa không còn thao tác gì trên webapp ngoài xem danh sách lỗi và xuất Excel.
- Quy trình mới: Khoa xem lỗi trên webapp → sửa trực tiếp trên HIS → liên hệ IT → IT reset/xử lý trên admin.

### Kiểm tra
- `py_compile` thành công cho `main.py` và `models.py`.
- Cần smoke test với trình duyệt để xác nhận UI hiển thị đúng.

### Lưu ý cho phiên sau
- Records cũ có `status=WAITING_REVIEW` vẫn tồn tại trong DB. Cần migration để chuyển về `PENDING` nếu muốn clean up.
- API `POST /api/records/{record_id}/approve` đã bị xóa. Nếu admin cần sinh SQL reset cho ca LOI, hiện phải dùng `POST /api/records/{record_id}/admin-resolve` hoặc thao tác thủ công.


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
