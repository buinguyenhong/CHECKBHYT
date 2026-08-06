import pandas as pd
from io import BytesIO
from typing import Union
from services.his_service import chuan_hoa_ma_lk, parse_datetime_to_date

def load_listbh(file_source: Union[str, BytesIO], key_col: str = "Mã liên kết", date_col: str = "Ngày ra") -> pd.DataFrame:
    """
    Đọc file listbh.xlsx từ file path hoặc luồng byte, chuẩn hoá cột
    """
    df = pd.read_excel(file_source)
    
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
    if not found_key:
        raise ValueError(f"Tệp danh sách BHYT thiếu cột khóa chính 'Mã liên kết' / 'MA_LK'. Các cột hiện có: {list(df.columns)}")
        
    df[found_key] = df[found_key].apply(chuan_hoa_ma_lk)

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

    if found_date:
        df["_ngay"] = parse_datetime_to_date(df[found_date])
    else:
        df["_ngay"] = pd.NaT

    out = df[[found_key, "_ngay"]].copy()
    out = out.rename(columns={found_key: "MA_LK"})
    return out

def load_hosoloichitiet(file_source: Union[str, BytesIO]) -> pd.DataFrame:
    """
    Đọc file lỗi HoSoLoiChiTiet.xlsx từ file path hoặc luồng byte
    """
    df = pd.read_excel(file_source)
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

    df["MA_LK"] = df["MA_LK"].apply(chuan_hoa_ma_lk)

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
