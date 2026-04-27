# Project: CheckBHYT

## 1. Mục đích phần mềm

CheckBHYT là phần mềm desktop nội bộ dùng để hỗ trợ quy trình kiểm tra và xử lý dữ liệu gửi XML lên cổng Bảo hiểm y tế (BHYT).

Phần mềm này **không trực tiếp tạo XML và không trực tiếp gửi XML**. Vai trò chính của phần mềm là xử lý sau khi người dùng hoặc một hệ thống khác đã gửi XML:

- Đọc danh sách hồ sơ đã gửi thành công/đã ghi nhận từ cổng hoặc phần mềm BHYT.
- Lấy danh sách hồ sơ cần gửi từ cơ sở dữ liệu SQL Server.
- So sánh hai nguồn dữ liệu để tìm các ca còn thiếu, tức có trong database nhưng chưa xuất hiện trong danh sách đã gửi BHYT.
- Sinh hoặc chạy script SQL reset cờ xuất dữ liệu để các ca thiếu được hệ thống gửi XML bên ngoài gửi lại.
- Đọc file lỗi trả về từ cổng BHYT và ghép với thông tin bệnh nhân từ database để nhân viên dễ xử lý.

Tên app khi chạy GUI: `Kiểm tra gửi BHYT (SQL + File) — BNH`.

Entry point hiện tại: `main.py`.

File đóng gói PyInstaller: `KiemTraGuiBHYT.spec`.

## 2. Bối cảnh nghiệp vụ thực tế

Luồng nghiệp vụ ngoài đời được hiểu như sau:

1. Người dùng hoặc phần mềm HIS/EMR/BHYT xuất và gửi các file XML lên cổng BHYT.
2. Sau khi gửi, người dùng lấy danh sách các hồ sơ đã gửi được từ cổng/phần mềm BHYT.
3. Người dùng đưa danh sách đã gửi được vào CheckBHYT.
4. CheckBHYT kết nối SQL Server, chạy stored procedure để lấy danh sách hồ sơ đáng lẽ phải gửi trong khoảng ngày.
5. CheckBHYT so sánh danh sách trong database với danh sách đã gửi được.
6. Những hồ sơ có trong database nhưng không có trong danh sách đã gửi được được xem là `FAIL` hoặc chưa gửi thành công.
7. CheckBHYT tạo script SQL reset các cờ xuất dữ liệu cho những ca `FAIL`.
8. Người dùng có thể copy script để chạy thủ công, hoặc để phần mềm chạy trực tiếp script reset trên database.
9. Sau khi reset, hệ thống gửi XML bên ngoài sẽ gửi lại các ca đó.
10. Người dùng lấy file lỗi từ cổng BHYT, thường là `HoSoLoiChiTiet.xlsx`.
11. Người dùng đưa file lỗi vào CheckBHYT để ghép mã lỗi, mô tả lỗi với thông tin bệnh nhân/khoa/mã thẻ lấy từ database.
12. Kết quả ghép lỗi được xuất Excel để phục vụ sửa dữ liệu hoặc xử lý nghiệp vụ tiếp theo.

Tóm lại, phần mềm nằm ở khâu **đối soát sau gửi**, **reset để gửi lại**, và **tổng hợp lỗi sau khi cổng BHYT trả về**.

## 3. Công nghệ sử dụng

Ngôn ngữ và framework:

- Python 3.13.x.
- PySide6 cho giao diện desktop.
- pandas cho xử lý bảng dữ liệu và Excel.
- pyodbc cho kết nối SQL Server.
- pyperclip để copy script SQL vào clipboard, có fallback sang Qt clipboard nếu thiếu.
- openpyxl gián tiếp qua pandas để đọc/ghi `.xlsx`.
- PyInstaller để đóng gói thành `.exe`.

Thư mục và file chính:

- `main.py`: toàn bộ source chính của phần mềm.
- `main02022026.py`: bản cũ/backup, không phải entry point hiện tại.
- `KiemTraGuiBHYT.spec`: cấu hình PyInstaller, đang trỏ tới `main.py`.
- `checkbh.ico`: icon app khi build.
- `dist/`: output đã build.
- `build/`: output trung gian của PyInstaller.
- `.venv/`: môi trường Python local.

Hiện repo không có `.git`, `README.md`, `requirements.txt`, hoặc test tự động.

## 4. Các nguồn dữ liệu

### 4.1. Dữ liệu từ SQL Server

Phần mềm lấy dữ liệu database bằng cách chạy 2 stored procedure:

- Ngoại trú:
  - `dbo.sp_BCVP_095_DsDeNghiThanhToanBHYT_NgoaiTru_25a_CV5937`
- Nội trú:
  - `dbo.sp_BCVP_096_DsDeNghiThanhToanBHYT_NoiTru_26A_CV5937`

Hai stored procedure được nhập trong tab `SQL (LAN) — Kết nối & xuất sql_list`; người dùng có thể sửa tên SP trên giao diện.

Tham số truyền vào SP:

- `@TuNgay`
- `@DenNgay`

Định dạng ngày truyền vào SQL là `yyyyMMdd`, ví dụ `20260427`.

Các cột bắt buộc từ SP ngoại trú:

- `TenBenhNhan`
- `SoBHYT`
- `Column4`
- `SoPhieuThanhToanNgoaiTru`
- `NgayRa`

Các cột bắt buộc từ SP nội trú:

- `TenBenhNhan`
- `SoBHYT`
- `SoPhieu_BA`
- `khoadieutri`
- `NgayRa`

Nếu thiếu một trong các cột trên, phần mềm sẽ báo lỗi rõ tên cột thiếu và danh sách cột hiện có.

### 4.2. Dữ liệu danh sách đã gửi BHYT

Người dùng chọn file Excel, trên giao diện gọi là `listbh.xlsx` hoặc "file danh sách đã gửi BHYT".

Cấu hình mặc định:

- Cột mã liên kết: `Mã liên kết`
- Cột ngày ra: `Ngày ra`

File này được hiểu là danh sách hồ sơ đã gửi được hoặc đã được cổng/phần mềm BHYT ghi nhận. Phần mềm chỉ cần mã liên kết và ngày ra để đối soát.

Nếu cột ngày trong cấu hình không tồn tại nhưng file có cột `Ngày ra`, phần mềm tự fallback sang `Ngày ra`.

Kết quả đọc file `listbh` được chuẩn hóa thành:

- `MA_LK`
- `_ngay`

Sau đó người dùng lọc theo khoảng ngày trên giao diện.

### 4.3. Dữ liệu file lỗi từ cổng BHYT

Người dùng chọn file Excel lỗi, thường là `HoSoLoiChiTiet.xlsx`.

Cột bắt buộc:

- `MA_LK`

Cột tùy chọn:

- `MALOI`
- `MOTALOI`
- `Ngày ra`

Nếu `MALOI` hoặc `MOTALOI` không tồn tại, phần mềm tự tạo cột rỗng.

File lỗi được ghép với `sql_list` hiện có trong phiên làm việc theo `MA_LK`.

## 5. Dữ liệu đầu ra

Phần mềm có thể xuất các file Excel:

- `sql_list.xlsx`: danh sách hồ sơ lấy từ database sau khi chuẩn hóa.
- `DANH_SACH_FAIL.xlsx`: danh sách hồ sơ có trong database nhưng chưa thấy trong danh sách đã gửi BHYT.
- `DANH_SACH_KEM_LOI.xlsx`: danh sách lỗi từ cổng BHYT đã ghép thêm thông tin bệnh nhân từ database.

Ngoài ra phần mềm có thể:

- Copy SQL reset ngoại trú vào clipboard.
- Copy SQL reset nội trú vào clipboard.
- Chạy trực tiếp SQL reset ngoại trú.
- Chạy trực tiếp SQL reset nội trú.

## 6. Luồng hoạt động trong giao diện

Giao diện chính có nhóm `Quy trình thao tác` với các bước:

1. `Thêm file danh sách đã gửi BHYT`
   - Người dùng chọn file Excel danh sách đã gửi.
   - Code xử lý: `on_add_listbh()`, `load_listbh()`.

2. `Lọc list bh theo ngày`
   - Người dùng chọn `Từ ngày`, `Đến ngày`.
   - Phần mềm lọc danh sách đã gửi theo cột ngày.
   - Code xử lý: `on_filter_bh()`, `filter_listbh_by_date()`.

3. `So sánh dữ liệu database và BHYT`
   - Điều kiện: đã có `sql_list` từ SQL và đã lọc list BHYT.
   - Phần mềm so sánh `MA_LK`.
   - Nếu `MA_LK` có trong danh sách BHYT: trạng thái `Đã gửi BH`.
   - Nếu `MA_LK` không có trong danh sách BHYT: trạng thái `FAIL`.
   - Code xử lý: `on_compare()`, `refresh_compare_table()`.

4. `Copy SQL reset Ngoại trú` / `Copy SQL reset Nội trú`
   - Lấy các ca `FAIL`, tách ngoại trú/nội trú.
   - Sinh script reset cờ xuất dữ liệu.
   - Copy vào clipboard.
   - Code xử lý: `get_reset_keys()`, `build_reset_sql()`, `copy_reset()`.

5. `CHẠY reset Ngoại trú` / `CHẠY reset Nội trú`
   - Lấy các ca `FAIL`, sinh script reset.
   - Hỏi xác nhận trước khi chạy.
   - Chạy script trên database hiện cấu hình.
   - Code xử lý: `run_reset()`, `run_update_sql()`.

6. `Thêm HoSoLoiChiTiet.xlsx`
   - Người dùng chọn file lỗi trả về từ cổng BHYT.
   - Code xử lý: `on_add_loi()`, `load_hosoloichitiet()`.

7. `Ghép lỗi + bỏ trùng hoàn toàn`
   - Ghép file lỗi với thông tin bệnh nhân trong `sql_list`.
   - Bỏ trùng hoàn toàn bằng `drop_duplicates(keep="first")`.
   - Code xử lý: `on_merge_loi()`, `merge_error_with_sql()`.

8. Xuất Excel
   - `Xuất Excel dữ liệu database`: gọi `export_sql_list()`.
   - `Xuất Excel: DANH_SACH_FAIL.xlsx`: gọi `export_fail()`.
   - `Xuất Excel: DANH_SACH_KEM_LOI.xlsx`: gọi `export_loi()`.

## 7. Luồng SQL

Tab SQL có các trường:

- Driver ODBC.
- Server.
- Database.
- Kiểu xác thực:
  - `Windows Auth`
  - `SQL Auth`
- User.
- Password.
- Từ ngày.
- Đến ngày.
- SP Ngoại trú.
- SP Nội trú.

Các action chính:

- `Lưu cấu hình`
  - Ghi vào `config.json`.
  - Code: `on_save_config()`, `save_config()`.

- `Test kết nối`
  - Chạy `SELECT 1`.
  - Code: `on_test_connection()`, `get_conn()`.

- `Chạy SP → Tạo sql_list (có cache)`
  - Chạy 2 stored procedure trong khoảng ngày.
  - Chuẩn hóa thành một dataframe thống nhất.
  - Hiển thị ở tab `sql_list`.
  - Code: `on_run_sp()`, `_run_sp_range()`, `sql_exec_sp()`, `normalize_sql_list()`.

- `Clear cache SQL`
  - Xóa thư mục `cache_sql`.
  - Code: `on_clear_cache()`, `cache_clear_all()`.

## 8. Chuẩn hóa dữ liệu SQL thành sql_list

Hàm chính: `normalize_sql_list(df_op, df_ip)`.

### 8.1. Ngoại trú

Mapping từ SP ngoại trú:

- `Loại ca` = `Ngoại trú`
- `MA_LK` = `Column4`
- `Họ tên` = `TenBenhNhan`
- `Mã thẻ` = `SoBHYT`
- `Tên khoa` = `Khám bệnh`
- `Mã y tế` = `SoPhieuThanhToanNgoaiTru`
- `Ngày ra viện` = `NgayRa`

### 8.2. Nội trú

Mapping từ SP nội trú:

- `Loại ca` = `Nội trú`
- `MA_LK` = `SoPhieu_BA`, sau đó bỏ ký tự `A` ở đầu nếu có.
- `Họ tên` = `TenBenhNhan`
- `Mã thẻ` = `SoBHYT`
- `Tên khoa` = `khoadieutri`
- `Mã y tế` = rỗng
- `Ngày ra viện` = `NgayRa`

### 8.3. Chuẩn hóa chung

Sau khi ghép ngoại trú và nội trú:

- Loại bỏ dòng có `MA_LK` rỗng.
- Chuẩn hóa `MA_LK`.
- Bỏ trùng theo `MA_LK`, giữ dòng đầu tiên.
- Trả về các cột:
  - `Loại ca`
  - `MA_LK`
  - `Họ tên`
  - `Mã thẻ`
  - `Tên khoa`
  - `Mã y tế`
  - `Ngày ra viện`

## 9. Quy tắc chuẩn hóa nghiệp vụ

### 9.1. Chuẩn hóa MA_LK

Hàm: `chuan_hoa_ma_lk(value)`.

Quy tắc:

- Nếu giá trị null/NaN thì trả về chuỗi rỗng.
- Ép sang chuỗi.
- `strip()` khoảng trắng đầu cuối.
- Thay `_CC` bằng `/CC`.

Ví dụ:

- `TN.123_CC` thành `TN.123/CC`.

### 9.2. Bỏ chữ A đầu mã bệnh án nội trú

Hàm: `remove_leading_A(value)`.

Quy tắc:

- Chuẩn hóa `MA_LK`.
- Nếu chuỗi bắt đầu bằng `A`, bỏ ký tự `A` đầu.
- Dùng cho `SoPhieu_BA` của nội trú.

### 9.3. Phân loại ngoại trú/nội trú khi reset

Trong `get_reset_keys(loai)`:

- Ngoại trú: `MA_LK` bắt đầu bằng `TN.`
- Nội trú: `MA_LK` không bắt đầu bằng `TN.`

Đây là giả định nghiệp vụ quan trọng. Nếu format mã liên kết thay đổi, logic reset có thể sai.

## 10. Logic so sánh

Hàm chính: `on_compare()`.

Điều kiện trước khi so sánh:

- `df_sql_list` không rỗng.
- `df_listbh_filtered` không rỗng.

Các bước:

1. Lấy tập `MA_LK` từ danh sách BHYT đã lọc.
2. Chuẩn hóa `MA_LK` của `sql_list`.
3. Với từng dòng trong `sql_list`:
   - Nếu `MA_LK` có trong tập BHYT: `Trạng thái = Đã gửi BH`.
   - Nếu không có: `Trạng thái = FAIL`.
4. Lưu toàn bộ kết quả vào `df_compare`.
5. Lưu riêng danh sách lệch vào `df_fail`.
6. Cập nhật KPI:
   - Tổng ca SQL.
   - Tổng ca BH đã lọc.
   - Đã gửi BH.
   - FAIL.

Lưu ý: phần mềm đang tìm các ca **có trong SQL nhưng không có trong danh sách đã gửi BHYT**. Chiều ngược lại, tức có trong danh sách BHYT nhưng không có trong SQL, hiện chưa được báo riêng.

## 11. Logic reset để gửi lại

Hàm sinh SQL: `build_reset_sql(keys, loai)`.

Mục tiêu reset:

- `Export=0`
- `Export1=0`
- `Export_CV130=0`

### 11.1. Reset ngoại trú

Điều kiện:

- Hồ sơ `FAIL`.
- `MA_LK` bắt đầu bằng `TN.`

SQL sinh ra:

```sql
UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM TiepNhan tn
JOIN XacNhanChiPhi xn ON xn.TiepNhan_Id = tn.TiepNhan_Id
WHERE tn.SoTiepNhan IN (
    ...
);
```

### 11.2. Reset nội trú

Điều kiện:

- Hồ sơ `FAIL`.
- `MA_LK` không bắt đầu bằng `TN.`

SQL sinh ra:

```sql
UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM BenhAn ba
JOIN XacNhanChiPhi xn ON xn.BenhAn_Id = ba.BenhAn_Id
WHERE ba.SoBenhAn IN (
    ...
);
```

### 11.3. Copy và chạy reset

Người dùng có hai lựa chọn:

- Copy script rồi chạy ngoài SQL Server Management Studio hoặc công cụ khác.
- Chạy trực tiếp từ phần mềm.

Khi chạy trực tiếp, phần mềm luôn hiển thị hộp thoại xác nhận với:

- Loại ca.
- Số ca.
- Cảnh báo đang chạy update trên database.

## 12. Logic xử lý file lỗi BHYT

File lỗi được đọc bởi `load_hosoloichitiet(path)`.

Quy tắc:

- File phải có `MA_LK`.
- Nếu thiếu `MALOI`, tạo cột rỗng.
- Nếu thiếu `MOTALOI`, tạo cột rỗng.
- Chuẩn hóa `MA_LK`.
- Nếu có `Ngày ra`, parse về dạng date.

Ghép lỗi bằng `merge_error_with_sql(hsloi, sql_list)`:

- Lấy thông tin bệnh nhân từ `sql_list`:
  - `MA_LK`
  - `Họ tên`
  - `Mã thẻ`
  - `Tên khoa`
  - `Mã y tế`
  - `Ngày ra viện`
- Merge với file lỗi theo `MA_LK`.
- Bỏ trùng hoàn toàn.
- Trả về các cột ưu tiên:
  - `MA_LK`
  - `Họ tên`
  - `Mã thẻ`
  - `Tên khoa`
  - `Mã y tế`
  - `Ngày ra viện`
  - `Ngày ra` nếu file lỗi có
  - `MALOI`
  - `MOTALOI`

Lưu ý: file lỗi chỉ ghép được thông tin bệnh nhân nếu `sql_list` hiện tại có chứa `MA_LK` tương ứng. Nếu người dùng chạy SQL sai khoảng ngày hoặc chưa chạy SQL cho các hồ sơ lỗi, kết quả ghép sẽ thiếu thông tin bệnh nhân.

## 13. Cache SQL

Cache được lưu trong thư mục:

- `cache_sql/`

File index:

- `cache_sql/index.json`

File dữ liệu:

- `cache_sql/sql_list_<TuNgay>.pkl`

Logic cache:

- Cache theo `TuNgay`.
- Nếu chạy lại cùng `TuNgay` và cùng `DenNgay`, dùng cache.
- Nếu chạy lại cùng `TuNgay` nhưng `DenNgay` lớn hơn ngày đã cache, phần mềm chỉ chạy phần thiếu từ ngày kế tiếp sau `cached_end` đến `DenNgay`, sau đó ghép vào cache cũ.
- Nếu `DenNgay` nhỏ hơn `cached_end`, phần mềm chạy full lại để đảm bảo đúng range.

Điểm cần cẩn trọng:

- Cache hiện chỉ key theo `TuNgay`, chưa phân biệt server, database, stored procedure, user, hoặc cấu hình SQL.
- Nếu đổi server/database/SP mà không clear cache, có thể dùng nhầm dữ liệu cũ.
- Khi nghi ngờ dữ liệu không khớp, nên bấm `Clear cache SQL` trước khi chạy lại.

## 14. Config

File config:

- `config.json`

Cấu hình mặc định:

```json
{
  "sql": {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "",
    "database": "",
    "auth": "Windows Auth",
    "user": "",
    "password": ""
  },
  "bh": {
    "listbh_key_col": "Mã liên kết",
    "listbh_date_col": "Ngày ra"
  }
}
```

Lưu ý bảo mật:

- Nếu dùng `SQL Auth`, password hiện được lưu plain text trong `config.json`.
- Không nên commit hoặc chia sẻ `config.json` nếu chứa thông tin thật.

## 15. Trạng thái dữ liệu trong MainWindow

Các dataframe chính:

- `df_listbh_all`: toàn bộ dữ liệu đọc từ file danh sách đã gửi BHYT.
- `df_listbh_filtered`: danh sách BHYT đã lọc theo ngày.
- `df_sql_list`: danh sách hồ sơ từ SQL đã chuẩn hóa.
- `df_compare`: kết quả so sánh toàn bộ `sql_list`.
- `df_fail`: các hồ sơ trong SQL nhưng chưa có trong danh sách BHYT.
- `df_hsloi`: file lỗi BHYT đã đọc.
- `df_loi_merged`: file lỗi đã ghép thông tin từ SQL.

Các bảng hiển thị:

- `tbl_sql`: tab `sql_list`.
- `tbl_bh`: tab `listbh (lọc)`.
- `tbl_compare`: tab `So sánh`.
- `tbl_loi`: tab `Ghép lỗi`.

## 16. KPI trên giao diện

KPI được lưu bằng dataclass `KPI`:

- `tong_sql`: tổng số ca trong `sql_list`.
- `tong_bh`: tổng số ca trong danh sách BHYT đã lọc.
- `da_gui`: số ca SQL đã tìm thấy trong danh sách BHYT.
- `fail`: số ca SQL chưa tìm thấy trong danh sách BHYT.

## 17. Build và chạy

Chạy app từ source:

```powershell
.\.venv\Scripts\python.exe main.py
```

Kiểm tra cú pháp:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py
```

Build bằng PyInstaller:

```powershell
.\.venv\Scripts\pyinstaller.exe KiemTraGuiBHYT.spec
```

File `.exe` sau build:

```text
dist\KiemTraGuiBHYT\KiemTraGuiBHYT.exe
```

File zip hiện có:

```text
dist\KiemTraGuiBHYT0402.zip
```

## 18. Các hàm quan trọng trong `main.py`

Config:

- `load_config()`
- `save_config(cfg)`

Cache:

- `cache_get(tu)`
- `cache_put(tu, den, df)`
- `cache_clear_all()`

Chuẩn hóa:

- `chuan_hoa_ma_lk(value)`
- `remove_leading_A(value)`
- `unique_keep_order(items)`
- `parse_datetime_to_date(series)`

File BHYT đã gửi:

- `load_listbh(path, key_col, date_col)`
- `filter_listbh_by_date(df, tu_ngay, den_ngay)`

SQL:

- `build_conn_str(driver, server, db, auth, user, pw)`
- `get_conn(cfg)`
- `sql_exec_sp(conn, sp_name, tu, den)`
- `run_update_sql(conn, sql_text)`
- `normalize_sql_list(df_op, df_ip)`

Reset:

- `build_reset_sql(keys, loai)`
- `get_reset_keys(loai)`
- `copy_reset(loai)`
- `run_reset(loai)`

File lỗi:

- `load_hosoloichitiet(path)`
- `merge_error_with_sql(hsloi, sql_list)`

GUI:

- `MainWindow`
- `build_tab_sql()`
- `update_buttons()`
- `df_to_table(table, df)`

## 19. Những giả định nghiệp vụ quan trọng

Các agent khác cần đặc biệt chú ý các giả định sau khi sửa code:

1. `listbh.xlsx` đại diện cho danh sách hồ sơ đã gửi được, không phải XML gốc.
2. `MA_LK` là khóa chính để so sánh giữa database, danh sách BHYT và file lỗi.
3. Ngoại trú được xác định bằng `MA_LK.startswith("TN.")`.
4. Nội trú là các mã còn lại.
5. Mã nội trú từ `SoPhieu_BA` có thể bắt đầu bằng `A`; phần mềm bỏ `A` đầu chuỗi trước khi so sánh/reset.
6. `_CC` trong mã liên kết được đổi thành `/CC`.
7. Reset không gửi XML; reset chỉ đưa cờ xuất về `0` để hệ thống gửi XML khác gửi lại.
8. File lỗi BHYT chỉ được ghép với `sql_list` hiện đang có trong bộ nhớ.
9. Cache SQL có thể làm dữ liệu cũ xuất hiện nếu người dùng đổi DB/SP nhưng không clear cache.
10. Password SQL Auth hiện lưu plain text nếu người dùng bấm lưu cấu hình.

## 20. Các rủi ro kỹ thuật hiện tại

### 20.1. UI có thể bị đứng khi chạy dữ liệu lớn

Các thao tác đọc Excel, chạy SP, xử lý pandas, ghi Excel đang chạy trực tiếp trên UI thread. Nếu dữ liệu lớn hoặc SQL chậm, giao diện có thể tạm đứng.

Hướng cải thiện:

- Dùng `QThread` hoặc worker background cho tác vụ SQL/Excel.
- Disable nút khi đang chạy.
- Có progress/status rõ hơn.

### 20.2. Cache chưa đủ khóa định danh

Cache chỉ theo `TuNgay`, nên dễ nhầm nếu đổi:

- Server.
- Database.
- Stored procedure.
- Cột mapping.
- Phiên bản nghiệp vụ.

Hướng cải thiện:

- Cache key nên gồm hash của server, database, SP ngoại trú, SP nội trú, `TuNgay`, `DenNgay`, và có thể version schema.

### 20.3. SQL reset đang ghép chuỗi

`build_reset_sql()` đưa trực tiếp giá trị `MA_LK` vào chuỗi SQL.

Trong nghiệp vụ nội bộ có thể chấp nhận nếu dữ liệu tin cậy, nhưng về kỹ thuật nên escape dấu `'` hoặc dùng bảng tạm/parameterized query khi chạy trực tiếp.

### 20.4. Chưa báo chiều lệch ngược

Hiện phần mềm chỉ báo:

- Có trong SQL nhưng không có trong BHYT.

Chưa báo:

- Có trong BHYT nhưng không có trong SQL.

Nếu cần đối soát đầy đủ, nên thêm một tab hoặc báo cáo "BHYT không có trong SQL".

### 20.5. File lỗi phụ thuộc vào `sql_list` đang có

Nếu người dùng mở file lỗi nhưng chưa chạy SQL đúng range, dữ liệu ghép có thể thiếu `Họ tên`, `Mã thẻ`, `Tên khoa`, `Mã y tế`.

Hướng cải thiện:

- Khi ghép lỗi, cảnh báo số dòng không ghép được.
- Cho phép chạy SQL bổ sung theo ngày trong file lỗi.
- Cho phép import `sql_list.xlsx` đã xuất trước đó.

### 20.6. Chưa có test tự động

Các hàm nghiệp vụ có thể test độc lập:

- `chuan_hoa_ma_lk`
- `remove_leading_A`
- `normalize_sql_list`
- `filter_listbh_by_date`
- `build_reset_sql`
- `load_hosoloichitiet`
- `merge_error_with_sql`

Nên tách business logic ra module riêng để test không cần mở GUI.

## 21. Gợi ý hướng phát triển tiếp theo

Các hướng cải thiện có giá trị cao:

1. Thêm `requirements.txt`.
2. Tách business logic khỏi GUI:
   - `services/sql_service.py`
   - `services/bhyt_compare.py`
   - `services/error_merge.py`
   - `services/cache.py`
3. Thêm test cho các hàm nghiệp vụ.
4. Thêm import nhiều file `listbh` hoặc import cả thư mục nếu thực tế người dùng lấy nhiều file đã gửi.
5. Thêm báo cáo lệch hai chiều.
6. Thêm cảnh báo số dòng lỗi không ghép được thông tin bệnh nhân.
7. Thêm lựa chọn import/export `sql_list` để xử lý offline.
8. Cải thiện cache key.
9. Không lưu password plain text, hoặc tối thiểu không lưu password nếu người dùng không chọn.
10. Chạy SQL/Excel bằng background worker để tránh đứng UI.

## 22. Cách hiểu nhanh cho Agent mới

Nếu cần sửa hoặc mở rộng dự án, hãy hiểu theo thứ tự:

1. `main.py` là source chính.
2. App là PySide6 desktop app, không phải web app.
3. Business key là `MA_LK`.
4. `sql_list` là danh sách hồ sơ đáng lẽ phải gửi, lấy từ SQL Server.
5. `listbh` là danh sách đã gửi được, lấy từ cổng/phần mềm BHYT.
6. `FAIL` là ca có trong SQL nhưng chưa có trong danh sách BHYT.
7. Reset SQL chỉ đặt lại cờ để hệ thống khác gửi lại XML.
8. `HoSoLoiChiTiet.xlsx` là danh sách lỗi sau khi gửi lại, được ghép với `sql_list`.
9. Không sửa `dist/` hoặc `build/` trừ khi đang xử lý đóng gói.
10. Nếu thay đổi nghiệp vụ, ưu tiên sửa hàm nghiệp vụ trước, sau đó cập nhật GUI.

