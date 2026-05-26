import pandas as pd
from typing import Optional
import datetime

# Clipboard / ODBC imports
try:
    import pyodbc
except Exception:
    pyodbc = None

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
        conn_str += "TrustServerCertificate=yes;Encrypt=no;"
        
    return conn_str

def get_conn(cfg: dict):
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
    return pyodbc.connect(conn_str, timeout=25)

def test_connection(cfg: dict) -> bool:
    conn = get_conn(cfg)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return True
    finally:
        conn.close()

def sql_exec_sp(conn, sp_name: str, tu: str, den: str) -> pd.DataFrame:
    cur = conn.cursor()
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

def fetch_his_data(cfg: dict, tu_ngay: str, den_ngay: str) -> pd.DataFrame:
    """
    Kết nối SQL Server HIS và tải danh sách bệnh nhân đã thanh toán
    """
    conn = get_conn(cfg)
    try:
        df_op = sql_exec_sp(conn, cfg.get("sp_op"), tu_ngay, den_ngay)
        df_ip = sql_exec_sp(conn, cfg.get("sp_ip"), tu_ngay, den_ngay)
        
        if df_op.empty and df_ip.empty:
            return pd.DataFrame()
            
        return normalize_sql_list(df_op, df_ip)
    finally:
        conn.close()

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
