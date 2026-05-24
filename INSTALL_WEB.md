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

### Bước 3: Cài đặt các thư viện phụ thuộc
Đảm bảo bạn đã kích hoạt môi trường ảo (đầu dòng lệnh có chữ `(.venv)`). Tiến hành cài đặt:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```
*Ghi chú: File `requirements.txt` đã được cấu hình tự động tích hợp đầy đủ mọi thư viện phục vụ cả bản Desktop PySide6 và bản LAN WebApp (FastAPI, Uvicorn, SQLAlchemy, Jinja2, v.v.).*

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
