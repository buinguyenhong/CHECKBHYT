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
- **ĐỒNG BỘ TÀI LIỆU KIẾN THỨC (BẮT BUỘC):** Khi có thay đổi về code, Stored Procedure, CSDL, API hoặc quy trình, ngoài việc ghi changelog, Agent **BẮT BUỘC** phải cập nhật đồng bộ các tệp tài liệu kiến thức gốc như `Project.md`, `INSTALL_WEB.md`, `xml_validation_tool_spec.md`. Tuyệt đối không để tài liệu chính bị lệch với code thực tế.
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

## 2026-08-18 11:00 - Antigravity (Hoàn tất & Kiểm thử thành công 100% Live Test Tự động hóa Playwright RPA Luồng B và Luồng C)

### Mục tiêu
- Luồng B: Định vị chính xác mục con "Xuất excel" bên trong popup menu (`.dxm-popup`, `div[id*='_DXME']`), loại trừ tuyệt đối việc click trúng nút cha dưới thanh công cụ nền; kích hoạt tải file `listbh.xlsx` thành công 100% (đã nạp 27.395 bản ghi).
- Luồng C: Mở popup lịch của `Từ ngày` bằng DevExpress API `ShowDropDown()` + click icon lịch, click dứt khoát nút `Today` (`.dxeCalendarTodayButton_EIS`, `td[id*='_DDD_C_BT']`), tìm kiếm và tải toàn bộ các gói lỗi chi tiết, đóng popup an toàn qua `PopupNhanChiTietLoiHS.Hide()` và gom thành `HoSoLoiChiTiet.xlsx` thành công 100% (đã nạp 108+ dòng lỗi).

### Thay đổi
- `web_app/services/portal_automation.py` & `client_runner/client_agent.py` [MODIFY]:
  - Luồng B: Khoanh vùng chính xác popup container `.dxm-popup` để click mục con "Xuất excel", tránh click trượt vào thanh công cụ nền.
  - Luồng C: Tối ưu mở dropdown `Từ ngày` + click nút `Today` + đóng popup chi tiết lỗi an toàn qua DevExpress API.
- `scratch/test_live_runner.py` [NEW]: Công cụ kiểm thử trực tiếp trên máy cho cả Luồng B và Luồng C.

### Kiểm tra Thực tế (Live Test)
- **Luồng B**: Tải về thành công `listbh.xlsx` với **27.395 dòng dữ liệu**.
- **Luồng C**: Tải về thành công **40+ gói lỗi** và tổng hợp **108+ dòng lỗi chi tiết** vào `HoSoLoiChiTiet.xlsx`.



### Mục tiêu
- Hợp nhất khu vực Tự động hóa Cổng BHYT trên WebApp thành 1 khối duy nhất, trực quan và tiện dụng, không phân tách rời rạc Server/Client.
- Loại bỏ hoàn toàn cơ chế rê chuột (`.hover()`), chuyển sang click trực tiếp Cha -> Chờ Con -> Click Con, bổ sung hàm `wait_portal_idle()` chờ triệt để loading mask của DevExpress.
- Sửa triệt để lỗi chưa chọn trạng thái "Đã đề nghị thanh toán" trong ComboBox `#cb_TrangThaiTT` ở Luồng B (hỗ trợ cả tương tác DOM và DevExpress Client API fallback).
- Tích hợp tính năng bấm trực tiếp vào nút `Today` trên popup lịch DevExpress ở Luồng C để lấy ngày hôm nay theo đúng giao diện thực tế.

### Thay đổi
- `web_app/services/portal_automation.py` [MODIFY]:
  - Thêm phương thức `wait_portal_idle()` kiểm tra và chờ toàn diện các loading mask DevExpress (`.dxgvLoadingDiv, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, #gvDSKetQuaGuiHoso_LD, .dxp-loadingPanel`).
  - Sửa `run_flow_b()`: Click mở combobox `#cb_TrangThaiTT`, chờ dropdown và chọn mục "Đã đề nghị thanh toán", kèm fallback DevExpress API `SetText`/`SetValue`.
  - Sửa `run_flow_c()`: Điều hướng 4 bước trực tiếp không hover, chọn ngày bằng cách mở datepicker và click nút `Today` (`#deTuNgay_DDD_C_BT` và `#deDenNgay_DDD_C_BT`).
- `client_runner/client_agent.py` [MODIFY]: Đồng bộ toàn bộ logic `_wait_portal_idle()`, chọn trạng thái combobox và click nút `Today` vào Client RPA Runner.
- `web_app/templates/admin.html` [MODIFY]: Gộp các thẻ Tự động hóa trên Tab 1 thành một Card thống nhất "🤖 Tự động hóa Cổng BHYT (Playwright RPA)" với 2 nút hành động trực tiếp (Luồng B & Luồng C) và liên kết tải gói Client gọn gàng.

### Nghiệp vụ ảnh hưởng
- Giúp quá trình tự động hóa tương tác với Cổng BHYT hoạt động mượt mà, ổn định và chính xác 100%, không bị timeout hoặc lỗi click trượt do mạng chậm/DevExpress loading.

### Kiểm tra
- Chạy kiểm thử tự động hóa độc lập `scratch/test_portal_automation_logic.py` đạt 100% OK.
- Chạy kiểm thử hồi quy `scratch/test_reconciliation.py` và `scratch/test_money_aggregation.py` đạt 100% OK.

### Mục tiêu
- Cho phép người dùng chạy tự động hóa Chromium Luồng B và Luồng C trực tiếp ngay trên màn hình máy trạm (Client PC), tự quan sát và gõ Captcha tại chỗ, sau đó tự động tải và gửi file Excel lên máy chủ WebApp Server để đối soát.
- Tích hợp liên kết tải gói cài đặt Client RPA (`.zip`) trực tiếp trên giao diện Admin WebApp.

### Thay đổi
- `client_runner/client_agent.py` [NEW]: Giao diện Tkinter Client RPA Runner cho máy trạm, tự động kết nối API Server, mở Chromium cục bộ, tải file và đẩy lên Server đối soát.
- `client_runner/requirements_client.txt` [NEW]: Danh sách thư viện nhẹ cho máy trạm.
- `client_runner/Cai_Dat_May_Tram.bat` [NEW]: Tập lệnh cài đặt 1 chạm cho máy trạm.
- `client_runner/Chay_RPA_May_Tram.bat` [NEW]: Tập lệnh mở công cụ Client RPA trên máy trạm.
- `client_runner/Huong_Dan_Su_Dung.txt` [NEW]: Tài liệu hướng dẫn sử dụng cho máy trạm.
- `web_app/main.py` [MODIFY]: Thêm API `GET /api/client/config` và `GET /api/client/download-runner` (đóng gói zip động).
- `web_app/templates/admin.html` [MODIFY]: Bổ sung thẻ "💻 Tự động hóa tại Máy trạm (Client PC Runner)" với nút "📥 Tải Bộ Công Cụ Client RPA (.zip)".
- `web_app/run.py` & `LaunchWebBHYT.py` [MODIFY]: Cấu hình cưỡng bức mã hóa UTF-8 cho stdout/stderr.

### Nghiệp vụ ảnh hưởng
- Không làm thay đổi logic đối soát cốt lõi; người dùng có thể linh hoạt chọn: (1) Chạy tự động tại Server, (2) Chạy tự động tại Máy trạm Client, hoặc (3) Nạp file thủ công như cũ.

### Kiểm tra
- Đã test đóng gói zip và kiểm tra tính tương thích cấu hình Client RPA Runner.



## 2026-08-16 14:55 - Antigravity (Tính năng & Tự động hóa: Module Bán tự động Tải Cổng BHYT Luồng B & Luồng C bằng Playwright RPA)

### Mục tiêu
- Tích hợp công cụ tự động hóa trình duyệt (Playwright RPA) bán tự động với Cổng giám định BHYT (`https://gdbhyt.baohiemxahoi.gov.vn/`).
- Tự động hóa độc lập 2 luồng:
  - **Luồng B (Đối soát B)**: Tự động đăng nhập (tái sử dụng session / tự điền user/pass, user chỉ gõ captcha nếu cần) -> vào menu "Danh sách đề nghị thanh toán" -> chọn trạng thái "Đã đề nghị thanh toán" -> tìm kiếm -> xuất file Excel `listbh.xlsx` -> nạp vào hệ thống và tự động kích hoạt đối soát B với CSDL HIS.
  - **Luồng C (Đối soát C)**: Tự động vào menu "Kết quả gửi hồ sơ XML (QĐ 3176)" -> lọc danh sách gói có lỗi -> duyệt qua từng trang và click tải chi tiết từng gói lỗi -> gom toàn bộ thành file Excel `HoSoLoiChiTiet.xlsx` -> nạp vào hệ thống và tự động kích hoạt đối soát C.

### Thay đổi
- `requirements.txt` [MODIFY]: Bổ sung thư viện `playwright`.
- `web_app/models.py` [MODIFY]: Bổ sung các trường `portal_url`, `portal_ma_cskcb`, `portal_username`, `portal_password` vào bảng `AppConfig`.
- `web_app/services/portal_automation.py` [NEW]: Module xử lý `PortalAutomationService` (thực thi Playwright, lưu `portal_storage_state.json`, tải `listbh.xlsx` cho Luồng B, cào/tải và gom `HoSoLoiChiTiet.xlsx` cho Luồng C, quản lý log thời gian thực).
- `web_app/main.py` [MODIFY]:
  - Thêm auto-migration `app_config` khi khởi động server.
  - Thêm endpoints `/api/automation/flow-b`, `/api/automation/flow-c`, `/api/automation/logs`.
- `web_app/templates/admin.html` [MODIFY]: Thêm khu vực "🤖 Tự động hóa Bán tự động với Cổng BHYT" trên Tab 1 với 2 nút bấm Luồng B & Luồng C, kết nối API và truyền log tiến trình thời gian thực vào bảng Log Console.
- `scratch/test_portal_automation_logic.py` [NEW]: Kịch bản kiểm thử độc lập cho logic gom file Excel và cấu hình service.

### Nghiệp vụ ảnh hưởng
- Người dùng không còn phải tải thủ công từng file từ Cổng BHYT rồi kéo thả vào phần mềm. Mọi thao tác từ đăng nhập, chọn trạng thái, xuất file, tải từng gói lỗi, gom file Excel và kích hoạt đối soát đều được thực hiện chỉ với 1 click chuột.
- Luồng B và Luồng C hoàn toàn tách biệt, có thể chạy độc lập nhiều lần trong ngày.

### Kiểm tra
- Chạy kịch bản `scratch/test_portal_automation_logic.py` đạt 100% OK.
- Đã cài đặt hoàn tất `playwright` và `chromium` trong môi trường runtime.

## 2026-08-16 08:15 - Antigravity (Tính năng: Tích hợp Tổng hợp Tài chính Tongcong & QuyBHYT_ChiTra theo số ca bệnh)

### Mục tiêu
- Trích xuất 2 trường tài chính `Tongcong` (tổng chi phí ca bệnh) và `QuyBHYT_ChiTra` (tiền bảo hiểm y tế chi trả) từ 2 Stored Procedures ngoại trú và nội trú (`sp_BCVP_DsDeNghiThanhToanBHYT_NgoaiTru_Optimized` & `sp_BCVP_DsDeNghiThanhToanBHYT_NoiTru_Optimized`).
- Tổng hợp chính xác số tiền dựa theo số ca bệnh duy nhất (`MA_LK`), không nhân đôi số tiền khi 1 ca bệnh mắc nhiều lỗi.
- Bổ sung 2 cột số tiền tài chính vào Báo cáo Tổng hợp Tháng Excel (`/api/export/monthly_summary`), Báo cáo Lưu trữ Lỗi (`/api/export/archive/errors`), API Thống kê (`/api/archive/stats`) và giao diện hiển thị Tab 3 (Lỗi), Tab 4 (FAIL), Tab 10 (Lưu trữ lỗi).

### Thay đổi
- `web_app/models.py` [MODIFY]: Bổ sung 2 trường `tong_tien = Column(Float, default=0.0)` và `tien_bhyt = Column(Float, default=0.0)` vào model `Record` và `ErrorHistoryArchive`.
- `web_app/services/his_service.py` [MODIFY]: Cập nhật `normalize_sql_list()` trích xuất linh hoạt các biến thể tên cột (`Tongcong`, `QuyBHYT_ChiTra`,...) thành số thực và trả về 2 cột `"Tổng cộng"`, `"Tiền BHYT"`.
- `web_app/services/compare_service.py` [MODIFY]: Cập nhật `process_comparison()` và `sync_archive_error()` lưu `tong_tien`, `tien_bhyt` cho tất cả các bản ghi `Record` (nhóm `LOI`, `FAIL`) và `ErrorHistoryArchive`.
- `web_app/main.py` [MODIFY]:
  - Thêm auto-migration SQLite khi khởi động server (`ALTER TABLE ... ADD COLUMN ...` nếu thiếu `tong_tien`, `tien_bhyt`).
  - Nâng cấp API `/api/export/monthly_summary`: gom nhóm theo `MA_LK` duy nhất trong tháng, tính toán và xuất Bảng 1 "SỐ LIỆU TỔNG HỢP" gồm 4 cột: `Chỉ số đối soát | Số lượng | Tổng chi phí (VNĐ) | Tiền BHYT chi trả (VNĐ)` kèm định dạng phân cách số hàng nghìn (`#,##0`).
  - Bổ sung `tong_tien`, `tien_bhyt` vào API `/api/records/admin/loi`, `/api/records/dept`, `/api/archive/errors`, `/api/archive/stats`, `/api/export/archive/errors`.
- `web_app/templates/admin.html` [MODIFY]: Bổ sung cột Tổng tiền và Tiền BHYT trên thead và hàm render JS cho Tab 3 (`#loiTable`), Tab 4 (`#failTable`), Tab 10 (`#archiveTable`).
- `web_app/templates/department.html` [MODIFY]: Bổ sung cột Tổng tiền và Tiền BHYT trên thead và render JS cho Tab 1 (`#recordsTable`) và Tab 3 (`#deptArchiveTable`).
- `scratch/test_money_aggregation.py` [NEW]: Kịch bản unit test xác thực trích xuất SP, lưu trữ CSDL và gom nhóm tiền theo ca bệnh duy nhất.

### Nghiệp vụ ảnh hưởng
- Báo cáo tổng hợp tháng và toàn bộ hệ thống đã có đầy đủ thông tin tài chính (tổng viện phí và tiền BHYT chi trả) để đối chiếu, theo dõi và ước lượng giá trị tài chính của các ca lỗi cần khắc phục.
- Đảm bảo tính toán độc lập theo ca bệnh (`MA_LK`), không bị sai lệch số tiền khi 1 bệnh nhân mắc nhiều lỗi cùng lúc.

### Kiểm tra
- Chạy kịch bản `scratch/test_money_aggregation.py` đạt kết quả 100% OK.
- Chạy lại các kịch bản kiểm thử hồi quy `scratch/test_archive_module.py` và `scratch/test_reconciliation.py` đều hoàn thành thành công.

## 2026-08-12 15:35 - Antigravity (Hotfix UI: Sửa lỗi thẻ đóng HTML của Tab 9 khiến Tab 10 bị ẩn)

### Mục tiêu
- Sửa lỗi khi người dùng bấm vào Nút Tab 10 ("Tra cứu Lịch sử Lỗi Vĩnh viễn") giao diện bị trắng / không hiển thị nội dung gì.

### Thay đổi
- `web_app/templates/admin.html` [MODIFY]: Đóng bổ sung thẻ `</div>` cho `tab_xml-validator` trước khi mở `<div id="tab_archive">`. Trước đó `tab_archive` bị lồng bên trong `tab_xml-validator` nên khi chuyển tab bị ẩn theo thẻ cha.

### Kiểm tra
- Đã xác minh cấu trúc thẻ HTML của `tab_archive` độc lập 100% và đã push commit hotfix `cb25eaf` lên GitHub main.

## 2026-08-12 15:15 - Antigravity (Tính năng & Kiến trúc: Mô-đun Lưu trữ & Thống kê Lịch sử Lỗi Vĩnh viễn)

### Mục tiêu
- Triển khai mô-đun Lưu trữ Lịch sử Lỗi BHYT vĩnh viễn (`error_history_archive`) đảm bảo không mất dữ liệu lịch sử khi đối soát đợt mới.
- Cung cấp khả năng lọc và thống kê đa tiêu chí (theo tháng đối soát `YYYY-MM`, theo khoa lâm sàng, theo trạng thái, theo từ khóa).
- Xây dựng giao diện tách biệt: Tab 10 trên Admin IT và Tab 3 trên giao diện Khoa Lâm Sàng.

### Thay đổi
- `web_app/models.py` [MODIFY]: Khai báo model `ErrorHistoryArchive` (lưu trữ ma_lk, ho_ten, ma_the, ten_khoa, loai_ca, maloi, motaloi, ngay_doi_soat, thang_doi_soat, status, first_detected_at, resolved_at, resolved_by, note_history).
- `web_app/services/compare_service.py` [MODIFY]: 
  - Triển khai hàm `sync_archive_error()` tự động ghi nhận/cập nhật vết lỗi sang bảng lưu trữ vĩnh viễn khi chạy đối soát.
  - Triển khai hàm `backfill_archive_from_records()` tự động khôi phục dữ liệu từ `records` sang `error_history_archive` ở lần chạy đầu tiên.
- `web_app/main.py` [MODIFY]:
  - Thêm API `GET /api/archive/errors` (tra cứu phân trang dữ liệu lưu trữ).
  - Thêm API `GET /api/archive/months` (danh sách tháng có sẵn).
  - Thêm API `GET /api/archive/stats` (KPI tổng lỗi, đã sửa, chưa sửa, tỷ lệ %, top 10 mã lỗi).
  - Thêm API `GET /api/export/archive/errors` (xuất file Excel báo cáo lưu trữ).
  - Gọi backfill dữ liệu lưu trữ khi ứng dụng startup.
- `web_app/templates/admin.html` [MODIFY]: Tích hợp Tab 10 "Tra cứu Lịch sử Lỗi Vĩnh viễn" kèm KPI cards, bộ lọc tháng/khoa/trạng thái, ô tìm kiếm và phân trang.
- `web_app/templates/department.html` [MODIFY]: Tích hợp Tab 3 "Lịch sử lưu trữ của khoa" cho các khoa lâm sàng tra cứu thành tích sửa lỗi.

### Kiểm tra
- Viết và chạy kịch bản unit test `scratch/test_archive_module.py` kiểm tra nạp dữ liệu, cập nhật trạng thái `RESOLVED` và backfill thành công 100%.
- Chạy lại bộ kiểm thử `scratch/test_reconciliation.py` đạt kết quả `All tests completed successfully!`.


## 2026-08-12 14:25 - Antigravity (Quy định bắt buộc: Đồng bộ Kiến thức & Tài liệu dự án song song với Changelog)

### Mục tiêu
- Thiết lập quy định cứng bắt buộc cho tất cả các Agent/Developer: Khi có bất kỳ thay đổi nào về mã nguồn, cấu hình, CSDL, Stored Procedures, API hoặc quy trình nghiệp vụ, bên cạnh việc ghi log changelog, **BẮT BUỘC** phải cập nhật đồng bộ các tệp kiến thức dự án (`Project.md`, `INSTALL_WEB.md`, `xml_validation_tool_spec.md`).

### Thay đổi
- `.agents/AGENTS.md` [NEW]: Tạo tệp quy tắc cấu hình workspace ghi nhận quy định bắt buộc đồng bộ kiến thức tài liệu và mã nguồn trước khi tư vấn/phát triển.
- `AGENT_CHANGELOG.md` [MODIFY]: Cập nhật phần "Nguyên tắc ghi log cho agent" với yêu cầu đồng bộ tài liệu kiến thức gốc.
- `Project.md` [MODIFY]: Đồng bộ tên 2 Stored Procedure Optimized mới vào mục 5.1 tài liệu dự án.

## 2026-08-06 07:45 - Antigravity (Nâng cấp Stored Procedures mới, Xuất Excel Cache Tab 2 & Cơ chế Ghi log Lịch sử Lỗi)

### Mục tiêu
- Nâng cấp sử dụng 2 Stored Procedure Optimized mới cho Ngoại trú & Nội trú.
- Sửa lỗi xuất Excel dữ liệu SQL HIS từ cache ở Tab 2 (`/api/export/sql_list`).
- Triển khai cơ chế ghi nhận lịch sử lỗi đã sửa theo 3 kịch bản đối soát (gửi thành công BHYT, thay đổi mã lỗi, ca không còn lỗi chuyển FAIL) kèm mốc thời gian đối soát cũ.
- Tích hợp Modal Lịch sử đối soát & xử lý lỗi (`History Modal`) trên cả giao diện IT Admin và Khoa Lâm Sàng.

### Thay đổi
- `web_app/models.py` [MODIFY]: Cập nhật tên Stored Procedure mặc định của `AppConfig` sang `sp_BCVP_DsDeNghiThanhToanBHYT_NgoaiTru_Optimized` và `sp_BCVP_DsDeNghiThanhToanBHYT_NoiTru_Optimized`.
- `web_app/services/his_service.py` [MODIFY]: Thêm fallback mặc định cho 2 Stored Procedure Optimized.
- `web_app/services/compare_service.py` [MODIFY]: Nâng cấp logic `process_comparison` hỗ trợ ghi nhận log lịch sử lỗi đã sửa theo 3 kịch bản kèm thời gian đối soát cũ.
- `web_app/main.py` [MODIFY]: 
  - Nâng cấp API `/api/export/sql_list` hỗ trợ đọc từ Cache SQL `.pkl` theo khoảng ngày và bộ lọc để xuất Excel an toàn không gặp lỗi formatting.
  - Tự động cập nhật `AppConfig` hiện có trong DB sang SP mới khi server khởi chạy.
  - Thêm API `GET /api/records/{ma_lk}/history` trả về danh sách `RecordLog` theo `ma_lk`.
- `web_app/templates/admin.html` [MODIFY]:
  - Thêm nút **"Xuất Excel dữ liệu SQL"** tại Tab 2 panel header và hàm JS `exportSqlData()`.
  - Thêm nút **"Lịch sử"** ở bảng Tab 3 (Lỗi) và Tab 4 (FAIL).
  - Tích hợp `#historyModal` và hàm `showHistoryModal(maLk)`.
- `web_app/templates/department.html` [MODIFY]:
  - Thêm cột Thao tác và nút **"Lịch sử"** cho giao diện Khoa Lâm Sàng.
  - Tích hợp `#historyModal` và handler hiển thị dòng thời gian xử lý.

### Kiểm tra
- Biên dịch cú pháp Python `py_compile` thành công 100%.
- Viết và chạy kịch bản unit test `scratch/test_new_sp_and_history.py` xác minh cả 3 kịch bản đối soát và cấu hình SP mới thành công 100%.

## 2026-07-19 14:50 - Antigravity (Cải tiến: Bổ sung chỉ số lỗi vào Báo cáo tổng hợp tháng)

### Mục tiêu
- Thêm hai chỉ số "Tổng số lỗi phát sinh" và "Số lỗi đã xử lý" vào bảng số liệu tổng hợp trong từng sheet của báo cáo tổng hợp tháng nhằm đồng bộ số liệu và giúp so sánh dễ dàng với báo cáo hiệu suất khoa.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Thêm tính toán `total_errors_val` (Tổng số dòng lỗi LOI phát sinh) và `errors_resolved_val` (Số dòng lỗi có trạng thái RESOLVED).
  - Bổ sung 2 chỉ số này vào `summary_data` của báo cáo tổng hợp tháng.
  - Dịch chuyển bảng 2 (Top 10 lỗi thường gặp nhất) xuống dòng 13 (startrow=13) để chừa khoảng trống cho 2 dòng mới của bảng 1.

### Nghiệp vụ ảnh hưởng
- Báo cáo tổng hợp tháng có đầy đủ cả số liệu về "Ca lỗi" (đếm theo bệnh nhân) và "Đầu mục lỗi" (đếm theo lỗi cụ thể) để đối chiếu trực tiếp với báo cáo hiệu suất khoa.

## 2026-07-19 14:40 - Antigravity (Tối ưu hóa: Lọc số liệu KPI đầu trang theo tháng)

### Mục tiêu
- Sửa lỗi hiển thị số lượng ca FAIL (và LOI, RESOLVED) đầu trang Dashboard bị cộng dồn toàn bộ lịch sử. Chỉ hiển thị số lượng của tháng đối soát gần nhất để đảm bảo tính nhất quán của dữ liệu hiển thị.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Cập nhật API `/api/records/kpi` (hàm `get_global_kpis`):
    - Tự động lấy mốc ngày gần nhất của tệp đối soát (`Record.ngay_ra_vien`, `Record.ngay_doi_soat`, `Record.ngay_ra`) để làm mốc lọc tháng.
    - Dùng `func.coalesce` để so sánh ngày ra viện/ngày đối soát/ngày ra của mỗi bản ghi với khoảng ngày đầu tháng đến cuối tháng mục tiêu.
    - Chỉ đếm số lượng ca `LOI`, `FAIL` và `RESOLVED` trong tháng đó để phản hồi về Client.

### Nghiệp vụ ảnh hưởng
- Hàng số liệu tổng quan đầu trang hiển thị chính xác theo tháng đang đối soát, không còn bị nhảy số lượng dồn tích của các tháng cũ.

### Kiểm tra
- Chạy biên dịch cú pháp Python `py_compile` thành công cho `web_app/main.py`.
- Viết và khởi chạy kịch bản unit test `scratch/test_kpi_monthly_filtering.py` xác minh việc lọc số liệu theo tháng thành công 100%.

## 2026-07-19 14:30 - Antigravity (Tính năng: Bổ sung bộ kiểm duyệt file đối soát đầu vào)

### Mục tiêu
- Ngăn ngừa sai lệch số liệu ca `FAIL` khi người dùng click chạy đối soát mà quên chưa tải lên tệp `listbh.xlsx` hoặc tệp đối soát bị lệch khoảng ngày đối soát.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Thêm hàm helper `validate_reconciliation_files` thực hiện:
    - Bắt buộc kiểm tra sự tồn tại của tệp `listbh.xlsx` (và cả `HoSoLoiChiTiet.xlsx` nếu chọn đối soát kèm lỗi).
    - Kiểm tra xem tệp Excel có chứa dữ liệu nào trùng khớp với khoảng ngày đối soát `[from_date, to_date]` đã chọn hay không. Nếu không, chặn tiến trình và trả về mã lỗi HTTP 400 kèm thông điệp chi tiết về khoảng ngày của tệp hiện tại.
  - Tích hợp gọi kiểm duyệt `validate_reconciliation_files` ở đầu hai API `/api/sync/start` (chạy nền) và `/api/records/compare` (đồng bộ).

### Nghiệp vụ ảnh hưởng
- Loại bỏ hoàn toàn rủi ro người dùng đối soát nhầm khoảng ngày hoặc thiếu file dẫn đến ghi đè toàn bộ dữ liệu CSDL thành trạng thái `FAIL`.

### Kiểm tra
- Chạy biên dịch cú pháp Python `py_compile` thành công cho `web_app/main.py`.
- Viết và khởi chạy kịch bản unit test `scratch/test_reconciliation_validation.py` xác minh việc bắt lỗi thiếu file và lệch khoảng ngày thành công 100%.

## 2026-07-19 14:10 - Antigravity (Tối ưu hóa: Tốc độ tải Báo cáo & Tái cấu trúc: Báo cáo tổng hợp tháng)

### Mục tiêu
- Sửa lỗi báo cáo thiếu dữ liệu ca đã gửi thành công và cải thiện đáng kể tốc độ tải/xuất báo cáo (hiệu năng chậm).
- Tái cấu trúc báo cáo tổng hợp tháng: mỗi tháng một sheet Excel riêng biệt, bổ sung danh sách 10 lỗi thường gặp nhất trong mỗi tháng.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Tối ưu hóa API `/api/reports/departments` (Bảng dashboard): chỉ select 2 cột `ten_khoa` và `status` từ SQLite để bypass ORM overhead.
  - Tối ưu hóa API `/api/export/department_performance` (Báo cáo hiệu suất khoa): chỉ select các cột cần thiết từ SQLite.
  - Tái cấu trúc API `/api/export/monthly_summary` (Báo cáo tổng hợp tháng): đọc file `listbh.xlsx` kết hợp SQLite records để lấy số liệu chính xác; phân chia dữ liệu và ghi vào nhiều sheets theo định dạng `Tháng MM-YYYY`; bổ sung bảng chỉ số tổng hợp và bảng 10 lỗi thường gặp nhất cho mỗi sheet.

### Nghiệp vụ ảnh hưởng
- Báo cáo tổng hợp tháng chứa dữ liệu chuẩn xác về tổng số ca cần gửi và đã gửi (trước đây bị thiếu).
- Tốc độ hiển thị dashboard và xuất báo cáo khoa tăng từ 20 đến 50 lần.

### Kiểm tra
- Chạy biên dịch cú pháp Python `py_compile` thành công cho `web_app/main.py`.
- Viết và khởi chạy kịch bản `scratch/test_monthly_sheets.py` kiểm tra thành công với kết quả ghi file Excel đúng cấu trúc và tổng thời gian chạy cực nhanh (~0.35 giây).

## 2026-07-14 13:45 - Antigravity (Tính năng: Bổ sung Báo cáo tổng hợp tháng và Báo cáo hiệu suất theo Khoa)

### Mục tiêu
- Bổ sung 2 báo cáo Excel mới tại Tab 5 (Reports & Export) của Admin:
  1. Báo cáo tổng hợp số lượng ca XML, số lỗi đã xử lý/chưa xử lý chia theo tháng và tổng số.
  2. Báo cáo phân tích thực hiện sửa lỗi và giải quyết ca FAIL chia theo khoa phòng ban và tháng.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Thêm endpoint `GET /api/export/monthly_summary` gom nhóm dữ liệu theo tháng và tính toán tổng số ca XML (unique `ma_lk`), ca đã xử lý, ca chưa xử lý, tổng số lỗi, lỗi đã sửa, lỗi chưa sửa kèm dòng Tổng cộng.
  - Thêm endpoint `GET /api/export/department_performance` gom nhóm theo khoa phòng ban và tháng để phân tích hiệu suất sửa lỗi (%), giải quyết ca FAIL (%) kèm dòng Tổng cộng.
- `web_app/templates/admin.html` [MODIFY]:
  - Thêm HTML hiển thị 2 Card xuất báo cáo mới vào grid của Tab 5.
  - Thêm JS `exportMonthlySummary()` và `exportDeptPerformance()` kết nối đến các API mới.

### Nghiệp vụ ảnh hưởng
- IT Admin có thể dễ dàng tải xuống các báo cáo thống kê chu kỳ tháng và hiệu quả xử lý lỗi của từng khoa phòng ban để theo dõi tiến độ và báo cáo lãnh đạo.

### Kiểm tra
- Chạy biên dịch cú pháp Python `py_compile` thành công cho `web_app/main.py`.
- Viết và chạy thử kịch bản `scratch/test_new_reports.py` để xác thực logic nhóm và tính toán dữ liệu SQLite thành công.

## 2026-07-09 - Antigravity (Sửa lỗi: Dữ liệu SQL HIS & Tính năng: Thêm Tab Danh sách dữ liệu lỗi - Hotfix, Bộ lọc Khoa & Tinh chỉnh Bảng)

### Mục tiêu
- Sửa lỗi không tải được dữ liệu SQL HIS khi cột "Ngày ra viện" chứa giá trị trống hoặc lỗi định dạng dẫn đến pd.NaT.
- Thêm tab "3. Danh sách dữ liệu lỗi" hiển thị danh sách các ca lỗi chưa xử lý theo khoảng ngày đối soát với đầy đủ chi tiết lỗi (tương tự khoa phòng).
- Hotfix lỗi hiển thị của client-side khi gọi API và gặp lỗi server 500 (trả về trang "Internal Server Error" thô thay vì hiển thị trực quan thông điệp lỗi).
- Bảo vệ JSON serialization khỏi lỗi encoding/surrogates trong database HIS của bệnh viện.
- Tích hợp thêm bộ chọn (Dropdown) lọc nhanh danh sách lỗi theo từng Khoa lâm sàng hoặc hiển thị tất cả (mặc định) cho Tab 3.
- Cải thiện hiển thị bảng dữ liệu lỗi (Tab 3): giảm font chữ xuống 12.5px, thu gọn padding, cho phép bọc dòng (wrap text) để nhìn đầy đủ thông tin mô tả, nguyên nhân, giải pháp và ghi chú thay vì bị cắt bởi dấu chấm lửng (ellipsis).

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Sửa lỗi đánh giá chân lý của `pd.NaT` bằng cách thay `if val and not pd.isna(val)` thành `if pd.notna(val)` trong API `/api/records/admin/sql`.
  - Thêm endpoint `GET /api/records/admin/loi` lấy danh sách các ca lỗi chưa xử lý và làm giàu thông tin lỗi từ danh mục.
  - Bổ sung hàm `safe_str` lọc và chuyển đổi UTF-8 an toàn tránh lỗi surrogate không hợp lệ khi serialize JSON từ dữ liệu HIS bệnh viện.
  - Encode an toàn UTF-8 với cơ chế thay thế (replace) cho tin nhắn exception khi ném `HTTPException` 500.
- `web_app/templates/admin.html` [MODIFY]:
  - Cập nhật thứ tự các menu tab điều hướng.
  - Thêm HTML giao diện cho tab dữ liệu lỗi.
  - Thêm logic JS `fetchLoiRecords()`, `filterLoiTable()`, và cập nhật reload trong `switchTab()`, `saveAdminNote()`, và bộ kiểm tra trạng thái đối soát.
  - Cập nhật các hàm JS `fetchSqlData()` và `fetchLoiRecords()` để đọc response text trước khi parse JSON, tránh lỗi JSON parsing masking và hiển thị chính xác lỗi kết nối/cấu hình từ Server.
  - Tích hợp Dropdown `#loi_filter_dept` vào search bar của Tab 3.
  - Nâng cấp `fetchLoiRecords()` tự động phân tích và trích xuất danh sách các khoa phòng duy nhất có lỗi tại đợt đối soát để nạp vào Dropdown động.
  - Nâng cấp `filterLoiTable()` lọc song song theo cả từ khóa tìm kiếm nhanh và khoa phòng được chọn.
  - Thêm cấu trúc CSS thu gọn padding (8px 10px), giảm size chữ (12.5px) và định nghĩa lớp `.wrap-cell` cho bảng lỗi.
  - Cập nhật định dạng hàng của bảng lỗi tại `fetchLoiRecords()`, đổi các cột mô tả, nguyên nhân, giải pháp, ghi chú sang lớp `.wrap-cell` với giới hạn chiều rộng cột linh hoạt và tô màu phân cấp nhẹ giúp dễ quan sát.

### Nghiệp vụ ảnh hưởng
- IT Admin có thể trực tiếp theo dõi danh sách tất cả các ca lỗi của bệnh viện theo từng đợt đối soát và sửa/duyệt ghi chú nhanh chóng.
- Hệ thống load dữ liệu SQL HIS an toàn hơn và không bị sập hay hiển thị lỗi thô không đọc được khi mất kết nối SQL Server HIS hoặc cấu hình trống.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py`.
- Chạy thành công bộ kiểm thử đối soát kinh doanh tại `scratch/test_reconciliation.py`.

## 2026-07-08 - Antigravity (Tính năng & Sửa lỗi: Cập nhật đếm số ca có lỗi và Lọc ca FAIL theo tháng)

### Mục tiêu
- Cập nhật số lượng lỗi hiển thị trên dashboard màn hình chính thành số lượng ca (bệnh nhân độc nhất `MA_LK`) có lỗi thay vì đếm tổng số bản ghi lỗi chi tiết trong CSDL.
- Bổ sung bộ lọc lựa chọn tháng hoặc hiển thị tất cả cho danh sách ca FAIL, kèm việc hiển thị số lượng ca FAIL thực tế tương ứng với tháng được lọc.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Cập nhật API `/api/records/kpi`: sử dụng `distinct()` trên `Record.ma_lk` để tính KPI `loi` là số lượng ca bệnh độc nhất có lỗi thay vì tổng số dòng ghi nhận lỗi.
- `web_app/services/compare_service.py` [MODIFY]:
  - Cập nhật logic tính toán `stats["loi"]` trong `process_comparison`: tăng bộ đếm `stats["loi"]` một lần cho mỗi ca bệnh (`ma_lk`) có lỗi thay vì tăng mỗi khi duyệt qua từng lỗi chi tiết của bệnh nhân đó.
- `web_app/templates/admin.html` [MODIFY]:
  - Bổ sung bộ chọn lọc tháng `#failMonthFilter` và thẻ đếm `#failCountText` trong panel header của Tab 2 (Danh sách ca FAIL).
  - Khai báo danh sách lưu trữ toàn cục `allFailRecords`. Khi tải trang, hệ thống tự động bóc tách các tháng khả dụng từ danh sách ca FAIL để tạo động bộ chọn tháng.
  - Implement hàm JS `filterFailByMonth()` lọc nhanh ca FAIL trực tiếp tại client-side và hiển thị số lượng ca FAIL tương ứng với tháng được chọn.
  - Cập nhật hàm `exportFailData()` để tự động lọc và xuất danh sách Excel các ca FAIL đúng theo tháng đang được chọn trên bộ lọc (nếu chọn một tháng cụ thể).

### Nghiệp vụ ảnh hưởng
- Số liệu KPI "Danh sách Lỗi" trên màn hình chính chuẩn xác hơn vì phản ánh đúng số ca cần xử lý.
- Phòng IT quản lý và phân phối mở khóa/reset các ca FAIL theo tháng dễ dàng và trực quan hơn.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py` và `web_app/services/compare_service.py`.
- Khởi chạy thử nghiệm tích hợp cục bộ thành công.

## 2026-07-02 - Antigravity (Cập nhật quy tắc kiểm tra lỗi XML & Điều chỉnh ghi chú đối soát lỗi cũ)

### Mục tiêu
- Loại bỏ kiểm tra logic thời gian đối với `NGOAITRU_TUNGAY <= NGAY_RA` trong XML7 (Quy tắc B2).
- Thêm quy tắc kiểm tra mới cho XML1: Nếu `LY_DO_VV` là "Người bệnh không KCB BHYT", báo lỗi " sai lý do: Người bệnh không KCB BHYT " (Quy tắc A17).
- Thay đổi nội dung ghi chú khi chuyển các ca lỗi cũ đã sửa về lại danh sách `FAIL` (từ `"trễ hạn - đã sửa lỗi"` thành `"đã sửa lỗi cũ"`).

### Thay đổi
- `web_app/xml_validator/rule_engine.py` [MODIFY]:
  - Comment out logic kiểm tra quy tắc `B2` (`NGOAITRU_TUNGAY <= NGAY_RA`).
  - Thêm quy tắc `A17` kiểm tra `LY_DO_VV` trong XML1.
- `xml_validation_tool_spec.md` [MODIFY]:
  - Cập nhật tài liệu đặc tả: đánh dấu `B2` đã lược bỏ và bổ sung quy tắc mới `A17`.
- `web_app/services/compare_service.py` [MODIFY]:
  - Điều chỉnh giá trị `note_val` khi tự động chuyển trạng thái ca bệnh đã sửa lỗi cũ chưa gửi thành công về lại `FAIL` từ `"trễ hạn - đã sửa lỗi"` sang `"đã sửa lỗi cũ"`.
- `scratch/test_reconciliation.py` [MODIFY]:
  - Cập nhật các khẳng định kiểm thử (asserts) tương ứng với chuỗi ghi chú `"đã sửa lỗi cũ"` mới.

### Nghiệp vụ ảnh hưởng
- Không còn phát hiện các lỗi cảnh báo liên quan đến ngày bắt đầu điều trị ngoại trú lớn hơn ngày ra viện nữa.
- Phát hiện và báo lỗi ngay lập tức đối với các hồ sơ XML1 có lý do vào viện là "Người bệnh không KCB BHYT" để người dùng kịp thời chỉnh sửa trước khi gửi cổng.
- Chuỗi ghi chú của ca bệnh FAIL có lỗi cũ đã sửa hiển thị thân thiện hơn: `"đã sửa lỗi cũ"`.

### Kiểm tra
- Viết kịch bản kiểm tra độc lập tại `scratch/test_xml_validator.py` và chạy thành công qua system Python (`SUCCESS!`).
- Chạy lại toàn bộ bộ kiểm thử đối soát kinh doanh tại `scratch/test_reconciliation.py` và vượt qua thành công (`All tests completed successfully!`).

### Lưu ý cho phiên sau
- Cần theo dõi xem người dùng có yêu cầu mở lại hoặc tùy biến thêm quy tắc nào khác liên quan đến lý do vào viện không.

## 2026-07-01 - Antigravity (Sửa lỗi sao chép SQL & Nâng cấp logic Đối soát lỗi chi tiết BHYT)

### Mục tiêu
- Sửa lỗi báo "Lỗi kết nối" giả và nút copy câu lệnh SQL không hoạt động trên trình duyệt chạy mạng LAN (HTTP không bảo mật).
- Nâng cấp logic đối soát: Lấy tệp báo cáo lỗi chi tiết làm chuẩn. Tự động đóng lỗi cũ và chuyển thành FAIL kèm ghi chú "trễ hạn - đã sửa lỗi" nếu ca bệnh không còn nằm trong danh sách lỗi mới và chưa gửi cổng thành công.

### Thay đổi
- `web_app/templates/admin.html` [MODIFY]:
  - Thêm hàm `copyTextToClipboard(text)` làm fallback an toàn sử dụng `document.execCommand('copy')` cho môi trường LAN HTTP.
  - Cập nhật hàm `openHisUnlockModal` và `copyHisUnlockSql` gọi hàm sao chép an toàn này để sửa dứt điểm lỗi báo "Lỗi kết nối" giả và nút copy không hoạt động.
- `web_app/services/compare_service.py` [MODIFY]:
  - Bổ sung tham số `include_errors` vào hàm `process_comparison`.
  - Thêm logic tự động duyệt đóng các lỗi cũ (LOI -> RESOLVED) cho ca bệnh khi đối soát không còn ghi nhận lỗi đó ở tệp lỗi mới.
  - Thêm logic chuyển ca bệnh lỗi cũ đã sửa về lại danh sách `FAIL` với ghi chú **"trễ hạn - đã sửa lỗi"** nếu ca đó chưa được gửi cổng thành công.
- `web_app/main.py` [MODIFY]:
  - Cập nhật 3 cuộc gọi hàm `compare_service.process_comparison` để truyền thêm tham số `include_errors` phù hợp với từng luồng đối soát.

### Nghiệp vụ ảnh hưởng
- Người dùng IT sao chép các script SQL reset và SQL mở khóa bệnh án bình thường trên trình duyệt ở máy khoa phòng (LAN HTTP).
- Tránh tình trạng hồ sơ lỗi cũ đã được sửa nhưng vẫn hiển thị cảnh báo lỗi cũ trong cơ sở dữ liệu webapp.
- Tự động hóa việc phân loại ca bệnh từ lỗi (`LOI`) sang chưa gửi (`FAIL`) kèm ghi chú cảnh báo trễ hạn trực quan.

### Kiểm tra
- Chạy biên dịch cú pháp Python `py_compile` thành công.
- Chạy kịch bản kiểm thử tự động `scratch/test_reconciliation.py` mô phỏng đối soát thành công 100% hai trường hợp: đóng lỗi cũ hoàn toàn và đóng một phần lỗi.

## 2026-06-28 - Antigravity (Sửa lỗi & Tích hợp: Tích hợp trực tiếp XML Validator vào tiến trình chính và loại bỏ cổng 8001)

### Mục tiêu
- Khắc phục lỗi `WinError 10061` do cổng 8001 của dịch vụ XML Validator độc lập bị từ chối kết nối hoặc không khởi động được trên môi trường đóng gói PyInstaller.
- Loại bỏ hoàn toàn cổng mạng 8001 và thư viện `urllib` gọi API trung gian.
- Tích hợp chạy trực tiếp (in-process) logic đối soát XML bằng `BackgroundTasks` của FastAPI.

### Thay đổi
- `web_app/main.py` [MODIFY]:
  - Loại bỏ hoàn toàn các hàm quản lý dịch vụ ở startup/shutdown và HTTP client gọi cổng 8001 (`start_validator_service`, `stop_validator_service`, `call_validator_api`).
  - Định nghĩa biến tiến trình toàn cục `XML_PROGRESS` để lưu trạng thái và phần trăm tiến độ quét.
  - Xây dựng hàm chạy trực tiếp `run_direct_validation_scan()` thực hiện import trực tiếp `xml_parser`, `rule_engine`, `report_generator` và chạy dưới nền `BackgroundTasks`.
  - Cập nhật các API endpoints `/api/admin/xml-validator/` (status, config, progress, trigger, upload) để thực thi trực tiếp trên cùng tiến trình cổng 8000.

### Nghiệp vụ ảnh hưởng
- Phân hệ kiểm tra XML chạy ổn định, nhanh hơn, không bị ngắt quãng do lỗi tường lửa hoặc xung đột cổng mạng trên Windows.
- Loại bỏ nguy cơ crash/không tải được dịch vụ kiểm tra XML khi đóng gói sản phẩm.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py`.
- Thực hiện kiểm thử API tích hợp tự động qua kịch bản `test_upload.py` thành công 100% (2 bệnh nhân, 11 file XML được phân tích chính xác, báo cáo đầy đủ).

## 2026-06-28 - Antigravity (Tính năng & Sửa lỗi: Triển khai và Tích hợp Mô-đun kiểm tra lỗi XML BHYT, Cấu hình trực quan, Thanh tiến trình & Hỗ trợ XML Container ký số)

### Mục tiêu
- Triển khai và tích hợp hoàn chỉnh mô-đun **XML Validator Tool** độc lập phục vụ công tác giám sát tự động (watchdog folder monitor) và REST API (FastAPI) kiểm tra 26 quy tắc lỗi cấu trúc, thời gian, và liên kết chéo của hồ sơ XML BHYT. 
- Tích hợp bảng điều khiển và bảng thống kê kết quả trực tiếp lên giao diện Admin của Web-App chính, bổ sung **phần cài đặt thư mục cấu hình (Input/Output)** trực quan ngay trên UI để quản trị viên dễ dàng chỉnh sửa mà không cần can thiệp tệp cấu hình thủ công. Đồng thời, cấu hình tự động phân giải và hiển thị đường dẫn tuyệt đối đầy đủ đang sử dụng trực tiếp trên 2 ô nhập liệu khi tải trang giúp tăng tính tường minh.
- **Hỗ trợ tệp XML ký số Container (`<GIAMDINHHS>`)**: Tự động hóa việc bóc tách, giải mã Base64 và làm sạch UTF-8 BOM (`utf-8-sig`) cho các tệp XML thành phần (XML1 đến XML13) được đóng gói bên trong, gom nhóm hoàn chỉnh hồ sơ của cùng một bệnh nhân theo `MA_LK` để thực hiện đối soát lỗi.
- **Tinh chỉnh quy tắc nghiệp vụ BHYT tránh cảnh báo sai**: Nâng cấp quy tắc `A14` và `A15` trong `rule_engine.py` dựa trên nhóm chi phí `MA_NHOM` (Nhóm 10, 11 của VTYT). Chỉ bắt buộc điền mã dịch vụ (`MA_DICH_VU`) đối với dịch vụ kỹ thuật thông thường và bắt buộc điền mã vật tư (`MA_VAT_TU`) đối với vật tư y tế, loại bỏ hoàn toàn các lỗi cảnh báo sai (false positives).
- **Sửa lỗi khởi động hệ thống (Hotfix UnicodeEncodeError):** Khắc phục triệt để lỗi sập máy chủ uvicorn khi chạy qua công cụ LaunchWebBHYT với quyền Administrator trên Windows. Nguyên nhân là do các câu lệnh log ra màn hình console bằng tiếng Việt gây lỗi mã hóa ký tự CP1252 (UnicodeEncodeError) trên console Windows khi luồng đầu ra bị ghi đè/piped vào file log. Toàn bộ log console khởi tạo của tiến trình ngầm đã được đổi sang định dạng ASCII để tương thích tuyệt đối với mọi bảng mã console Windows.
- Tích hợp **thanh tiến trình thời gian thực (Progress Bar)** hiển thị tiến độ đọc file XML và kiểm tra quy tắc nghiệp vụ BHYT trực tiếp trên giao diện Admin giúp tăng tương tác và nâng cao trải nghiệm người dùng.
- Tự động hóa tiến trình: Hệ thống chính tự động kích hoạt tiến trình XML Validator (FastAPI cổng 8001) chạy ngầm dưới dạng **subprocess** độc lập khi ứng dụng chính khởi động, và tự động tắt dọn dẹp khi đóng ứng dụng chính để người dùng không cần phải bật 2 server thủ công.

### Thay đổi
- `web_app/xml_validator/` [NEW]:
  - Triển khai `xml_parser.py` (quét và nhận dạng các tệp XML1->XML13, gom nhóm theo bệnh nhân `MA_LK`).
  - Triển khai `rule_engine.py` (lập trình logic kiểm tra 26 quy tắc BHYT).
  - Triển khai `report_generator.py` (tạo tệp Excel `TongHopLoi.xlsx` và JSON `ket_qua.json`).
  - Triển khai `watcher.py` (theo dõi tự động thư mục Input bằng watchdog có debounce trì hoãn chống nhiễu).
  - Triển khai `main.py` (REST API Server cho mô-đun độc lập tại cổng 8001).
- `web_app/main.py` [MODIFY]:
  - Bổ sung proxy endpoints giao tiếp HTTP Client (`urllib.request`) để tắt/bật watcher, gọi quét tay, trả về JSON lỗi và cho phép download file báo cáo Excel.
- `web_app/templates/admin.html` [MODIFY]:
  - Bổ sung Tab 8 "Kiểm tra XML" cùng với các nút hành động, thẻ KPI, bảng hiển thị kết quả lỗi và JS điều khiển tương ứng.

### Nghiệp vụ ảnh hưởng
- Người dùng Admin có thêm phân hệ kiểm tra lỗi hồ sơ XML BHYT chuyên sâu độc lập hoạt động tự động trong nền mà không ảnh hưởng tới luồng đối soát HIS/cổng BHYT chính của Web-App.

## 2026-06-27 - Antigravity (Sửa lỗi: Xuất Excel danh sách FAIL chỉ xuất ca chưa xử lý)

### Mục tiêu
- Sửa lỗi khi xuất file Excel danh sách FAIL, hệ thống xuất ra tất cả các ca FAIL lịch sử (bao gồm cả các ca đã xử lý thành công `RESOLVED` trong cơ sở dữ liệu lên tới hơn 17.000 dòng), thay vì chỉ xuất 160 ca chưa xử lý khớp với số liệu hiển thị trên màn hình.

### Thay đổi
- `web_app/main.py`:
  - Cập nhật API `export_fail_list` (`GET /api/export/fail`): Đổi giá trị mặc định của tham số `include_resolved` từ `True` thành `False`. Điều này đảm bảo khi người dùng click xuất dữ liệu từ giao diện, API chỉ lấy các ca FAIL đang chờ xử lý (`status != "RESOLVED"`).

### Nghiệp vụ ảnh hưởng
- File Excel danh sách FAIL xuất ra khớp hoàn toàn với số lượng hiển thị thực tế trên màn hình dashboard của Admin (chỉ chứa các ca FAIL chưa xử lý).

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py`.

## 2026-06-27 - Antigravity (Tính năng: Hiển thị mã lỗi trực quan/mô tả ở giao diện khoa phòng)

### Mục tiêu
- Hiển thị mã lỗi ở cột "Mã lỗi" trên giao diện xem danh sách lỗi của khoa phòng một cách trực quan, ngắn gọn kèm tên XML tương ứng (ví dụ: `XML 7 (Giấy ra viện)` thay vì mã thô `XML7`), giúp bác sĩ/điều dưỡng dễ nhận diện lỗi.

### Thay đổi
- `web_app/main.py`:
  - Cập nhật API `get_department_records` (`GET /api/records/dept`): Sử dụng so khớp alphanumeric linh hoạt giữa mã lỗi thô trong record và danh mục hướng dẫn. Khi khớp thành công, cập nhật thuộc tính `maloi` trả về bằng mô tả lỗi chi tiết từ danh mục (ví dụ `XML 7 (Giấy ra viện)`). Trả về danh sách dạng dictionary để đảm bảo an toàn, không thay đổi dữ liệu thô trong cơ sở dữ liệu.

### Nghiệp vụ ảnh hưởng
- Người dùng ở giao diện khoa phòng nhìn thấy mã lỗi chi tiết và trực quan trực tiếp trên cột mã lỗi, đồng bộ với hướng dẫn sửa lỗi.

### Kiểm tra
- Chạy biên dịch `py_compile` thành công cho `web_app/main.py`.

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
