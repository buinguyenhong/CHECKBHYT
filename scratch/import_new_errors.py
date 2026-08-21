import os
import sys
import glob
import re
import pandas as pd
import sqlite3

# Set UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

folder_path = r"C:\Users\Admin\Downloads\XuatHoSoLoi (2)"
db_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app", "app_state.db")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app_state.db"))
]

print(f"Scanning folder: {folder_path}")

files = glob.glob(os.path.join(folder_path, "**", "*.xlsx"), recursive=True) + \
        glob.glob(os.path.join(folder_path, "**", "*.xls"), recursive=True) + \
        glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)

print(f"Found {len(files)} files.")

def clean_error_desc(text: str) -> str:
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def extract_field_tag(maloi: str, motaloi: str) -> str:
    clean_desc = clean_error_desc(motaloi)
    clean_desc = re.sub(r'^(?:Chi tiết thứ|STT|Dòng|Bản ghi)\s*\d+[\s\:\.\-]+', '', clean_desc, flags=re.IGNORECASE).strip()
    
    # Check specific patterns
    if "KET_LUAN không được để trống khi XML3.MA_NHOM = 2" in clean_desc:
        return "KET_LUAN"
    if "NGUOI_THUC_HIEN không được để trống khi mã nhóm" in clean_desc:
        return "NGUOI_THUC_HIEN"
    if "THANH_TIEN_BH" in clean_desc and "công thức" in clean_desc:
        return "THANH_TIEN_BH"
    if "MA_THE_TAM" in clean_desc:
        return "MA_THE_TAM"
    if "SO_CCCD_NND" in clean_desc:
        return "SO_CCCD_NND"
    if "SO_CCCD" in clean_desc:
        return "SO_CCCD"
    if "NGOAITRU_TUNGAY" in clean_desc:
        return "NGOAITRU_TUNGAY"
    if "THOI_DIEM_DBLS" in clean_desc:
        return "THOI_DIEM_DBLS"
    if "MA_BS_DOC_KQ" in clean_desc:
        return "MA_BS_DOC_KQ"
    if "QT_BENHLY" in clean_desc:
        return "QT_BENHLY"
    if "MA_BENH_CHINH" in clean_desc:
        return "MA_BENH_CHINH"
    if "MA_BENH_KT" in clean_desc:
        return "MA_BENH_KT"
    if "GT_THE_DEN" in clean_desc:
        return "GT_THE_DEN"
    if "GT_THE_TU" in clean_desc:
        return "GT_THE_TU"
    if "MA_DKBD" in clean_desc:
        return "MA_DKBD"
    if "SO_NGAY_DTRI" in clean_desc:
        return "SO_NGAY_DTRI"
    if "NGAY_SINH_CON" in clean_desc:
        return "NGAY_SINH_CON"
    if "MATINH_CU_TRU" in clean_desc:
        return "MATINH_CU_TRU"
    if "MA_GIUONG" in clean_desc:
        return "MA_GIUONG"
    if "TEN_DICH_VU" in clean_desc:
        return "TEN_DICH_VU"
    if "MA_NOI_DEN" in clean_desc:
        return "MA_NOI_DEN"
    if "NGAY_TTOAN" in clean_desc:
        return "NGAY_TTOAN"
    if "CAN_NANG" in clean_desc:
        return "CAN_NANG"
    if "GIOI_TINH" in clean_desc:
        return "GIOI_TINH"
    if "CHAN_DOAN_VAO" in clean_desc:
        return "CHAN_DOAN_VAO"
    if "CHAN_DOAN_RV" in clean_desc:
        return "CHAN_DOAN_RV"
    if "PP_DIEUTRI" in clean_desc:
        return "PP_DIEUTRI"
    if "TOMTAT_KQ" in clean_desc:
        return "TOMTAT_KQ"
    if "DIEN_BIEN_LS" in clean_desc:
        return "DIEN_BIEN_LS"
    if "MA_TTDV" in clean_desc:
        return "MA_TTDV"
    if "MA_BAC_SI" in clean_desc:
        return "MA_BAC_SI"
    if "MA_THUOC" in clean_desc:
        return "MA_THUOC"
    if "MA_VAT_TU" in clean_desc:
        return "MA_VAT_TU"
    if "NGAY_TH_YL" in clean_desc:
        return "NGAY_TH_YL"
    if "NGAY_YL" in clean_desc:
        return "NGAY_YL"
    if "NGAY_KQ" in clean_desc:
        return "NGAY_KQ"
    if "NGAY_RA" in clean_desc:
        return "NGAY_RA"
    if "NGAY_VAO" in clean_desc:
        return "NGAY_VAO"
    if "NGAY_CT" in clean_desc:
        return "NGAY_CT"
    if "NAM_QT" in clean_desc:
        return "NAM_QT"
    if "THANG_QT" in clean_desc:
        return "THANG_QT"
    if "T_BNTT" in clean_desc:
        return "T_BNTT"
    if "T_BNCCT" in clean_desc:
        return "T_BNCCT"
    if "LAN_SINH" in clean_desc:
        return "LAN_SINH"
    if "HO_TEN" in clean_desc:
        return "HO_TEN"
    if "MA_NHOM" in clean_desc:
        return "MA_NHOM"
    if "MA_LK" in clean_desc:
        return "MA_LK"

    tags = re.findall(r'\b([A-Z][A-Z0-9_]{2,})\b', clean_desc)
    EXCLUDE = {
        "BHYT", "BHXH", "KCB", "CSKCB", "XML", "HTML", "HTTP", "HTTPS", "JSON", 
        "STT", "CCCD", "CMND", "VND", "BYT", "QD", "QCVN", "TT", "BV", "HIS",
        "KHONG", "DUOC", "TRONG", "TRUNG", "CHUAN", "NGAY", "THANG", "NAM", "HOSO"
    }
    valid = [t for t in tags if t not in EXCLUDE and not t.isdigit()]
    if valid: return valid[0]
    return maloi if maloi else "CHUNG"

# Collect all items
all_items = {}

for f in files:
    try:
        df = pd.read_csv(f) if f.endswith('.csv') else pd.read_excel(f)
        if df.empty: continue
        
        col_map = {}
        for c in df.columns:
            c_str = str(c).strip().upper()
            if "MA_LK" in c_str or "MÃ LIÊN KẾT" in c_str: col_map[c] = "MA_LK"
            elif "MALOI" in c_str or "MÃ LỖI" in c_str: col_map[c] = "MALOI"
            elif "MOTALOI" in c_str or "MÔ TẢ" in c_str or "NỘI DUNG LỖI" in c_str: col_map[c] = "MOTALOI"
        df = df.rename(columns=col_map)
        
        if "MALOI" not in df.columns and "MOTALOI" not in df.columns: continue
        
        for _, row in df.iterrows():
            maloi = str(row.get("MALOI", "") if not pd.isna(row.get("MALOI")) else "").strip()
            motaloi = str(row.get("MOTALOI", "") if not pd.isna(row.get("MOTALOI")) else "").strip()
            if not maloi and not motaloi: continue
            
            # Standardize MALOI
            m_code = re.search(r'XML\s*([0-9]+)', maloi + " " + motaloi, re.IGNORECASE)
            if m_code:
                code_std = f"XML{m_code.group(1)}"
            else:
                code_std = maloi.upper() if maloi else "XML1"
                
            kw = extract_field_tag(code_std, motaloi)
            if kw in ["HOSO", "XML", "CHUNG", ""] or kw.isdigit():
                continue
                
            key = (code_std, kw)
            if key not in all_items:
                all_items[key] = {
                    "error_code": code_std,
                    "keyword": kw,
                    "sample": motaloi,
                    "count": 0
                }
            all_items[key]["count"] += 1
            if len(motaloi) > len(all_items[key]["sample"]):
                all_items[key]["sample"] = motaloi
    except Exception as e:
        print(f"Error {f}: {e}")

print(f"Total distilled error types: {len(all_items)}")

# Process each DB
for db_p in db_paths:
    if not os.path.exists(db_p):
        continue
    print(f"\nUpdating Database: {db_p}")
    conn = sqlite3.connect(db_p)
    cur = conn.cursor()
    
    cur.execute("SELECT id, error_code, keyword, root_cause, resolution, requires_his_reset FROM error_definitions")
    rows = cur.fetchall()
    
    existing = set()
    for r_id, ec, kw, rc, res, r_his in rows:
        # Match normalized
        ec_n = str(ec or "").strip().upper().replace(" (", "").replace(")", "").split()[0]
        kw_n = str(kw or "").strip().upper()
        existing.add((ec_n, kw_n))
        existing.add((str(ec or "").strip().upper(), kw_n))
        
    inserted = 0
    for (ec, kw), data in sorted(all_items.items()):
        is_in = False
        for ex_ec, ex_kw in existing:
            if (ec == ex_ec or ec in ex_ec or ex_ec in ec) and kw == ex_kw:
                is_in = True
                break
                
        if not is_in:
            sample_txt = clean_error_desc(data["sample"])
            # Format friendly error_code name
            xml_names = {
                "XML0": "XML 0 (Danh mục chung)",
                "XML1": "XML 1 (Tổng hợp KBCB)",
                "XML2": "XML 2 (Chi tiết thuốc)",
                "XML3": "XML 3 (Dịch vụ kỹ thuật)",
                "XML4": "XML 4 (Cận lâm sàng)",
                "XML5": "XML 5 (Diễn biến LS)",
                "XML7": "XML 7 (Giấy ra viện)",
                "XML8": "XML 8 (Tóm tắt HSBA)",
                "XML9": "XML 9 (Bảng kê chi phí)",
                "XML11": "XML 11 (Giấy nghỉ việc BHXH)",
                "XML13": "XML 13 (Hồ sơ khác)"
            }
            code_display = xml_names.get(ec, ec)
            
            # Determine root cause summary from sample
            root_cause = sample_txt if len(sample_txt) <= 200 else sample_txt[:197] + "..."
            resolution = "Chờ phòng IT bổ sung hướng dẫn chi tiết"
            req_reset = True if ec in ["XML1", "XML2", "XML3", "XML4", "XML5", "XML7", "XML8", "XML11"] else False
            
            cur.execute("""
                INSERT INTO error_definitions (error_code, keyword, root_cause, resolution, requires_his_reset)
                VALUES (?, ?, ?, ?, ?)
            """, (code_display, kw, root_cause, resolution, 1 if req_reset else 0))
            
            existing.add((ec, kw))
            existing.add((code_display, kw))
            inserted += 1
            print(f"  + Added: {code_display:<26} | Keyword: {kw:<20} | Sample: {root_cause[:60]}")
            
    conn.commit()
    conn.close()
    print(f"Successfully added {inserted} new error definitions to {db_p}!")
