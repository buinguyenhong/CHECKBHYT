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
            if df_listbh.empty:
                SYNC_PROGRESS["logs"].append("Thông báo: Tệp listbh.xlsx không chứa dữ liệu trong khoảng ngày đối soát. Chạy đối soát không có listbh (không đánh dấu ca FAIL).")
            else:
                SYNC_PROGRESS["logs"].append(f"Đọc listbh.xlsx thành công. Có {len(df_listbh)} ca trong ngày đối soát.")
        else:
            df_listbh = pd.DataFrame()
            SYNC_PROGRESS["logs"].append("Thông báo: Không tìm thấy file listbh.xlsx. Chạy đối soát không có listbh (không đánh dấu ca FAIL).")
            
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
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat, include_errors=include_errors)
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

# Tự động dọn dẹp các bản ghi trùng lặp trong DB khi khởi chạy WebApp
try:
    from services.compare_service import deduplicate_database_records
    from database import SessionLocal
    db_clean = SessionLocal()
    try:
        deduplicate_database_records(db_clean)
    finally:
        db_clean.close()
except Exception as startup_dedup_err:
    print(f"[STARTUP] Loi khi tu dong don dep trung lap du lieu cu: {startup_dedup_err}")

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

    # Seed danh mục lỗi mẫu (bổ sung & cập nhật định dạng)
    from models import ErrorDefinition
    import re
    
    sample_errors = [
        ErrorDefinition(
            error_code="XML 5 (Diễn biến LS)", 
            keyword="DIEN_BIEN_LS", 
            root_cause="Bác sĩ hoặc điều dưỡng quên ghi chép diễn biến bệnh / phiếu chăm sóc hàng ngày", 
            resolution="Mở bệnh án HIS -> Tab Khám bệnh -> Điền đầy đủ Diễn biến lâm sàng rồi bấm Lưu", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 8 (Tóm tắt HSBA)", 
            keyword="TOMTAT_KQ", 
            root_cause="Thiếu tóm tắt kết quả cận lâm sàng quan trọng", 
            resolution="Nhập đầy đủ thông tin tóm tắt kết quả cận lâm sàng trên phần mềm HIS rồi cho ra viện lại", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 8 (Tóm tắt HSBA)", 
            keyword="MA_TTDV", 
            root_cause="Thiếu mã tương đương dịch vụ kỹ thuật hoặc thuốc", 
            resolution="Liên hệ phòng IT để cập nhật danh mục tương đương hoặc ánh xạ mã dịch vụ kỹ thuật", 
            requires_his_reset=False
        ),
        ErrorDefinition(
            error_code="XML 3 (Dịch vụ kỹ thuật)", 
            keyword="NGAY_TH_YL", 
            root_cause="Ngày thực hiện y lệnh bị trống hoặc sai định dạng", 
            resolution="Sửa lại ngày thực hiện y lệnh trên HIS cho khớp với ngày ra viện", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 1 (Tổng hợp KBCB)", 
            keyword="XML1", 
            root_cause="Thông tin XML1 (Tổng hợp) chưa chuẩn xác, sai lệch số tiền hoặc thẻ BHYT", 
            resolution="Kiểm tra lại thẻ BHYT của bệnh nhân hoặc tính toán lại chi phí trên HIS trước khi phê duyệt gửi cổng", 
            requires_his_reset=False
        ),
        ErrorDefinition(
            error_code="XML 3 (Dịch vụ kỹ thuật)", 
            keyword="NGAY_YL", 
            root_cause="Giờ cấp y lệnh (NGAY_YL ở XML3) nằm trước giờ vào viện (NGAY_VAO ở XML1, XML8), thường do gộp chi phí ngoại trú vào nội trú", 
            resolution="Điều chỉnh lại trường NGAY_VAO lùi về đúng thời điểm đón tiếp ở phòng khám. Đảm bảo: NGAY_VAO <= NGAY_YL <= NGAY_VAO_NOI_TRU", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 4 (Cận lâm sàng)", 
            keyword="NGAY_KQ", 
            root_cause="Khai báo kết quả cận lâm sàng (GIA_TRI) nhưng bỏ trống ngày kết quả (NGAY_KQ)", 
            resolution="Bắt buộc điền NGAY_KQ nếu đã có kết quả. Nếu phải chờ nuôi cấy lâu ngày, có thể để trống khi gửi thông tuyến nhưng bắt buộc nhập bổ sung trên cổng trước khi đề nghị giám định", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 2 (Chi tiết thuốc)", 
            keyword="MA_DICH_VU", 
            root_cause="Khai báo thuốc/máu ở XML 2 có kèm dịch vụ (ví dụ: 2.6.NAT hoặc thuốc cản quang), nhưng mã dịch vụ này không có mặt trong XML 3", 
            resolution="Bổ dung dịch vụ kỹ thuật tương ứng vào XML 3, đảm bảo mã bên XML 2 và XML 3 khớp nhau từng ký tự", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 1 (Tổng hợp KBCB)", 
            keyword="MA_LOAI_KCB", 
            root_cause="Mã loại KCB là nội trú (3, 4) nhưng hồ sơ thiếu file Giấy ra viện (XML 7) hoặc Tóm tắt HSBA (XML 8)", 
            resolution="Lập và trích xuất thêm XML 7 và XML 8. Nếu bệnh nhân thực tế là ngoại trú, hãy sửa MA_LOAI_KCB về 01 hoặc 02", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 2 (Chi tiết thuốc)", 
            keyword="T_BNCCT", 
            root_cause="Chênh lệch tiền cùng chi trả (T_BNCCT, T_BHTT) do sai số làm tròn khi nhân tỷ lệ % giữa HIS và Cổng giám định", 
            resolution="Sửa trực tiếp số tiền ở dòng bị báo lỗi theo đúng con số mà hệ thống giám định gợi ý (thường lệch 0.01 đồng). Đảm bảo T_BNCCT + T_BHTT = THANH_TIEN_BH", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 3 (Dịch vụ kỹ thuật)", 
            keyword="TT_THAU", 
            root_cause="Nhóm Vật tư y tế (MA_NHOM = 10 ở XML 3) bắt buộc phải có thông tin thầu", 
            resolution="Nhập chuẩn 4 định dạng thầu theo quy định (Số quyết định;Gói thầu;Nhóm thầu;Năm;Đơn vị đấu thầu)", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 7 (Giấy ra viện)", 
            keyword="NGAY_CT", 
            root_cause="Thiếu ngày ký chứng từ trên Giấy ra viện", 
            resolution="Cập nhật ngày chứng từ (NGAY_CT) trên Giấy ra viện bắt buộc phải trùng với ngày ra viện (NGAY_RA)", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 7 (Giấy ra viện)", 
            keyword="MA_DINH_CHI_THAI", 
            root_cause="Ghi nhận có đình chỉ thai (MA_DINH_CHI_THAI = 1) nhưng để trống tuần tuổi thai hoặc nguyên nhân", 
            resolution="Bắt buộc nhập tuần tuổi thai (TUOI_THAI từ 1 đến 42 tuần) và nguyên nhân đình chỉ (NGUYENNHAN_DINHCHI)", 
            requires_his_reset=True
        ),
        ErrorDefinition(
            error_code="XML 11 (Giấy nghỉ việc BHXH)", 
            keyword="SO_NGAY_NGHI", 
            root_cause="Khai báo số ngày nghỉ không khớp công thức (DEN_NGAY - TU_NGAY + 1) hoặc cấp quá 30 ngày/lần", 
            resolution="Cân chỉnh lại ngày bắt đầu (TU_NGAY) trùng ngày đến khám, ngày kết thúc và tổng số ngày cho khớp logic toán học", 
            requires_his_reset=True
        )
    ]

    all_existing = db.query(ErrorDefinition).all()
    for sample in sample_errors:
        sample_clean = re.sub(r'[^A-Z0-9]', '', sample.error_code.upper())
        
        # Tìm xem từ khóa này đã có trong danh mục chưa
        existing = None
        for ed in all_existing:
            ed_clean = re.sub(r'[^A-Z0-9]', '', str(ed.error_code or "").upper())
            if ed_clean.startswith(sample_clean) or sample_clean.startswith(ed_clean):
                if ed.keyword == sample.keyword:
                    existing = ed
                    break
        
        if existing:
            # Cập nhật thông tin mới
            existing.error_code = sample.error_code
            existing.root_cause = sample.root_cause
            existing.resolution = sample.resolution
            existing.requires_his_reset = sample.requires_his_reset
        else:
            # Thêm mới nếu chưa có
            db.add(sample)
            
    db.commit()
    print("[*] Da dong bo va khoi tao danh muc huong dan loi theo quy dinh moi.")
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

    # 3. Lọc theo ErrorDefinition: chỉ lấy ca khớp mã lỗi + keyword (so khớp mềm dẻo)
    matched_records = []
    for r in dept_records:
        r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
        for d in reset_defs:
            d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code or "").upper())
            if d_clean == r_clean or d_clean.startswith(r_clean):
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
        r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
        for d in reset_defs:
            d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code or "").upper())
            if d_clean == r_clean or d_clean.startswith(r_clean):
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

def validate_reconciliation_files(from_date: str, to_date: str, include_errors: bool):
    """Xác thực sự tồn tại và khoảng ngày của các file dữ liệu đầu vào (listbh.xlsx & HoSoLoiChiTiet.xlsx)"""
    # Chuẩn hóa khoảng ngày đối soát
    try:
        clean_from = from_date.replace('-', '').replace('/', '')
        clean_to = to_date.replace('-', '').replace('/', '')
        tu_date = datetime.datetime.strptime(clean_from, "%Y%m%d").date()
        den_date = datetime.datetime.strptime(clean_to, "%Y%m%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Khoảng ngày đối soát đầu vào không hợp lệ.")

    # Nếu đối soát kèm lỗi, kiểm tra HoSoLoiChiTiet.xlsx
    if include_errors:
        loi_path = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
        if not os.path.exists(loi_path):
            raise HTTPException(
                status_code=400, 
                detail="Chưa tải lên tệp lỗi chi tiết (HoSoLoiChiTiet.xlsx). Vui lòng upload trước khi chạy đối soát kèm lỗi."
            )
        try:
            df_hsloi = excel_service.load_hosoloichitiet(loi_path)
            if df_hsloi.empty:
                raise HTTPException(
                    status_code=400, 
                    detail="Tệp HoSoLoiChiTiet.xlsx đã tải lên trống hoặc không chứa dữ liệu hợp lệ."
                )
            
            # Lọc theo khoảng ngày nếu file lỗi có cột "Ngày ra"
            if "Ngày ra" in df_hsloi.columns:
                mask = (df_hsloi["Ngày ra"] >= tu_date) & (df_hsloi["Ngày ra"] <= den_date)
                df_hsloi_filtered = df_hsloi.loc[mask]
                if df_hsloi_filtered.empty:
                    dates = df_hsloi["Ngày ra"].dropna()
                    if not dates.empty:
                        min_d = min(dates).strftime("%d/%m/%Y")
                        max_d = max(dates).strftime("%d/%m/%Y")
                        range_hint = f"Tệp lỗi chỉ chứa dữ liệu từ ngày {min_d} đến {max_d}."
                    else:
                        range_hint = "Tệp lỗi không chứa cột ngày tháng hợp lệ."
                    raise HTTPException(
                        status_code=400,
                        detail=f"Tệp HoSoLoiChiTiet.xlsx không chứa dữ liệu lỗi nào trong khoảng ngày đối soát {tu_date.strftime('%d/%m/%Y')} - {den_date.strftime('%d/%m/%Y')}. {range_hint} Vui lòng upload tệp lỗi đúng."
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Lỗi đọc kiểm tra tệp HoSoLoiChiTiet.xlsx: {str(e)}")


@app.get("/api/records/compare")
def compare_records(
    from_date: str,
    to_date: str,
    include_errors: bool = False,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Đồng bộ SQL HIS bệnh viện, so sánh danh sách và sinh dữ liệu đối soát (Giải mã mật khẩu HIS)"""
    validate_reconciliation_files(from_date, to_date, include_errors)
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
        stats = compare_service.process_comparison(db, df_sql, df_listbh, df_hsloi, ngay_doi_soat, include_errors=include_errors)
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
    validate_reconciliation_files(from_date, to_date, include_errors)
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
    import re
    defs = db.query(ErrorDefinition).all()
    
    result = []
    for r in records:
        item = {
            "id": r.id,
            "ma_lk": r.ma_lk,
            "ho_ten": r.ho_ten,
            "ma_the": r.ma_the,
            "ten_khoa": r.ten_khoa,
            "ma_y_te": r.ma_y_te,
            "ngay_ra_vien": r.ngay_ra_vien,
            "ngay_ra": r.ngay_ra,
            "maloi": r.maloi,
            "motaloi": r.motaloi,
            "status": r.status,
            "note": r.note,
            "loai_ca": resolve_loai_ca(r),
            "root_cause": "Chưa rõ nguyên nhân (Hệ thống tự động quét)",
            "resolution": "Chờ phòng IT bổ sung hướng dẫn chi tiết",
            "requires_his_reset": False
        }
        
        r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
        for d in defs:
            d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code).upper())
            if d_clean == r_clean:
                if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                    item["root_cause"] = d.root_cause
                    item["resolution"] = d.resolution
                    item["requires_his_reset"] = d.requires_his_reset
                    item["maloi"] = d.error_code
                    break
        result.append(item)
    return result


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
    if not df.empty:
        mask_thau_thuoc = (
            df["Mã lỗi"].astype(str).str.upper().str.contains("TT_THAU|MA_THUOC", na=False) |
            df["Mô tả lỗi"].astype(str).str.upper().str.contains("TT_THAU|MA_THUOC", na=False)
        )
        df_thau_thuoc = df[mask_thau_thuoc]
        df_chung = df[~mask_thau_thuoc]
    else:
        df_thau_thuoc = pd.DataFrame(columns=df.columns)
        df_chung = df

    # Tính toán ngày bắt đầu và ngày kết thúc thực tế của tháng để hiển thị trên tên file (ví dụ: _0106_3006)
    end_of_month = month_end - datetime.timedelta(days=1)
    date_suffix = f"_{month_start.strftime('%d%m')}_{end_of_month.strftime('%d%m')}"

    dept_safe = user.department_name.replace(" ", "_").replace("/", "_")
    filename = f"LOI_BHYT_{dept_safe}{date_suffix}.xlsx"
    out_path = os.path.join(UPLOAD_DIR, filename)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_chung.to_excel(writer, sheet_name="Lỗi chung", index=False)
        df_thau_thuoc.to_excel(writer, sheet_name="Lỗi thầu thuốc", index=False)

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
        
        def safe_str(val) -> str:
            if val is None or pd.isna(val):
                return ""
            return str(val).encode('utf-8', errors='replace').decode('utf-8')

        records = []
        for _, r in df.iterrows():
            val = r.get("Ngày ra viện")
            dt_str = ""
            if pd.notna(val):
                try:
                    dt_str = val.strftime("%Y-%m-%d")
                except Exception:
                    dt_str = str(val).split()[0]
                    
            records.append({
                "loai_ca": safe_str(r.get("Loại ca", "Ngoại trú")),
                "ma_lk": safe_str(r.get("MA_LK", "")),
                "ho_ten": safe_str(r.get("Họ tên", "")),
                "ma_the": safe_str(r.get("Mã thẻ", "")),
                "ten_khoa": safe_str(r.get("Tên khoa", "")),
                "ma_y_te": safe_str(r.get("Mã y tế", "")),
                "ngay_ra_vien": safe_str(dt_str)
            })
        return records
    except Exception as e:
        error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/records/admin/loi")
def get_admin_loi_records(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các ca LỖI chưa xử lý theo đợt đối soát để IT theo dõi, sửa lỗi"""
    query = db.query(Record).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    )
    
    fd = normalize_date_to_iso(from_date)
    if fd:
        query = query.filter(Record.ngay_ra_vien >= fd)
            
    td = normalize_date_to_iso(to_date)
    if td:
        query = query.filter(Record.ngay_ra_vien <= td)
        
    records = query.order_by(Record.status.asc(), Record.ngay_ra_vien.asc()).all()
    
    from models import ErrorDefinition
    import re
    defs = db.query(ErrorDefinition).all()
    
    result = []
    for r in records:
        item = {
            "id": r.id,
            "ma_lk": r.ma_lk,
            "ho_ten": r.ho_ten,
            "ma_the": r.ma_the,
            "ten_khoa": r.ten_khoa,
            "ma_y_te": r.ma_y_te,
            "ngay_ra_vien": r.ngay_ra_vien,
            "ngay_ra": r.ngay_ra,
            "maloi": r.maloi,
            "motaloi": r.motaloi,
            "status": r.status,
            "note": r.note or "",
            "loai_ca": resolve_loai_ca(r),
            "root_cause": "Chưa rõ nguyên nhân (Hệ thống tự động quét)",
            "resolution": "Chờ phòng IT bổ sung hướng dẫn chi tiết",
            "requires_his_reset": False
        }
        
        r_clean = re.sub(r'[^A-Z0-9]', '', str(r.maloi or "").upper())
        for d in defs:
            d_clean = re.sub(r'[^A-Z0-9]', '', str(d.error_code).upper())
            if d_clean == r_clean:
                if not d.keyword or (d.keyword and r.motaloi and d.keyword in r.motaloi):
                    item["root_cause"] = d.root_cause
                    item["resolution"] = d.resolution
                    item["requires_his_reset"] = d.requires_his_reset
                    item["maloi"] = d.error_code
                    break
        result.append(item)
    return result


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
    action = data.get("action", "resolve").strip()

    record.note = note
    if action == "edit":
        log_msg = f"IT cập nhật ghi chú. Nội dung: {note}"
        log_action = "EDIT_NOTE"
    else:
        record.status = "RESOLVED"
        log_msg = f"IT xác nhận xử lý thành công. Ghi chú: {note}"
        log_action = "CHANGE_STATUS"

    # Ghi log
    log = RecordLog(
        record_id=record.id,
        username=user.username,
        action=log_action,
        note=log_msg
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
    """Lấy số liệu KPI tổng quan cho Dashboard (Lọc theo tháng đối soát gần nhất)"""
    cfg = db.query(AppConfig).first()
    tong_sql = 0
    tong_bh = 0
    da_gui = 0
    
    # Xác định mốc ngày gần nhất để lọc theo tháng
    last_record = db.query(Record.ngay_ra_vien, Record.ngay_doi_soat, Record.ngay_ra).order_by(Record.id.desc()).first()
    if last_record:
        ref_date = last_record[0] or last_record[1] or last_record[2] or datetime.date.today()
    else:
        ref_date = datetime.date.today()

    year = ref_date.year
    month = ref_date.month

    month_start = datetime.date(year, month, 1)
    if month == 12:
        month_end = datetime.date(year + 1, 1, 1)
    else:
        month_end = datetime.date(year, month + 1, 1)

    if cfg and getattr(cfg, "last_sync_date", None):
        tong_sql = getattr(cfg, "last_tong_sql", 0) or 0
        tong_bh = getattr(cfg, "last_tong_bh", 0) or 0
        da_gui = getattr(cfg, "last_da_gui", 0) or 0
    else:
        if last_record:
            # Lấy target_date là ngay_doi_soat của bản ghi gần nhất
            target_date = last_record[1] or datetime.date.today()
            base_query = db.query(Record).filter(Record.ngay_doi_soat == target_date)
            tong_sql = base_query.count()
            da_gui = base_query.filter(Record.status == "RESOLVED", Record.type_group != "LOI").count()

    from sqlalchemy import func
    date_field = func.coalesce(Record.ngay_ra_vien, Record.ngay_doi_soat, Record.ngay_ra)

    # Lọc số liệu động loi, fail, resolved thuộc khoảng ngày của tháng mục tiêu
    loi = db.query(Record.ma_lk).filter(
        Record.type_group == "LOI", 
        Record.status != "RESOLVED",
        date_field >= month_start,
        date_field < month_end
    ).distinct().count()

    fail = db.query(Record).filter(
        Record.type_group == "FAIL", 
        Record.status != "RESOLVED",
        date_field >= month_start,
        date_field < month_end
    ).count()

    resolved = db.query(Record).filter(
        Record.status == "RESOLVED",
        date_field >= month_start,
        date_field < month_end
    ).count()

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
    """Thống kê chi tiết số lỗi theo từng khoa lâm sàng (Tối ưu hóa tốc độ tải)"""
    last_record = db.query(Record.ngay_doi_soat).order_by(Record.ngay_doi_soat.desc()).first()
    if not last_record:
        return []
        
    # Query chỉ lấy 2 cột ten_khoa và status để bypass ORM object instantiation overhead
    err_records = db.query(Record.ten_khoa, Record.status).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()
    
    # Tổng hợp bằng Python dict
    dept_map = {}
    for r_ten_khoa, r_status in err_records:
        dept = r_ten_khoa or "Chưa phân khoa"
        if dept not in dept_map:
            dept_map[dept] = {"ten_khoa": dept, "pending": 0, "waiting": 0, "total": 0}
        
        dept_map[dept]["total"] += 1
        if r_status == "PENDING":
            dept_map[dept]["pending"] += 1
        elif r_status in {"WAITING_REVIEW", "WAITING_RESEND"}:
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
    include_resolved: bool = False,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách các ca bị FAIL kèm ghi chú và trạng thái"""
    query = db.query(Record).filter(
        Record.type_group == "FAIL"
    )
    if not include_resolved:
        query = query.filter(Record.status != "RESOLVED")
    
    if from_date or to_date:
        fd = normalize_date_to_iso(from_date)
        if fd:
            query = query.filter(Record.ngay_ra_vien >= fd)
        td = normalize_date_to_iso(to_date)
        if td:
            query = query.filter(Record.ngay_ra_vien <= td)

    records = query.order_by(Record.ngay_ra_vien.asc()).all()
    
    data = []
    for r in records:
        status_text = "Đã duyệt" if r.status == "RESOLVED" else ("Chờ gửi lại" if r.status == "WAITING_RESEND" else "Chưa xử lý (PENDING)")
        data.append({
            "Loại ca": resolve_loai_ca(r),
            "MA_LK": r.ma_lk,
            "Họ tên": r.ho_ten,
            "Mã thẻ": r.ma_the,
            "Tên khoa": r.ten_khoa,
            "Mã y tế": r.ma_y_te,
            "Ngày ra viện": r.ngay_ra_vien,
            "Trạng thái": status_text,
            "Ghi chú IT": r.note or ""
        })
        
    df = pd.DataFrame(data)
    date_suffix = ""
    # Trích xuất suffix ngày bắt đầu - ngày kết thúc
    fd_parsed = None
    td_parsed = None
    if from_date:
        fd_iso = normalize_date_to_iso(from_date)
        if fd_iso:
            try:
                fd_parsed = datetime.datetime.strptime(fd_iso, "%Y-%m-%d").date()
            except ValueError:
                pass
    if to_date:
        td_iso = normalize_date_to_iso(to_date)
        if td_iso:
            try:
                td_parsed = datetime.datetime.strptime(td_iso, "%Y-%m-%d").date()
            except ValueError:
                pass
                
    if fd_parsed and td_parsed:
        date_suffix = f"_{fd_parsed.strftime('%d%m')}_{td_parsed.strftime('%d%m')}"
    elif records:
        dates = [r.ngay_ra_vien for r in records if r.ngay_ra_vien]
        if dates:
            min_d = min(dates)
            max_d = max(dates)
            date_suffix = f"_{min_d.strftime('%d%m')}_{max_d.strftime('%d%m')}"

    filename = f"DANH_SACH_FAIL{date_suffix}.xlsx"
    out_path = os.path.join(UPLOAD_DIR, f"DANH_SACH_FAIL{date_suffix}_export.xlsx")
    df.to_excel(out_path, index=False)
    return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)


@app.get("/api/export/loi")
def export_loi_list(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel danh sách các ca bị LỖI kèm thông tin bệnh án"""
    query = db.query(Record).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    )
    
    if from_date or to_date:
        fd = normalize_date_to_iso(from_date)
        if fd:
            query = query.filter(Record.ngay_ra_vien >= fd)
        td = normalize_date_to_iso(to_date)
        if td:
            query = query.filter(Record.ngay_ra_vien <= td)
            
    records = query.order_by(Record.ngay_ra_vien.asc()).all()
    
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
    if not df.empty:
        mask_thau_thuoc = (
            df["MALOI"].astype(str).str.upper().str.contains("TT_THAU|MA_THUOC", na=False) |
            df["MOTALOI"].astype(str).str.upper().str.contains("TT_THAU|MA_THUOC", na=False)
        )
        df_thau_thuoc = df[mask_thau_thuoc]
        df_chung = df[~mask_thau_thuoc]
    else:
        df_thau_thuoc = pd.DataFrame(columns=df.columns)
        df_chung = df

    date_suffix = ""
    fd_parsed = None
    td_parsed = None
    if from_date:
        fd_iso = normalize_date_to_iso(from_date)
        if fd_iso:
            try:
                fd_parsed = datetime.datetime.strptime(fd_iso, "%Y-%m-%d").date()
            except ValueError:
                pass
    if to_date:
        td_iso = normalize_date_to_iso(to_date)
        if td_iso:
            try:
                td_parsed = datetime.datetime.strptime(td_iso, "%Y-%m-%d").date()
            except ValueError:
                pass
                
    if fd_parsed and td_parsed:
        date_suffix = f"_{fd_parsed.strftime('%d%m')}_{td_parsed.strftime('%d%m')}"
    elif records:
        dates = [r.ngay_ra_vien for r in records if r.ngay_ra_vien]
        if dates:
            min_d = min(dates)
            max_d = max(dates)
            date_suffix = f"_{min_d.strftime('%d%m')}_{max_d.strftime('%d%m')}"

    filename = f"DANH_SACH_KEM_LOI{date_suffix}.xlsx"
    out_path = os.path.join(UPLOAD_DIR, f"DANH_SACH_KEM_LOI{date_suffix}_export.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_chung.to_excel(writer, sheet_name="Lỗi chung", index=False)
        df_thau_thuoc.to_excel(writer, sheet_name="Lỗi thầu thuốc", index=False)

    return FileResponse(out_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)


@app.get("/api/export/monthly_summary")
def export_monthly_summary(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel báo cáo tổng hợp số lượng ca XML và lỗi theo tháng (Tách sheet và top 10 lỗi)"""
    # 1. Đọc listbh.xlsx nếu tồn tại để có toàn bộ danh sách đã gửi thực tế
    listbh_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
    if os.path.exists(listbh_path):
        try:
            df_listbh = excel_service.load_listbh(listbh_path)
            # Chuẩn hóa tháng từ cột _ngay
            df_listbh["month"] = pd.to_datetime(df_listbh["_ngay"], errors="coerce").dt.strftime("%Y-%m")
            df_listbh = df_listbh.dropna(subset=["month"])
        except Exception:
            df_listbh = pd.DataFrame(columns=["MA_LK", "_ngay", "month"])
    else:
        df_listbh = pd.DataFrame(columns=["MA_LK", "_ngay", "month"])

    # 2. Truy vấn danh sách records tối ưu hóa để bypass ORM overhead
    records = db.query(
        Record.ma_lk,
        Record.type_group,
        Record.status,
        Record.ngay_ra_vien,
        Record.ngay_doi_soat,
        Record.ngay_ra,
        Record.maloi,
        Record.motaloi
    ).all()

    rec_data = []
    for r in records:
        date_val = r[3] or r[4] or r[5] # ngay_ra_vien, ngay_doi_soat, ngay_ra
        month_str = date_val.strftime("%Y-%m") if date_val else "Không rõ"
        rec_data.append({
            "ma_lk": r[0],
            "type_group": r[1],
            "status": r[2],
            "maloi": r[6] or "",
            "motaloi": r[7] or "",
            "month": month_str
        })
    df_rec = pd.DataFrame(rec_data)
    if df_rec.empty:
        df_rec = pd.DataFrame(columns=["ma_lk", "type_group", "status", "maloi", "motaloi", "month"])

    # 3. Lấy tất cả các tháng khả dụng
    all_months = set()
    if not df_listbh.empty:
        all_months.update(df_listbh["month"].unique())
    if not df_rec.empty:
        all_months.update(df_rec["month"].unique())
    all_months.discard("Không rõ")

    sorted_months = sorted(list(all_months), reverse=True)
    if not sorted_months:
        sorted_months = [datetime.date.today().strftime("%Y-%m")]

    filename = "BAO_CAO_TONG_HOP_THANG.xlsx"
    out_path = os.path.join(UPLOAD_DIR, filename)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for m in sorted_months:
            parts = m.split("-")
            sheet_name = f"Tháng {parts[1]}-{parts[0]}" if len(parts) == 2 else f"Tháng {m}"

            # A. Tính toán số liệu tổng hợp của tháng
            sent_lks = set(df_listbh[df_listbh["month"] == m]["MA_LK"].unique()) if not df_listbh.empty else set()
            df_rec_m = df_rec[df_rec["month"] == m] if not df_rec.empty else pd.DataFrame()
            rec_lks = set(df_rec_m["ma_lk"].unique()) if not df_rec_m.empty else set()

            total_cases_val = len(sent_lks | rec_lks)
            sent_cases_val = len(sent_lks)

            err_cases_val = 0
            err_resolved_val = 0
            total_errors_val = 0
            errors_resolved_val = 0
            fail_cases_val = 0
            fail_resolved_val = 0

            if not df_rec_m.empty:
                df_loi_m = df_rec_m[df_rec_m["type_group"] == "LOI"]
                err_cases_val = len(df_loi_m["ma_lk"].unique())
                err_resolved_val = len(df_loi_m[df_loi_m["status"] == "RESOLVED"]["ma_lk"].unique())

                total_errors_val = len(df_loi_m)
                errors_resolved_val = len(df_loi_m[df_loi_m["status"] == "RESOLVED"])

                df_fail_m = df_rec_m[df_rec_m["type_group"] == "FAIL"]
                fail_cases_val = len(df_fail_m["ma_lk"].unique())
                fail_resolved_val = len(df_fail_m[df_fail_m["status"] == "RESOLVED"]["ma_lk"].unique())

            summary_data = {
                "Chỉ số đối soát": [
                    "Tổng số ca cần gửi",
                    "Số ca đã gửi",
                    "Số ca lỗi",
                    "Số ca lỗi đã từng xử lý",
                    "Tổng số lỗi phát sinh",
                    "Số lỗi đã xử lý",
                    "Số ca fail",
                    "Số ca fail đã xử lý"
                ],
                "Số lượng": [
                    total_cases_val,
                    sent_cases_val,
                    err_cases_val,
                    err_resolved_val,
                    total_errors_val,
                    errors_resolved_val,
                    fail_cases_val,
                    fail_resolved_val
                ]
            }
            df_summary = pd.DataFrame(summary_data)

            # B. Tính danh sách 10 lỗi thường gặp nhất trong tháng
            top_errs = pd.DataFrame(columns=["STT", "Mã lỗi", "Mô tả lỗi", "Số ca mắc"])
            if not df_rec_m.empty:
                df_loi_m = df_rec_m[df_rec_m["type_group"] == "LOI"]
                if not df_loi_m.empty:
                    top_errs = df_loi_m.groupby(["maloi", "motaloi"])["ma_lk"].nunique().reset_index()
                    top_errs.columns = ["Mã lỗi", "Mô tả lỗi", "Số ca mắc"]
                    top_errs = top_errs.sort_values(by="Số ca mắc", ascending=False).head(10)
                    top_errs.insert(0, "STT", range(1, len(top_errs) + 1))

            # Ghi tiêu đề báo cáo
            title_df = pd.DataFrame([[f"BÁO CÁO ĐỐI SOÁT BHYT - THÁNG {parts[1]}/{parts[0]}"]], columns=["TITLE"])
            title_df.to_excel(writer, sheet_name=sheet_name, startrow=0, startcol=0, header=False, index=False)

            # Ghi bảng 1
            pd.DataFrame([["1. SỐ LIỆU TỔNG HỢP"]]).to_excel(writer, sheet_name=sheet_name, startrow=2, startcol=0, header=False, index=False)
            df_summary.to_excel(writer, sheet_name=sheet_name, startrow=3, startcol=0, index=False)

            # Ghi bảng 2
            pd.DataFrame([["2. DANH SÁCH 10 LỖI THƯỜNG GẶP NHẤT"]]).to_excel(writer, sheet_name=sheet_name, startrow=13, startcol=0, header=False, index=False)
            top_errs.to_excel(writer, sheet_name=sheet_name, startrow=14, startcol=0, index=False)

            # Định dạng độ rộng cột tối ưu
            ws = writer.sheets[sheet_name]
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['B'].width = 20
            ws.column_dimensions['C'].width = 65
            ws.column_dimensions['D'].width = 20

    return FileResponse(
        out_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=filename
    )


@app.get("/api/export/department_performance")
def export_department_performance(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Xuất file Excel báo cáo phân tích thực hiện sửa lỗi theo khoa phòng ban và tháng (Tối ưu hóa tốc độ tải)"""
    # Chỉ select các trường cần thiết để bypass ORM instantiation overhead
    records = db.query(
        Record.type_group,
        Record.status,
        Record.ten_khoa,
        Record.ngay_ra_vien,
        Record.ngay_doi_soat,
        Record.ngay_ra
    ).all()

    if not records:
        df = pd.DataFrame(columns=[
            "Khoa/Phòng", "Tháng", 
            "Tổng số lỗi phát sinh", "Số lỗi đã xử lý", "Số lỗi chưa xử lý", "Tỷ lệ sửa lỗi (%)",
            "Tổng số ca FAIL phát sinh", "Số ca FAIL đã xử lý", "Số ca FAIL chưa xử lý", "Tỷ lệ giải quyết FAIL (%)"
        ])
    else:
        data = []
        for r in records:
            date_val = r[3] or r[4] or r[5] # ngay_ra_vien, ngay_doi_soat, ngay_ra
            month_str = date_val.strftime("%Y-%m") if date_val else "Không rõ"
            data.append({
                "type_group": r[0],
                "status": r[1],
                "ten_khoa": r[2] or "Chưa phân khoa",
                "month": month_str
            })
        df_rec = pd.DataFrame(data)
        
        # Group by department and month
        grouped = df_rec.groupby(["ten_khoa", "month"])
        
        report_data = []
        for (dept, month), group in grouped:
            # Errors (LOI)
            df_err = group[group["type_group"] == "LOI"]
            tot_err = len(df_err)
            res_err = len(df_err[df_err["status"] == "RESOLVED"])
            unres_err = tot_err - res_err
            err_rate = f"{(res_err / tot_err * 100):.1f}%" if tot_err > 0 else "0.0%"
            
            # Fail (FAIL)
            df_fail = group[group["type_group"] == "FAIL"]
            tot_fail = len(df_fail)
            res_fail = len(df_fail[df_fail["status"] == "RESOLVED"])
            unres_fail = tot_fail - res_fail
            fail_rate = f"{(res_fail / tot_fail * 100):.1f}%" if tot_fail > 0 else "0.0%"
            
            report_data.append({
                "Khoa/Phòng": dept,
                "Tháng": month,
                "Tổng số lỗi phát sinh": tot_err,
                "Số lỗi đã xử lý": res_err,
                "Số lỗi chưa xử lý": unres_err,
                "Tỷ lệ sửa lỗi (%)": err_rate,
                "Tổng số ca FAIL phát sinh": tot_fail,
                "Số ca FAIL đã xử lý": res_fail,
                "Số ca FAIL chưa xử lý": unres_fail,
                "Tỷ lệ giải quyết FAIL (%)": fail_rate
            })
            
        df = pd.DataFrame(report_data)
        # Sort by Department and Month
        df = df.sort_values(by=["Khoa/Phòng", "Tháng"])
        
        # Add total row
        total_err = df["Tổng số lỗi phát sinh"].sum()
        total_res_err = df["Số lỗi đã xử lý"].sum()
        total_unres_err = df["Số lỗi chưa xử lý"].sum()
        total_err_rate = f"{(total_res_err / total_err * 100):.1f}%" if total_err > 0 else "0.0%"
        
        total_fail = df["Tổng số ca FAIL phát sinh"].sum()
        total_res_fail = df["Số ca FAIL đã xử lý"].sum()
        total_unres_fail = df["Số ca FAIL chưa xử lý"].sum()
        total_fail_rate = f"{(total_res_fail / total_fail * 100):.1f}%" if total_fail > 0 else "0.0%"
        
        total_row = {
            "Khoa/Phòng": "Tổng cộng",
            "Tháng": "-",
            "Tổng số lỗi phát sinh": total_err,
            "Số lỗi đã xử lý": total_res_err,
            "Số lỗi chưa xử lý": total_unres_err,
            "Tỷ lệ sửa lỗi (%)": total_err_rate,
            "Tổng số ca FAIL phát sinh": total_fail,
            "Số ca FAIL đã xử lý": total_res_fail,
            "Số ca FAIL chưa xử lý": total_unres_fail,
            "Tỷ lệ giải quyết FAIL (%)": total_fail_rate
        }
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
        
    filename = "BAO_CAO_KHOA_PHONG_THEO_THANG.xlsx"
    out_path = os.path.join(UPLOAD_DIR, filename)
    df.to_excel(out_path, index=False)
    
    return FileResponse(
        out_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename=filename
    )


# ==========================================
# API: XML VALIDATOR INTEGRATION
# ==========================================
import json
import urllib.request
import urllib.parse

def get_validator_output_dir():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "xml_validator", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                out_dir = cfg.get("output_dir", "Output")
                if not os.path.isabs(out_dir):
                    return os.path.abspath(os.path.join(os.path.dirname(__file__), "xml_validator", out_dir))
                return out_dir
    except Exception:
        pass
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "xml_validator", "Output"))

def get_validator_input_dir():
    try:
        config_path = os.path.join(os.path.dirname(__file__), "xml_validator", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                in_dir = cfg.get("input_dir", "Input")
                if not os.path.isabs(in_dir):
                    return os.path.abspath(os.path.join(os.path.dirname(__file__), "xml_validator", in_dir))
                return in_dir
    except Exception:
        pass
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "xml_validator", "Input"))

XML_PROGRESS = {
    "status": "idle",
    "total_files": 0,
    "processed_files": 0,
    "percent": 0,
    "message": ""
}

def run_direct_validation_scan():
    global XML_PROGRESS
    try:
        XML_PROGRESS["status"] = "scanning"
        XML_PROGRESS["percent"] = 0
        XML_PROGRESS["message"] = "Bắt đầu quét và phân tích XML..."
        
        input_dir = get_validator_input_dir()
        output_dir = get_validator_output_dir()
        
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        def progress_cb(idx, total, filename_msg):
            pct = int((idx / total) * 60) if total > 0 else 0
            XML_PROGRESS["total_files"] = total
            XML_PROGRESS["processed_files"] = idx
            XML_PROGRESS["percent"] = pct
            XML_PROGRESS["message"] = f"[{idx}/{total}] Đang đọc {filename_msg}..."
            
        from xml_validator.xml_parser import group_xml_files
        grouped_data, invalid_files = group_xml_files(input_dir, progress_callback=progress_cb)
        
        XML_PROGRESS["percent"] = 60
        XML_PROGRESS["message"] = "Đang áp dụng 26 quy tắc kiểm tra lỗi BHYT..."
        
        from xml_validator.rule_engine import XMLRuleEngine
        engine = XMLRuleEngine()
        rule_errors = []
        total_p = len(grouped_data)
        
        for idx, (ma_lk, xmls) in enumerate(grouped_data.items()):
            errors = engine.check_rules(ma_lk, xmls)
            rule_errors.extend(errors)
            pct_rules = 60 + int(((idx + 1) / total_p) * 30) if total_p > 0 else 90
            XML_PROGRESS["percent"] = pct_rules
            XML_PROGRESS["message"] = f"Đang đối chiếu quy tắc cho bệnh nhân: {ma_lk} ({idx+1}/{total_p})"
            
        XML_PROGRESS["percent"] = 90
        XML_PROGRESS["message"] = "Đang khởi tạo tệp báo cáo Excel và JSON..."
        
        from xml_validator.report_generator import generate_reports
        excel_path, json_path = generate_reports(grouped_data, rule_errors, invalid_files, output_dir)
        
        XML_PROGRESS["status"] = "completed"
        XML_PROGRESS["percent"] = 100
        XML_PROGRESS["message"] = f"Hoàn tất! Quét xong {total_p} bệnh nhân. Tìm thấy {len(rule_errors) + len(invalid_files)} lỗi."
        
    except Exception as e:
        print(f"[!] Direct scan error: {e}")
        XML_PROGRESS["status"] = "error"
        XML_PROGRESS["percent"] = 0
        XML_PROGRESS["message"] = f"Gặp sự cố lỗi: {str(e)}"

@app.get("/api/admin/xml-validator/status")
def get_main_validator_status(user: User = Depends(require_admin)):
    return {
        "watcher_running": False,
        "input_dir": get_validator_input_dir(),
        "output_dir": get_validator_output_dir()
    }

@app.post("/api/admin/xml-validator/toggle")
def toggle_main_validator(enable: bool, user: User = Depends(require_admin)):
    return {"watcher_running": False, "message": "Tính năng Watcher đã được vô hiệu hóa để chạy trực tiếp."}

@app.post("/api/admin/xml-validator/trigger")
def trigger_main_validator(background_tasks: BackgroundTasks, user: User = Depends(require_admin)):
    global XML_PROGRESS
    if XML_PROGRESS["status"] == "scanning":
        return {"status": "scanning", "message": "Tiến trình quét đang chạy."}
    
    background_tasks.add_task(run_direct_validation_scan)
    return {"status": "scanning", "message": "Đã kích hoạt tiến trình quét đối soát trực tiếp."}

@app.get("/api/admin/xml-validator/config")
def get_main_validator_config(user: User = Depends(require_admin)):
    return {
        "input_dir": get_validator_input_dir(),
        "output_dir": get_validator_output_dir(),
        "api_port": 8000
    }

@app.post("/api/admin/xml-validator/config")
def update_main_validator_config(new_config: dict, user: User = Depends(require_admin)):
    config_path = os.path.join(os.path.dirname(__file__), "xml_validator", "config.json")
    try:
        cfg = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["input_dir"] = new_config.get("input_dir", cfg.get("input_dir", "Input"))
        cfg["output_dir"] = new_config.get("output_dir", cfg.get("output_dir", "Output"))
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể cập nhật cấu hình: {str(e)}")
    return {
        "status": "success",
        "input_dir": get_validator_input_dir(),
        "output_dir": get_validator_output_dir(),
        "watcher_running": False
    }

@app.get("/api/admin/xml-validator/progress")
def get_main_validator_progress(user: User = Depends(require_admin)):
    global XML_PROGRESS
    return XML_PROGRESS

@app.get("/api/admin/xml-validator/results")
def get_xml_validator_results(user: User = Depends(require_admin)):
    output_dir = get_validator_output_dir()
    json_path = os.path.join(output_dir, "ket_qua.json")
    if not os.path.exists(json_path):
        return {"summary": {"total_patients": 0, "total_files": 0, "error_patients": 0, "error_count": 0, "scan_time": "Chưa quét"}, "errors": []}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể đọc kết quả: {str(e)}")

@app.post("/api/admin/xml-validator/upload")
async def upload_xml_files(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), user: User = Depends(require_admin)):
    input_dir = get_validator_input_dir()
    os.makedirs(input_dir, exist_ok=True)
    
    # Xóa toàn bộ file XML cũ trong thư mục Input để tránh nhiễu dữ liệu cũ
    try:
        for f_name in os.listdir(input_dir):
            if f_name.lower().endswith(".xml"):
                os.remove(os.path.join(input_dir, f_name))
    except Exception as e:
        print(f"Error clearing input dir: {str(e)}")
        
    # Lưu các file XML mới
    saved_count = 0
    for file in files:
        if not file.filename.lower().endswith(".xml"):
            continue
        file_path = os.path.join(input_dir, os.path.basename(file.filename))
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        saved_count += 1
        
    if saved_count == 0:
        raise HTTPException(status_code=400, detail="Không có tệp XML hợp lệ nào được tải lên.")
        
    # Kích hoạt quét đối soát ngay lập tức
    global XML_PROGRESS
    if XML_PROGRESS["status"] != "scanning":
        background_tasks.add_task(run_direct_validation_scan)
        
    return {"status": "success", "message": f"Tải lên thành công {saved_count} tệp và kích hoạt quét đối soát."}

@app.get("/api/admin/xml-validator/download")
def download_xml_validator_report(user: User = Depends(require_admin)):
    output_dir = get_validator_output_dir()
    excel_path = os.path.join(output_dir, "TongHopLoi.xlsx")
    if not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Chưa có file báo cáo lỗi Excel. Vui lòng chạy phân tích trước.")
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="TongHopLoi.xlsx"
    )


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
                                    
                                stats = compare_service.process_comparison(temp_db, df_sql, df_listbh, df_hsloi, now.date(), include_errors=False)
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




