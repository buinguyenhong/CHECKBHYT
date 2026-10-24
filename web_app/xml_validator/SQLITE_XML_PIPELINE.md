# CHECKBHYT: SQL Server HIS → SQLite → XML Validate

## Mục tiêu

Giữ nguyên đối soát danh sách hồ sơ theo `MA_LK`; dùng danh sách SQL HIS hiện có làm danh sách hồ sơ cần kiểm tra. Với các hồ sơ chưa có trong danh sách cổng/đã gửi, tra cứu `BenhAn_Id` hoặc `TiepNhan_Id`, tìm `XacNhanChiPhi_Id`, đọc các bảng XML đã tồn tại trong `eHospital_ThienHanh_XML`, lưu snapshot vào SQLite rồi chạy bộ `XMLRuleEngine` hiện tại.

## Quy tắc không được vi phạm

- Không gọi `sp_BangKe01_NgoaiTru_eClaim_QD3176`, `sp_Create_BangKe01_NgoaiTru_eClaim_QD3176`, `sp_Create_BangKe02_NoiTru_eClaim_QD3176` hoặc hàm/procedure tạo lại XML trong luồng đọc.
- Không xóa hoặc ghi đè snapshot cũ khi chạy đợt kiểm tra mới.
- Dùng `MA_LK` để đối soát nghiệp vụ. `BenhAn_Id`, `TiepNhan_Id`, `XacNhanChiPhi_Id` chỉ phục vụ truy xuất dữ liệu nội bộ HIS.
- Chỉ dùng SELECT/metadata queries với SQL Server. Ghi dữ liệu snapshot vào SQLite cục bộ.
- Không thay đổi phần bảo mật/đăng nhập/phân quyền trong đợt refactor này.

## Trạng thái triển khai

1. `sql_schema_diagnostic.sql` là script chỉ đọc để xác định schema thực tế của XML1–XML15 và các bảng có cột khóa liên quan. Chạy trong SSMS; script không chạy stored procedure nghiệp vụ và không ghi dữ liệu.
2. `sqlite_snapshot_store.py` tạo kho snapshot theo từng lần chạy, lưu JSON payload, nguồn bảng, khóa nội bộ và SHA-256 để truy vết.
3. Cần dựa trên kết quả schema thật để hoàn thiện adapter SQL đọc XML. Không thể đoán an toàn rằng bảng dùng dạng key/value hay wide-table, cũng không thể đoán tên bảng nối `MA_LK` → `TiepNhan_Id`/`BenhAn_Id` → `XacNhanChiPhi_Id`.
4. Sau khi adapter ánh xạ payload về XML text/field tree đúng định dạng, dùng `XMLRuleEngine.check_rules(ma_lk, xmls)` hiện có. Không thay đổi bộ quy tắc hiện hành trong bước đọc dữ liệu.

## Kết quả cần lấy từ SQL Server

- Danh sách cột và kiểu dữ liệu của `XML1_CV130` … `XML15_CV130`.
- Schema/tên bảng có `XacNhanChiPhi_Id`, `BenhAn_Id`, `TiepNhan_Id`, `MA_LK` hoặc `SoTiepNhan`.
- 5–20 dòng mẫu chỉ đọc từ một bảng XML đã tồn tại (nên che thông tin định danh trước khi chia sẻ kết quả).
- Quan hệ thực tế từ hồ sơ sang `XacNhanChiPhi_Id`.

Không triển khai truy vấn lấy XML cuối cùng cho đến khi các thông tin trên được xác nhận, nhằm tránh đọc nhầm phiên bản hồ sơ hoặc gọi nhầm luồng có side effect.
