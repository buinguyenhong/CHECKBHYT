import os
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
    encrypted_chars = []
    for i, char in enumerate(password):
        key_char = SECRET_KEY[i % len(SECRET_KEY)]
        encrypted_chars.append(chr(ord(char) ^ ord(key_char)))
    encrypted_str = "".join(encrypted_chars)
    return base64.b64encode(encrypted_str.encode('utf-8')).decode('utf-8')

def decrypt_password(encrypted_base64: str) -> str:
    if not encrypted_base64:
        return ""
    try:
        raw_encrypted = base64.b64decode(encrypted_base64.encode('utf-8')).decode('utf-8')
        decrypted_chars = []
        for i, char in enumerate(raw_encrypted):
            key_char = SECRET_KEY[i % len(SECRET_KEY)]
            decrypted_chars.append(chr(ord(char) ^ ord(key_char)))
        return "".join(decrypted_chars)
    except Exception:
        return encrypted_base64

# ==========================================
# GLOBAL STATE FOR ASYNC SYNC PROGRESS
# ==========================================
SYNC_PROGRESS = {
    "active": False,
    "progress": 0,
    "status": "Idle",
    "logs": []
}

def run_sync_in_background(from_date: str, to_date: str):
    global SYNC_PROGRESS
    SYNC_PROGRESS["active"] = True
    SYNC_PROGRESS["progress"] = 5
    SYNC_PROGRESS["status"] = "Đang bắt đầu..."
    SYNC_PROGRESS["logs"] = ["Khởi chạy tiến trình đối soát & đồng bộ..."]
    
    db_gen = get_db()
    db = next(db_gen)
    try:
        cfg = db.query(AppConfig).first()
        if not cfg:
            SYNC_PROGRESS["active"] = False
            SYNC_PROGRESS["status"] = "Lỗi"
            SYNC_PROGRESS["logs"].append("Lỗi: Chưa cấu hình kết nối SQL Server HIS.")
            return
            
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
        
        SYNC_PROGRESS["progress"] = 30
        SYNC_PROGRESS["status"] = "Đang truy vấn SQL Server HIS..."
        SYNC_PROGRESS["logs"].append(f"Truy vấn stored procedure Ngoại trú và Nội trú từ {from_date} đến {to_date}...")
        
        try:
            df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date)
            SYNC_PROGRESS["logs"].append(f"Đã tải thành công {len(df_sql)} bản ghi từ CSDL HIS.")
        except Exception as e:
            SYNC_PROGRESS["active"] = False
            SYNC_PROGRESS["status"] = "Lỗi"
            SYNC_PROGRESS["logs"].append(f"Lỗi truy vấn HIS LAN: {str(e)}")
            return
            
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
            
        SYNC_PROGRESS["progress"] = 75
        SYNC_PROGRESS["status"] = "Đang đọc tệp báo cáo lỗi..."
        loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
        if os.path.exists(loi_path):
            df_hsloi = excel_service.load_hosoloichitiet(loi_path)
            SYNC_PROGRESS["logs"].append(f"Đọc HoSoLoiChiTiet.xlsx thành công. Có {len(df_hsloi)} lỗi chi tiết.")
        else:
            df_hsloi = pd.DataFrame()
            SYNC_PROGRESS["logs"].append("Cảnh báo: Không tìm thấy file HoSoLoiChiTiet.xlsx. Bỏ qua ghép mã lỗi.")
            
        SYNC_PROGRESS["progress"] = 85
        SYNC_PROGRESS["status"] = "Đang chạy đối soát & lưu trữ vào SQLite..."
        SYNC_PROGRESS["logs"].append("Đang đối soát 2 chiều, kế thừa ghi chú và tự động duyệt...")
        
        ngay_doi_soat = datetime.date.today()
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat)
        
        SYNC_PROGRESS["progress"] = 100
        SYNC_PROGRESS["status"] = "Hoàn tất"
        SYNC_PROGRESS["logs"].append(f"ĐỐI SOÁT HOÀN TẤT THÀNH CÔNG. Ghi nhận: Tổng ca: {stats['total']} | Lỗi BHYT: {stats['loi']} | FAIL: {stats['fail']} | Đã gửi: {stats['sent']}")
        SYNC_PROGRESS["active"] = False
        
    except Exception as e:
        SYNC_PROGRESS["active"] = False
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
except Exception as e:
    print(f"[*] Thong tin di tru tu dong: {e}")

app = FastAPI(
    title="CheckBHYT LAN WebApp",
    description="Hệ thống đối soát BHYT chạy mạng LAN nội bộ bệnh viện",
    version="2.0.0"
)

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


@app.post("/api/config/test-connection")
def test_his_connection(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Kiểm tra kết nối CSDL HIS trên mạng LAN (giải mã mật khẩu)"""
    cfg = db.query(AppConfig).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Chưa cấu hình thông tin kết nối")
    try:
        password_plain = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
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
        df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date)
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

        # 3. Đọc file lỗi Excel tạm đã upload
        loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
        if os.path.exists(loi_path):
            df_hsloi = excel_service.load_hosoloichitiet(loi_path)
        else:
            df_hsloi = pd.DataFrame()

        # 4. Thực hiện đối soát thông minh
        ngay_doi_soat = datetime.date.today()
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat)
        
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
    user: User = Depends(require_admin)
):
    """Kích hoạt tiến trình đối soát chạy ngầm bất đồng bộ"""
    global SYNC_PROGRESS
    if SYNC_PROGRESS["active"]:
        raise HTTPException(status_code=400, detail="Đang có một tiến trình đối soát khác chạy ngầm. Vui lòng đợi.")
        
    background_tasks.add_task(run_sync_in_background, from_date.replace('-', ''), to_date.replace('-', ''))
    return {"status": "success", "message": "Đã bắt đầu đối soát chạy ngầm."}


@app.get("/api/sync/status")
def get_sync_status(user: User = Depends(require_admin)):
    """Lấy trạng thái & phần trăm tiến trình đối soát thời gian thực"""
    global SYNC_PROGRESS
    return SYNC_PROGRESS


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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các ca LỖI thuộc quản lý của khoa (sắp xếp ngày ra viện xa nhất đến mới nhất)"""
    if not user.department_name:
        return []
        
    query = db.query(Record).filter(
        Record.ten_khoa == user.department_name,
        Record.type_group == "LOI"
    )
    
    if status != "ALL":
        query = query.filter(Record.status == status)
        
    # Sắp xếp ngày ra viện từ xa nhất đến mới nhất (tăng dần)
    return query.order_by(Record.status.asc(), Record.ngay_ra_vien.asc()).all()


@app.post("/api/records/{record_id}/flag")
def flag_record_for_review(
    record_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Khoa lâm sàng điền giải trình/ghi chú sửa lỗi và đổi cờ trạng thái
    sang WAITING_REVIEW (Chờ kiểm tra) để gửi báo cáo lên phòng IT.
    """
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Hồ sơ ca bệnh không tồn tại.")
        
    # Chỉ cho phép khoa sở quản cập nhật thông tin
    if record.ten_khoa != user.department_name:
        raise HTTPException(status_code=403, detail="Hồ sơ này không thuộc quyền quản lý của khoa phòng bạn.")

    if record.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Ca này phòng IT đã duyệt hoàn tất, không thể chỉnh sửa.")

    note = data.get("note", "").strip()
    record.note = note
    record.status = "WAITING_REVIEW"
    
    # Ghi log lịch sử thay đổi
    log = RecordLog(
        record_id=record.id,
        username=user.username,
        action="CHANGE_STATUS",
        note=f"Khoa gửi yêu cầu kiểm tra. Ghi chú: {note}"
    )
    db.add(log)
    db.commit()
    
    return {"status": "success"}


# ==========================================
# API: IT ADMIN PROCESS (FAIL & REVIEW LIST)
# ==========================================

@app.get("/api/records/admin/fail")
def get_admin_fail_records(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các ca FAIL (sắp xếp ngày ra viện xa nhất đến mới nhất) để IT sửa tay"""
    return db.query(Record).filter(
        Record.type_group == "FAIL",
        Record.status != "RESOLVED"
    ).order_by(Record.ngay_ra_vien.asc()).all()


@app.get("/api/records/admin/review")
def get_admin_review_records(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách hồ sơ lỗi do các Khoa lâm sàng gửi yêu cầu duyệt kiểm tra"""
    return db.query(Record).filter(
        Record.status == "WAITING_REVIEW"
    ).order_by(Record.updated_at.desc()).all()


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


@app.post("/api/records/{record_id}/approve")
def approve_and_reset_sql(
    record_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    IT duyệt hồ sơ lỗi khoa gửi lên: Đánh dấu RESOLVED và tự động
    chạy lệnh UPDATE reset cờ xuất (Export=0) trực tiếp trên database HIS.
    """
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Hồ sơ không tồn tại.")

    cfg = db.query(AppConfig).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Thiếu cấu hình kết nối SQL Server HIS.")

    try:
        # 1. Chạy Reset SQL
        password_plain = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
            "password": password_plain
        }
        rc = his_service.execute_reset(cfg_dict, [record.ma_lk], record.loai_ca)

        # 2. Cập nhật trạng thái WebApp
        record.status = "RESOLVED"
        log = RecordLog(
            record_id=record.id,
            username=user.username,
            action="CHANGE_STATUS",
            note=f"IT duyệt giải trình & chạy Reset SQL. Rowcount cập nhật: {rc}"
        )
        db.add(log)
        db.commit()

        return {"success": True, "rowcount": rc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn SQL reset: {str(e)}")


@app.post("/api/records/admin/fail/reset")
def run_bulk_fail_reset(
    loai: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """IT chạy Reset cờ xuất hàng loạt cho tất cả ca FAIL (Ngoại trú hoặc Nội trú) đang PENDING"""
    records = db.query(Record).filter(
        Record.type_group == "FAIL",
        Record.status == "PENDING",
        Record.loai_ca == loai
    ).all()

    if not records:
        return {"success": True, "rowcount": 0, "message": "Không có ca FAIL nào đang chờ reset."}

    cfg = db.query(AppConfig).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Thiếu cấu hình kết nối SQL Server HIS.")

    try:
        password_plain = decrypt_password(cfg.password) if cfg.password else ""
        cfg_dict = {
            "driver": cfg.driver,
            "server": cfg.server,
            "database": cfg.database,
            "auth": cfg.auth,
            "user": cfg.user,
            "password": password_plain
        }
        
        keys = [r.ma_lk for r in records]
        rc = his_service.execute_reset(cfg_dict, keys, loai)

        # Đánh dấu đã xử lý xong cho các ca trên WebApp
        for r in records:
            r.status = "RESOLVED"
            log = RecordLog(
                record_id=r.id,
                username=user.username,
                action="CHANGE_STATUS",
                note=f"IT chạy Reset hàng loạt ({loai})."
            )
            db.add(log)
            
        db.commit()
        return {"success": True, "rowcount": rc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/records/kpi")
def get_global_kpis(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy số liệu KPI tổng quan cho Dashboard"""
    today_date = datetime.date.today()
    
    # Lấy đối soát của ngày gần nhất có dữ liệu
    last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        return {"tong_sql": 0, "da_gui": 0, "loi": 0, "fail": 0, "resolved": 0}
        
    target_date = last_record.ngay_doi_soat

    base_query = db.query(Record).filter(Record.ngay_doi_soat == target_date)
    
    tong_sql = base_query.count()
    da_gui = base_query.filter(Record.status == "RESOLVED", Record.type_group != "LOI").count()
    loi = base_query.filter(Record.type_group == "LOI", Record.status != "RESOLVED").count()
    fail = base_query.filter(Record.type_group == "FAIL", Record.status == "PENDING").count()
    resolved = base_query.filter(Record.status == "RESOLVED").count()

    return {
        "tong_sql": tong_sql,
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
    
    # Query tất cả các records lỗi trong ngày đối soát gần nhất
    err_records = db.query(Record).filter(
        Record.ngay_doi_soat == target_date,
        Record.type_group == "LOI"
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
        elif r.status == "WAITING_REVIEW":
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
            "Loại ca": r.loai_ca,
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
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách các ca bị FAIL"""
    last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        raise HTTPException(status_code=400, detail="Không có dữ liệu đối soát để xuất.")
        
    records = db.query(Record).filter(
        Record.ngay_doi_soat == last_record.ngay_doi_soat,
        Record.type_group == "FAIL",
        Record.status == "PENDING"
    ).all()
    
    data = []
    for r in records:
        data.append({
            "Loại ca": r.loai_ca,
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
    last_record = db.query(Record).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        raise HTTPException(status_code=400, detail="Không có dữ liệu đối soát để xuất.")
        
    records = db.query(Record).filter(
        Record.ngay_doi_soat == last_record.ngay_doi_soat,
        Record.type_group == "LOI"
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
                                df_sql = his_service.fetch_his_data(cfg_dict, from_date, to_date)
                                
                                listbh_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
                                if os.path.exists(listbh_path):
                                    df_listbh_raw = excel_service.load_listbh(listbh_path)
                                    df_listbh = excel_service.filter_listbh_by_date(df_listbh_raw, from_dt, now.date())
                                else:
                                    df_listbh = pd.DataFrame()
                                    
                                loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
                                if os.path.exists(loi_path):
                                    df_hsloi = excel_service.load_hosoloichitiet(loi_path)
                                else:
                                    df_hsloi = pd.DataFrame()
                                    
                                compare_service.process_comparison(temp_db, df_sql, df_listbh, df_hsloi, now.date())
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
