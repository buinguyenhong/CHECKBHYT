import datetime
import re

class XMLRuleEngine:
    def __init__(self, db_session=None):
        self.db = db_session

    def get_nodes(self, tree, tag_name):
        return tree.xpath(f"//*[local-name()='{tag_name}']")

    def get_tag_value(self, tree, tag_name):
        nodes = self.get_nodes(tree, tag_name)
        if nodes and nodes[0].text:
            return nodes[0].text.strip()
        return ""

    def parse_xml_date(self, val):
        if not val:
            return None
        clean = "".join([c for c in str(val) if c.isdigit()])
        if len(clean) >= 12:
            try:
                return datetime.datetime.strptime(clean[:12], "%Y%m%d%H%M")
            except ValueError:
                pass
        if len(clean) >= 8:
            try:
                return datetime.datetime.strptime(clean[:8], "%Y%m%d")
            except ValueError:
                pass
        return None

    def check_rules(self, ma_lk, xml_files):
        """
        Thực hiện kiểm tra 26 quy tắc cho một nhóm tệp XML của cùng một bệnh nhân (MA_LK).
        Trả về danh sách các lỗi phát hiện.
        """
        errors = []
        
        # Helper để thêm lỗi nhanh
        def add_error(rule_id, xml_type, tag_name, message):
            errors.append({
                "ma_lk": ma_lk,
                "rule_id": rule_id,
                "xml_type": xml_type,
                "tag_name": tag_name,
                "message": message
            })

        # ----------------------------------------------------
        # C5: Kiểm tra tính chuẩn xác của XML1 trước
        # ----------------------------------------------------
        xml1_list = xml_files.get("XML1", [])
        if not xml1_list:
            add_error("C5", "XML1", "FILE", "Thông tin XML1 chưa chuẩn xác. Hệ thống tạm dừng check các XML liên quan.")
            return errors
            
        xml1_info = xml1_list[0]
        xml1_tree = xml1_info["tree"]
        
        ma_benh_chinh = self.get_tag_value(xml1_tree, "MA_BENH_CHINH")
        nam_qt = self.get_tag_value(xml1_tree, "NAM_QT")
        
        if not ma_benh_chinh and not nam_qt:
            add_error("C5", "XML1", "FILE", "Thông tin XML1 chưa chuẩn xác. Hệ thống tạm dừng check các XML liên quan.")
            return errors

        # ----------------------------------------------------
        # NHÓM A: Kiểm tra lỗi định dạng và Ràng buộc bắt buộc
        # ----------------------------------------------------
        # A1: XML1 - MA_BENH_CHINH không được để trống
        if not ma_benh_chinh:
            add_error("A1", "XML1", "MA_BENH_CHINH", "MA_BENH_CHINH không được để trống")
            
        # A2: XML1 - NAM_QT không được để trống
        if not nam_qt:
            add_error("A2", "XML1", "NAM_QT", "NAM_QT không được để trống")

        # A17: XML1 - LY_DO_VV check
        ly_do_vv = self.get_tag_value(xml1_tree, "LY_DO_VV")
        if ly_do_vv == "Người bệnh không KCB BHYT":
            add_error("A17", "XML1", "LY_DO_VV", " sai lý do: Người bệnh không KCB BHYT ")

        # A3: XML2 - MA_THUOC không được để trống
        xml2_list = xml_files.get("XML2", [])
        for xml2 in xml2_list:
            ma_thuoc_nodes = self.get_nodes(xml2["tree"], "MA_THUOC")
            if not ma_thuoc_nodes:
                add_error("A3", "XML2", "MA_THUOC", "MA_THUOC không được để trống")
            else:
                for idx, node in enumerate(ma_thuoc_nodes):
                    if not node.text or not node.text.strip():
                        add_error("A3", "XML2", f"MA_THUOC[{idx}]", "MA_THUOC không được để trống")

        # A4: XML3 - MA_BAC_SI không được để trống
        xml3_list = xml_files.get("XML3", [])
        for xml3 in xml3_list:
            ma_bs_nodes = self.get_nodes(xml3["tree"], "MA_BAC_SI")
            if not ma_bs_nodes:
                add_error("A4", "XML3", "MA_BAC_SI", "MA_BAC_SI không được để trống")
            else:
                for idx, node in enumerate(ma_bs_nodes):
                    if not node.text or not node.text.strip():
                        add_error("A4", "XML3", f"MA_BAC_SI[{idx}]", "MA_BAC_SI không được để trống")

        # A5: XML4 - MA_BS_DOC_KQ không được để trống
        xml4_list = xml_files.get("XML4", [])
        for xml4 in xml4_list:
            ma_bs_kq = self.get_nodes(xml4["tree"], "MA_BS_DOC_KQ")
            if not ma_bs_kq:
                add_error("A5", "XML4", "MA_BS_DOC_KQ", "MA_BS_DOC_KQ không được để trống")
            else:
                for idx, node in enumerate(ma_bs_kq):
                    if not node.text or not node.text.strip():
                        add_error("A5", "XML4", f"MA_BS_DOC_KQ[{idx}]", "MA_BS_DOC_KQ không được để trống")

        # A6: XML5 - DIEN_BIEN_LS không được để trống
        xml5_list = xml_files.get("XML5", [])
        for xml5 in xml5_list:
            dien_bien = self.get_nodes(xml5["tree"], "DIEN_BIEN_LS")
            if not dien_bien:
                add_error("A6", "XML5", "DIEN_BIEN_LS", "DIEN_BIEN_LS không được để trống")
            else:
                for idx, node in enumerate(dien_bien):
                    if not node.text or not node.text.strip():
                        add_error("A6", "XML5", f"DIEN_BIEN_LS[{idx}]", "DIEN_BIEN_LS không được để trống")

        # A7: XML5 - NGUOI_THUC_HIEN không được để trống
        for xml5 in xml5_list:
            nguoi_th = self.get_nodes(xml5["tree"], "NGUOI_THUC_HIEN")
            if not nguoi_th:
                add_error("A7", "XML5", "NGUOI_THUC_HIEN", "NGUOI_THUC_HIEN không được để trống")
            else:
                for idx, node in enumerate(nguoi_th):
                    if not node.text or not node.text.strip():
                        add_error("A7", "XML5", f"NGUOI_THUC_HIEN[{idx}]", "NGUOI_THUC_HIEN không được để trống")

        # A8: XML8 - MA_TTDV không được để trống
        xml8_list = xml_files.get("XML8", [])
        for xml8 in xml8_list:
            ma_ttdv = self.get_nodes(xml8["tree"], "MA_TTDV")
            if not ma_ttdv:
                add_error("A8", "XML8", "MA_TTDV", "MA_TTDV không để trống")
            else:
                for idx, node in enumerate(ma_ttdv):
                    if not node.text or not node.text.strip():
                        add_error("A8", "XML8", f"MA_TTDV[{idx}]", "MA_TTDV không để trống")

        # A9: XML8 - TOMTAT_KQ không được để trống
        for xml8 in xml8_list:
            tomtat = self.get_nodes(xml8["tree"], "TOMTAT_KQ")
            if not tomtat:
                add_error("A9", "XML8", "TOMTAT_KQ", "TOMTAT_KQ không được để trống")
            else:
                for idx, node in enumerate(tomtat):
                    if not node.text or not node.text.strip():
                        add_error("A9", "XML8", f"TOMTAT_KQ[{idx}]", "TOMTAT_KQ không được để trống")

        # A10: XML8 - PP_DIEUTRI không được để trống
        for xml8 in xml8_list:
            pp_dt = self.get_nodes(xml8["tree"], "PP_DIEUTRI")
            if not pp_dt:
                add_error("A10", "XML8", "PP_DIEUTRI", "PP_DIEUTRI không được để trống")
            else:
                for idx, node in enumerate(pp_dt):
                    if not node.text or not node.text.strip():
                        add_error("A10", "XML8", f"PP_DIEUTRI[{idx}]", "PP_DIEUTRI không được để trống")

        # A11: XML8 - CHAN_DOAN_RV không được để trống
        for xml8 in xml8_list:
            cd_rv = self.get_nodes(xml8["tree"], "CHAN_DOAN_RV")
            if not cd_rv:
                add_error("A11", "XML8", "CHAN_DOAN_RV", "CHAN_DOAN_RV không được để trống")
            else:
                for idx, node in enumerate(cd_rv):
                    if not node.text or not node.text.strip():
                        add_error("A11", "XML8", f"CHAN_DOAN_RV[{idx}]", "CHAN_DOAN_RV không được để trống")

        # A12: XML9 - MA_TTDV không được để trống
        xml9_list = xml_files.get("XML9", [])
        for xml9 in xml9_list:
            ma_ttdv = self.get_nodes(xml9["tree"], "MA_TTDV")
            if not ma_ttdv:
                add_error("A12", "XML9", "MA_TTDV", "MA_TTDV không được để trống")
            else:
                for idx, node in enumerate(ma_ttdv):
                    if not node.text or not node.text.strip():
                        add_error("A12", "XML9", f"MA_TTDV[{idx}]", "MA_TTDV không được để trống")

        # A13: XML13 - HO_TEN không được để trống
        xml13_list = xml_files.get("XML13", [])
        for xml13 in xml13_list:
            ho_ten = self.get_nodes(xml13["tree"], "HO_TEN")
            if not ho_ten:
                add_error("A13", "XML13", "HO_TEN", "HO_TEN không được để trống")
            else:
                for idx, node in enumerate(ho_ten):
                    if not node.text or not node.text.strip():
                        add_error("A13", "XML13", f"HO_TEN[{idx}]", "HO_TEN không được để trống")

        # A14: XML0 - MA_DICH_VU không được để trống (kiểm tra XML3)
        for xml3 in xml3_list:
            records = self.get_nodes(xml3["tree"], "CHI_TIET_DVKT")
            for idx, rec in enumerate(records):
                ma_nhom_nodes = rec.xpath(".//*[local-name()='MA_NHOM']")
                ma_nhom = ma_nhom_nodes[0].text.strip() if ma_nhom_nodes and ma_nhom_nodes[0].text else ""
                
                # Nếu là vật tư y tế (nhóm 10, 11) thì không bắt buộc MA_DICH_VU
                if ma_nhom in ["10", "11"]:
                    continue
                    
                ma_dv_nodes = rec.xpath(".//*[local-name()='MA_DICH_VU']")
                if not ma_dv_nodes or not ma_dv_nodes[0].text or not ma_dv_nodes[0].text.strip():
                    add_error("A14", "XML3", f"MA_DICH_VU[{idx}]", "MA_DICH_VU không được để trống đối với dịch vụ kỹ thuật")

        # A15: XML0 - MA_VAT_TU không được để trống (kiểm tra XML3)
        for xml3 in xml3_list:
            records = self.get_nodes(xml3["tree"], "CHI_TIET_DVKT")
            for idx, rec in enumerate(records):
                ma_nhom_nodes = rec.xpath(".//*[local-name()='MA_NHOM']")
                ma_nhom = ma_nhom_nodes[0].text.strip() if ma_nhom_nodes and ma_nhom_nodes[0].text else ""
                
                # Chỉ kiểm tra khi là vật tư y tế (nhóm 10, 11)
                if ma_nhom in ["10", "11"]:
                    ma_vt_nodes = rec.xpath(".//*[local-name()='MA_VAT_TU']")
                    if not ma_vt_nodes or not ma_vt_nodes[0].text or not ma_vt_nodes[0].text.strip():
                        add_error("A15", "XML3", f"MA_VAT_TU[{idx}]", "MA_VAT_TU không được để trống đối với vật tư y tế")

        # A16: XML0 - MA_THUOC không được để trống (kiểm tra XML2)
        for xml2 in xml2_list:
            ma_thuoc = self.get_nodes(xml2["tree"], "MA_THUOC")
            for idx, node in enumerate(ma_thuoc):
                if not node.text or not node.text.strip():
                    add_error("A16", "XML2", f"MA_THUOC[{idx}]", "MA_THUOC không được để trống")


        # ----------------------------------------------------
        # NHÓM B: Kiểm tra logic thời gian và Định dạng chuỗi
        # ----------------------------------------------------
        # B1: XML4 - NGAY_KQ format YYYYMMDDHHMM và <= thời gian hiện tại
        now = datetime.datetime.now()
        for xml4 in xml4_list:
            ngay_kq_nodes = self.get_nodes(xml4["tree"], "NGAY_KQ")
            for idx, node in enumerate(ngay_kq_nodes):
                val = node.text.strip() if node.text else ""
                if not val:
                    continue
                dt = self.parse_xml_date(val)
                if not dt or len(val) < 12:
                    add_error("B1", "XML4", f"NGAY_KQ[{idx}]", "NGAY_KQ sai định dạng quy định")
                elif dt > now:
                    add_error("B1", "XML4", f"NGAY_KQ[{idx}]", "NGAY_KQ không được lớn hơn thời gian hiện tại")

        # B2: XML7 - NGOAITRU_TUNGAY <= XML1 NGAY_RA (Lược bỏ theo yêu cầu: không kiểm tra)
        # ngay_ra_str = self.get_tag_value(xml1_tree, "NGAY_RA")
        # ngay_ra_dt = self.parse_xml_date(ngay_ra_str)
        # 
        # xml7_list = xml_files.get("XML7", [])
        # for xml7 in xml7_list:
        #     tungay_nodes = self.get_nodes(xml7["tree"], "NGOAITRU_TUNGAY")
        #     for idx, node in enumerate(tungay_nodes):
        #         val = node.text.strip() if node.text else ""
        #         if not val:
        #             continue
        #         dt_tu = self.parse_xml_date(val)
        #         if dt_tu and ngay_ra_dt and dt_tu > ngay_ra_dt:
        #             add_error("B2", "XML7", f"NGOAITRU_TUNGAY[{idx}]", "NGOAITRU_TUNGAY không được lớn hơn NGAY_RA")

        # B3: XML3 - NGAY_YL >= XML1 NGAY_VAO
        ngay_vao_str = self.get_tag_value(xml1_tree, "NGAY_VAO")
        ngay_vao_dt = self.parse_xml_date(ngay_vao_str)
        
        for xml3 in xml3_list:
            ngay_yl_nodes = self.get_nodes(xml3["tree"], "NGAY_YL")
            for idx, node in enumerate(ngay_yl_nodes):
                val = node.text.strip() if node.text else ""
                if not val:
                    continue
                dt_yl = self.parse_xml_date(val)
                if dt_yl and ngay_vao_dt and dt_yl < ngay_vao_dt:
                    add_error("B3", "XML3", f"NGAY_YL[{idx}]", "ngày y lệnh trước ngày vào viện.")

        # Helper check TT_THAU
        def validate_tt_thau(val):
            # Cấu trúc: QuyetDinh;GoiThau;NhomThau;...
            # Phải có ít nhất 2 dấu chấm phẩy
            if not val or val.count(";") < 2:
                return "TT_THAU sai định dạng quy định"
            # Kiểm tra năm đấu thầu (tìm 4 chữ số liên tiếp)
            years = re.findall(r'\b(20\d{2})\b', val)
            if not years:
                return "TT_THAU sai - Sai năm đấu thầu"
            for y in years:
                y_val = int(y)
                # Năm đấu thầu hợp lý
                if y_val < 2010 or y_val > now.year + 2:
                    return "TT_THAU sai - Sai năm đấu thầu"
            return None

        # B4: XML3 - TT_THAU format
        for xml3 in xml3_list:
            tt_thau_nodes = self.get_nodes(xml3["tree"], "TT_THAU")
            for idx, node in enumerate(tt_thau_nodes):
                val = node.text.strip() if node.text else ""
                # Bắt buộc check nếu có nội dung thầu vật tư y tế
                if val:
                    err_msg = validate_tt_thau(val)
                    if err_msg:
                        add_error("B4", "XML3", f"TT_THAU[{idx}]", err_msg)

        # B5: XML2 - TT_THAU format
        for xml2 in xml2_list:
            tt_thau_nodes = self.get_nodes(xml2["tree"], "TT_THAU")
            for idx, node in enumerate(tt_thau_nodes):
                val = node.text.strip() if node.text else ""
                if val:
                    err_msg = validate_tt_thau(val)
                    if err_msg:
                        add_error("B5", "XML2", f"TT_THAU[{idx}]", err_msg)


        # ----------------------------------------------------
        # NHÓM C: Kiểm tra liên kết logic chéo
        # ----------------------------------------------------
        # C1: XML3 MA_NHOM = 2 bắt buộc phải có XML4 và KET_LUAN không rỗng
        has_ma_nhom_2 = False
        for xml3 in xml3_list:
            ma_nhom_nodes = self.get_nodes(xml3["tree"], "MA_NHOM")
            for node in ma_nhom_nodes:
                if node.text and node.text.strip() == "2":
                    has_ma_nhom_2 = True
                    break
            if has_ma_nhom_2:
                break
                
        if has_ma_nhom_2:
            if not xml4_list:
                add_error("C1", "XML4", "FILE", "KET_LUAN không được để trống khi XML3.MA_NHOM = 2.")
            else:
                has_ket_luan = False
                for xml4 in xml4_list:
                    kl_nodes = self.get_nodes(xml4["tree"], "KET_LUAN")
                    for node in kl_nodes:
                        if node.text and node.text.strip():
                            has_ket_luan = True
                            break
                    if has_ket_luan:
                        break
                if not has_ket_luan:
                    add_error("C1", "XML4", "KET_LUAN", "KET_LUAN không được để trống khi XML3.MA_NHOM = 2.")

        # C2: XML3 MA_NHOM thuộc [1, 2, 3, 8, 18] bắt buộc NGUOI_THUC_HIEN có giá trị
        for xml3 in xml3_list:
            # Lấy tất cả các chi tiết dịch vụ
            # Thường cấu trúc là danh sách các thẻ <CHI_TIET_DV> hoặc tương tự, hoặc tìm tất cả MA_NHOM trực tiếp
            # Để an toàn, duyệt song song hoặc tìm cha
            # Giả định đơn giản: duyệt tất cả các thẻ MA_NHOM trong XML3 và tìm thẻ NGUOI_THUC_HIEN kế cận
            # Cách an toàn nhất: duyệt qua từng node dịch vụ
            rows = xml3["tree"].xpath("//*[local-name()='MA_NHOM']/..")
            for idx, row in enumerate(rows):
                ma_nhom_node = row.xpath("./*[local-name()='MA_NHOM']")
                ma_nhom = ma_nhom_node[0].text.strip() if ma_nhom_node and ma_nhom_node[0].text else ""
                if ma_nhom in ["1", "2", "3", "8", "18"]:
                    nguoi_th_node = row.xpath("./*[local-name()='NGUOI_THUC_HIEN']")
                    nguoi_th = nguoi_th_node[0].text.strip() if nguoi_th_node and nguoi_th_node[0].text else ""
                    if not nguoi_th:
                        add_error("C2", "XML3", f"NGUOI_THUC_HIEN[dòng_{idx}]", "NGUOI_THUC_HIEN không được để trống khi mã nhóm bằng 1 2 3 8 18")

        # C3: Đối chiếu MA_DICH_VU/MA_THUOC trong XML2 xem có khớp/nằm trong XML3
        # Gom danh sách MA_DICH_VU và MA_VAT_TU từ XML3 làm catalog
        xml3_codes = set()
        for xml3 in xml3_list:
            dv_nodes = self.get_nodes(xml3["tree"], "MA_DICH_VU")
            vt_nodes = self.get_nodes(xml3["tree"], "MA_VAT_TU")
            for node in dv_nodes:
                if node.text:
                    xml3_codes.add(node.text.strip().upper())
            for node in vt_nodes:
                if node.text:
                    xml3_codes.add(node.text.strip().upper())
                    
        # Check XML2
        for xml2 in xml2_list:
            # Check cả MA_DICH_VU (nếu có) hoặc MA_THUOC
            ma_dv_nodes = self.get_nodes(xml2["tree"], "MA_DICH_VU")
            ma_thuoc_nodes = self.get_nodes(xml2["tree"], "MA_THUOC")
            
            for idx, node in enumerate(ma_dv_nodes):
                val = node.text.strip().upper() if node.text else ""
                if val and val not in xml3_codes:
                    add_error("C3", "XML2", f"MA_DICH_VU[{idx}]", f"MA_DICH_VU {val} không nằm trong XML3.")
            
            # Phép check dự phòng mã thuốc nếu hệ thống mapping thuốc vào dịch vụ
            # (chỉ cảnh báo/check nếu người dùng yêu cầu nghiêm ngặt hoặc mã thuốc phải khai báo trong danh mục XML3)
            # Theo chuẩn Bộ Y Tế, thuốc XML2 không nhất thiết phải trùng XML3, nên chỉ check thẻ MA_DICH_VU ở XML2 nếu có.

        # C4: XML1 MA_LOAI_KCB thuộc [3, 4, 9] bắt buộc phải có XML7 (Giấy ra viện)
        ma_loai_kcb = self.get_tag_value(xml1_tree, "MA_LOAI_KCB")
        if ma_loai_kcb in ["3", "4", "9"]:
            if not xml7_list:
                add_error("C4", "XML7", "FILE", "MA_LOAI_KCB ở XML1 = 3,4,9 thì phải có XML7 (giấy ra viện).")

        return errors
