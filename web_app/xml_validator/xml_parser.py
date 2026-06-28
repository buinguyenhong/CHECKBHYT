import os
import re
from lxml import etree

def get_xml_type_and_ma_lk(filepath):
    """
    Đọc tệp XML, trả về loại XML (XML1->XML13) và mã liên kết MA_LK.
    Hỗ trợ bỏ qua namespace và không phân biệt chữ hoa/thường của tag.
    """
    try:
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        tree = etree.parse(filepath, parser=parser)
        root = tree.getroot()
        
        # Tìm kiếm MA_LK không phân biệt namespace
        ma_lk_nodes = root.xpath("//*[local-name()='MA_LK']")
        ma_lk = ""
        if ma_lk_nodes and ma_lk_nodes[0].text:
            ma_lk = ma_lk_nodes[0].text.strip()
            
        # Tự động nhận diện loại XML dựa trên root tag hoặc các tag con đặc trưng
        root_tag_lower = root.tag.split("}")[-1].lower()
        
        xml_type = None
        if "xml1" in root_tag_lower or root.xpath("//*[local-name()='MA_BENH_CHINH']") or root.xpath("//*[local-name()='NGAY_VAO']"):
            xml_type = "XML1"
        elif "xml2" in root_tag_lower or root.xpath("//*[local-name()='MA_THUOC']") and not root.xpath("//*[local-name()='MA_DICH_VU']"):
            xml_type = "XML2"
        elif "xml3" in root_tag_lower or root.xpath("//*[local-name()='MA_DICH_VU']") or root.xpath("//*[local-name()='MA_VAT_TU']"):
            xml_type = "XML3"
        elif "xml4" in root_tag_lower or root.xpath("//*[local-name()='MA_BS_DOC_KQ']") or root.xpath("//*[local-name()='NGAY_KQ']"):
            xml_type = "XML4"
        elif "xml5" in root_tag_lower or root.xpath("//*[local-name()='DIEN_BIEN_LS']"):
            xml_type = "XML5"
        elif "xml7" in root_tag_lower or root.xpath("//*[local-name()='NGOAITRU_TUNGAY']"):
            xml_type = "XML7"
        elif "xml8" in root_tag_lower or root.xpath("//*[local-name()='TOMTAT_KQ']"):
            xml_type = "XML8"
        elif "xml9" in root_tag_lower or root.xpath("//*[local-name()='CHI_TIEU_BANG_KE_CHI_PHI_KCB']"):
            xml_type = "XML9"
        elif "xml13" in root_tag_lower or root.xpath("//*[local-name()='CHI_TIEU_CHI_TIET_HO_SO_KHAC']"):
            xml_type = "XML13"
            
        # Fallback nhận diện theo tên file nếu không phát hiện được qua tag
        if not xml_type:
            filename = os.path.basename(filepath).upper()
            match = re.search(r'XML\s*(\d+)', filename)
            if match:
                xml_type = f"XML{match.group(1)}"
                
        return xml_type, ma_lk, tree, None
    except Exception as e:
        return None, "", None, str(e)

def group_xml_files(directory, progress_callback=None):
    """
    Quét thư mục, phân tích tất cả các file XML và nhóm theo MA_LK.
    Trả về dict: { ma_lk: { 'XML1': [info], 'XML2': [info], ... } } và danh sách file lỗi định dạng.
    """
    grouped = {}
    invalid_files = []
    
    if not os.path.exists(directory):
        return grouped, invalid_files
        
    filenames = [f for f in os.listdir(directory) if f.lower().endswith(".xml")]
    total = len(filenames)
    
    if progress_callback and total > 0:
        progress_callback(0, total, "Đang bắt đầu quét danh sách tệp tin...")
        
    for idx, filename in enumerate(filenames):
        filepath = os.path.join(directory, filename)
        xml_type, ma_lk, tree, err = get_xml_type_and_ma_lk(filepath)
        
        if err or not xml_type:
            invalid_files.append({
                "filepath": filepath,
                "filename": filename,
                "error": err or "Không thể nhận diện loại bảng XML"
            })
            continue
            
        # Nếu thiếu MA_LK, gán mã tạm để gom nhóm theo tên file
        if not ma_lk:
            ma_lk = f"UNKNOWN_{filename}"
            
        if ma_lk not in grouped:
            grouped[ma_lk] = {}
            
        info = {
            "filename": filename,
            "filepath": filepath,
            "tree": tree,
            "xml_type": xml_type
        }
        
        if xml_type not in grouped[ma_lk]:
            grouped[ma_lk][xml_type] = []
        grouped[ma_lk][xml_type].append(info)
        
        if progress_callback:
            progress_callback(idx + 1, total, f"Đang đọc tệp tin: {filename}")
            
    return grouped, invalid_files
