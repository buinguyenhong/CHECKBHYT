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
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app", "app_state.db"))

print(f"Scanning folder: {folder_path}")

files = glob.glob(os.path.join(folder_path, "**", "*.xlsx"), recursive=True) + \
        glob.glob(os.path.join(folder_path, "**", "*.xls"), recursive=True) + \
        glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)

print(f"Found {len(files)} files in folder.")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT id, error_code, keyword, root_cause, resolution, requires_his_reset FROM error_definitions")
existing_defs = cur.fetchall()

existing_pairs = set()
for r_id, ec, kw, rc, res, r_his in existing_defs:
    # Normalize
    n_ec = str(ec or "").strip().upper().replace(" (", "").replace(")", "").split()[0]
    n_kw = str(kw or "").strip().upper()
    existing_pairs.add((n_ec, n_kw))
    existing_pairs.add((str(ec or "").strip().upper(), n_kw))

print(f"Existing error_definitions count in DB: {len(existing_defs)}")

def clean_error_desc(text: str) -> str:
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def extract_field_tag(maloi: str, motaloi: str) -> str:
    """
    Trích xuất từ khóa thẻ dữ liệu chính xác từ mô tả lỗi.
    Ví dụ:
      'Chi tiết thứ 87: MA_BS_DOC_KQ không được để trống' -> 'MA_BS_DOC_KQ'
      'STT198 KET_LUAN không được để trống khi XML3.MA_NHOM = 2.' -> 'KET_LUAN'
      'NGOAITRU_TUNGAY không được lớn hơn NGAY_RA' -> 'NGOAITRU_TUNGAY'
    """
    clean_desc = clean_error_desc(motaloi)
    
    # 1. Bỏ phần tiền tố như "Chi tiết thứ 123:", "STT123:", "Dòng 45:", v.v.
    clean_desc = re.sub(r'^(?:Chi tiết thứ|STT|Dòng|Bản ghi)\s*\d+[\s\:\.\-]+', '', clean_desc, flags=re.IGNORECASE).strip()
    
    # 2. Tìm các thẻ XML chuẩn dạng [A-Z0-9_]{3,}
    tags = re.findall(r'\b([A-Z][A-Z0-9_]{2,})\b', clean_desc)
    
    # Danh sách các từ cần loại trừ không phải là tên trường dữ liệu
    EXCLUDE = {
        "BHYT", "BHXH", "KCB", "CSKCB", "XML", "HTML", "HTTP", "HTTPS", "JSON", 
        "STT", "CCCD", "CMND", "VND", "BYT", "QD", "QCVN", "TT", "BV", "HIS",
        "KHONG", "DUOC", "TRONG", "TRUNG", "CHUAN", "NGAY", "THANG", "NAM"
    }
    
    valid_tags = [t for t in tags if t not in EXCLUDE and not t.isdigit()]
    
    if valid_tags:
        # Ưu tiên tag đầu tiên xuất hiện vì thường là trường gây lỗi
        return valid_tags[0]
        
    return maloi if maloi else "CHUNG"

extracted_errors = []

for f in files:
    try:
        if f.endswith('.csv'):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
            
        if df.empty: continue
            
        col_map = {}
        for c in df.columns:
            c_str = str(c).strip().upper()
            if "MA_LK" in c_str or "MÃ LIÊN KẾT" in c_str or "MÃ LK" in c_str:
                col_map[c] = "MA_LK"
            elif "MALOI" in c_str or "MÃ LỖI" in c_str:
                col_map[c] = "MALOI"
            elif "MOTALOI" in c_str or "MÔ TẢ" in c_str or "NỘI DUNG LỖI" in c_str or "CHI TIẾT LỖI" in c_str:
                col_map[c] = "MOTALOI"
                
        df = df.rename(columns=col_map)
        
        if "MALOI" not in df.columns and "MOTALOI" not in df.columns:
            continue
            
        for _, row in df.iterrows():
            maloi = str(row.get("MALOI", "") if not pd.isna(row.get("MALOI")) else "").strip()
            motaloi = str(row.get("MOTALOI", "") if not pd.isna(row.get("MOTALOI")) else "").strip()
            
            if not maloi and not motaloi:
                continue
                
            # Chuẩn hóa mã lỗi
            if not maloi:
                m_xml = re.search(r'XML\s*([0-9]+)', motaloi, re.IGNORECASE) or re.search(r'Bảng\s*([0-9]+)', motaloi, re.IGNORECASE)
                if m_xml:
                    maloi = f"XML{m_xml.group(1)}"
                else:
                    maloi = "XML"
            else:
                # Nếu mã lỗi dạng "XML 3 (Dịch vụ kỹ thuật)" -> rút gọn thành XML3
                m_code = re.search(r'XML\s*([0-9]+)', maloi, re.IGNORECASE)
                if m_code:
                    maloi = f"XML{m_code.group(1)}"
                    
            kw = extract_field_tag(maloi, motaloi)

            extracted_errors.append({
                "file": os.path.basename(f),
                "maloi": maloi.upper(),
                "motaloi": motaloi,
                "keyword": kw.upper()
            })
    except Exception as e:
        print(f"Error reading {f}: {e}")

print(f"\nTotal error rows extracted: {len(extracted_errors)}")

# Group unique (maloi, keyword)
unique_map = {}
for e in extracted_errors:
    key = (e["maloi"], e["keyword"])
    if key not in unique_map:
        unique_map[key] = {
            "maloi": e["maloi"],
            "keyword": e["keyword"],
            "sample_motaloi": e["motaloi"],
            "count": 0
        }
    unique_map[key]["count"] += 1
    if len(e["motaloi"]) > len(unique_map[key]["sample_motaloi"]):
        unique_map[key]["sample_motaloi"] = e["motaloi"]

print(f"\n--- DANH SÁCH LỖI DUY NHẤT TRÍCH XUẤT ({len(unique_map)}) ---")
new_items = []
existing_items = []

for (ec, kw), data in sorted(unique_map.items()):
    is_existing = False
    for ex_ec, ex_kw in existing_pairs:
        if (ec == ex_ec or ec in ex_ec or ex_ec in ec) and kw == ex_kw:
            is_existing = True
            break
            
    if is_existing:
        existing_items.append(data)
    else:
        new_items.append(data)

print(f"\n✅ ĐÃ CÓ TRONG HƯỚNG DẪN LỖI: {len(existing_items)} mục")
for it in existing_items:
    print(f"  [EXISTING] {it['maloi']} | {it['keyword']} (Gặp {it['count']} lần)")

print(f"\n🔥 LỖI MỚI CHƯA CÓ TRONG HƯỚNG DẪN: {len(new_items)} mục")
for it in new_items:
    print(f"  [NEW] Mã: {it['maloi']:<8} | Từ khóa: {it['keyword']:<20} | Gặp: {it['count']:<5} | Mẫu lỗi: {it['sample_motaloi'][:85]}")

conn.close()
