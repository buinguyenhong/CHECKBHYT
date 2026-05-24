import pandas as pd
from io import BytesIO
from typing import Union
from services.his_service import chuan_hoa_ma_lk, parse_datetime_to_date

def load_listbh(file_source: Union[str, BytesIO], key_col: str = "Mã liên kết", date_col: str = "Ngày ra") -> pd.DataFrame:
    """
    Đọc file listbh.xlsx từ file path hoặc luồng byte, chuẩn hoá cột
    """
    df = pd.read_excel(file_source)
    if key_col not in df.columns:
        raise ValueError(f"Tệp danh sách BHYT thiếu cột khóa chính được chỉ định: '{key_col}'")
        
    df[key_col] = df[key_col].apply(chuan_hoa_ma_lk)

    if date_col not in df.columns and "Ngày ra" in df.columns:
        date_col = "Ngày ra"

    if date_col in df.columns:
        df["_ngay"] = parse_datetime_to_date(df[date_col])
    else:
        df["_ngay"] = pd.NaT

    out = df[[key_col, "_ngay"]].copy()
    out = out.rename(columns={key_col: "MA_LK"})
    return out

def load_hosoloichitiet(file_source: Union[str, BytesIO]) -> pd.DataFrame:
    """
    Đọc file lỗi HoSoLoiChiTiet.xlsx từ file path hoặc luồng byte
    """
    df = pd.read_excel(file_source)
    if "MA_LK" not in df.columns:
        raise ValueError("Tệp lỗi HoSoLoiChiTiet.xlsx phải chứa cột bắt buộc 'MA_LK'")
        
    if "MALOI" not in df.columns:
        df["MALOI"] = ""
    if "MOTALOI" not in df.columns:
        df["MOTALOI"] = ""

    df["MA_LK"] = df["MA_LK"].apply(chuan_hoa_ma_lk)

    if "Ngày ra" in df.columns:
        df["Ngày ra"] = parse_datetime_to_date(df["Ngày ra"])

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
