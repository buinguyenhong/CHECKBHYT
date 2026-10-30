import re
from typing import List, Dict, Any, Optional
from ..rule_models import RuleResult, RuleStatus, RuleViolation, CaseXmlData

def check_rules_4750_ctn(case: CaseXmlData) -> List[RuleResult]:
    """
    Tích hợp các quy tắc kiểm tra cấu trúc, trường bắt buộc và ràng buộc CTN
    trích xuất từ tệp 'QD4750_Check_Validate CTN QĐ_4750.xlsx'.
    """
    results: List[RuleResult] = []
    xml1 = case.xml1
    if not xml1:
        return results

    # =========================================================================
    # 1. CTN_MANDATORY_XML1: Kiểm tra các trường bắt buộc trong Bảng 1 (XML1)
    # =========================================================================
    mandatory_fields_xml1 = [
        ("MA_LK", "Mã liên kết hồ sơ"),
        ("MA_CSKCB", "Mã cơ sở khám chữa bệnh"),
        ("MA_BN", "Mã người bệnh"),
        ("HO_TEN", "Họ và tên người bệnh"),
        ("NGAY_SINH", "Ngày sinh người bệnh"),
        ("GIOI_TINH", "Giới tính người bệnh"),
        ("DIA_CHI", "Địa chỉ cư trú"),
        ("NGAY_VAO", "Thời điểm vào viện"),
        ("NGAY_RA", "Thời điểm ra viện"),
        ("MA_LOAI_KCB", "Mã loại hình KCB"),
        ("MA_BENH_CHINH", "Mã chẩn đoán bệnh chính"),
        ("KET_QUA_DTRI", "Kết quả điều trị"),
        ("TINH_TRANG_RV", "Tình trạng ra viện")
    ]
    missing_xml1_violations = []
    for f_code, f_label in mandatory_fields_xml1:
        raw_val = xml1.get(f_code, "")
        if (not raw_val or str(raw_val).strip() == "") and f_code == "TINH_TRANG_RV":
            raw_val = xml1.get("MA_LOAI_RV", "")
        val = str(raw_val if raw_val is not None else "").strip()
        if not val or val.lower() in ["none", "nan", "null"]:
            missing_xml1_violations.append(RuleViolation(
                standard="4750_CTN",
                rule_code=f"CTN_REQ_XML1_{f_code}",
                rule_name=f"Trường bắt buộc XML1.{f_code} không được để trống",
                xml_table="XML1",
                field_name=f_code,
                actual_value="",
                expected_condition="Bắt buộc có dữ liệu",
                message=f"Bảng 1 (XML1): Trường '{f_code}' ({f_label}) bắt buộc nhập nhưng đang để trống."
            ))

    results.append(RuleResult(
        rule_code="CTN_REQ_XML1",
        standard="4750",
        rule_name="Kiểm tra trường bắt buộc Bảng 1 (XML1)",
        status=RuleStatus.VIOLATED if missing_xml1_violations else RuleStatus.PASSED,
        violations=missing_xml1_violations
    ))

    # =========================================================================
    # 2. CTN_MANDATORY_XML2: Kiểm tra các trường bắt buộc Bảng 2 (Thuốc)
    # =========================================================================
    missing_xml2_violations = []
    req_xml2_fields = ["MA_THUOC", "TEN_THUOC", "HAM_LUONG", "DON_VI_TINH", "SO_LUONG", "DON_GIA", "TYLE_TT", "THANH_TIEN", "MA_KHOA"]
    for idx, row in enumerate(case.xml2 or []):
        for f_code in req_xml2_fields:
            raw_v = row.get(f_code, "")
            if (not raw_v or str(raw_v).strip() == "") and f_code == "TYLE_TT":
                raw_v = row.get("TYLE_TT_BH", row.get("TYLE", ""))
            if (not raw_v or str(raw_v).strip() == "") and f_code == "THANH_TIEN":
                raw_v = row.get("THANH_TIEN_BV", "")
            val = str(raw_v if raw_v is not None else "").strip()
            if not val or val.lower() in ["none", "nan", "null"]:
                missing_xml2_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code=f"CTN_REQ_XML2_{f_code}",
                    rule_name=f"Trường bắt buộc XML2.{f_code} không được rỗng",
                    xml_table="XML2",
                    field_name=f_code,
                    actual_value="",
                    expected_condition="Bắt buộc có dữ liệu",
                    message=f"Dòng thuốc #{idx+1} ({row.get('MA_THUOC', '')}): Trường '{f_code}' để trống."
                ))
    results.append(RuleResult(
        rule_code="CTN_REQ_XML2",
        standard="4750",
        rule_name="Kiểm tra trường bắt buộc Bảng 2 (Thuốc)",
        status=RuleStatus.VIOLATED if missing_xml2_violations else RuleStatus.PASSED,
        violations=missing_xml2_violations[:10]  # Giới hạn tối đa 10 lỗi mẫu nếu danh sách quá dài
    ))

    # =========================================================================
    # 3. CTN_MANDATORY_XML3: Kiểm tra các trường bắt buộc Bảng 3 (DVKT, VTYT)
    # =========================================================================
    missing_xml3_violations = []
    req_xml3_fields = ["MA_DICH_VU", "TEN_DICH_VU", "SO_LUONG", "DON_GIA", "TYLE_TT", "THANH_TIEN", "MA_KHOA"]
    for idx, row in enumerate(case.xml3 or []):
        for f_code in req_xml3_fields:
            raw_v = row.get(f_code, "")
            if (not raw_v or str(raw_v).strip() == "") and f_code == "MA_DICH_VU":
                raw_v = row.get("MA_VAT_TU", "")
            if (not raw_v or str(raw_v).strip() == "") and f_code == "TEN_DICH_VU":
                raw_v = row.get("TEN_VAT_TU", "")
            if (not raw_v or str(raw_v).strip() == "") and f_code == "DON_GIA":
                raw_v = row.get("DON_GIA_BV", row.get("DON_GIA_BH", ""))
            if (not raw_v or str(raw_v).strip() == "") and f_code == "TYLE_TT":
                raw_v = row.get("TYLE_TT_DV", row.get("TYLE_TT_BH", row.get("TYLE", "")))
            if (not raw_v or str(raw_v).strip() == "") and f_code == "THANH_TIEN":
                raw_v = row.get("THANH_TIEN_BV", "")
            val = str(raw_v if raw_v is not None else "").strip()
            if not val or val.lower() in ["none", "nan", "null"]:
                missing_xml3_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code=f"CTN_REQ_XML3_{f_code}",
                    rule_name=f"Trường bắt buộc XML3.{f_code} không được rỗng",
                    xml_table="XML3",
                    field_name=f_code,
                    actual_value="",
                    expected_condition="Bắt buộc có dữ liệu",
                    message=f"Dòng DVKT #{idx+1} ({row.get('MA_DICH_VU', '')}): Trường '{f_code}' để trống."
                ))
    results.append(RuleResult(
        rule_code="CTN_REQ_XML3",
        standard="4750",
        rule_name="Kiểm tra trường bắt buộc Bảng 3 (DVKT, VTYT)",
        status=RuleStatus.VIOLATED if missing_xml3_violations else RuleStatus.PASSED,
        violations=missing_xml3_violations[:10]
    ))

    # =========================================================================
    # 4. CTN_CCCD_FORMAT: Định dạng số căn cước công dân / CMND
    # Ràng buộc: Định dạng 9 hoặc 12 ký tự số, hoặc 8 ký tự bắt đầu bằng chữ hoa + 7 số
    # =========================================================================
    so_cccd = str(xml1.get("SO_CCCD", "")).strip()
    cccd_violations = []
    if so_cccd and so_cccd.lower() not in ["none", "nan", "null"]:
        pattern_cccd = r"^(\d{9}|\d{12}|[A-Z]\d{7})$"
        if not re.match(pattern_cccd, so_cccd):
            cccd_violations.append(RuleViolation(
                standard="4750_CTN",
                rule_code="CTN_CCCD_FORMAT",
                rule_name="Định dạng số CCCD/CMND không hợp lệ",
                xml_table="XML1",
                field_name="SO_CCCD",
                actual_value=so_cccd,
                expected_condition="9 hoặc 12 số, hoặc 8 ký tự (1 chữ hoa + 7 số)",
                message=f"Số CCCD/CMND '{so_cccd}' sai định dạng chuẩn."
            ))
    results.append(RuleResult(
        rule_code="CTN_CCCD_FORMAT",
        standard="4750",
        rule_name="Định dạng số CCCD/CMND",
        status=RuleStatus.VIOLATED if cccd_violations else RuleStatus.PASSED,
        violations=cccd_violations
    ))

    # =========================================================================
    # 5. CTN_CROSS_CONSISTENCY: Tính nhất quán nhân thân giữa XML1 và các bảng phụ
    # Quy định: HO_TEN, NGAY_SINH, GIOI_TINH ở XML6, XML7, XML8, XML9, XML13, XML14, XML15
    # nếu có dữ liệu thì phải giống thông tin này ở Bảng 1.
    # =========================================================================
    ho_ten_xml1 = str(xml1.get("HO_TEN", "")).strip().upper()
    ngay_sinh_xml1 = str(xml1.get("NGAY_SINH", "")).strip()
    gioi_tinh_xml1 = str(xml1.get("GIOI_TINH", "")).strip()

    cross_violations = []
    sub_tables = [
        ("XML6", case.get_table("XML6")),
        ("XML7", case.xml7),
        ("XML8", case.xml8),
        ("XML9", case.xml9),
        ("XML13", case.xml13),
        ("XML14", case.get_table("XML14")),
        ("XML15", case.get_table("XML15"))
    ]

    for tbl_name, rows in sub_tables:
        if not rows: continue
        for r_idx, r in enumerate(rows):
            # So sánh HO_TEN
            sub_ho_ten = str(r.get("HO_TEN", "")).strip().upper()
            if sub_ho_ten and ho_ten_xml1 and sub_ho_ten != ho_ten_xml1:
                cross_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code=f"CTN_CONSISTENCY_{tbl_name}_HO_TEN",
                    rule_name=f"Họ tên ở {tbl_name} không khớp XML1",
                    xml_table=tbl_name,
                    field_name="HO_TEN",
                    actual_value=sub_ho_ten,
                    expected_condition=ho_ten_xml1,
                    message=f"Bảng {tbl_name} có HO_TEN ('{sub_ho_ten}') không trùng khớp với XML1 ('{ho_ten_xml1}')."
                ))
            # So sánh NGAY_SINH
            sub_ns = str(r.get("NGAY_SINH", "")).strip()
            if sub_ns and ngay_sinh_xml1 and sub_ns != ngay_sinh_xml1:
                cross_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code=f"CTN_CONSISTENCY_{tbl_name}_NGAY_SINH",
                    rule_name=f"Ngày sinh ở {tbl_name} không khớp XML1",
                    xml_table=tbl_name,
                    field_name="NGAY_SINH",
                    actual_value=sub_ns,
                    expected_condition=ngay_sinh_xml1,
                    message=f"Bảng {tbl_name} có NGAY_SINH ('{sub_ns}') không khớp với XML1 ('{ngay_sinh_xml1}')."
                ))
            # So sánh GIOI_TINH
            sub_gt = str(r.get("GIOI_TINH", "")).strip()
            if sub_gt and gioi_tinh_xml1 and sub_gt != gioi_tinh_xml1:
                cross_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code=f"CTN_CONSISTENCY_{tbl_name}_GIOI_TINH",
                    rule_name=f"Giới tính ở {tbl_name} không khớp XML1",
                    xml_table=tbl_name,
                    field_name="GIOI_TINH",
                    actual_value=sub_gt,
                    expected_condition=gioi_tinh_xml1,
                    message=f"Bảng {tbl_name} có GIOI_TINH ('{sub_gt}') không khớp với XML1 ('{gioi_tinh_xml1}')."
                ))

    results.append(RuleResult(
        rule_code="CTN_CROSS_CONSISTENCY",
        standard="4750",
        rule_name="Tính nhất quán nhân thân giữa XML1 và các bảng phụ",
        status=RuleStatus.VIOLATED if cross_violations else RuleStatus.PASSED,
        violations=cross_violations
    ))

    # =========================================================================
    # =========================================================================
    # 6. CTN_XML8_APPLICABILITY: Điều kiện áp dụng Bảng 8 (Tóm tắt HSBA)
    # Quy định: Bảng 8 chỉ có khi MA_LOAI_KCB ở XML1 in ('03', '04', '06')
    # Nếu MA_LOAI_KCB là khám bệnh ngoại trú (01/1) mà lại gửi kèm Bảng 8 -> Vi phạm
    # =========================================================================
    if case.is_table_error("XML8"):
        results.append(RuleResult(
            rule_code="CTN_XML8_APPLICABILITY",
            standard="4750",
            rule_name="Điều kiện áp dụng Bảng 8 (Tóm tắt HSBA)",
            status=RuleStatus.INCOMPLETE_DATA,
            reason="Bảng XML8_CV130 gặp sự cố truy vấn từ CSDL SQL Server, chưa đủ dữ liệu đánh giá."
        ))
    else:
        ma_loai_kcb = str(xml1.get("MA_LOAI_KCB", "")).strip()
        r_xml8_violations = []
        if case.xml8 and len(case.xml8) > 0:
            if ma_loai_kcb not in ["03", "3", "04", "4", "06", "6"]:
                r_xml8_violations.append(RuleViolation(
                    standard="4750_CTN",
                    rule_code="CTN_XML8_APPLICABILITY",
                    rule_name="Bảng 8 (Tóm tắt HSBA) chỉ áp dụng cho nội trú/ban ngày",
                    xml_table="XML8",
                    field_name="MA_LOAI_KCB",
                    actual_value=ma_loai_kcb,
                    expected_condition="MA_LOAI_KCB thuộc ('03', '04', '06')",
                    message=f"Hồ sơ có Bảng 8 (Tóm tắt HSBA) nhưng loại KCB là '{ma_loai_kcb}' (chỉ áp dụng cho điều trị nội trú/ngoại trú ban ngày)."
                ))
        results.append(RuleResult(
            rule_code="CTN_XML8_APPLICABILITY",
            standard="4750",
            rule_name="Điều kiện áp dụng Bảng 8 (Tóm tắt HSBA)",
            status=RuleStatus.VIOLATED if r_xml8_violations else RuleStatus.PASSED,
            violations=r_xml8_violations
        ))

    # =========================================================================
    # 7. CTN_XML14_APPOINTMENT_DATE: Ngày hẹn khám lại ở Bảng 14 > Ngày ra viện
    # =========================================================================
    if case.is_table_error("XML14"):
        results.append(RuleResult(
            rule_code="CTN_XML14_APPOINTMENT_DATE",
            standard="4750",
            rule_name="Ràng buộc thời điểm hẹn khám lại (Bảng 14)",
            status=RuleStatus.INCOMPLETE_DATA,
            reason="Bảng XML14_CV130 gặp sự cố truy vấn từ CSDL SQL Server, chưa đủ dữ liệu đánh giá."
        ))
    else:
        xml14_table = case.get_table("XML14")
        r_xml14_violations = []
        ngay_ra_str = str(xml1.get("NGAY_RA", "")).strip()
        if xml14_table:
            for idx, r in enumerate(xml14_table):
                ngay_hen = str(r.get("NGAY_HEN_KL", "")).strip()
                if ngay_hen and ngay_ra_str and len(ngay_hen) >= 8 and len(ngay_ra_str) >= 8:
                    if ngay_hen[:8] <= ngay_ra_str[:8]:
                        r_xml14_violations.append(RuleViolation(
                            standard="4750_CTN",
                            rule_code="CTN_XML14_APPOINTMENT_DATE",
                            rule_name="Ngày hẹn khám lại phải lớn hơn ngày ra viện",
                            xml_table="XML14",
                            field_name="NGAY_HEN_KL",
                            actual_value=f"HEN={ngay_hen}, RA={ngay_ra_str}",
                            expected_condition="NGAY_HEN_KL > NGAY_RA",
                            message=f"Bảng 14: Ngày hẹn khám lại '{ngay_hen}' nhỏ hơn hoặc bằng ngày ra viện '{ngay_ra_str}'."
                        ))
        results.append(RuleResult(
            rule_code="CTN_XML14_APPOINTMENT_DATE",
            standard="4750",
            rule_name="Ràng buộc thời điểm hẹn khám lại (Bảng 14)",
            status=RuleStatus.VIOLATED if r_xml14_violations else RuleStatus.PASSED,
            violations=r_xml14_violations
        ))

    return results
