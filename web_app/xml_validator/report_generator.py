import os
import json
import datetime
import pandas as pd

def get_tag_value(tree, tag_name):
    if tree is None:
        return ""
    nodes = tree.xpath(f"//*[local-name()='{tag_name}']")
    if nodes and nodes[0].text:
        return nodes[0].text.strip()
    return ""

def generate_reports(grouped_data, rule_errors, invalid_files, output_dir):
    """
    Tạo tệp báo cáo Excel TongHopLoi.xlsx và tệp kết quả JSON ket_qua.json.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Thu thập thông tin bệnh nhân từ XML1
    patient_info = {}
    for ma_lk, xmls in grouped_data.items():
        ho_ten = ""
        ma_the = ""
        ten_khoa = ""
        
        if "XML1" in xmls and xmls["XML1"]:
            xml1_tree = xmls["XML1"][0]["tree"]
            ho_ten = get_tag_value(xml1_tree, "HO_TEN")
            ma_the = get_tag_value(xml1_tree, "MA_THE")
            ten_khoa = get_tag_value(xml1_tree, "TEN_KHOA")
            
        patient_info[ma_lk] = {
            "ho_ten": ho_ten,
            "ma_the": ma_the,
            "ten_khoa": ten_khoa
        }
        
    # 2. Xây dựng danh sách lỗi đầy đủ thông tin hành chính
    detailed_errors = []
    for err in rule_errors:
        info = patient_info.get(err["ma_lk"], {"ho_ten": "", "ma_the": "", "ten_khoa": ""})
        detailed_errors.append({
            "MA_LK": err["ma_lk"],
            "Họ tên": info["ho_ten"],
            "Mã thẻ BHYT": info["ma_the"],
            "Tên khoa": info["ten_khoa"],
            "Bảng XML lỗi": err["xml_type"],
            "Mã quy tắc": err["rule_id"],
            "Thẻ lỗi": err["tag_name"],
            "Nội dung lỗi chi tiết": err["message"]
        })
        
    # Thêm các tệp XML bị lỗi cú pháp nghiêm trọng (invalid_files) vào danh sách lỗi
    for inv in invalid_files:
        detailed_errors.append({
            "MA_LK": "N/A (Lỗi file)",
            "Họ tên": "N/A",
            "Mã thẻ BHYT": "N/A",
            "Tên khoa": "N/A",
            "Bảng XML lỗi": "XML_FORMAT",
            "Mã quy tắc": "C5_CRITICAL",
            "Thẻ lỗi": inv["filename"],
            "Nội dung lỗi chi tiết": f"Lỗi cú pháp XML: {inv['error']}"
        })

    # 3. Xuất file Excel TongHopLoi.xlsx
    excel_path = os.path.join(output_dir, "TongHopLoi.xlsx")
    if detailed_errors:
        df = pd.DataFrame(detailed_errors)
    else:
        df = pd.DataFrame(columns=[
            "MA_LK", "Họ tên", "Mã thẻ BHYT", "Tên khoa", 
            "Bảng XML lỗi", "Mã quy tắc", "Thẻ lỗi", "Nội dung lỗi chi tiết"
        ])
    df.to_excel(excel_path, index=False)
    
    # 4. Xuất file JSON ket_qua.json
    # Đếm số ca bệnh bị lỗi (chỉ đếm MA_LK hợp lệ)
    error_ma_lks = set(err["ma_lk"] for err in rule_errors)
    total_files_count = sum(len(files) for xmls in grouped_data.values() for files in xmls.values())
    
    summary = {
        "total_patients": len(grouped_data),
        "total_files": total_files_count,
        "error_patients": len(error_ma_lks),
        "error_count": len(detailed_errors),
        "scan_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Chuẩn hóa key JSON cho frontend
    json_errors = []
    for de in detailed_errors:
        json_errors.append({
            "ma_lk": de["MA_LK"],
            "ho_ten": de["Họ tên"],
            "ma_the": de["Mã thẻ BHYT"],
            "ten_khoa": de["Tên khoa"],
            "xml_type": de["Bảng XML lỗi"],
            "rule_id": de["Mã quy tắc"],
            "tag_name": de["Thẻ lỗi"],
            "message": de["Nội dung lỗi chi tiết"]
        })
        
    json_data = {
        "summary": summary,
        "errors": json_errors
    }
    
    json_path = os.path.join(output_dir, "ket_qua.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
        
    return excel_path, json_path
