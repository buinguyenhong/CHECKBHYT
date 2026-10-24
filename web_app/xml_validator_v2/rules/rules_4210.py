import re
from decimal import Decimal
import datetime
from typing import List, Dict, Any
from ..rule_models import RuleResult, RuleStatus, RuleViolation, CaseXmlData, to_decimal, round_money

def check_rules_4210(case: CaseXmlData) -> List[RuleResult]:
    results: List[RuleResult] = []
    xml1 = case.xml1
    xml2 = case.xml2
    xml3 = case.xml3

    if not xml1:
        return results

    # ----------------------------------------------------
    # Rule 1: Sai lý do vào viện
    # ----------------------------------------------------
    ly_do_vv = str(xml1.get("MA_LYDO_VVIEN", xml1.get("LY_DO_VV", ""))).strip()
    ma_dkbd = str(xml1.get("MA_DKBD", "")).strip().upper()
    ma_cskcb = str(xml1.get("MA_CSKCB", "")).strip().upper()

    r1_violations = []
    if ly_do_vv not in ["1", "2", "3", "4"]:
        r1_violations.append(RuleViolation(
            standard="4210", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=ly_do_vv,
            expected_condition="Thuộc danh sách (1, 2, 3, 4)",
            message=f"Mã lý do vào viện '{ly_do_vv}' không hợp lệ (phải là 1, 2, 3 hoặc 4)."
        ))
    elif ly_do_vv == "3" and ma_dkbd and ma_cskcb and ma_dkbd == ma_cskcb:
        r1_violations.append(RuleViolation(
            standard="4210", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=f"LYDO={ly_do_vv}, DKBD={ma_dkbd}, CSKCB={ma_cskcb}",
            expected_condition="Mã ĐKBĐ khác Mã CSKCB khi lý do vào viện là trái tuyến (3)",
            message="Mã lý do vào viện = 3 (trái tuyến) nhưng Mã ĐKBĐ trùng với Mã CSKCB (đúng tuyến)."
        ))
    results.append(RuleResult(rule_code="1", standard="4210", rule_name="Sai lý do vào viện",
                              status=RuleStatus.VIOLATED if r1_violations else RuleStatus.PASSED, violations=r1_violations))

    # ----------------------------------------------------
    # Rule 15: Ngày sinh không hợp lệ
    # ----------------------------------------------------
    ngay_sinh_str = str(xml1.get("NGAY_SINH", "")).strip()
    r15_violations = []
    if not ngay_sinh_str or len(ngay_sinh_str) not in [4, 8, 12]:
        r15_violations.append(RuleViolation(
            standard="4210", rule_code="15", rule_name="Ngày sinh không hợp lệ",
            xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh_str,
            expected_condition="Định dạng YYYY hoặc YYYYMMDD hoặc YYYYMMDDHHMM",
            message=f"Độ dài ngày sinh '{ngay_sinh_str}' không hợp lệ."
        ))
    else:
        try:
            nam_sinh = int(ngay_sinh_str[:4])
            cur_year = datetime.datetime.now().year
            if nam_sinh < 1900 or nam_sinh > cur_year:
                r15_violations.append(RuleViolation(
                    standard="4210", rule_code="15", rule_name="Ngày sinh không hợp lệ",
                    xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh_str,
                    expected_condition=f"1900 <= Năm sinh <= {cur_year}",
                    message=f"Năm sinh {nam_sinh} nằm ngoài giới hạn hợp lệ (1900 - {cur_year})."
                ))
        except Exception:
            r15_violations.append(RuleViolation(
                standard="4210", rule_code="15", rule_name="Ngày sinh không hợp lệ",
                xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh_str,
                expected_condition="Chuỗi ký tự số hợp lệ",
                message=f"Ngày sinh '{ngay_sinh_str}' không đúng định dạng số."
            ))
    results.append(RuleResult(rule_code="15", standard="4210", rule_name="Ngày sinh không hợp lệ",
                              status=RuleStatus.VIOLATED if r15_violations else RuleStatus.PASSED, violations=r15_violations))

    # ----------------------------------------------------
    # Rule 16: Giới tính không hợp lệ (1: Nam, 2: Nữ)
    # ----------------------------------------------------
    gioi_tinh = str(xml1.get("GIOI_TINH", "")).strip()
    r16_violations = []
    if gioi_tinh not in ["1", "2"]:
        r16_violations.append(RuleViolation(
            standard="4210", rule_code="16", rule_name="Giới tính không hợp lệ",
            xml_table="XML1", field_name="GIOI_TINH", actual_value=gioi_tinh,
            expected_condition="GIOI_TINH thuộc [1, 2] (1: Nam, 2: Nữ)",
            message=f"Mã giới tính '{gioi_tinh}' không hợp lệ (phải là 1 hoặc 2)."
        ))
    results.append(RuleResult(rule_code="16", standard="4210", rule_name="Giới tính không hợp lệ",
                              status=RuleStatus.VIOLATED if r16_violations else RuleStatus.PASSED, violations=r16_violations))

    # ----------------------------------------------------
    # Rule 17: Mã thẻ không hợp lệ (15 ký tự, 10 ký tự cuối số)
    # ----------------------------------------------------
    ma_the = str(xml1.get("MA_THE", xml1.get("SO_THE", ""))).strip().upper()
    r17_violations = []
    if not ma_the or len(ma_the) < 15:
        r17_violations.append(RuleViolation(
            standard="4210", rule_code="17", rule_name="Mã thẻ không hợp lệ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="Đủ 15 ký tự",
            message=f"Mã thẻ '{ma_the}' không đủ 15 ký tự."
        ))
    elif not ma_the[5:].isdigit() or ma_the[5:] == "0000000000":
        r17_violations.append(RuleViolation(
            standard="4210", rule_code="17", rule_name="Mã thẻ không hợp lệ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="10 ký tự cuối là số khác 0000000000",
            message=f"10 ký tự cuối của mã thẻ '{ma_the[5:]}' không hợp lệ."
        ))
    results.append(RuleResult(rule_code="17", standard="4210", rule_name="Mã thẻ không hợp lệ",
                              status=RuleStatus.VIOLATED if r17_violations else RuleStatus.PASSED, violations=r17_violations))

    # ----------------------------------------------------
    # Rule 23: Ngày vào không hợp lệ (Định dạng YYYYMMDDHHMM)
    # Rule 24: Ngày ra không hợp lệ (Ngày ra >= Ngày vào)
    # ----------------------------------------------------
    ngay_vao = str(xml1.get("NGAY_VAO", "")).strip()
    ngay_ra = str(xml1.get("NGAY_RA", "")).strip()
    r23_violations = []
    r24_violations = []

    if not ngay_vao or len(ngay_vao) < 12 or not ngay_vao[:12].isdigit():
        r23_violations.append(RuleViolation(
            standard="4210", rule_code="23", rule_name="Ngày vào không hợp lệ",
            xml_table="XML1", field_name="NGAY_VAO", actual_value=ngay_vao,
            expected_condition="Định dạng YYYYMMDDHHMM",
            message=f"Ngày vào '{ngay_vao}' không đúng định dạng YYYYMMDDHHMM."
        ))
    if not ngay_ra or len(ngay_ra) < 12 or not ngay_ra[:12].isdigit():
        r24_violations.append(RuleViolation(
            standard="4210", rule_code="24", rule_name="Ngày ra không hợp lệ",
            xml_table="XML1", field_name="NGAY_RA", actual_value=ngay_ra,
            expected_condition="Định dạng YYYYMMDDHHMM",
            message=f"Ngày ra '{ngay_ra}' không đúng định dạng YYYYMMDDHHMM."
        ))
    elif ngay_vao and len(ngay_vao) >= 12 and ngay_ra < ngay_vao:
        r24_violations.append(RuleViolation(
            standard="4210", rule_code="24", rule_name="Ngày ra nhỏ hơn ngày vào",
            xml_table="XML1", field_name="NGAY_RA", actual_value=f"RA={ngay_ra}, VAO={ngay_vao}",
            expected_condition="Ngày ra >= Ngày vào",
            message=f"Ngày ra '{ngay_ra}' trước ngày vào viện '{ngay_vao}'."
        ))

    results.append(RuleResult(rule_code="23", standard="4210", rule_name="Ngày vào không hợp lệ",
                              status=RuleStatus.VIOLATED if r23_violations else RuleStatus.PASSED, violations=r23_violations))
    results.append(RuleResult(rule_code="24", standard="4210", rule_name="Ngày ra không hợp lệ",
                              status=RuleStatus.VIOLATED if r24_violations else RuleStatus.PASSED, violations=r24_violations))

    # ----------------------------------------------------
    # Rule 31: T_BHTT trong XML1 khác tổng cộng các T_BHTT trong XML2 và XML3
    # ----------------------------------------------------
    t_bhtt_xml1 = to_decimal(xml1.get("T_BHTT", 0))
    sum_bhtt_xml2 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml2])
    sum_bhtt_xml3 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml3])
    sum_bhtt_23 = sum_bhtt_xml2 + sum_bhtt_xml3

    r31_violations = []
    if abs(t_bhtt_xml1 - sum_bhtt_23) > Decimal("1.0"):
        r31_violations.append(RuleViolation(
            standard="4210", rule_code="31", rule_name="T_BHTT trong XML1 khác tổng XML2, XML3",
            xml_table="XML1", field_name="T_BHTT", actual_value=str(t_bhtt_xml1),
            expected_condition=f"Tổng XML2 ({sum_bhtt_xml2}) + XML3 ({sum_bhtt_xml3}) = {sum_bhtt_23}",
            message=f"T_BHTT XML1 ({t_bhtt_xml1}) khác tổng T_BHTT XML2+XML3 ({sum_bhtt_23}) (lệch > 1 đồng)."
        ))
    results.append(RuleResult(rule_code="31", standard="4210", rule_name="T_BHTT XML1 khác tổng XML23",
                              status=RuleStatus.VIOLATED if r31_violations else RuleStatus.PASSED, violations=r31_violations))

    # ----------------------------------------------------
    # Rule 34: TONGCHI trong XML1 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC
    # ----------------------------------------------------
    tong_chi_xml1 = to_decimal(xml1.get("TONG_CHI", xml1.get("T_TONGCHI", 0)))
    t_bntt = to_decimal(xml1.get("T_BNTT", 0))
    t_bncct = to_decimal(xml1.get("T_BNCCT", 0))
    t_bhtt = to_decimal(xml1.get("T_BHTT", 0))
    t_nguonkhac = to_decimal(xml1.get("T_NGUONKHAC", 0))
    sum_chi_tiet = t_bntt + t_bncct + t_bhtt + t_nguonkhac

    r34_violations = []
    if abs(tong_chi_xml1 - sum_chi_tiet) > Decimal("1.0"):
        r34_violations.append(RuleViolation(
            standard="4210", rule_code="34", rule_name="TONGCHI XML1 khác tổng các thành phần tiền",
            xml_table="XML1", field_name="TONG_CHI", actual_value=str(tong_chi_xml1),
            expected_condition=f"T_BNTT+T_BNCCT+T_BHTT+NGUONKHAC = {sum_chi_tiet}",
            message=f"TONGCHI ({tong_chi_xml1}) khác tổng các thành phần ({sum_chi_tiet})."
        ))
    results.append(RuleResult(rule_code="34", standard="4210", rule_name="TONGCHI XML1 khác tổng chi tiết",
                              status=RuleStatus.VIOLATED if r34_violations else RuleStatus.PASSED, violations=r34_violations))

    # ----------------------------------------------------
    # Rule 35: Năm quyết toán không hợp lệ
    # Rule 36: Tháng quyết toán không hợp lệ
    # ----------------------------------------------------
    nam_qt = str(xml1.get("NAM_QT", "")).strip()
    thang_qt = str(xml1.get("THANG_QT", "")).strip()
    r35_violations = []
    r36_violations = []
    if not nam_qt.isdigit() or int(nam_qt) < 2015 or int(nam_qt) > datetime.datetime.now().year + 1:
        r35_violations.append(RuleViolation(
            standard="4210", rule_code="35", rule_name="Năm quyết toán không hợp lệ",
            xml_table="XML1", field_name="NAM_QT", actual_value=nam_qt,
            expected_condition="Năm hợp lệ (>= 2015)", message=f"Năm quyết toán '{nam_qt}' không hợp lệ."
        ))
    if not thang_qt.isdigit() or int(thang_qt) < 1 or int(thang_qt) > 12:
        r36_violations.append(RuleViolation(
            standard="4210", rule_code="36", rule_name="Tháng quyết toán không hợp lệ",
            xml_table="XML1", field_name="THANG_QT", actual_value=thang_qt,
            expected_condition="Tháng trong khoảng 1 đến 12", message=f"Tháng quyết toán '{thang_qt}' không hợp lệ."
        ))
    results.append(RuleResult(rule_code="35", standard="4210", rule_name="Năm quyết toán không hợp lệ",
                              status=RuleStatus.VIOLATED if r35_violations else RuleStatus.PASSED, violations=r35_violations))
    results.append(RuleResult(rule_code="36", standard="4210", rule_name="Tháng quyết toán không hợp lệ",
                              status=RuleStatus.VIOLATED if r36_violations else RuleStatus.PASSED, violations=r36_violations))

    # ----------------------------------------------------
    # Rule 41 & Rule 47: Kiểm tra thành tiền và các khoản tiền trong XML2
    # ----------------------------------------------------
    r41_violations = []
    r47_violations = []
    for idx, row in enumerate(xml2):
        sl = to_decimal(row.get("SO_LUONG", 0))
        dg = to_decimal(row.get("DON_GIA", 0))
        tl = to_decimal(row.get("TYLE_TT", 100))
        tt_actual = to_decimal(row.get("THANH_TIEN", 0))
        tt_expected = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_actual - tt_expected) > Decimal("1.0"):
            r47_violations.append(RuleViolation(
                standard="4210", rule_code="47", rule_name="Thành tiền XML2 không hợp lệ",
                xml_table="XML2", field_name="THANH_TIEN", actual_value=str(tt_actual),
                expected_condition=f"{sl}*{dg}*{tl}% = {tt_expected}",
                message=f"Dòng thuốc #{idx+1} ({row.get('MA_THUOC', '')}): THANH_TIEN {tt_actual} != {tt_expected}."
            ))
        tt_row = to_decimal(row.get("THANH_TIEN", 0))
        bntt_row = to_decimal(row.get("T_BNTT", 0))
        bncct_row = to_decimal(row.get("T_BNCCT", 0))
        bhtt_row = to_decimal(row.get("T_BHTT", 0))
        ngk_row = to_decimal(row.get("T_NGUONKHAC", 0))
        ngoaids_row = to_decimal(row.get("T_NGOAIDS", 0))
        if abs(tt_row - (bntt_row + bncct_row + bhtt_row + ngk_row + ngoaids_row)) > Decimal("1.0"):
            r41_violations.append(RuleViolation(
                standard="4210", rule_code="41", rule_name="THANHTIEN XML2 khác tổng chi tiết",
                xml_table="XML2", field_name="THANH_TIEN", actual_value=str(tt_row),
                expected_condition="Bằng tổng BNTT+BNCCT+BHTT+NGUONKHAC+NGOAIDS",
                message=f"Dòng thuốc #{idx+1} ({row.get('MA_THUOC', '')}): THANHTIEN không bằng tổng các khoản tiền."
            ))

    results.append(RuleResult(rule_code="41", standard="4210", rule_name="THANHTIEN XML2 khác tổng tiền chi tiết",
                              status=RuleStatus.VIOLATED if r41_violations else RuleStatus.PASSED, violations=r41_violations))
    results.append(RuleResult(rule_code="47", standard="4210", rule_name="Thành tiền trong XML2 không hợp lệ",
                              status=RuleStatus.VIOLATED if r47_violations else RuleStatus.PASSED, violations=r47_violations))

    # ----------------------------------------------------
    # Rule 45 & Rule 52: Kiểm tra thành tiền và các khoản tiền trong XML3
    # ----------------------------------------------------
    r45_violations = []
    r52_violations = []
    for idx, row in enumerate(xml3):
        sl = to_decimal(row.get("SO_LUONG", 0))
        dg = to_decimal(row.get("DON_GIA", 0))
        tl = to_decimal(row.get("TYLE_TT", 100))
        tt_actual = to_decimal(row.get("THANH_TIEN", 0))
        tt_expected = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_actual - tt_expected) > Decimal("1.0"):
            r52_violations.append(RuleViolation(
                standard="4210", rule_code="52", rule_name="Thành tiền XML3 không hợp lệ",
                xml_table="XML3", field_name="THANH_TIEN", actual_value=str(tt_actual),
                expected_condition=f"{sl}*{dg}*{tl}% = {tt_expected}",
                message=f"Dòng DVKT #{idx+1} ({row.get('MA_DICH_VU', '')}): THANH_TIEN {tt_actual} != {tt_expected}."
            ))
        tt_row = to_decimal(row.get("THANH_TIEN", 0))
        bntt_row = to_decimal(row.get("T_BNTT", 0))
        bncct_row = to_decimal(row.get("T_BNCCT", 0))
        bhtt_row = to_decimal(row.get("T_BHTT", 0))
        ngk_row = to_decimal(row.get("T_NGUONKHAC", 0))
        ngoaids_row = to_decimal(row.get("T_NGOAIDS", 0))
        if abs(tt_row - (bntt_row + bncct_row + bhtt_row + ngk_row + ngoaids_row)) > Decimal("1.0"):
            r45_violations.append(RuleViolation(
                standard="4210", rule_code="45", rule_name="THANHTIEN XML3 khác tổng chi tiết",
                xml_table="XML3", field_name="THANH_TIEN", actual_value=str(tt_row),
                expected_condition="Bằng tổng BNTT+BNCCT+BHTT+NGUONKHAC+NGOAIDS",
                message=f"Dòng DVKT #{idx+1} ({row.get('MA_DICH_VU', '')}): THANHTIEN không bằng tổng các khoản tiền."
            ))

    results.append(RuleResult(rule_code="45", standard="4210", rule_name="THANHTIEN XML3 khác tổng tiền chi tiết",
                              status=RuleStatus.VIOLATED if r45_violations else RuleStatus.PASSED, violations=r45_violations))
    results.append(RuleResult(rule_code="52", standard="4210", rule_name="Thành tiền trong XML3 không hợp lệ",
                              status=RuleStatus.VIOLATED if r52_violations else RuleStatus.PASSED, violations=r52_violations))

    return results
