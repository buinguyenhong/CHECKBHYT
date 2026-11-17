import os
import re
import glob
import datetime
from decimal import Decimal, InvalidOperation
import openpyxl
import pandas as pd
from io import BytesIO
from typing import Union, Optional, Set, Dict, Iterable, List, Tuple
from services.his_service import chuan_hoa_ma_lk, parse_datetime_to_date

MA_LK_CANDIDATE_HEADERS = {
    "ma_lk", "mã liên kết", "mã_lk", "ma lk", "so_seri"
}


def extract_cell_text_openpyxl(cell) -> str:
    """
    Đọc trực tiếp giá trị từ đối tượng Cell của openpyxl, kiểm tra:
    - cell.value
    - cell.data_type
    - cell.number_format
    Nguyên tắc:
    1. Nếu ô là chuỗi (data_type in ('s', 'str', 'inlineStr') hoặc isinstance(val, str)):
       Giữ nguyên chuỗi gốc (bảo toàn số 0 ở cuối như '26.035530').
    2. Nếu ô là kiểu số (data_type == 'n' hoặc int/float):
       - Nếu cell.number_format có khai báo phần thập phân cố định (ví dụ '0.000000', '#,##0.000000'):
         Khôi phục đúng số chữ số thập phân theo định dạng hiển thị của ô đó.
       - Nếu cell.number_format là 'General' hoặc '@':
         Tuyệt đối KHÔNG tự động thêm số 0 nếu không có căn cứ định dạng.
    """
    val = cell.value
    if val is None:
        return ""
    if cell.data_type in ("s", "str", "inlineStr") or isinstance(val, str):
        return str(val).strip()

    if cell.data_type == "n" or isinstance(val, (int, float, Decimal)):
        fmt = str(getattr(cell, "number_format", "") or "").strip()
        # Lấy phần định dạng cho số dương (trước dấu ';')
        pos_fmt = fmt.split(";")[0].strip() if fmt else ""
        if pos_fmt and pos_fmt.lower() != "general" and pos_fmt != "@":
            m = re.search(r"[0#]\.([0#]+)", pos_fmt)
            if m:
                dec_mask = m.group(1)
                min_decimals = len(dec_mask.rstrip("#"))
                if min_decimals > 0:
                    try:
                        d_val = Decimal(str(val))
                        quant = Decimal("1." + ("0" * min_decimals))
                        return str(d_val.quantize(quant))
                    except (InvalidOperation, ValueError):
                        pass
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        return str(val).strip()

    if isinstance(val, float) and pd.isna(val):
        return ""
    return str(val).strip()


def read_excel_preserving_ma_lk(file_source: Union[str, BytesIO, bytes]) -> pd.DataFrame:
    """
    Đọc tệp Excel sang DataFrame với dtype=str, đồng thời dùng openpyxl kiểm tra trực tiếp
    cell.value, cell.data_type, cell.number_format trên cột MA_LK / Mã liên kết để khôi phục
    chính xác các ô số có định dạng hiển thị thập phân (ví dụ number_format='0.000000').
    """
    if isinstance(file_source, bytes):
        stream_for_pd = BytesIO(file_source)
        stream_for_wb = BytesIO(file_source)
    elif isinstance(file_source, BytesIO):
        raw_bytes = file_source.getvalue()
        stream_for_pd = BytesIO(raw_bytes)
        stream_for_wb = BytesIO(raw_bytes)
    else:
        stream_for_pd = file_source
        stream_for_wb = file_source

    df = pd.read_excel(stream_for_pd, dtype=str)
    if df.empty:
        return df

    raw_len = len(df)
    non_empty_mask = df.notna().any(axis=1)
    if not non_empty_mask.any():
        return df.iloc[0:0].copy()

    wb = None
    try:
        wb = openpyxl.load_workbook(stream_for_wb, read_only=True, data_only=True)
        ws = wb.active
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=False), [])
        lk_cols = []
        for idx, h_cell in enumerate(header_row):
            h_name = str(h_cell.value or "").strip()
            if h_name.lower() in MA_LK_CANDIDATE_HEADERS and h_name in df.columns:
                lk_cols.append((idx, h_name))

        if lk_cols:
            max_idx = max(idx for idx, _ in lk_cols)
            max_row_limit = raw_len + 1
            extracted_by_name = {h_name: [] for _, h_name in lk_cols}
            for row in ws.iter_rows(min_row=2, max_row=max_row_limit, min_col=1, max_col=max_idx + 1, values_only=False):
                for idx, h_name in lk_cols:
                    cell = row[idx] if idx < len(row) else None
                    extracted_by_name[h_name].append(extract_cell_text_openpyxl(cell) if cell is not None else "")
            for _, h_name in lk_cols:
                vals = extracted_by_name[h_name]
                if len(vals) == raw_len:
                    df[h_name] = vals
                elif len(vals) > raw_len:
                    df[h_name] = vals[:raw_len]
    except Exception:
        pass
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass

    return df.loc[non_empty_mask].reset_index(drop=True)


def build_trusted_numeric_ma_lk_map(trusted_keys: Iterable[str]) -> Dict[str, Optional[str]]:
    """
    Xây dựng bảng ánh xạ từ dạng chuẩn hóa số thập phân (đã bỏ số 0 cuối, hỗ trợ kèm hậu tố /CC)
    sang mã MA_LK gốc từ nguồn dữ liệu đáng tin cậy (SQL Server HIS / bảng Record).
    Nếu có từ 2 mã khác nhau cùng rút gọn về 1 giá trị (nhập nhằng), đánh dấu None để không tự đoán.
    """
    numeric_map: Dict[str, Optional[str]] = {}
    for raw_k in trusted_keys:
        if not raw_k:
            continue
        k = chuan_hoa_ma_lk(raw_k).upper()
        m = re.match(r"^(\d+\.\d+)(/CC)?$", k)
        if m:
            base = m.group(1).rstrip("0").rstrip(".")
            suffix = m.group(2) or ""
            canon = f"{base}{suffix}"
            if canon not in numeric_map:
                numeric_map[canon] = k
            elif numeric_map[canon] != k:
                numeric_map[canon] = None
    return numeric_map


def resolve_ma_lk_against_trusted_set(
    ma_lk: str,
    trusted_keys: Set[str],
    numeric_map: Optional[Dict[str, Optional[str]]] = None
) -> str:
    """
    Đối chiếu mã MA_LK đọc từ Excel với tập mã nguồn đáng tin cậy (SQL Server HIS):
    - Nếu khớp trực tiếp trong trusted_keys -> giữ nguyên.
    - Nếu là mã dạng số thập phân (có thể kèm /CC) bị mất số 0 ở cuối (do Excel lưu kiểu số General)
      và trong trusted_keys có DUY NHẤT 1 mã khớp chính xác giá trị số đó -> khôi phục theo mã chuẩn của HIS.
    - Nếu không có căn cứ trong trusted_keys hoặc bị trùng/nhập nhằng -> giữ nguyên, tuyệt đối không tự thêm số 0.
    """
    lk = chuan_hoa_ma_lk(ma_lk).upper()
    if not lk or not trusted_keys:
        return lk
    if lk in trusted_keys:
        return lk
    m = re.match(r"^(\d+\.\d+)(/CC)?$", lk)
    if m:
        if numeric_map is None:
            numeric_map = build_trusted_numeric_ma_lk_map(trusted_keys)
        base = m.group(1).rstrip("0").rstrip(".")
        suffix = m.group(2) or ""
        canon = f"{base}{suffix}"
        candidate = numeric_map.get(canon)
        if candidate:
            cand_base = candidate[:-3] if candidate.endswith("/CC") else candidate
            lk_base = m.group(1)
            if cand_base.startswith(lk_base) and candidate.endswith(suffix):
                return candidate
    return lk


def _find_listbh_columns(
    df: pd.DataFrame,
    key_col: str = "Mã liên kết",
    date_col: str = "Ngày ra"
) -> Tuple[Optional[str], Optional[str]]:
    """Tìm tên cột khóa chính MA_LK và cột ngày ra trong DataFrame listbh."""
    found_key = None
    candidates_key = [key_col, "Mã liên kết", "MA_LK", "MÃ LIÊN KẾT", "Mã Liên Kết", "MÃ_LK", "Ma_LK", "Mã LK", "SO_SERI"]
    for c in candidates_key:
        if c in df.columns:
            found_key = c
            break
    if not found_key:
        col_map = {str(c).lower(): c for c in df.columns}
        for c in ["mã liên kết", "ma_lk", "mã_lk", "ma lk"]:
            if c in col_map:
                found_key = col_map[c]
                break

    found_date = None
    candidates_date = [date_col, "Ngày ra", "NGÀY RA", "NgayRa", "NGAY_RA", "Ngày ra viện", "NGÀY RA VIỆN", "Ngay_Ra"]
    for c in candidates_date:
        if c in df.columns:
            found_date = c
            break
    if not found_date:
        col_map = {str(c).lower(): c for c in df.columns}
        for c in ["ngày ra", "ngayra", "ngay_ra", "ngày ra viện"]:
            if c in col_map:
                found_date = col_map[c]
                break

    return found_key, found_date


def apply_text_format_to_ma_lk_columns(ws, fallback_first_col: bool = False) -> None:
    """Định dạng Text (@) cho các cột MA_LK / Mã liên kết trên worksheet openpyxl để bảo toàn số 0 ở cuối."""
    header_cells = next(ws.iter_rows(min_row=1, max_row=1, values_only=False), [])
    lk_cols = [
        idx + 1 for idx, h_cell in enumerate(header_cells)
        if str(h_cell.value or "").strip().lower() in MA_LK_CANDIDATE_HEADERS
    ]
    if not lk_cols and fallback_first_col and len(header_cells) > 0:
        lk_cols = [1]
    for col_idx in lk_cols:
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx, values_only=False):
            cell = row[0]
            if isinstance(cell.value, str):
                cell.number_format = "@"


def _write_df_preserving_text_excel(df: pd.DataFrame, out_path: str) -> None:
    """Ghi DataFrame ra file Excel (atomic qua file tạm) và định dạng Text (@) cho cột MA_LK để bảo toàn số 0 ở cuối."""
    tmp_path = f"{out_path}.{os.getpid()}.tmp.xlsx"
    try:
        try:
            with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
                apply_text_format_to_ma_lk_columns(writer.sheets["Sheet1"], fallback_first_col=True)
        except Exception:
            df.to_excel(tmp_path, index=False)
        os.replace(tmp_path, out_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def load_listbh(
    file_source: Union[str, BytesIO, bytes, pd.DataFrame],
    key_col: str = "Mã liên kết",
    date_col: str = "Ngày ra",
    trusted_keys: Optional[Set[str]] = None
) -> pd.DataFrame:
    """
    Đọc file listbh.xlsx từ file path, luồng byte hoặc DataFrame đã nạp, chuẩn hoá cột và bảo toàn MA_LK
    """
    if isinstance(file_source, pd.DataFrame):
        df = file_source.copy()
    else:
        df = read_excel_preserving_ma_lk(file_source)
    found_key, found_date = _find_listbh_columns(df, key_col=key_col, date_col=date_col)
    if not found_key:
        raise ValueError(f"Tệp danh sách BHYT thiếu cột khóa chính 'Mã liên kết' / 'MA_LK'. Các cột hiện có: {list(df.columns)}")

    df[found_key] = df[found_key].map(chuan_hoa_ma_lk)
    if trusted_keys:
        num_map = build_trusted_numeric_ma_lk_map(trusted_keys)
        df[found_key] = df[found_key].map(lambda x: resolve_ma_lk_against_trusted_set(x, trusted_keys, num_map))

    if found_date:
        df["_ngay"] = parse_datetime_to_date(df[found_date])
    else:
        df["_ngay"] = pd.NaT

    out = df[[found_key, "_ngay"]].copy()
    out = out.rename(columns={found_key: "MA_LK"})
    out["MA_LK"] = out["MA_LK"].astype(str).str.strip()
    out = out[out["MA_LK"].str.len() > 0]
    out = out.drop_duplicates(subset=["MA_LK"], keep="last").reset_index(drop=True)
    return out

def load_hosoloichitiet(
    file_source: Union[str, BytesIO],
    trusted_keys: Optional[Set[str]] = None
) -> pd.DataFrame:
    """
    Đọc file lỗi HoSoLoiChiTiet.xlsx từ file path hoặc luồng byte, kiểm tra trực tiếp openpyxl
    """
    df = read_excel_preserving_ma_lk(file_source)
    found_key = None
    for c in ["MA_LK", "Mã liên kết", "MÃ LIÊN KẾT", "MÃ_LK", "Ma_LK"]:
        if c in df.columns:
            found_key = c
            break
    if not found_key:
        col_map = {str(c).lower(): c for c in df.columns}
        for c in ["ma_lk", "mã liên kết", "mã_lk"]:
            if c in col_map:
                found_key = col_map[c]
                break
    if not found_key:
        raise ValueError(f"Tệp lỗi HoSoLoiChiTiet.xlsx phải chứa cột bắt buộc 'MA_LK'. Các cột hiện có: {list(df.columns)}")

    if found_key != "MA_LK":
        df = df.rename(columns={found_key: "MA_LK"})

    found_loi = None
    for c in ["MALOI", "Mã lỗi", "MÃ LỖI", "MaLoi"]:
        if c in df.columns:
            found_loi = c
            break
    if found_loi and found_loi != "MALOI":
        df = df.rename(columns={found_loi: "MALOI"})
    elif "MALOI" not in df.columns:
        df["MALOI"] = ""

    found_mota = None
    for c in ["MOTALOI", "Mô tả lỗi", "MÔ TẢ LỖI", "MoTaLoi", "Nội dung lỗi"]:
        if c in df.columns:
            found_mota = c
            break
    if found_mota and found_mota != "MOTALOI":
        df = df.rename(columns={found_mota: "MOTALOI"})
    elif "MOTALOI" not in df.columns:
        df["MOTALOI"] = ""

    df["MALOI"] = df["MALOI"].fillna("")
    df["MOTALOI"] = df["MOTALOI"].fillna("")
    df["MA_LK"] = df["MA_LK"].apply(chuan_hoa_ma_lk)
    if trusted_keys:
        num_map = build_trusted_numeric_ma_lk_map(trusted_keys)
        df["MA_LK"] = df["MA_LK"].apply(lambda x: resolve_ma_lk_against_trusted_set(x, trusted_keys, num_map))

    found_date = None
    for c in ["Ngày ra", "NGÀY RA", "NgayRa", "NGAY_RA", "Ngày ra viện"]:
        if c in df.columns:
            found_date = c
            break
    if found_date:
        df["Ngày ra"] = parse_datetime_to_date(df[found_date])

    out_cols = ["MA_LK", "MALOI", "MOTALOI"]
    if "Ngày ra" in df.columns:
        out_cols.append("Ngày ra")

    return df[out_cols].copy()

def filter_listbh_by_date(df: pd.DataFrame, tu_ngay, den_ngay) -> pd.DataFrame:
    """
    Lọc danh sách đã gửi BHYT trong khoảng ngày được chọn
    """
    if df.empty:
        return df
    if "_ngay" not in df.columns:
        return df
    # Đảm bảo tu_ngay và den_ngay là đối tượng date
    mask = (df["_ngay"] >= tu_ngay) & (df["_ngay"] <= den_ngay)
    return df.loc[mask].copy()


def cleanup_legacy_monthly_listbh(upload_dir: str = "uploaded_files") -> None:
    """Dọn dẹp các tệp listbh_YYYY_MM.xlsx tách tháng cũ để tránh sai lệch cấu trúc hoặc nhân số dòng."""
    if not upload_dir or not os.path.exists(upload_dir):
        return
    for old_path in glob.glob(os.path.join(upload_dir, "listbh_[0-9][0-9][0-9][0-9]_[0-9][0-9].xlsx")):
        try:
            os.remove(old_path)
        except Exception:
            pass


def archive_listbh_by_months(
    file_source: Union[str, BytesIO, bytes],
    upload_dir: str = "uploaded_files",
    explicit_month: Optional[int] = None,
    explicit_year: Optional[int] = None,
    preloaded_df: Optional[pd.DataFrame] = None
) -> List[str]:
    """
    Giữ nguyên bản 100% file listbh.xlsx gốc (không cắt cột, không ghép nhân bản giữa các tháng)
    và dọn dẹp các tệp listbh_YYYY_MM.xlsx cũ nếu có.
    """
    os.makedirs(upload_dir, exist_ok=True)
    cleanup_legacy_monthly_listbh(upload_dir)
    master_path = os.path.join(upload_dir, "listbh.xlsx")
    return [master_path] if os.path.exists(master_path) else []


def load_combined_listbh_for_range(
    upload_dir: str = "uploaded_files",
    tu_date: Optional[datetime.date] = None,
    den_date: Optional[datetime.date] = None,
    trusted_keys: Optional[Set[str]] = None
) -> pd.DataFrame:
    """
    Nạp danh sách BHYT đã gửi trực tiếp từ tệp listbh.xlsx gốc (giữ nguyên cấu trúc và tự khử trùng MA_LK trong RAM).
    """
    cleanup_legacy_monthly_listbh(upload_dir)
    master_path = os.path.join(upload_dir, "listbh.xlsx")
    if not os.path.exists(master_path):
        return pd.DataFrame(columns=["MA_LK", "_ngay"])

    try:
        df = load_listbh(master_path, trusted_keys=trusted_keys)
    except Exception:
        return pd.DataFrame(columns=["MA_LK", "_ngay"])

    if df.empty:
        return pd.DataFrame(columns=["MA_LK", "_ngay"])

    out = df.copy()
    out["MA_LK"] = out["MA_LK"].apply(lambda x: chuan_hoa_ma_lk(x).upper())
    out = out[out["MA_LK"].str.len() > 0]
    out = out.drop_duplicates(subset=["MA_LK"], keep="last").reset_index(drop=True)
    return out
