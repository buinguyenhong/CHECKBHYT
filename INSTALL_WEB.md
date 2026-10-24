# HƯỚNG DẪN TRIỂN KHAI LAN WEBAPP CHECKBHYT TỪ GITHUB

Tài liệu này hướng dẫn chi tiết cách tải mã nguồn hệ thống đối soát BHYT (LAN WebApp) từ GitHub, thiết lập môi trường và vận hành dịch vụ trong mạng LAN nội bộ bệnh viện.

---

## 1. Yêu cầu Hệ thống tối thiểu

*   **Hệ điều hành**: Windows 10/11 hoặc Windows Server 2016/2019/2022.
*   **Python**: Phiên bản 3.10 trở lên (Khuyến nghị **Python 3.13.x**).
*   **ODBC Driver**: Đã cài đặt **ODBC Driver 17 for SQL Server** (hoặc bản 18/SQL Server) trên máy chủ host để phục vụ pyodbc kết nối tới SQL HIS.
*   **Môi trường**: Máy chủ phải kết nối được vào mạng LAN nội bộ chứa cơ sở dữ liệu HIS của bệnh viện.

---

## 2. Các bước Cài đặt & Khởi chạy chi tiết

### Bước 1: Tải mã nguồn từ GitHub về máy tính
Mở công cụ dòng lệnh (PowerShell / Command Prompt) tại thư mục bạn muốn lưu trữ dự án và chạy lệnh:
```bash
git clone https://github.com/username/CHECKBHYT.git
cd CHECKBHYT
```
*(Thay thế URL trên bằng đường dẫn repository thực tế của bạn)*

### Bước 2: Khởi tạo môi trường ảo (Virtual Environment)
Việc sử dụng môi trường ảo giúp cô lập các thư viện của dự án, tránh xung đột hệ thống:
```powershell
# Tạo môi trường ảo tên là .venv
python -m venv .venv

# Kích hoạt môi trường ảo trên Windows
.\.venv\Scripts\activate
```

### Bước 3: Cài đặt các thư viện phụ thuộc & Trình duyệt Playwright
Đảm bảo bạn đã kích hoạt môi trường ảo (đầu dòng lệnh có chữ `(.venv)`). Tiến hành cài đặt:
```powershell
pip install --upgrade pip
pip install -r requirements.txt

# Cài đặt trình duyệt Chromium cho tính năng Tự động hóa Cổng BHYT (Playwright RPA)
playwright install chromium
```
*Ghi chú: File `requirements.txt` đã được cấu hình tự động tích hợp đầy đủ mọi thư viện phục vụ cả bản Desktop PySide6, bản LAN WebApp (FastAPI, Uvicorn, SQLAlchemy, Jinja2) và module Tự động hóa Cổng BHYT Playwright.*


### Bước 4: Khởi chạy Máy chủ LAN WebApp
Khởi động máy chủ dịch vụ bằng tập lệnh tích hợp sẵn:
```powershell
python web_app/run.py
```

Sau khi chạy lệnh, màn hình console sẽ tự động quét và in ra thông tin dạng:
```text
==================================================================
   HE THONG DOI SOAT BHYT MANG NOI BO (LAN WEBAPP) - BNH          
==================================================================
[*] May chu dang khoi chay tai IP LAN: 192.168.1.15
[*] Cac khoa lam sang truy cap qua dia chi:
    http://192.168.1.15:8000
------------------------------------------------------------------
[*] Tai khoan admin mac dinh:
   - Username: admin
   - Password: adminBHYT2026
   (Vui long dang nhap bang quyen IT de cau hinh SQL HIS va tao tk)
==================================================================
Khoi dong may chu uvicorn...
```

---

## 3. Cấu hình & Vận hành lần đầu (Nhiệm vụ của IT)

1.  **Đăng nhập Quản trị viên**:
    *   Mở trình duyệt và truy cập: `http://localhost:8000` (hoặc `http://<IP_MÁY_CHỦ>:8000` từ máy khách).
    *   Đăng nhập bằng tài khoản Quản trị mặc định: `admin` / `adminBHYT2026`.
2.  **Cấu hình kết nối SQL Server HIS**:
    *   Vào **Tab 1: Đồng bộ & Đối soát**.
    *   Nhập đầy đủ thông tin kết nối SQL Server (IP, Database, Driver, Tài khoản sa).
    *   Bấm **"Lưu cấu hình"**, sau đó bấm **"Test kết nối SQL Server"** để xác nhận thông suốt.
3.  **Tạo tài khoản cho các Khoa Lâm Sàng**:
    *   Vào **Tab 4: Quản lý Khoa Phòng**.
    *   Nhập thông tin đăng nhập cho khoa (ví dụ: user `khoasan` / pass `123456`, map đúng tên khoa điều trị là `Sản` hoặc `Khoa Sản` tương ứng trên HIS).
    *   Bác sĩ lâm sàng của khoa đó sẽ đăng nhập bằng tài khoản này để xem và sửa lỗi.
4.  **Vận hành Tab 9: Kiểm tra XML Độc Lập (Validate XML V2)**:
    *   Vào **Tab 9: Kiểm tra XML**.
    *   Bấm **"Cấu hình CSDL XML"** để xác nhận kết nối tới máy chủ CSDL XML (mặc định server `thsrvsql01`, database `eHospital_ThienHanh_XML`).
    *   Bấm **"Kiểm tra XML ca chưa gửi cổng"** để hệ thống tự động lọc các ca chưa gửi thành công từ đợt đối soát hiện tại và thực hiện kiểm tra 116 quy tắc logic theo chuẩn 9324, 4210, 4750.
    *   Theo dõi tiến trình thời gian thực, xem chi tiết lỗi vi phạm và xuất báo cáo Excel (`BaoCao_ValidateXML_*.xlsx`).
    *   Hệ thống chạy hoàn toàn ở chế độ Read-Only, snapshot và kết quả lưu riêng tại tệp `web_app/xml_validation_v2.db`.

---

## 4. Hướng dẫn chạy WebApp dưới dạng Windows Service (Khuyên dùng)

Để WebApp tự động chạy ngầm mỗi khi máy chủ Windows Server khởi động (không cần mở cửa sổ dòng lệnh CMD liên tục):

### Cách 1: Sử dụng File Batch (.bat) kết hợp Task Scheduler
1.  Tạo một file đặt tên là `run_bg.bat` trong thư mục dự án với nội dung:
    ```bat
    @echo off
    cd /d d:\Project\newcheckBHYT\CHECKBHYT\CHECKBHYT
    call .venv\Scripts\activate.bat
    python web_app\run.py
    ```
2.  Mở **Windows Task Scheduler** và tạo một Task mới:
    *   *Trigger*: `At startup` (Khi khởi động máy).
    *   *Action*: `Start a program` $\rightarrow$ Chọn đường dẫn tới file `run_bg.bat`.
    *   *Security options*: Chọn `Run whether user is logged on or not` và tích chọn `Run with highest privileges`.

### Cách 2: Triển khai bằng công cụ NSSM (Khuyên dùng cho Server)
1.  Tải công cụ **NSSM** (Non-Sucking Service Manager) về máy chủ.
2.  Mở CMD bằng quyền Administrator và chạy lệnh:
    ```bash
    nssm.exe install CheckBHYTService
    ```
3.  Trên bảng GUI của NSSM hiện ra, điền thông tin:
    *   *Path*: `d:\Project\newcheckBHYT\CHECKBHYT\CHECKBHYT\.venv\Scripts\python.exe`
    *   *Startup directory*: `d:\Project\newcheckBHYT\CHECKBHYT\CHECKBHYT`
    *   *Arguments*: `web_app/run.py`
4.  Bấm **Install service**. Mở Trình quản lý Services của Windows (`services.msc`), tìm `CheckBHYTService` và bấm **Start**.

---

## 5. Hướng dẫn Vận hành bằng Giao diện Đồ họa (LaunchWebBHYT.py)

Ngoài cách dòng lệnh ở trên, hệ thống tích hợp sẵn công cụ GUI `LaunchWebBHYT.py` giúp quản trị viên thao tác nhanh:
```powershell
python LaunchWebBHYT.py
```
* **Tab 1: Thiết lập & Cài đặt môi trường:** Nhấn "Kích hoạt cài đặt thư viện & Chromium RPA" để tự động cài `requirements.txt` và Playwright Chromium vào môi trường ảo `.venv`.
* **Tab 2: Vận hành Hệ thống:** Khởi chạy máy chủ LAN WebApp chạy ngầm trong Windows, giám sát trạng thái máy chủ (ONLINE / STOPPED), kiểm tra IP LAN và mở trực tiếp trang quản trị.
* **Tab 3: Tự động khởi động (Auto-start):** Đăng ký tự động chạy cùng Windows Task Scheduler chỉ với 1 click chuột mà không cần cấu hình file batch thủ công.

