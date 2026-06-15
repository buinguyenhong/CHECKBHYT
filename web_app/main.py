import os
from typing import Optional
import datetime
import base64
import asyncio
from io import BytesIO
from fastapi import FastAPI, Depends, Request, Response, Form, UploadFile, File, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pandas as pd

from database import engine, Base, get_db
from models import User, AppConfig, Record, RecordLog
from auth import (
    hash_password, verify_password, get_current_user, require_admin, SESSION_COOKIE_NAME
)
from services import his_service, excel_service, compare_service

# ==========================================
# XOR CRYPTOGRAPHY FOR HIS DB PASSWORD
# ==========================================
SECRET_KEY = "bnkBHYT_encryptionKey_2026"

def encrypt_password(password: str) -> str:
    if not password:
        return ""
    try:
        pw_bytes = password.encode('utf-8')
        key_bytes = SECRET_KEY.encode('utf-8')
        encrypted_bytes = bytearray()
        for i, b in enumerate(pw_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            encrypted_bytes.append(b ^ key_byte)
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception:
        return ""

def decrypt_password(encrypted_base64: str) -> str:
    if not encrypted_base64:
        return ""
    try:
        encrypted_bytes = base64.b64decode(encrypted_base64.encode('utf-8'))
        key_bytes = SECRET_KEY.encode('utf-8')
        decrypted_bytes = bytearray()
        for i, b in enumerate(encrypted_bytes):
            key_byte = key_bytes[i % len(key_bytes)]
            decrypted_bytes.append(b ^ key_byte)
        return decrypted_bytes.decode('utf-8')
    except Exception:
        return encrypted_base64

def resolve_loai_ca(record: Record) -> str:
    """Trả về 'Ngoại trú' hoặc 'Nội trú' với cơ chế fallback nếu loai_ca bị 'nan' hoặc trống."""
    loai_ca_val = record.loai_ca
    if not loai_ca_val or str(loai_ca_val).strip().lower() in ("nan", "none", ""):
        if record.ma_lk and record.ma_lk.startswith("TN."):
            return "Ngoại trú"
        else:
            return "Nội trú"
    return str(loai_ca_val).strip()

def normalize_date_to_iso(d_str: str) -> str:
    if not d_str:
        return ""
    clean = "".join([c for c in str(d_str) if c.isdigit()])
    if len(clean) == 8:
        return f"{clean[0:4]}-{clean[4:6]}-{clean[6:8]}"
    return ""

# ==========================================
# GLOBAL STATE FOR ASYNC SYNC PROGRESS
# ==========================================
SYNC_PROGRESS = {
    "active": False,
    "progress": 0,
    "status": "Idle",
    "logs": [],
    "should_stop": False
}

def run_sync_in_background(from_date: str, to_date: str, include_errors: bool = False):
    global SYNC_PROGRESS
    SYNC_PROGRESS["active"] = True
    SYNC_PROGRESS["progress"] = 5
    SYNC_PROGRESS["status"] = "Đang bắt đầu..."
    SYNC_PROGRESS["logs"] = ["Khởi chạy tiến trình đối soát & đồng bộ..."]
    if include_errors:
        SYNC_PROGRESS["logs"].append("Chế độ: đối soát kèm file lỗi HoSoLoiChiTiet.xlsx.")
    else:
        SYNC_PROGRESS["logs"].append("Chế độ: đối soát danh sách đã gửi để tìm ca FAIL, chưa dùng file lỗi.")
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        cfg = db.query(AppConfig).first()
        if not cfg:
            SYNC_PROGRESS["active"] = False
            SYNC_PROGRESS["status"] = "Lỗi"
            SYNC_PROGRESS["logs"].append("Lỗi: Chưa cấu hình kết nối SQL Server HIS.")
            return
            
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        SYNC_PROGRESS["progress"] = 15
        SYNC_PROGRESS["status"] = "Đang kết nối SQL Server HIS..."
        SYNC_PROGRESS["logs"].append("Đang kiểm tra kết nối LAN tới CSDL SQL Server...")
        
        password = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
            "password": password,
            "sp_op": cfg.sp_op,
            "sp_ip": cfg.sp_ip
        }
        
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        SYNC_PROGRESS["progress"] = 30
        SYNC_PROGRESS["status"] = "Đang truy vấn SQL Server HIS..."
        SYNC_PROGRESS["logs"].append(f"Truy vấn stored procedure Ngoại trú và Nội trú từ {from_date} đến {to_date}...")
        
        def sync_log(msg):
            SYNC_PROGRESS["logs"].append(msg)
            his_service.safe_print(f"[*] [Sync] {msg}")

        try:
            df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date, log_callback=sync_log)
            if SYNC_PROGRESS.get("should_stop"):
                raise ValueError("Tiến trình bị dừng bởi người dùng.")
            SYNC_PROGRESS["logs"].append(f"Đã tải thành công tổng cộng {len(df_sql)} bản ghi từ CSDL HIS.")
        except Exception as e:
            if SYNC_PROGRESS.get("should_stop") or str(e) == "Tiến trình bị dừng bởi người dùng.":
                raise ValueError("Tiến trình bị dừng bởi người dùng.")
            SYNC_PROGRESS["active"] = False
            SYNC_PROGRESS["status"] = "Lỗi"
            SYNC_PROGRESS["logs"].append(f"Lỗi truy vấn HIS LAN: {str(e)}")
            return
            
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        tu_date = datetime.datetime.strptime(from_date, "%Y%m%d").date()
        den_date = datetime.datetime.strptime(to_date, "%Y%m%d").date()
        
        SYNC_PROGRESS["progress"] = 55
        SYNC_PROGRESS["status"] = "Đang đọc danh sách BHYT..."
        listbh_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
        if os.path.exists(listbh_path):
            df_listbh_raw = excel_service.load_listbh(listbh_path)
            df_listbh = excel_service.filter_listbh_by_date(df_listbh_raw, tu_date, den_date)
            SYNC_PROGRESS["logs"].append(f"Đọc listbh.xlsx thành công. Có {len(df_listbh)} ca trong ngày đối soát.")
        else:
            df_listbh = pd.DataFrame()
            SYNC_PROGRESS["logs"].append("Cảnh báo: Không tìm thấy file listbh.xlsx. Bỏ qua so sánh đẩy cổng.")
            
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        SYNC_PROGRESS["progress"] = 75
        if include_errors:
            SYNC_PROGRESS["status"] = "Đang đọc tệp báo cáo lỗi..."
            loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
            if os.path.exists(loi_path):
                df_hsloi = excel_service.load_hosoloichitiet(loi_path)
                SYNC_PROGRESS["logs"].append(f"Đọc HoSoLoiChiTiet.xlsx thành công. Có {len(df_hsloi)} lỗi chi tiết.")
            else:
                df_hsloi = pd.DataFrame()
                SYNC_PROGRESS["logs"].append("Cảnh báo: Đã bật dùng file lỗi nhưng chưa tìm thấy HoSoLoiChiTiet.xlsx.")
        else:
            df_hsloi = pd.DataFrame()
            SYNC_PROGRESS["status"] = "Bỏ qua file lỗi chi tiết..."
            SYNC_PROGRESS["logs"].append("Bỏ qua HoSoLoiChiTiet.xlsx. Các ca chưa có trong listbh và chưa có lỗi sẽ được xếp nhóm FAIL.")
            
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        SYNC_PROGRESS["progress"] = 85
        SYNC_PROGRESS["status"] = "Đang chạy đối soát & lưu trữ vào SQLite..."
        SYNC_PROGRESS["logs"].append("Đang đối soát 2 chiều, kế thừa ghi chú và tự động duyệt...")
        
        ngay_doi_soat = datetime.date.today()
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat)
        save_last_kpis(db, stats, df_listbh, ngay_doi_soat)
        
        if SYNC_PROGRESS.get("should_stop"):
            raise ValueError("Tiến trình bị dừng bởi người dùng.")

        SYNC_PROGRESS["progress"] = 100
        SYNC_PROGRESS["status"] = "Hoàn tất"
        SYNC_PROGRESS["logs"].append(f"ĐỐI SOÁT HOÀN TẤT THÀNH CÔNG. Ghi nhận: Tổng ca: {stats['total']} | Lỗi BHYT: {stats['loi']} | FAIL: {stats['fail']} | Đã gửi: {stats['sent']}")
        SYNC_PROGRESS["active"] = False
        
    except Exception as e:
        SYNC_PROGRESS["active"] = False
        if SYNC_PROGRESS.get("should_stop") or str(e) == "Tiến trình bị dừng bởi người dùng.":
            SYNC_PROGRESS["status"] = "Đã dừng"
            SYNC_PROGRESS["logs"].append("Tiến trình đối soát đã DỪNG theo yêu cầu người dùng.")
        else:
            SYNC_PROGRESS["status"] = "Lỗi"
            SYNC_PROGRESS["logs"].append(f"Lỗi đối soát ngầm: {str(e)}")
    finally:
        db.close()

# 1. Khởi tạo cơ sở dữ liệu SQLite
Base.metadata.create_all(bind=engine)

# Tự động đồng bộ các cột mới trong app_config nếu đã tồn tại CSDL cũ
from sqlalchemy import text
try:
    with engine.begin() as conn:
        res = conn.execute(text("PRAGMA table_info(app_config)")).fetchall()
        columns = [r[1] for r in res]
        if "auto_sync_enabled" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN auto_sync_enabled BOOLEAN DEFAULT 0"))
        if "auto_sync_time" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN auto_sync_time VARCHAR DEFAULT '00:30'"))
        if "last_sync_date" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_sync_date DATE"))
        if "last_tong_sql" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_tong_sql INTEGER DEFAULT 0"))
        if "last_tong_bh" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_tong_bh INTEGER DEFAULT 0"))
        if "last_da_gui" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_da_gui INTEGER DEFAULT 0"))
        if "last_loi" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_loi INTEGER DEFAULT 0"))
        if "last_fail" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_fail INTEGER DEFAULT 0"))
        if "last_resolved" not in columns:
            conn.execute(text("ALTER TABLE app_config ADD COLUMN last_resolved INTEGER DEFAULT 0"))
            
        res_rec = conn.execute(text("PRAGMA table_info(records)")).fetchall()
        columns_rec = [r[1] for r in res_rec]
        if "his_unlock_status" not in columns_rec:
            conn.execute(text("ALTER TABLE records ADD COLUMN his_unlock_status VARCHAR DEFAULT 'NORMAL'"))
except Exception as e:
    print(f"[*] Thong tin di tru tu dong: {e}")

app = FastAPI(
    title="CheckBHYT LAN WebApp",
    description="Hệ thống đối soát BHYT chạy mạng LAN nội bộ bệnh viện",
    version="2.0.0"
)

def save_last_kpis(db: Session, stats: dict, df_listbh: pd.DataFrame, ngay_doi_soat: datetime.date):
    """Lưu KPI lần đối soát gần nhất. Không dùng count(records) vì records chỉ lưu ca cần xử lý."""
    cfg = db.query(AppConfig).first()
    if not cfg:
        cfg = AppConfig()
        db.add(cfg)

    cfg.last_sync_date = ngay_doi_soat
    cfg.last_tong_sql = int(stats.get("total", 0))
    cfg.last_tong_bh = int(len(df_listbh)) if df_listbh is not None else 0
    cfg.last_da_gui = int(stats.get("sent", 0))
    cfg.last_loi = int(stats.get("loi", 0))
    cfg.last_fail = int(stats.get("fail", 0))
    cfg.last_resolved = db.query(Record).filter(Record.status == "RESOLVED").count()
    db.commit()

# 2. Tạo tài khoản admin mặc định & config mặc định khi khởi chạy
db = next(get_db())
try:
    # Seed tài khoản admin
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed = hash_password("adminBHYT2026")
        new_admin = User(username="admin", password_hash=hashed, role="admin", department_name="")
        db.add(new_admin)
        db.commit()
        print("[*] Da tao tai khoan admin mac dinh: admin / adminBHYT2026")

    # Seed cấu hình mặc định
    cfg = db.query(AppConfig).first()
    if not cfg:
        new_cfg = AppConfig()
        db.add(new_cfg)
        db.commit()
        print("[*] Da khoi tao cau hinh CSDL HIS mac dinh.")

    # Seed danh mục lỗi mẫu
    from models import ErrorDefinition
    err_count = db.query(ErrorDefinition).count()
    if err_count == 0:
        sample_errors = [
            ErrorDefinition(error_code="XML3", keyword="DIEN_BIEN_LS", root_cause="Khoa lâm sàng quên nhập diễn biến bệnh án lúc cho ra viện", resolution="Mở bệnh án HIS -> Tab Khám bệnh -> Điền đầy đủ Diễn biến lâm sàng rồi bấm Lưu", requires_his_reset=True),
            ErrorDefinition(error_code="XML3", keyword="TOMTAT_KQ", root_cause="Thiếu tóm tắt kết quả cận lâm sàng quan trọng", resolution="Nhập đầy đủ thông tin tóm tắt kết quả cận lâm sàng trên phần mềm HIS rồi cho ra viện lại", requires_his_reset=True),
            ErrorDefinition(error_code="XML8", keyword="MA_TTDV", root_cause="Thiếu mã tương đương dịch vụ kỹ thuật hoặc thuốc", resolution="Liên hệ phòng IT để cập nhật danh mục tương đương hoặc ánh xạ mã dịch vụ kỹ thuật", requires_his_reset=False),
            ErrorDefinition(error_code="XML5", keyword="NGAY_TH_YL", root_cause="Ngày thực hiện y lệnh bị trống hoặc sai định dạng", resolution="Sửa lại ngày thực hiện y lệnh trên HIS cho khớp với ngày ra viện", requires_his_reset=True),
            ErrorDefinition(error_code="XML1", keyword="XML1", root_cause="Thông tin XML1 (Tổng hợp) chưa chuẩn xác, sai lệch số tiền hoặc thẻ BHYT", resolution="Kiểm tra lại thẻ BHYT của bệnh nhân hoặc tính toán lại chi phí trên HIS trước khi phê duyệt gửi cổng", requires_his_reset=False)
        ]
        db.add_all(sample_errors)
        db.commit()
        print("[*] Da khoi tao danh muc huong dan loi mau.")
finally:
    db.close()

# 3. Cấu hình Templates & Static files
# Tạo thư mục static trống nếu chưa tồn tại
os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


# ==========================================
# ROUTERS: RENDERING PAGES
# ==========================================

@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    """Chuyển hướng trang dựa trên trạng thái đăng nhập"""
    username = request.cookies.get(SESSION_COOKIE_NAME)
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/department", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Trang đăng nhập"""
    return templates.TemplateResponse(request=request, name="login.html")


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user: User = Depends(require_admin)):
    """Bảng điều khiển dành cho phòng IT"""
    return templates.TemplateResponse(request=request, name="admin.html")


@app.get("/department", response_class=HTMLResponse)
def department_page(request: Request, user: User = Depends(get_current_user)):
    """Bảng điều khiển dành cho các Khoa Lâm Sàng"""
    if user.role == "admin":
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="department.html")


# ==========================================
# API: AUTHENTICATION
# ==========================================

@app.post("/auth/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Đăng nhập hệ thống & thiết lập Cookie"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(user.password_hash, password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác"
        )
        
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=username,
        httponly=True,
        max_age=86400 * 30  # Lưu session 30 ngày
    )
    return {"status": "success", "role": user.role}


@app.post("/auth/logout")
def logout():
    """Đăng xuất hệ thống & Xóa Cookie"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/auth/me")
def get_me(user: User = Depends(get_current_user)):
    """Lấy thông tin tài khoản đang đăng nhập"""
    return {
        "username": user.username,
        "role": user.role,
        "department_name": user.department_name
    }


# ==========================================
# API: DATABASE CONFIG & TEST (IT ONLY)
# ==========================================

@app.get("/api/config")
def get_config(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Lấy cấu hình kết nối SQL Server HIS hiện tại (ẩn mật khẩu thực tế)"""
    cfg = db.query(AppConfig).first()
    if not cfg:
        return None
    return {
        "driver": cfg.driver,
        "server": cfg.server,
        "database": cfg.database,
        "auth": cfg.auth,
        "user": cfg.user,
        "password": "••••••••" if cfg.password else "",
        "sp_op": cfg.sp_op,
        "sp_ip": cfg.sp_ip,
        "auto_sync_enabled": getattr(cfg, "auto_sync_enabled", False),
        "auto_sync_time": getattr(cfg, "auto_sync_time", "00:30")
    }


@app.post("/api/config")
def save_config(
    cfg_data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cập nhật cấu hình CSDL HIS (mã hóa mật khẩu)"""
    cfg = db.query(AppConfig).first()
    if not cfg:
        cfg = AppConfig()
        db.add(cfg)

    cfg.driver = cfg_data.get("driver", cfg.driver)
    cfg.server = cfg_data.get("server", cfg.server)
    cfg.database = cfg_data.get("database", cfg.database)
    cfg.auth = cfg_data.get("auth", cfg.auth)
    cfg.user = cfg_data.get("user", cfg.user)
    
    new_pw = cfg_data.get("password", "")
    if new_pw and new_pw != "••••••••":
        cfg.password = encrypt_password(new_pw)
        
    cfg.sp_op = cfg_data.get("sp_op", cfg.sp_op)
    cfg.sp_ip = cfg_data.get("sp_ip", cfg.sp_ip)
    cfg.auto_sync_enabled = cfg_data.get("auto_sync_enabled", False)
    cfg.auto_sync_time = cfg_data.get("auto_sync_time", "00:30")

    db.commit()
    return {"status": "success"}


@app.get("/api/config/drivers")
def get_available_drivers(user: User = Depends(require_admin)):
    """Lấy danh sách các ODBC drivers đã cài đặt trên hệ thống máy chủ"""
    try:
        import pyodbc
        drivers = pyodbc.drivers()
    except Exception:
        drivers = []
    return {"drivers": drivers}


@app.post("/api/config/clear-cache")
def clear_his_cache(user: User = Depends(require_admin)):
    """Xóa toàn bộ các tệp cache truy vấn SQL Server HIS để giải phóng dung lượng và tải mới dữ liệu"""
    try:
        his_service.clear_sql_cache()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/error-definitions")
def get_error_definitions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lấy danh sách danh mục hướng dẫn lỗi"""
    from models import ErrorDefinition
    defs = db.query(ErrorDefinition).all()
    return defs


@app.post("/api/error-definitions")
def save_error_definition(
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Thêm mới hoặc cập nhật một định nghĩa lỗi"""
    from models import ErrorDefinition
    def_id = data.get("id")
    if def_id:
        err_def = db.query(ErrorDefinition).filter(ErrorDefinition.id == def_id).first()
    else:
        err_def = None
        
    if not err_def:
        err_def = ErrorDefinition()
        db.add(err_def)
        
    err_def.error_code = data.get("error_code", "").strip()
    err_def.keyword = data.get("keyword", "").strip()
    err_def.root_cause = data.get("root_cause", "").strip()
    err_def.resolution = data.get("resolution", "").strip()
    err_def.requires_his_reset = data.get("requires_his_reset", False)
    
    db.commit()
    return {"status": "success", "id": err_def.id}


@app.delete("/api/error-definitions/{id}")
def delete_error_definition(
    id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xóa một định nghĩa lỗi khỏi danh mục"""
    from models import ErrorDefinition
    err_def = db.query(ErrorDefinition).filter(ErrorDefinition.id == id).first()
    if not err_def:
        raise HTTPException(status_code=404, detail="Không tìm thấy lỗi cần xóa")
    db.delete(err_def)
    db.commit()
    return {"status": "success"}


@app.post("/api/records/{id}/toggle-his-unlock")
def toggle_record_his_unlock(
    id: int,
    action_type: str = Form(...), # 'UNLOCK' | 'CLOSE'
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Bật/Tắt trạng thái mở khóa bệnh án và sinh script TrangThai cho IT copy chạy trên SSMS"""
    record = db.query(Record).filter(Record.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ bệnh nhân này")
        
    ma_lk = record.ma_lk

    if action_type not in {"UNLOCK", "CLOSE"}:
        raise HTTPException(status_code=400, detail="Loại thao tác mở/khóa HIS không hợp lệ.")

    if resolve_loai_ca(record) != "Nội trú":
        raise HTTPException(status_code=400, detail="Script mở khóa bệnh án hiện chỉ áp dụng cho ca Nội trú.")

    sql_command = his_service.build_benhan_unlock_sql([ma_lk], action_type)

    if action_type == "UNLOCK":
        record.his_unlock_status = "UNLOCKED"
        log_action = "IT Admin sinh script đưa BenhAn.TrangThai về DaXuatVien để khoa sửa."
    else:
        record.his_unlock_status = "NORMAL"
        log_action = "IT Admin sinh script đưa BenhAn.TrangThai về DaThanhToan để khóa lại sau khi khoa sửa."
        
    new_log = RecordLog(
        record_id=record.id,
        username=user.username,
        action="CHANGE_STATUS",
        note=log_action
    )
    db.add(new_log)
    db.commit()
    
    return {
        "status": "success", 
        "his_unlock_status": record.his_unlock_status,
        "sql_command": sql_command
    }


@app.post("/api/admin/bulk-unlock")
def bulk_unlock_department_records(
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    IT sinh script mở khóa / khóa lại bệnh án hàng loạt theo khoa.
    Chỉ lấy các ca LOI chưa RESOLVED mà ErrorDefinition đánh dấu requires_his_reset=True.
    """
    department_name = data.get("department_name", "").strip()
    action_type = data.get("action_type", "").strip()  # 'UNLOCK' | 'CLOSE'
    
    if not department_name:
        raise HTTPException(status_code=400, detail="Chưa chọn khoa phòng.")
    if action_type not in {"UNLOCK", "CLOSE"}:
        raise HTTPException(status_code=400, detail="Loại thao tác không hợp lệ. Chỉ hỗ trợ UNLOCK hoặc CLOSE.")

    # 1. Lấy danh sách mã lỗi cần trả hồ sơ về khoa
    from models import ErrorDefinition
    reset_defs = db.query(ErrorDefinition).filter(
        ErrorDefinition.requires_his_reset == True
    ).all()
    
    if not reset_defs:
        return {
            "status": "success",
            "sql_command": "-- Chưa có mã lỗi nào được đánh dấu 'Cần trả hồ sơ về khoa' trong danh mục Hướng dẫn Lỗi.",
            "count": 0,
            "records": []
        }

    # 2. Lấy tất cả ca LOI chưa RESOLVED của khoa
    dept_records = db.query(Record).filter(
        Record.ten_khoa == department_name,
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()

    # 3. Lọc theo ErrorDefinition: chỉ lấy ca khớp mã lỗi + keyword
    matched_records = []
    for r in dept_records:
        for d in reset_defs:
            if d.error_code == r.maloi:
                if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                    matched_records.append(r)
                    break

    if not matched_records:
        action_label = "mở khóa" if action_type == "UNLOCK" else "khóa lại"
        return {
            "status": "success",
            "sql_command": f"-- Không có ca nào trong khoa [{department_name}] cần {action_label} bệnh án.",
            "count": 0,
            "records": []
        }

    # 4. Lọc chỉ lấy nội trú (script mở khóa bệnh án chỉ áp dụng nội trú)
    noi_tru_records = [r for r in matched_records if resolve_loai_ca(r) == "Nội trú"]
    ngoai_tru_records = [r for r in matched_records if resolve_loai_ca(r) != "Nội trú"]

    keys = [r.ma_lk for r in noi_tru_records]
    sql_command = his_service.build_benhan_unlock_sql(keys, action_type) if keys else ""

    # Nếu có ca ngoại trú khớp ErrorDef nhưng không cần mở khóa, ghi chú thêm
    notes = []
    if ngoai_tru_records:
        notes.append(f"-- Lưu ý: Có {len(ngoai_tru_records)} ca ngoại trú cần sửa lỗi nhưng không cần mở khóa bệnh án.")
    if not keys:
        sql_command = "-- Không có ca nội trú nào cần mở khóa bệnh án trong khoa này."
        if notes:
            sql_command = "\n".join(notes) + "\n" + sql_command

    if keys:
        if notes:
            sql_command = "\n".join(notes) + "\n\n" + sql_command
            
        # 5. Cập nhật trạng thái mở khóa cho từng record
        new_status = "UNLOCKED" if action_type == "UNLOCK" else "NORMAL"
        action_label = "Trả hồ sơ về khoa (mở khóa bệnh án)" if action_type == "UNLOCK" else "Khóa lại bệnh án sau khi khoa sửa xong"
        
        for r in noi_tru_records:
            r.his_unlock_status = new_status
            log = RecordLog(
                record_id=r.id,
                username=user.username,
                action="CHANGE_STATUS",
                note=f"[Hàng loạt] {action_label}. Khoa: {department_name}"
            )
            db.add(log)
        db.commit()

    # Trả về thông tin ca đã xử lý để frontend hiển thị
    record_info = []
    for r in noi_tru_records:
        record_info.append({
            "ma_lk": r.ma_lk,
            "ho_ten": r.ho_ten,
            "ma_the": r.ma_the,
            "maloi": r.maloi,
            "motaloi": r.motaloi
        })

    return {
        "status": "success",
        "sql_command": sql_command,
        "count": len(noi_tru_records),
        "ngoai_tru_count": len(ngoai_tru_records),
        "records": record_info
    }


@app.get("/api/admin/dept-unlock-preview")
def preview_department_unlock(
    department_name: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xem trước danh sách ca LOI của khoa và cờ requires_his_reset"""
    from models import ErrorDefinition
    reset_defs = db.query(ErrorDefinition).filter(
        ErrorDefinition.requires_his_reset == True
    ).all()

    dept_records = db.query(Record).filter(
        Record.ten_khoa == department_name,
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()

    matched = []
    for r in dept_records:
        requires_reset = False
        for d in reset_defs:
            if d.error_code == r.maloi:
                if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                    requires_reset = True
                    break
        matched.append({
            "id": r.id,
            "ma_lk": r.ma_lk,
            "ho_ten": r.ho_ten,
            "ma_the": r.ma_the,
            "maloi": r.maloi,
            "motaloi": r.motaloi,
            "loai_ca": resolve_loai_ca(r),
            "ngay_ra_vien": r.ngay_ra_vien.isoformat() if r.ngay_ra_vien else "",
            "his_unlock_status": r.his_unlock_status or "NORMAL",
            "requires_his_reset": requires_reset
        })

    noi_tru_reset = len([m for m in matched if m["loai_ca"] == "Nội trú" and m["requires_his_reset"]])

    return {
        "department_name": department_name,
        "total": len(matched),
        "noi_tru_reset": noi_tru_reset,
        "records": matched
    }

@app.post("/api/config/test-connection")
def test_his_connection(
    test_data: dict = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Kiểm tra kết nối CSDL HIS trên mạng LAN. Hỗ trợ cả test cấu hình lưu sẵn hoặc test cấu hình truyền trực tiếp từ UI"""
    cfg = db.query(AppConfig).first()
    
    if test_data:
        driver = test_data.get("driver")
        server = test_data.get("server")
        database = test_data.get("database")
        auth = test_data.get("auth")
        user_db = test_data.get("user")
        password_raw = test_data.get("password", "")
        
        if password_raw == "••••••••":
            password_plain = decrypt_password(cfg.password) if (cfg and cfg.password) else ""
        else:
            password_plain = password_raw
    else:
        if not cfg:
            raise HTTPException(status_code=400, detail="Chưa cấu hình thông tin kết nối")
        driver = cfg.driver
        server = cfg.server
        database = cfg.database
        auth = cfg.auth
        user_db = cfg.user
        password_plain = decrypt_password(cfg.password) if cfg.password else ""

    try:
        cfg_dict = {
            "driver": driver,
            "server": server,
            "database": database,
            "auth": auth,
            "user": user_db,
            "password": password_plain
        }
        success = his_service.test_connection(cfg_dict)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# API: EXCEL FILE UPLOADS (IT ONLY)
# ==========================================

# Thư mục tạm lưu trữ tệp Excel tải lên
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload/listbh")
async def upload_listbh(
    file: UploadFile = File(...),
    user: User = Depends(require_admin)
):
    """Tải lên file Excel danh sách BHYT đã gửi"""
    try:
        contents = await file.read()
        df = excel_service.load_listbh(BytesIO(contents))
        
        # Lưu file tạm cục bộ để dùng đối soát sau
        save_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
        with open(save_path, "wb") as f:
            f.write(contents)
            
        return {"status": "success", "rows": len(df), "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi đọc file Excel listbh: {str(e)}")


@app.post("/api/upload/loi")
async def upload_loi(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Tải lên file Excel báo cáo lỗi chi tiết từ cổng BHYT và tự động cập nhật/ghép lỗi ngay lập tức"""
    try:
        contents = await file.read()
        df = excel_service.load_hosoloichitiet(BytesIO(contents))
        
        # Lưu file tạm cục bộ để dùng đối soát sau
        save_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
        with open(save_path, "wb") as f:
            f.write(contents)
            
        # 1. Tìm ngày đối soát gần nhất có dữ liệu
        last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
        updated_count = 0
        if last_record and not df.empty:
            target_date = last_record.ngay_doi_soat
            # Chuyển df thành dictionary để tra cứu nhanh O(1)
            error_map = {}
            for _, row in df.iterrows():
                lk = his_service.chuan_hoa_ma_lk(row["MA_LK"])
                if lk:
                    error_map[lk] = {
                        "maloi": str(row.get("MALOI", "")).strip(),
                        "motaloi": str(row.get("MOTALOI", "")).strip(),
                        "ngay_ra": row.get("Ngày ra", None) if not pd.isna(row.get("Ngày ra")) else None
                    }
            
            # Lấy tất cả records thuộc ngày đối soát đó và chưa được giải quyết
            active_records = db.query(Record).filter(
                Record.ngay_doi_soat == target_date,
                Record.status != "RESOLVED"
            ).all()
            
            for r in active_records:
                if r.ma_lk in error_map:
                    err = error_map[r.ma_lk]
                    r.type_group = "LOI"
                    r.maloi = err["maloi"]
                    r.motaloi = err["motaloi"]
                    r.ngay_ra = err["ngay_ra"]
                    updated_count += 1
                    
                    # Thêm log lịch sử ghi nhận ghép lỗi
                    log = RecordLog(
                        record_id=r.id,
                        username=user.username,
                        action="CHANGE_STATUS",
                        note=f"Tu dong ghep ma loi moi nap: {err['maloi']} - {err['motaloi']}"
                    )
                    db.add(log)
            db.commit()
            
        return {
            "status": "success", 
            "rows": len(df), 
            "filename": file.filename,
            "updated_records": updated_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi đọc file Excel HoSoLoiChiTiet: {str(e)}")


# ==========================================
# API: CORRELATION & COMPARE ENGINE
# ==========================================

@app.get("/api/records/compare")
def compare_records(
    from_date: str,
    to_date: str,
    include_errors: bool = False,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Đồng bộ SQL HIS bệnh viện, so sánh danh sách và sinh dữ liệu đối soát (Giải mã mật khẩu HIS)"""
    cfg = db.query(AppConfig).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Vui lòng cấu hình kết nối SQL Server trước.")

    try:
        # 1. Truy vấn SQL Server HIS
        password_plain = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
            "password": password_plain,
            "sp_op": cfg.sp_op,
            "sp_ip": cfg.sp_ip
        }
        df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date, log_callback=lambda msg: his_service.safe_print(f"[*] [Compare] {msg}"))
        if df_sql.empty:
            raise HTTPException(status_code=400, detail="Stored Procedure HIS không trả về bản ghi nào trong khoảng ngày này.")

        # Parse ngày đối soát dạng yyyyMMdd thành datetime.date
        tu_date = datetime.datetime.strptime(from_date, "%Y%m%d").date()
        den_date = datetime.datetime.strptime(to_date, "%Y%m%d").date()

        # 2. Đọc file listbh Excel tạm đã upload và lọc theo khoảng ngày
        listbh_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
        if os.path.exists(listbh_path):
            df_listbh_raw = excel_service.load_listbh(listbh_path)
            df_listbh = excel_service.filter_listbh_by_date(df_listbh_raw, tu_date, den_date)
        else:
            df_listbh = pd.DataFrame()

        # 3. Đọc file lỗi Excel tạm đã upload nếu người dùng chủ động bật
        if include_errors:
            loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
            if os.path.exists(loi_path):
                df_hsloi = excel_service.load_hosoloichitiet(loi_path)
            else:
                df_hsloi = pd.DataFrame()
        else:
            df_hsloi = pd.DataFrame()

        # 4. Thực hiện đối soát thông minh
        ngay_doi_soat = datetime.date.today()
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat)
        save_last_kpis(db, stats, df_listbh, ngay_doi_soat)
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# API: ASYNC PROGRESS BAR FOR RECONCILIATION
# ==========================================

@app.post("/api/sync/start")
def start_sync(
    from_date: str,
    to_date: str,
    background_tasks: BackgroundTasks,
    include_errors: bool = False,
    user: User = Depends(require_admin)
):
    """Kích hoạt tiến trình đối soát chạy ngầm bất đồng bộ"""
    global SYNC_PROGRESS
    if SYNC_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="Đang có một tiến trình đối soát khác chạy ngầm. Vui lòng đợi.")
        
    SYNC_PROGRESS["should_stop"] = False
    background_tasks.add_task(run_sync_in_background, from_date.replace('-', ''), to_date.replace('-', ''), include_errors)
    return {"status": "success", "message": "Đã bắt đầu đối soát chạy ngầm."}


@app.get("/api/sync/status")
def get_sync_status(user: User = Depends(require_admin)):
    """Lấy trạng thái & phần trăm tiến trình đối soát thời gian thực"""
    global SYNC_PROGRESS
    return SYNC_PROGRESS


@app.post("/api/sync/stop")
def stop_sync(user: User = Depends(require_admin)):
    """Dừng tiến trình đối soát đang chạy ngầm và ngắt các câu lệnh SQL đang thực thi"""
    global SYNC_PROGRESS
    if not SYNC_PROGRESS["active"]:
        return {"status": "success", "message": "Không có tiến trình đối soát nào đang chạy."}
        
    SYNC_PROGRESS["should_stop"] = True
    SYNC_PROGRESS["status"] = "Đang dừng..."
    SYNC_PROGRESS["logs"].append("Người dùng yêu cầu dừng đối soát. Đang ngắt kết nối SQL và dừng luồng...")
    
    # Ngắt các kết nối SQL đang hoạt động
    his_service.abort_all_queries()
    
    return {"status": "success", "message": "Đã gửi yêu cầu dừng đối soát."}


@app.get("/api/departments/unique")
def get_unique_departments(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các tên khoa phòng duy nhất có trong dữ liệu đối soát phục vụ Autocomplete"""
    depts = db.query(Record.ten_khoa).distinct().all()
    dept_names = [d[0] for d in depts if d[0]]
    if not dept_names:
        dept_names = ["Khám bệnh", "Khoa Ngoại", "Khoa Nội", "Khoa Sản", "Khoa Nhi"]
    return sorted(dept_names)


# ==========================================
# API: CLINICAL DEPARTMENT (KHOA LÂM SÀNG)
# ==========================================

@app.get("/api/records/dept")
def get_department_records(
    status: str = "ALL",
    month: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các ca LỖI thuộc quản lý của khoa (chỉ đọc, sắp xếp ngày ra viện xa nhất đến mới nhất)"""
    if not user.department_name:
        return []
        
    query = db.query(Record).filter(
        Record.ten_khoa == user.department_name,
        Record.type_group == "LOI"
    )
    
    if status == "PENDING":
        query = query.filter(Record.status.in_(["PENDING", "WAITING_RESEND"]))
    elif status == "RESOLVED":
        query = query.filter(Record.status == "RESOLVED")
    elif status != "ALL":
        query = query.filter(Record.status == status)

    # Lọc theo tháng nếu có (format YYYY-MM)
    if month:
        try:
            year, mon = map(int, month.split("-"))
            month_start = datetime.date(year, mon, 1)
            if mon == 12:
                month_end = datetime.date(year + 1, 1, 1)
            else:
                month_end = datetime.date(year, mon + 1, 1)
            query = query.filter(
                Record.ngay_ra_vien >= month_start,
                Record.ngay_ra_vien < month_end
            )
        except (ValueError, TypeError):
            pass
        
    records = query.order_by(Record.status.asc(), Record.ngay_ra_vien.asc()).all()
    
    # Làm giàu dữ liệu hướng dẫn sửa lỗi từ danh mục
    from models import ErrorDefinition
    defs = db.query(ErrorDefinition).all()
    
    for r in records:
        r.root_cause = "Chưa rõ nguyên nhân (Hệ thống tự động quét)"
        r.resolution = "Chờ phòng IT bổ sung hướng dẫn chi tiết"
        r.requires_his_reset = False
        
        for d in defs:
            if d.error_code == r.maloi:
                if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                    r.root_cause = d.root_cause
                    r.resolution = d.resolution
                    r.requires_his_reset = d.requires_his_reset
                    break
    return records


@app.get("/api/records/dept/stats")
def get_department_stats(
    month: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Thống kê theo tháng cho khoa lâm sàng: tổng lỗi, đã xử lý, chưa xử lý, quá 7 ngày, số lần đối soát"""
    if not user.department_name:
        return {"month": month or "", "total_loi": 0, "resolved": 0, "pending": 0, "overdue_7_days": 0, "sync_count": 0}

    # Parse tháng, mặc định tháng hiện tại
    today = datetime.date.today()
    if month:
        try:
            year, mon = map(int, month.split("-"))
        except (ValueError, TypeError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month
        month = f"{year:04d}-{mon:02d}"

    month_start = datetime.date(year, mon, 1)
    if mon == 12:
        month_end = datetime.date(year + 1, 1, 1)
    else:
        month_end = datetime.date(year, mon + 1, 1)

    base_query = db.query(Record).filter(
        Record.ten_khoa == user.department_name,
        Record.type_group == "LOI",
        Record.ngay_ra_vien >= month_start,
        Record.ngay_ra_vien < month_end
    )

    all_records = base_query.all()
    total_loi = len(all_records)
    resolved = sum(1 for r in all_records if r.status == "RESOLVED")
    pending = total_loi - resolved

    # Đếm quá 7 ngày: chỉ tính ca chưa RESOLVED
    overdue_threshold = today - datetime.timedelta(days=7)
    overdue_7_days = sum(
        1 for r in all_records
        if r.status != "RESOLVED" and r.ngay_ra_vien and r.ngay_ra_vien <= overdue_threshold
    )

    # Đếm số lần đối soát có tạo record LOI thuộc khoa trong tháng
    sync_dates = db.query(Record.ngay_doi_soat).filter(
        Record.ten_khoa == user.department_name,
        Record.type_group == "LOI",
        Record.ngay_doi_soat >= month_start,
        Record.ngay_doi_soat < month_end
    ).distinct().all()
    sync_count = len(sync_dates)

    return {
        "month": month,
        "total_loi": total_loi,
        "resolved": resolved,
        "pending": pending,
        "overdue_7_days": overdue_7_days,
        "sync_count": sync_count
    }


@app.get("/api/export/dept/loi")
def export_department_loi(
    month: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách lỗi BHYT của khoa theo tháng"""
    if not user.department_name:
        raise HTTPException(status_code=400, detail="Tài khoản chưa được gán khoa phòng.")

    today = datetime.date.today()
    if month:
        try:
            year, mon = map(int, month.split("-"))
        except (ValueError, TypeError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month

    month_start = datetime.date(year, mon, 1)
    if mon == 12:
        month_end = datetime.date(year + 1, 1, 1)
    else:
        month_end = datetime.date(year, mon + 1, 1)

    records = db.query(Record).filter(
        Record.ten_khoa == user.department_name,
        Record.type_group == "LOI",
        Record.status != "RESOLVED",
        Record.ngay_ra_vien >= month_start,
        Record.ngay_ra_vien < month_end
    ).order_by(Record.ngay_ra_vien.asc()).all()

    data = []
    for r in records:
        status_text = "Đã xử lý" if r.status == "RESOLVED" else "Chưa xử lý"
        days_overdue = ""
        if r.ngay_ra_vien and r.status != "RESOLVED":
            diff = (today - r.ngay_ra_vien).days
            if diff >= 7:
                days_overdue = f"Quá {diff} ngày"
            elif diff >= 5:
                days_overdue = f"Cảnh báo {diff} ngày"

        data.append({
            "MA_LK": r.ma_lk,
            "Họ tên": r.ho_ten,
            "Mã thẻ BHYT": r.ma_the,
            "Ngày ra viện": r.ngay_ra_vien,
            "Loại ca": resolve_loai_ca(r),
            "Mã lỗi": r.maloi,
            "Mô tả lỗi": r.motaloi,
            "Trạng thái": status_text,
            "Cảnh báo": days_overdue,
            "Ghi chú": r.note or ""
        })

    df = pd.DataFrame(data)
    dept_safe = user.department_name.replace(" ", "_").replace("/", "_")
    filename = f"LOI_BHYT_{dept_safe}_{year}{mon:02d}.xlsx"
    out_path = os.path.join(UPLOAD_DIR, filename)
    df.to_excel(out_path, index=False)
    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )


# ==========================================
# API: IT ADMIN PROCESS (FAIL & REVIEW LIST)
# ==========================================

@app.get("/api/records/admin/sql")
def get_admin_sql_records(
    from_date: str,
    to_date: str,
    loai_ca: Optional[str] = None,
    ngay_ra_vien: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách dữ liệu bệnh nhân tải từ SQL HIS (dùng cache nếu có)"""
    cfg = db.query(AppConfig).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Chưa cấu hình kết nối SQL Server HIS.")
        
    try:
        password_plain = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
            "password": password_plain,
            "sp_op": cfg.sp_op,
            "sp_ip": cfg.sp_ip
        }
        
        # Gọi fetch_his_data để tận dụng tối đa cơ chế cache .pkl
        df = his_service.fetch_his_data(cfg_dict, from_date.replace('-', ''), to_date.replace('-', ''), log_callback=lambda msg: his_service.safe_print(f"[*] [AdminSQL] {msg}"))
        if df.empty:
            return []
            
        # Lọc loại ca
        if loai_ca and loai_ca != "All":
            df = df[df["Loại ca"] == loai_ca]
            
        # Lọc ngày ra viện (dạng YYYY-MM-DD)
        if ngay_ra_vien:
            try:
                dt_filter = datetime.datetime.strptime(ngay_ra_vien, "%Y-%m-%d").date()
                
                # So sánh an toàn cả dạng date/datetime/Timestamp lẫn chuỗi string, bỏ qua giá trị rỗng
                def match_date(val):
                    if pd.isna(val) or val is None:
                        return False
                    
                    # Nếu là Timestamp hoặc datetime.datetime (có thuộc tính date)
                    if hasattr(val, "date"):
                        try:
                            return val.date() == dt_filter
                        except Exception:
                            pass
                            
                    # Nếu là datetime.date
                    if isinstance(val, datetime.date):
                        return val == dt_filter
                        
                    # Fallback so sánh chuỗi
                    try:
                        val_str = str(val).split()[0].replace('/', '-').strip()
                        return val_str == ngay_ra_vien
                    except Exception:
                        return False
                    
                df = df[df["Ngày ra viện"].apply(match_date)]
            except Exception:
                pass
                
        # Sắp xếp và giới hạn tối đa 5000 bản ghi để trình duyệt chạy mượt mà
        df["Ngày ra viện"] = pd.to_datetime(df["Ngày ra viện"], errors="coerce")
        df = df.sort_values(by="Ngày ra viện", ascending=True)
        
        records = []
        for _, r in df.iterrows():
            val = r.get("Ngày ra viện")
            dt_str = ""
            if val and not pd.isna(val):
                try:
                    dt_str = val.strftime("%Y-%m-%d")
                except Exception:
                    dt_str = str(val).split()[0]
                    
            records.append({
                "loai_ca": r.get("Loại ca", "Ngoại trú"),
                "ma_lk": r.get("MA_LK", ""),
                "ho_ten": r.get("Họ tên", ""),
                "ma_the": r.get("Mã thẻ", ""),
                "ten_khoa": r.get("Tên khoa", ""),
                "ma_y_te": r.get("Mã y tế", ""),
                "ngay_ra_vien": dt_str
            })
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/records/admin/fail")
def get_admin_fail_records(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các ca FAIL (sắp xếp ngày ra viện xa nhất đến mới nhất) để IT sửa tay"""
    query = db.query(Record).filter(
        Record.type_group == "FAIL",
        Record.status != "RESOLVED"
    )
    
    fd = normalize_date_to_iso(from_date)
    if fd:
        query = query.filter(Record.ngay_ra_vien >= fd)
            
    td = normalize_date_to_iso(to_date)
    if td:
        query = query.filter(Record.ngay_ra_vien <= td)

    records = query.order_by(Record.ngay_ra_vien.asc()).all()
    
    for r in records:
        r.root_cause = ""
        r.resolution = ""
        r.requires_his_reset = False
    return records


@app.post("/api/records/{record_id}/admin-resolve")
def resolve_fail_record(
    record_id: int,
    data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """IT ghi chú và chủ động đánh dấu xử lý hoàn tất cho ca FAIL hoặc LỖI"""
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Hồ sơ không tồn tại.")

    note = data.get("note", "").strip()
    record.note = note
    record.status = "RESOLVED"

    # Ghi log
    log = RecordLog(
        record_id=record.id,
        username=user.username,
        action="CHANGE_STATUS",
        note=f"IT xác nhận xử lý thành công. Ghi chú: {note}"
    )
    db.add(log)
    db.commit()
    return {"status": "success"}


@app.post("/api/records/admin/fail/reset")
def run_bulk_fail_reset(
    loai: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """IT sinh SQL reset hàng loạt cho ca FAIL và chuyển sang trạng thái chờ gửi lại."""
    query = db.query(Record).filter(
        Record.type_group == "FAIL",
        Record.status.in_(["PENDING", "WAITING_RESEND"])
    )
    
    fd = normalize_date_to_iso(from_date)
    if fd:
        query = query.filter(Record.ngay_ra_vien >= fd)
            
    td = normalize_date_to_iso(to_date)
    if td:
        query = query.filter(Record.ngay_ra_vien <= td)

    all_fail_records = query.all()
    records = [r for r in all_fail_records if resolve_loai_ca(r) == loai]

    if not records:
        return {"success": True, "rowcount": 0, "message": "Không có ca FAIL nào đang chờ reset."}

    try:
        keys = [r.ma_lk for r in records]
        # Sinh câu lệnh SQL Reset hàng loạt
        sql_command = his_service.build_reset_sql(keys, loai)

        # Không đánh dấu RESOLVED ngay khi sinh SQL.
        # Các ca này chỉ hoàn tất khi lần đối soát sau thấy xuất hiện trong listbh.
        for r in records:
            r.status = "WAITING_RESEND"
            log = RecordLog(
                record_id=r.id,
                username=user.username,
                action="CHANGE_STATUS",
                note=f"IT lấy câu lệnh SQL reset hàng loạt ({loai}). Chờ hệ thống gửi XML bên ngoài gửi lại."
            )
            db.add(log)
            
        db.commit()
        return {"success": True, "rowcount": len(records), "sql_command": sql_command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý hàng loạt: {str(e)}")


@app.get("/api/records/kpi")
def get_global_kpis(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy số liệu KPI tổng quan cho Dashboard"""
    cfg = db.query(AppConfig).first()
    tong_sql = 0
    tong_bh = 0
    da_gui = 0
    
    if cfg and getattr(cfg, "last_sync_date", None):
        tong_sql = getattr(cfg, "last_tong_sql", 0) or 0
        tong_bh = getattr(cfg, "last_tong_bh", 0) or 0
        da_gui = getattr(cfg, "last_da_gui", 0) or 0
    else:
        last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
        if last_record:
            target_date = last_record.ngay_doi_soat
            base_query = db.query(Record).filter(Record.ngay_doi_soat == target_date)
            tong_sql = base_query.count()
            da_gui = base_query.filter(Record.status == "RESOLVED", Record.type_group != "LOI").count()

    # Dynamic active counts representing the actual current state of the database
    loi = db.query(Record).filter(Record.type_group == "LOI", Record.status != "RESOLVED").count()
    fail = db.query(Record).filter(Record.type_group == "FAIL", Record.status != "RESOLVED").count()
    resolved = db.query(Record).filter(Record.status == "RESOLVED").count()

    return {
        "tong_sql": tong_sql,
        "tong_bh": tong_bh,
        "da_gui": da_gui,
        "loi": loi,
        "fail": fail,
        "resolved": resolved
    }


# ==========================================
# API: REPORTS & EXPORTS
# ==========================================

@app.get("/api/reports/departments")
def get_department_breakdown(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Thống kê chi tiết số lỗi theo từng khoa lâm sàng"""
    last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        return []
        
    target_date = last_record.ngay_doi_soat
    
    # Query tất cả các records lỗi chưa giải quyết trong hệ thống
    err_records = db.query(Record).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()
    
    # Tổng hợp bằng Python dict
    dept_map = {}
    for r in err_records:
        dept = r.ten_khoa or "Chưa phân khoa"
        if dept not in dept_map:
            dept_map[dept] = {"ten_khoa": dept, "pending": 0, "waiting": 0, "total": 0}
        
        dept_map[dept]["total"] += 1
        if r.status == "PENDING":
            dept_map[dept]["pending"] += 1
        elif r.status in {"WAITING_REVIEW", "WAITING_RESEND"}:
            dept_map[dept]["waiting"] += 1
            
    return list(dept_map.values())


@app.get("/api/export/sql_list")
def export_sql_list(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel sql_list chứa toàn bộ danh sách nạp từ HIS CSDL"""
    last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        raise HTTPException(status_code=400, detail="Không có dữ liệu đối soát để xuất.")
        
    records = db.query(Record).filter(Record.ngay_doi_soat == last_record.ngay_doi_soat).all()
    
    data = []
    for r in records:
        data.append({
            "Loại ca": resolve_loai_ca(r),
            "MA_LK": r.ma_lk,
            "Họ tên": r.ho_ten,
            "Mã thẻ": r.ma_the,
            "Tên khoa": r.ten_khoa,
            "Mã y tế": r.ma_y_te,
            "Ngày ra viện": r.ngay_ra_vien,
            "Trạng thái đối soát": "Đã gửi BHYT" if r.status == "RESOLVED" and r.type_group != "LOI" else "Chưa gửi / Lỗi"
        })
        
    df = pd.DataFrame(data)
    out_path = os.path.join(UPLOAD_DIR, "sql_list_export.xlsx")
    df.to_excel(out_path, index=False)
    return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="sql_list.xlsx")


@app.get("/api/export/fail")
def export_fail_list(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách các ca bị FAIL"""
    query = db.query(Record).filter(
        Record.type_group == "FAIL",
        Record.status != "RESOLVED"
    )
    
    if from_date or to_date:
        fd = normalize_date_to_iso(from_date)
        if fd:
            query = query.filter(Record.ngay_ra_vien >= fd)
        td = normalize_date_to_iso(to_date)
        if td:
            query = query.filter(Record.ngay_ra_vien <= td)

    records = query.all()
    
    data = []
    for r in records:
        data.append({
            "Loại ca": resolve_loai_ca(r),
            "MA_LK": r.ma_lk,
            "Họ tên": r.ho_ten,
            "Mã thẻ": r.ma_the,
            "Tên khoa": r.ten_khoa,
            "Mã y tế": r.ma_y_te,
            "Ngày ra viện": r.ngay_ra_vien,
            "Ghi chú IT": r.note
        })
        
    df = pd.DataFrame(data)
    out_path = os.path.join(UPLOAD_DIR, "DANH_SACH_FAIL_export.xlsx")
    df.to_excel(out_path, index=False)
    return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="DANH_SACH_FAIL.xlsx")


@app.get("/api/export/loi")
def export_loi_list(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách các ca bị LỖI kèm thông tin bệnh án"""
    records = db.query(Record).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()
    
    data = []
    for r in records:
        data.append({
            "MA_LK": r.ma_lk,
            "Họ tên": r.ho_ten,
            "Mã thẻ": r.ma_the,
            "Tên khoa": r.ten_khoa,
            "Mã y tế": r.ma_y_te,
            "Ngày ra viện": r.ngay_ra_vien,
            "Ngày ra": r.ngay_ra,
            "MALOI": r.maloi,
            "MOTALOI": r.motaloi,
            "Trạng thái": r.status,
            "Ý kiến khoa giải trình": r.note
        })
        
    df = pd.DataFrame(data)
    out_path = os.path.join(UPLOAD_DIR, "DANH_SACH_KEM_LOI_export.xlsx")
    df.to_excel(out_path, index=False)
    return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="DANH_SACH_KEM_LOI.xlsx")


# ==========================================
# API: USERS / DEPARTMENTS MANAGEMENT
# ==========================================

@app.get("/api/users")
def list_users(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các tài khoản người dùng"""
    return db.query(User).all()


@app.post("/api/users")
def create_user(
    user_data: dict,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Tạo tài khoản khoa phòng mới"""
    username = user_data.get("username", "").strip()
    password = user_data.get("password", "")
    role = user_data.get("role", "user")
    dept = user_data.get("department_name", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Vui lòng nhập Tên đăng nhập và Mật khẩu.")

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại trên hệ thống.")

    hashed = hash_password(password)
    new_user = User(
        username=username,
        password_hash=hashed,
        role=role,
        department_name=dept if role == "user" else ""
    )
    db.add(new_user)
    db.commit()
    return {"status": "success"}


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xóa tài khoản người dùng"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng cần xóa.")

    if target.username == "admin":
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản admin hệ thống.")

    db.delete(target)
    db.commit()
    return {"status": "success"}


# ==========================================
# BACKGROUND AUTO-SYNC SCHEDULER & STARTUP
# ==========================================

async def auto_sync_scheduler():
    await asyncio.sleep(10)  # Chờ uvicorn khởi chạy hoàn tất
    print("[*] Tien trinh dong bo tu dong HIS ngam da duoc kich hoat.")
    while True:
        try:
            now = datetime.datetime.now()
            db_gen = get_db()
            db = next(db_gen)
            try:
                cfg = db.query(AppConfig).first()
                if cfg and getattr(cfg, "auto_sync_enabled", False):
                    target_time_str = getattr(cfg, "auto_sync_time", "00:30")
                    target_hr, target_min = map(int, target_time_str.split(":"))
                    
                    if now.hour == target_hr and now.minute == target_min:
                        print(f"[*] [Scheduler] Bat dau dong bo tu dong luc {target_time_str}...")
                        
                        from_dt = now.date() - datetime.timedelta(days=3)
                        from_date = from_dt.strftime("%Y%m%d")
                        to_date = now.date().strftime("%Y%m%d")
                        
                        password = decrypt_password(cfg.password) if cfg.password else ""
                        cfg_dict = {
                            "driver": cfg.driver,
                            "server": cfg.server,
                            "database": cfg.database,
                            "auth": cfg.auth,
                            "user": cfg.user,
                            "password": password,
                            "sp_op": cfg.sp_op,
                            "sp_ip": cfg.sp_ip
                        }
                        
                        def run_sync_sync():
                            temp_db = next(get_db())
                            try:
                                df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date, log_callback=lambda msg: his_service.safe_print(f"[*] [Scheduler] {msg}"))
                                
                                listbh_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
                                if os.path.exists(listbh_path):
                                    df_listbh_raw = excel_service.load_listbh(listbh_path)
                                    df_listbh = excel_service.filter_listbh_by_date(df_listbh_raw, from_dt, now.date())
                                else:
                                    df_listbh = pd.DataFrame()
                                    
                                # Scheduler tự động chỉ đối soát SQL HIS với listbh để tìm FAIL.
                                # File lỗi chi tiết chỉ được dùng khi IT chủ động import/chạy lại.
                                df_hsloi = pd.DataFrame()
                                    
                                stats = compare_service.process_comparison(temp_db, df_sql, df_listbh, df_hsloi, now.date())
                                save_last_kpis(temp_db, stats, df_listbh, now.date())
                                print("[*] [Scheduler] Dong bo tu dong HIS thanh cong.")
                            except Exception as ex:
                                print(f"[!] [Scheduler] Loi khi thuc hien: {ex}")
                            finally:
                                temp_db.close()
                                
                        await asyncio.get_event_loop().run_in_executor(None, run_sync_sync)
                        await asyncio.sleep(65)  # Tránh kích hoạt lại trong cùng một phút
                        continue
            finally:
                db.close()
        except Exception as e:
            print(f"[!] Loi he thong Scheduler: {e}")
        await asyncio.sleep(30)  # Kế hoạch quét kiểm tra mỗi 30 giây


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_sync_scheduler())
