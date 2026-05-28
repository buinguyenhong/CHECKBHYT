import pandas as pd
from typing import Optional, Tuple
import datetime
import os
import json
import shutil

# Clipboard / ODBC imports
try:
    import pyodbc
except Exception:
    pyodbc = None

# ==========================================
# SQL CACHE CONFIGURATION
# ==========================================
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache_sql")
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, "index.json")

# Truy vấn HIS theo range dài (ví dụ 1 tháng) có thể chạy lâu.
# 0 = không giới hạn timeout truy vấn ở pyodbc; có thể override bằng biến môi trường.
SQL_QUERY_TIMEOUT_SECONDS = int(os.environ.get("BHYT_SQL_QUERY_TIMEOUT", "0"))
SQL_CONNECT_TIMEOUT_SECONDS = int(os.environ.get("BHYT_SQL_CONNECT_TIMEOUT", "60"))

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def load_cache_index() -> dict:
    ensure_cache_dir()
    if not os.path.exists(CACHE_INDEX_FILE):
        return {}
    try:
        with open(CACHE_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def save_cache_index(index: dict):
    ensure_cache_dir()
    with open(CACHE_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def cache_file_for_start(tu: str) -> str:
    return os.path.join(CACHE_DIR, f"sql_list_{tu}.pkl")

def cache_get(tu: str) -> Optional[Tuple[str, pd.DataFrame]]:
    """Lấy dữ liệu từ cache nếu có và khớp cấu trúc"""
    index = load_cache_index()
    if tu not in index:
        return None
    info = index.get(tu, {})
    cached_end = info.get("end")
    path = info.get("file")
    if not cached_end or not path or not os.path.exists(path):
        return None
    try:
        df = pd.read_pickle(path)
        if not isinstance(df, pd.DataFrame):
            return None
        return cached_end, df
    except Exception:
        return None

def cache_put(tu: str, den: str, df: pd.DataFrame):
    """Lưu dữ liệu vào cache dưới dạng file .pkl"""
    ensure_cache_dir()
    index = load_cache_index()
    path = cache_file_for_start(tu)
    df.to_pickle(path)
    index[tu] = {"end": den, "file": path}
    save_cache_index(index)

def clear_sql_cache():
    """Xóa toàn bộ thư mục cache SQL"""
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    ensure_cache_dir()


# Business logic normalization functions (taken from original main.py)
def chuan_hoa_ma_lk(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return ""
    s = str(value).strip()
    s = s.replace("_CC", "/CC")
    return s

def remove_leading_A(value) -> str:
    s = chuan_hoa_ma_lk(value)
    if s.startswith("A"):
        return s[1:].strip()
    return s

def parse_datetime_to_date(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return dt.dt.date

def build_conn_str(driver: str, server: str, db: str, auth: str, user: str, pw: str) -> str:
    if auth == "Windows Auth":
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};Trusted_Connection=yes;"
    else:
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};UID={user};PWD={pw};"
        
    # Khắc phục lỗi kết nối ODBC Driver 18+ trên mạng LAN bệnh viện (không có SSL tin cậy)
    # ODBC 18 mặc định Encrypt=yes và kiểm tra chứng chỉ nghiêm ngặt.
    if "18" in driver or "19" in driver or "20" in driver:
        conn_str += "TrustServerCertificate=yes;Encrypt=yes;"
        
    return conn_str

ACTIVE_CONNS = set()

def get_conn(cfg: dict):
    global ACTIVE_CONNS
    if pyodbc is None:
        raise RuntimeError("Chưa cài pyodbc trên hệ thống. Vui lòng chạy: pip install pyodbc")
    
    if not cfg.get("server") or not cfg.get("database"):
        raise RuntimeError("Cấu hình CSDL HIS bị thiếu Server hoặc Database.")
        
    auth = cfg.get("auth", "Windows Auth")
    if auth == "SQL Auth" and not cfg.get("user"):
        raise RuntimeError("SQL Auth cần nhập User.")
        
    conn_str = build_conn_str(
        cfg.get("driver", "ODBC Driver 17 for SQL Server"),
        cfg.get("server"),
        cfg.get("database"),
        auth,
        cfg.get("user", ""),
        cfg.get("password", "")
    )
    conn = pyodbc.connect(conn_str, timeout=SQL_CONNECT_TIMEOUT_SECONDS)
    try:
        conn.timeout = SQL_QUERY_TIMEOUT_SECONDS
    except Exception:
        pass
    
    try:
        ACTIVE_CONNS.add(conn)
    except Exception:
        pass
    return conn

def discard_conn(conn):
    global ACTIVE_CONNS
    try:
        ACTIVE_CONNS.discard(conn)
    except Exception:
        pass

def abort_all_queries():
    global ACTIVE_CONNS
    conns = list(ACTIVE_CONNS)
    ACTIVE_CONNS.clear()
    for conn in conns:
        try:
            conn.close()
        except Exception:
            pass

def test_connection(cfg: dict) -> bool:
    conn = get_conn(cfg)
    try:
        cur = conn.cursor()
        try:
            cur.timeout = SQL_QUERY_TIMEOUT_SECONDS
        except Exception:
            pass
        cur.execute("SELECT 1")
        cur.fetchone()
        return True
    finally:
        conn.close()
        discard_conn(conn)

def sql_exec_sp(conn, sp_name: str, tu: str, den: str) -> pd.DataFrame:
    cur = conn.cursor()
    try:
        cur.timeout = SQL_QUERY_TIMEOUT_SECONDS
    except Exception:
        pass
    cur.execute(f"SET NOCOUNT ON; EXEC {sp_name} @TuNgay=?, @DenNgay=?", (tu, den))

    while cur.description is None:
        has_next = cur.nextset()
        if not has_next:
            return pd.DataFrame()

    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return pd.DataFrame.from_records(rows, columns=cols)

def run_update_sql(conn, sql_text: str) -> int:
    cur = conn.cursor()
    try:
        cur.timeout = SQL_QUERY_TIMEOUT_SECONDS
    except Exception:
        pass
    cur.execute("SET NOCOUNT ON;")
    cur.execute(sql_text)
    try:
        rc = cur.rowcount
    except Exception:
        rc = -1
    conn.commit()
    return rc

def normalize_sql_list(df_op: pd.DataFrame, df_ip: pd.DataFrame) -> pd.DataFrame:
    req_op = ["TenBenhNhan", "SoBHYT", "Column4", "SoPhieuThanhToanNgoaiTru", "NgayRa"]
    req_ip = ["TenBenhNhan", "SoBHYT", "SoPhieu_BA", "khoadieutri", "NgayRa"]

    for c in req_op:
        if c not in df_op.columns:
            raise ValueError(f"Stored Procedure Ngoại trú thiếu cột '{c}'. Hiện có: {list(df_op.columns)}")
    for c in req_ip:
        if c not in df_ip.columns:
            raise ValueError(f"Stored Procedure Nội trú thiếu cột '{c}'. Hiện có: {list(df_ip.columns)}")

    op = pd.DataFrame()
    op["Loại ca"] = "Ngoại trú"
    op["MA_LK"] = df_op["Column4"].apply(chuan_hoa_ma_lk)
    op["Họ tên"] = df_op["TenBenhNhan"].fillna("")
    op["Mã thẻ"] = df_op["SoBHYT"].fillna("")
    op["Tên khoa"] = "Khám bệnh"
    op["Mã y tế"] = df_op["SoPhieuThanhToanNgoaiTru"].fillna("")
    op["Ngày ra viện"] = parse_datetime_to_date(df_op["NgayRa"])

    ip = pd.DataFrame()
    ip["Loại ca"] = "Nội trú"
    ip["MA_LK"] = df_ip["SoPhieu_BA"].apply(remove_leading_A)
    ip["Họ tên"] = df_ip["TenBenhNhan"].fillna("")
    ip["Mã thẻ"] = df_ip["SoBHYT"].fillna("")
    ip["Tên khoa"] = df_ip["khoadieutri"].fillna("")
    ip["Mã y tế"] = ""
    ip["Ngày ra viện"] = parse_datetime_to_date(df_ip["NgayRa"])

    out = pd.concat([op, ip], ignore_index=True)
    out = out[out["MA_LK"].astype(str).str.len() > 0]
    out["MA_LK"] = out["MA_LK"].apply(chuan_hoa_ma_lk)
    out = out.drop_duplicates(subset=["MA_LK"], keep="first")

    return out[["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện"]].copy()

def fetch_his_data_range(cfg: dict, tu_ngay: str, den_ngay: str) -> pd.DataFrame:
    """
    Truy vấn trực tiếp từ database cho khoảng ngày cụ thể [tu_ngay, den_ngay]
    """
    conn = get_conn(cfg)
    try:
        df_op = sql_exec_sp(conn, cfg.get("sp_op"), tu_ngay, den_ngay)
        df_ip = sql_exec_sp(conn, cfg.get("sp_ip"), tu_ngay, den_ngay)
        
        if df_op.empty and df_ip.empty:
            return pd.DataFrame()
            
        df = normalize_sql_list(df_op, df_ip)
        if df.empty:
            return df
            
        # Strict dynamic date filter to prevent HIS SP returning records outside the requested range
        try:
            dt_tu = datetime.date(int(tu_ngay[0:4]), int(tu_ngay[4:6]), int(tu_ngay[6:8]))
            dt_den = datetime.date(int(den_ngay[0:4]), int(den_ngay[4:6]), int(den_ngay[6:8]))
            df = df[(df["Ngày ra viện"] >= dt_tu) & (df["Ngày ra viện"] <= dt_den)]
        except Exception:
            pass
        return df
    finally:
        conn.close()
        discard_conn(conn)

def fetch_his_data(cfg: dict, tu_ngay: str, den_ngay: str) -> pd.DataFrame:
    """
    Tải danh sách bệnh nhân đã thanh toán kèm cơ chế CACHE:
    - Nếu đã cache (tu) và cached_end == den_ngay: dùng cache.
    - Nếu đã cache (tu) và cached_end < den_ngay: chỉ chạy phần thiếu [cached_end + 1, den_ngay] rồi ghép.
    - Nếu cached_end > den_ngay hoặc tu khác: chạy full (không cắt được).
    """
    if tu_ngay > den_ngay:
        return pd.DataFrame()

    cached = cache_get(tu_ngay)
    if cached is not None:
        cached_end, cached_df = cached

        if cached_end == den_ngay:
            # Dùng cache hoàn toàn
            return cached_df.copy()
        elif cached_end < den_ngay:
            # Chỉ chạy phần thiếu (cached_end + 1 -> den_ngay)
            try:
                dt_cached_end = datetime.datetime.strptime(cached_end, "%Y%m%d")
                dt_next_day = dt_cached_end + datetime.timedelta(days=1)
                tu2 = dt_next_day.strftime("%Y%m%d")
            except Exception:
                tu2 = tu_ngay # Fallback chạy full nếu lỗi parse ngày

            if tu2 <= den_ngay:
                new_df = fetch_his_data_range(cfg, tu2, den_ngay)
            else:
                new_df = pd.DataFrame()

            # Ghép cache cũ và phần mới
            merged = pd.concat([cached_df, new_df], ignore_index=True)
            merged = merged.drop_duplicates(subset=["MA_LK"], keep="first")
            
            # Cập nhật cache
            cache_put(tu_ngay, den_ngay, merged)
            return merged
            
    # Chạy full (chưa có cache hoặc cache không khớp)
    df = fetch_his_data_range(cfg, tu_ngay, den_ngay)
    cache_put(tu_ngay, den_ngay, df)
    return df


def build_reset_sql(keys: list[str], loai: str) -> str:
    keys = [chuan_hoa_ma_lk(k) for k in keys if chuan_hoa_ma_lk(k)]
    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
            
    if not unique_keys:
        return "-- Không có mã nào để reset."

    # Fallback cho loai nếu bị nan/trống
    if not loai or str(loai).strip().lower() in ("nan", "none", ""):
        if unique_keys and unique_keys[0].startswith("TN."):
            loai = "Ngoại trú"
        else:
            loai = "Nội trú"

    quoted = ",\n    ".join([f"'{k}'" for k in unique_keys])

    if loai == "Ngoại trú":
        return f"""UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM TiepNhan tn
JOIN XacNhanChiPhi xn ON xn.TiepNhan_Id = tn.TiepNhan_Id
WHERE tn.SoTiepNhan IN (
    {quoted}
);
"""
    return f"""UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM BenhAn ba
JOIN XacNhanChiPhi xn ON xn.BenhAn_Id = ba.BenhAn_Id
WHERE ba.SoBenhAn IN (
    {quoted}
);
"""

def build_benhan_unlock_sql(keys: list[str], action_type: str) -> str:
    """
    Sinh script mở/khóa lại bệnh án nội trú để IT copy chạy trên SSMS.

    - UNLOCK: đưa BenhAn.TrangThai về DaXuatVien để khoa sửa.
    - CLOSE: đưa BenhAn.TrangThai về DaThanhToan sau khi khoa sửa xong.
    """
    keys = [chuan_hoa_ma_lk(k) for k in keys if chuan_hoa_ma_lk(k)]
    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    if not unique_keys:
        return "-- Không có số bệnh án nào để cập nhật trạng thái."

    if action_type == "UNLOCK":
        target_status = "DaXuatVien"
        title = "MO KHOA BENH AN CHO KHOA SUA"
    elif action_type == "CLOSE":
        target_status = "DaThanhToan"
        title = "KHOA LAI BENH AN SAU KHI KHOA SUA XONG"
    else:
        return "-- action_type không hợp lệ. Chỉ hỗ trợ UNLOCK hoặc CLOSE."

    quoted_values = []
    for k in unique_keys:
        quoted_values.append("'" + k.replace("'", "''") + "'")
    quoted = ",\n    ".join(quoted_values)

    return f"""-- {title}
-- So ca: {len(unique_keys)}
-- Kiem tra truoc khi cap nhat:
SELECT ba.SoBenhAn, ba.TrangThai, ba.NgayRaVien
FROM BenhAn ba
WHERE ba.SoBenhAn IN (
    {quoted}
);

-- Chay lenh UPDATE ben duoi khi da kiem tra dung danh sach:
UPDATE ba
SET TrangThai = '{target_status}'
FROM BenhAn ba
WHERE ba.SoBenhAn IN (
    {quoted}
);
"""

def execute_reset(cfg: dict, keys: list[str], loai: str) -> int:
    """
    Chạy cập nhật reset cờ xuất trên database HIS của bệnh viện
    """
    sql_script = build_reset_sql(keys, loai)
    if sql_script.startswith("--"):
        return 0
        
    conn = get_conn(cfg)
    try:
        return run_update_sql(conn, sql_script)
    finally:
        conn.close()
