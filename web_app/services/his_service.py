import pandas as pd
from typing import Optional, Tuple
import datetime
import os
import json
import shutil
import sys

def safe_print(msg: str):
    try:
        print(msg)
    except Exception:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

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
    updated_at = info.get("updated_at")
    if not cached_end or not path or not os.path.exists(path):
        return None
    try:
        df = pd.read_pickle(path)
        if not isinstance(df, pd.DataFrame):
            return None
            
        # Nếu có thông tin ngày cập nhật cache, tự động trim bỏ phần cache không an toàn (sau ngày chạy sync)
        if updated_at:
            try:
                dt_update = datetime.datetime.strptime(updated_at, "%Y%m%d").date()
                # Ngày an toàn tối đa của dữ liệu cũ là ngày trước ngày cập nhật
                dt_safe = dt_update - datetime.timedelta(days=1)
                safe_end_str = dt_safe.strftime("%Y%m%d")
                
                # Nếu cache tuyên bố có dữ liệu vượt quá ngày an toàn, trim bớt để đảm bảo không bị stale
                if cached_end > safe_end_str:
                    try:
                        df_date = pd.to_datetime(df["Ngày ra viện"], errors="coerce").dt.date
                        df = df[df_date <= dt_safe]
                        cached_end = safe_end_str
                    except Exception:
                        return None # Lỗi filter thì bỏ qua cache
            except Exception:
                pass
                
        return cached_end, df
    except Exception:
        return None

def cache_put(tu: str, den: str, df: pd.DataFrame):
    """Lưu dữ liệu vào cache dưới dạng file .pkl"""
    ensure_cache_dir()
    index = load_cache_index()
    path = cache_file_for_start(tu)
    df.to_pickle(path)
    today_str = datetime.date.today().strftime("%Y%m%d")
    index[tu] = {
        "end": den,
        "file": path,
        "updated_at": today_str
    }
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
    if s.startswith("A."):
        return s[2:].strip()
    elif s.startswith("A"):
        return s[1:].strip()
    return s

def parse_datetime_to_date(series: pd.Series) -> pd.Series:
    def parse_single(val):
        if pd.isna(val) or val is None:
            return None
        if isinstance(val, (datetime.date, datetime.datetime)):
            if isinstance(val, datetime.datetime):
                return val.date()
            return val
        val_str = str(val).strip()
        if not val_str:
            return None
        try:
            # Nếu bắt đầu bằng 4 chữ số năm (ví dụ: 202606050823 hoặc 2026-06-01)
            if len(val_str) >= 4 and val_str[:4].isdigit():
                ts = pd.to_datetime(val_str, errors="coerce", dayfirst=False)
            else:
                ts = pd.to_datetime(val_str, errors="coerce", dayfirst=True)
            if pd.isna(ts):
                return None
            return ts.date()
        except Exception:
            return None
    return series.apply(parse_single)

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

def get_col_series(df: pd.DataFrame, candidates: list[str], default_val="") -> pd.Series:
    if df.empty:
        return pd.Series(dtype=str)
    for c in candidates:
        if c in df.columns:
            return df[c]
    col_map = {str(col).lower(): col for col in df.columns}
    for c in candidates:
        if c.lower() in col_map:
            return df[col_map[c.lower()]]
    return pd.Series([default_val] * len(df), index=df.index)

def fetch_phong_kham_ngoai_tru(conn, stn_list: list) -> dict:
    """
    Truy vấn tên phòng khám cho các ca Ngoại trú theo danh sách Số tiếp nhận (tn.SoTiepNhan).
    - Đã bỏ JOIN DM_DichVu không cần thiết để tối ưu tốc độ truy vấn CSDL HIS.
    - Trường hợp 1 phòng: hiển thị tên phòng khám.
    - Trường hợp nhiều phòng: hiển thị tên tất cả các phòng (ghép bằng dấu phẩy).
    """
    stn_clean = [str(s).strip() for s in stn_list if str(s).strip()]
    if not stn_clean or conn is None:
        return {}

    res_map = {}
    chunk_size = 500
    for i in range(0, len(stn_clean), chunk_size):
        chunk = stn_clean[i:i + chunk_size]
        quoted = ", ".join([f"'{s}'" for s in chunk])
        sql = f"""
        SELECT 
            tn.SoTiepNhan AS [So_Tiep_Nhan],
            pb.TenPhongBan AS [Ten_Phong_Kham]
        FROM KhamBenh kb WITH (NOLOCK)
        INNER JOIN TiepNhan tn WITH (NOLOCK) ON kb.TiepNhan_Id = tn.TiepNhan_Id
        INNER JOIN DM_PhongBan pb WITH (NOLOCK) ON kb.PhongBan_Id = pb.PhongBan_Id
        WHERE tn.SoTiepNhan IN ({quoted})
        """
        cur = None
        try:
            cur = conn.cursor()
            try:
                cur.timeout = SQL_QUERY_TIMEOUT_SECONDS
            except Exception:
                pass
            cur.execute(sql)
            rows = cur.fetchall()
            for r in rows:
                stn = str(r[0]).strip() if r[0] is not None else ""
                tpk = str(r[1]).strip() if r[1] is not None else ""
                if stn and tpk:
                    k_raw = stn.upper()
                    k_norm = chuan_hoa_ma_lk(stn).upper()
                    for k in set([k_raw, k_norm]):
                        if k not in res_map:
                            res_map[k] = []
                        if tpk not in res_map[k]:
                            res_map[k].append(tpk)
        except Exception as e:
            safe_print(f"Lỗi khi truy vấn tên phòng khám ngoại trú: {str(e)}")
        finally:
            if cur:
                try:
                    cur.close()
                except Exception:
                    pass

    final_map = {}
    for k, rooms in res_map.items():
        final_map[k] = ", ".join(rooms)
    return final_map

def normalize_sql_list(df_op: pd.DataFrame, df_ip: pd.DataFrame) -> pd.DataFrame:
    op = pd.DataFrame()
    if not df_op.empty:
        op["Loại ca"] = "Ngoại trú"
        s_ma_lk = get_col_series(df_op, ["column4", "SoPhieu_BA", "sobenhan", "ma_lk"])
        op["MA_LK"] = s_ma_lk.apply(chuan_hoa_ma_lk)
        op["Họ tên"] = get_col_series(df_op, ["TenBenhNhan", "ho_ten"]).fillna("")
        op["Mã thẻ"] = get_col_series(df_op, ["SoBHYT", "ma_the"]).fillna("")
        s_ten_khoa = get_col_series(df_op, ["Ten_Phong_Kham", "TenKhoa", "Tên khoa", "ten_khoa"]).fillna("")
        def clean_khoa(val):
            if pd.isna(val) or val is None:
                return "Khám bệnh"
            s = str(val).strip()
            if not s or s.lower() in ["nan", "none", "null"]:
                return "Khám bệnh"
            return s
        op["Tên khoa"] = s_ten_khoa.apply(clean_khoa)
        op["Mã y tế"] = get_col_series(df_op, ["ma_bn", "SoPhieuThanhToanNgoaiTru"]).fillna("")
        op["Ngày ra viện"] = parse_datetime_to_date(get_col_series(df_op, ["NgayRa", "ngay_ra"]))

    ip = pd.DataFrame()
    if not df_ip.empty:
        ip["Loại ca"] = "Nội trú"
        s_so_ba = get_col_series(df_ip, ["column4", "sobenhan", "SoPhieu_BA", "ma_lk"])
        ip["MA_LK"] = s_so_ba.apply(chuan_hoa_ma_lk)
        ip["Họ tên"] = get_col_series(df_ip, ["TenBenhNhan", "ho_ten"]).fillna("")
        ip["Mã thẻ"] = get_col_series(df_ip, ["SoBHYT", "ma_the"]).fillna("")
        ip["Tên khoa"] = get_col_series(df_ip, ["khoadieutri", "ten_khoa"]).fillna("")
        ip["Mã y tế"] = get_col_series(df_ip, ["ma_bn"]).fillna("")
        ip["Ngày ra viện"] = parse_datetime_to_date(get_col_series(df_ip, ["NgayRa", "ngay_ra"]))

    out = pd.concat([op, ip], ignore_index=True)
    if out.empty:
        return pd.DataFrame(columns=["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện"])

    out = out[out["MA_LK"].astype(str).str.len() > 0]
    out["MA_LK"] = out["MA_LK"].apply(chuan_hoa_ma_lk)
    out = out.drop_duplicates(subset=["MA_LK"], keep="first")

    return out[["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện"]].copy()

def fetch_his_data_range(cfg: dict, tu_ngay: str, den_ngay: str, log_callback=None) -> pd.DataFrame:
    """
    Truy vấn trực tiếp từ database cho khoảng ngày cụ thể [tu_ngay, den_ngay]
    """
    def log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        else:
            try:
                safe_print(f"[*] [SQL HIS] {msg}")
            except Exception:
                pass

    conn = get_conn(cfg)
    try:
        sp_op = cfg.get("sp_op") or "dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NgoaiTru_Optimized"
        sp_ip = cfg.get("sp_ip") or "dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NoiTru_Optimized"

        log(f"Bắt đầu gọi Stored Procedure Ngoại trú: {sp_op} từ {tu_ngay} đến {den_ngay}...")
        df_op = sql_exec_sp(conn, sp_op, tu_ngay, den_ngay)
        log(f"  -> Ngoại trú trả về: {len(df_op)} dòng. Cột: {list(df_op.columns)}")

        if not df_op.empty:
            stn_series = get_col_series(df_op, ["column4", "SoPhieu_BA", "sobenhan", "ma_lk"])
            stn_list = [s for s in stn_series.dropna().unique() if str(s).strip()]
            if stn_list:
                log(f"Đang lấy tên phòng khám cho {len(stn_list)} số tiếp nhận Ngoại trú...")
                pk_map = fetch_phong_kham_ngoai_tru(conn, stn_list)
                if pk_map:
                    def resolve_pk(val):
                        if pd.isna(val) or val is None:
                            return "Khám bệnh"
                        k_str = str(val).strip()
                        if not k_str:
                            return "Khám bệnh"
                        res = pk_map.get(k_str.upper()) or pk_map.get(chuan_hoa_ma_lk(k_str).upper())
                        return res if res else "Khám bệnh"

                    df_op["Ten_Phong_Kham"] = stn_series.apply(resolve_pk)
                    log(f"  -> Đã lấy được tên phòng khám cho các ca Ngoại trú.")

        log(f"Bắt đầu gọi Stored Procedure Nội trú: {sp_ip} từ {tu_ngay} đến {den_ngay}...")
        df_ip = sql_exec_sp(conn, sp_ip, tu_ngay, den_ngay)
        log(f"  -> Nội trú trả về: {len(df_ip)} dòng. Cột: {list(df_ip.columns)}")
        
        # Ghi debug ra file log để theo dõi dạng dữ liệu ngày thực tế dưới CSDL HIS bệnh viện
        try:
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "debug_date.log")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(f"--- DEBUG DATE: {datetime.datetime.now()} ---\n")
                f.write(f"Query range: {tu_ngay} -> {den_ngay}\n")
                
                f.write("\n=== NGOẠI TRÚ ===\n")
                if not df_op.empty and "NgayRa" in df_op.columns:
                    f.write("Raw values of NgayRa (first 30 rows):\n")
                    for idx in range(min(30, len(df_op))):
                        val = df_op.loc[idx, "NgayRa"]
                        f.write(f"Row {idx}: Raw={repr(val)} | Type={type(val)}\n")
                else:
                    f.write("df_op is empty or NgayRa not in columns\n")
                    
                f.write("\n=== NỘI TRÚ ===\n")
                if not df_ip.empty and "NgayRa" in df_ip.columns:
                    f.write("Raw values of NgayRa (first 30 rows):\n")
                    for idx in range(min(30, len(df_ip))):
                        val = df_ip.loc[idx, "NgayRa"]
                        f.write(f"Row {idx}: Raw={repr(val)} | Type={type(val)}\n")
                else:
                    f.write("df_ip is empty or NgayRa not in columns\n")
        except Exception as e:
            log(f"Lỗi ghi file debug: {str(e)}")
            
        if df_op.empty and df_ip.empty:
            log("Cả hai Stored Procedure đều trả về danh sách rỗng.")
            return pd.DataFrame()
            
        df = normalize_sql_list(df_op, df_ip)
        log(f"Sau khi chuẩn hóa và loại trùng lặp: {len(df)} ca.")
        
        if df.empty:
            return df
            
        # Tính toán min/max của cột Ngày ra viện thực tế để phục vụ phân tích
        try:
            non_null_dates = df["Ngày ra viện"].dropna()
            if not non_null_dates.empty:
                min_date = non_null_dates.min()
                max_date = non_null_dates.max()
                log(f"Khoảng Ngày ra viện thực tế trong dữ liệu thô: {min_date} -> {max_date}")
            else:
                log("Cảnh báo: Không có dòng nào có Ngày ra viện hợp lệ.")
        except Exception as ex:
            log(f"Không thể thống kê khoảng Ngày ra viện: {str(ex)}")

        # Strict dynamic date filter to prevent HIS SP returning records outside the requested range
        try:
            dt_tu = datetime.date(int(tu_ngay[0:4]), int(tu_ngay[4:6]), int(tu_ngay[6:8]))
            dt_den = datetime.date(int(den_ngay[0:4]), int(den_ngay[4:6]), int(den_ngay[6:8]))
            
            df_filtered = df[(df["Ngày ra viện"] >= dt_tu) & (df["Ngày ra viện"] <= dt_den)]
            log(f"Sau khi lọc Ngày ra viện trong khoảng đối soát [{dt_tu} -> {dt_den}]: {len(df_filtered)} ca.")
            
            diff = len(df) - len(df_filtered)
            if diff > 0:
                log(f"[Cảnh báo] Có {diff} ca có Ngày ra viện nằm ngoài khoảng đối soát đã bị loại bỏ.")
            df = df_filtered
        except Exception as ex:
            log(f"Lỗi khi áp dụng bộ lọc Ngày ra viện: {str(ex)}")
            
        return df
    finally:
        conn.close()
        discard_conn(conn)

def fetch_his_data(cfg: dict, tu_ngay: str, den_ngay: str, log_callback=None) -> pd.DataFrame:
    """
    Tải danh sách bệnh nhân đã thanh toán kèm cơ chế CACHE:
    - Nếu đã cache (tu) và cached_end == den_ngay: dùng cache.
    - Nếu đã cache (tu) và cached_end < den_ngay: chỉ chạy phần thiếu [cached_end + 1, den_ngay] rồi ghép.
    - Nếu cached_end > den_ngay hoặc tu khác: chạy full (không cắt được).
    """
    if tu_ngay > den_ngay:
        return pd.DataFrame()

    def log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass
        else:
            try:
                safe_print(f"[*] [SQL Cache] {msg}")
            except Exception:
                pass

    cached = cache_get(tu_ngay)
    if cached is not None:
        cached_end, cached_df = cached

        if cached_end == den_ngay:
            log(f"Sử dụng dữ liệu cache hoàn toàn từ {tu_ngay} đến {den_ngay} ({len(cached_df)} ca).")
            return cached_df.copy()
        elif cached_end < den_ngay:
            try:
                dt_cached_end = datetime.datetime.strptime(cached_end, "%Y%m%d")
                dt_next_day = dt_cached_end + datetime.timedelta(days=1)
                tu2 = dt_next_day.strftime("%Y%m%d")
            except Exception:
                tu2 = tu_ngay # Fallback chạy full nếu lỗi parse ngày

            if tu2 <= den_ngay:
                log(f"Cache hiện tại chỉ đến {cached_end}. Bắt đầu truy vấn phần còn thiếu [{tu2} -> {den_ngay}]...")
                new_df = fetch_his_data_range(cfg, tu2, den_ngay, log_callback=log_callback)
            else:
                new_df = pd.DataFrame()

            # Ghép cache cũ và phần mới
            merged = pd.concat([cached_df, new_df], ignore_index=True)
            merged = merged.drop_duplicates(subset=["MA_LK"], keep="first")
            
            # Cập nhật cache
            cache_put(tu_ngay, den_ngay, merged)
            log(f"Đã cập nhật và ghi đè cache mới. Tổng số ca: {len(merged)}.")
            return merged
            
    # Chạy full (chưa có cache hoặc cache không khớp)
    log(f"Không tìm thấy cache phù hợp cho {tu_ngay}. Thực hiện truy vấn mới toàn bộ...")
    df = fetch_his_data_range(cfg, tu_ngay, den_ngay, log_callback=log_callback)
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
