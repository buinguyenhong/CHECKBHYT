import re
from decimal import Decimal
import datetime
from typing import List, Dict, Any
from ..rule_models import (
    RuleResult, RuleStatus, RuleViolation, CaseXmlData,
    to_decimal, round_money, is_valid_date_str, is_valid_datetime_str
)

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
    ly_do_vv = str(xml1.get("MA_LYDO_VVIEN", xml1.get("LY_DO_VV", "1")) or "1").strip()
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
    # Rule 8, 9, 10, 11, 14
    # ----------------------------------------------------
    ma_the = str(xml1.get("MA_THE", xml1.get("SO_THE", ""))).strip().upper()
    r8_v = []
    if not ma_the or len(ma_the) < 15 or not ma_the[5:].isdigit() or ma_the[5:] == "0000000000":
        r8_v.append(RuleViolation(
            standard="4210", rule_code="8", rule_name="Sai thông tin thẻ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="Mã thẻ 15 ký tự hợp lệ", message=f"Mã thẻ '{ma_the}' sai thông tin."
        ))
    results.append(RuleResult(rule_code="8", standard="4210", rule_name="Sai thông tin thẻ",
                              status=RuleStatus.VIOLATED if r8_v else RuleStatus.PASSED, violations=r8_v))

    r9_v = []
    if ma_dkbd and len(ma_dkbd) != 5:
        r9_v.append(RuleViolation(
            standard="4210", rule_code="9", rule_name="Sai thông tin CSKCB ban đầu",
            xml_table="XML1", field_name="MA_DKBD", actual_value=ma_dkbd,
            expected_condition="Mã ĐKBĐ 5 ký tự", message=f"Mã ĐKBĐ '{ma_dkbd}' không đúng 5 ký tự."
        ))
    results.append(RuleResult(rule_code="9", standard="4210", rule_name="Sai thông tin CSKCB ban đầu",
                              status=RuleStatus.VIOLATED if r9_v else RuleStatus.PASSED, violations=r9_v))

    r10_v = []
    if ma_cskcb and len(ma_cskcb) != 5:
        r10_v.append(RuleViolation(
            standard="4210", rule_code="10", rule_name="Sai thông tin CSKCB",
            xml_table="XML1", field_name="MA_CSKCB", actual_value=ma_cskcb,
            expected_condition="Mã CSKCB 5 ký tự", message=f"Mã CSKCB '{ma_cskcb}' không đúng 5 ký tự."
        ))
    results.append(RuleResult(rule_code="10", standard="4210", rule_name="Sai thông tin CSKCB",
                              status=RuleStatus.VIOLATED if r10_v else RuleStatus.PASSED, violations=r10_v))

    t_bhtt_xml1 = to_decimal(xml1.get("T_BHTT", 0))
    r11_v = []
    if t_bhtt_xml1 <= Decimal("0"):
        r11_v.append(RuleViolation(
            standard="4210", rule_code="11", rule_name="Không phát sinh chi phí đề nghị thanh toán",
            xml_table="XML1", field_name="T_BHTT", actual_value=str(t_bhtt_xml1),
            expected_condition="T_BHTT > 0", message="Tiền đề nghị BHTT trống hoặc = 0."
        ))
    results.append(RuleResult(rule_code="11", standard="4210", rule_name="Không phát sinh chi phí BHTT",
                              status=RuleStatus.VIOLATED if r11_v else RuleStatus.PASSED, violations=r11_v))

    stent_count = Decimal("0")
    for r in xml3:
        if "STENT" in str(r.get("TEN_DICH_VU", "")).upper() or "STENT" in str(r.get("MA_DICH_VU", "")).upper() or "N06.02.020" in str(r.get("MA_VAT_TU", "")).upper():
            stent_count += to_decimal(r.get("SO_LUONG", 0))
    r14_v = []
    if stent_count > Decimal("2"):
        r14_v.append(RuleViolation(
            standard="4210", rule_code="14", rule_name="Stent động mạch vành vượt quá số lượng",
            xml_table="XML3", field_name="SO_LUONG", actual_value=str(stent_count),
            expected_condition="Số lượng Stent <= 2", message=f"Số lượng stent ({stent_count}) vượt quá 2."
        ))
    results.append(RuleResult(rule_code="14", standard="4210", rule_name="Stent động mạch vành tối đa 2",
                              status=RuleStatus.VIOLATED if r14_v else RuleStatus.PASSED, violations=r14_v))

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

    # ----------------------------------------------------
    # Các quy tắc bổ sung chuẩn 4210: 18-22, 25-27, 37-40, 42-44, 46, 48-51, 53-56
    # ----------------------------------------------------
    r18_v, r19_v, r20_v, r21_v, r22_v, r25_v, r26_v, r27_v, r37_v, r38_v = [], [], [], [], [], [], [], [], [], []
    gt_tu = str(xml1.get("GT_THE_TU", "") or "").strip()
    if gt_tu and gt_tu.lower() not in ["none", "null", "nan"]:
        for p in gt_tu.split(";"):
            if not is_valid_date_str(p.strip()[:8]):
                r18_v.append(RuleViolation(standard="4210", rule_code="18", rule_name="Giá trị thẻ từ không hợp lệ",
                                           xml_table="XML1", field_name="GT_THE_TU", actual_value=gt_tu,
                                           expected_condition="YYYYMMDD hợp lệ", message=f"GT_THE_TU '{p.strip()}' sai định dạng."))
    gt_den = str(xml1.get("GT_THE_DEN", "") or "").strip()
    if gt_den and gt_den.lower() not in ["none", "null", "nan"]:
        for p in gt_den.split(";"):
            if not is_valid_date_str(p.strip()[:8]):
                r19_v.append(RuleViolation(standard="4210", rule_code="19", rule_name="Giá trị thẻ đến không hợp lệ",
                                           xml_table="XML1", field_name="GT_THE_DEN", actual_value=gt_den,
                                           expected_condition="YYYYMMDD hợp lệ", message=f"GT_THE_DEN '{p.strip()}' sai định dạng."))
    khac_4 = [str(xml1.get(k, "") or "").strip() for k in ["MA_THE_KHAC", "MA_DKBD_KHAC", "GT_THE_TU_KHAC", "GT_THE_DEN_KHAC"]]
    khac_4 = [x if x.lower() not in ["none", "null", "nan"] else "" for x in khac_4]
    if any(khac_4) and (not all(khac_4) or len(set(len(x.split(";")) for x in khac_4)) > 1):
        r20_v.append(RuleViolation(standard="4210", rule_code="20", rule_name="Thông tin thẻ khác không tương ứng",
                                   xml_table="XML1", field_name="MA_THE_KHAC", actual_value=str(khac_4),
                                   expected_condition="4 trường thẻ khác có số phần tử bằng nhau", message="Số lượng phần tử thẻ khác không khớp."))
    mien_cct = str(xml1.get("NGAY_MIEN_CCT", "") or "").strip()
    if mien_cct and mien_cct.lower() not in ["none", "null", "nan"] and not is_valid_date_str(mien_cct[:8]):
        r21_v.append(RuleViolation(standard="4210", rule_code="21", rule_name="Miễn cùng chi trả không hợp lệ",
                                   xml_table="XML1", field_name="NGAY_MIEN_CCT", actual_value=mien_cct,
                                   expected_condition="YYYYMMDD hợp lệ", message=f"NGAY_MIEN_CCT '{mien_cct}' không hợp lệ."))
    ma_tn = str(xml1.get("MA_TAI_NAN", "") or "").strip()
    if ma_tn and ma_tn.lower() not in ["none", "null", "nan"] and ma_tn not in [str(i) for i in range(9)]:
        r22_v.append(RuleViolation(standard="4210", rule_code="22", rule_name="Mã tai nạn không hợp lệ",
                                   xml_table="XML1", field_name="MA_TAI_NAN", actual_value=ma_tn,
                                   expected_condition="Thuộc 0..8", message=f"MA_TAI_NAN '{ma_tn}' không hợp lệ."))
    kq_dt = str(xml1.get("KET_QUA_DTRI", "") or "").strip()
    if kq_dt and kq_dt.lower() not in ["none", "null", "nan"] and kq_dt not in ["1", "2", "3", "4", "5"]:
        r25_v.append(RuleViolation(standard="4210", rule_code="25", rule_name="Kết quả điều trị không hợp lệ",
                                   xml_table="XML1", field_name="KET_QUA_DTRI", actual_value=kq_dt,
                                   expected_condition="Thuộc 1..5", message=f"KET_QUA_DTRI '{kq_dt}' không hợp lệ."))
    tt_rv = str(xml1.get("TINH_TRANG_RV", xml1.get("MA_LOAI_RV", "")) or "").strip()
    if tt_rv and tt_rv.lower() not in ["none", "null", "nan"] and tt_rv not in ["1", "2", "3", "4"]:
        r26_v.append(RuleViolation(standard="4210", rule_code="26", rule_name="Tình trạng ra viện không hợp lệ",
                                   xml_table="XML1", field_name="TINH_TRANG_RV", actual_value=tt_rv,
                                   expected_condition="Thuộc 1..4", message=f"TINH_TRANG_RV '{tt_rv}' không hợp lệ."))
    ngay_tt = str(xml1.get("NGAY_TTOAN", "") or "").strip()
    if ngay_tt and ngay_tt.lower() not in ["none", "null", "nan"] and not is_valid_datetime_str(ngay_tt[:12]):
        r27_v.append(RuleViolation(standard="4210", rule_code="27", rule_name="Ngày thanh toán không hợp lệ",
                                   xml_table="XML1", field_name="NGAY_TTOAN", actual_value=ngay_tt,
                                   expected_condition="YYYYMMDDHHMM hợp lệ", message=f"NGAY_TTOAN '{ngay_tt}' không hợp lệ."))
    loai_kcb = str(xml1.get("MA_LOAI_KCB", "") or "").strip()
    if loai_kcb and loai_kcb not in ["1", "2", "3", "5"]:
        r37_v.append(RuleViolation(standard="4210", rule_code="37", rule_name="Mã loại KCB không hợp lệ",
                                   xml_table="XML1", field_name="MA_LOAI_KCB", actual_value=loai_kcb,
                                   expected_condition="Thuộc (1, 2, 3)", message=f"MA_LOAI_KCB '{loai_kcb}' không hợp lệ."))
    ma_kv = str(xml1.get("MA_KHU_VUC", "") or "").strip().upper()
    if ma_kv and ma_kv not in ["NONE", "NULL", "NAN"] and ma_kv not in ["K1", "K2", "K3"]:
        r38_v.append(RuleViolation(standard="4210", rule_code="38", rule_name="Mã khu vực không hợp lệ",
                                   xml_table="XML1", field_name="MA_KHU_VUC", actual_value=ma_kv,
                                   expected_condition="Thuộc (K1, K2, K3)", message=f"MA_KHU_VUC '{ma_kv}' không hợp lệ."))

    for code, name, v_list in [
        ("18", "Giá trị thẻ từ không hợp lệ", r18_v),
        ("19", "Giá trị thẻ đến không hợp lệ", r19_v),
        ("20", "Số lượng mã thẻ khác không tương ứng", r20_v),
        ("21", "Miễn cùng chi trả không hợp lệ", r21_v),
        ("22", "Mã tai nạn không hợp lệ", r22_v),
        ("25", "Kết quả điều trị không hợp lệ", r25_v),
        ("26", "Tình trạng ra viện không hợp lệ", r26_v),
        ("27", "Ngày thanh toán không hợp lệ", r27_v),
        ("37", "Mã loại KCB không hợp lệ", r37_v),
        ("38", "Mã khu vực không hợp lệ", r38_v),
    ]:
        results.append(RuleResult(rule_code=code, standard="4210", rule_name=name,
                                  status=RuleStatus.VIOLATED if v_list else RuleStatus.PASSED, violations=v_list))

    r39_v, r40_v, r42_v, r48_v, r49_v, r50_v, r51_v = [], [], [], [], [], [], []
    for idx, r in enumerate(xml2):
        nhom = str(r.get("MA_NHOM", "") or "").strip()
        if nhom and nhom not in ["4", "5", "6", "7"]:
            r39_v.append(RuleViolation(standard="4210", rule_code="39", rule_name="Mã nhóm XML2 không hợp lệ",
                                       xml_table="XML2", field_name="MA_NHOM", actual_value=nhom,
                                       expected_condition="Thuộc (4, 5, 6, 7)", message=f"Dòng thuốc #{idx+1}: MA_NHOM '{nhom}' sai."))
        pv = str(r.get("PHAM_VI", "") or "").strip()
        if pv and pv not in ["1", "2"]:
            r40_v.append(RuleViolation(standard="4210", rule_code="40", rule_name="Phạm vi XML2 không hợp lệ",
                                       xml_table="XML2", field_name="PHAM_VI", actual_value=pv,
                                       expected_condition="Thuộc (1, 2)", message=f"Dòng thuốc #{idx+1}: PHAM_VI '{pv}' sai."))
        tt = to_decimal(r.get("THANH_TIEN", 0))
        bhtt = to_decimal(r.get("T_BHTT", 0))
        bncct = to_decimal(r.get("T_BNCCT", 0))
        bntt = to_decimal(r.get("T_BNTT", 0))
        ngk = to_decimal(r.get("T_NGUONKHAC", 0))
        nds = to_decimal(r.get("T_NGOAIDS", 0))
        if nds != Decimal("0") and nds != bhtt:
            r42_v.append(RuleViolation(standard="4210", rule_code="42", rule_name="T_NGOAIDS XML2 không hợp lệ",
                                       xml_table="XML2", field_name="T_NGOAIDS", actual_value=str(nds),
                                       expected_condition="Bằng 0 hoặc bằng T_BHTT", message=f"Dòng thuốc #{idx+1}: T_NGOAIDS khác 0 và khác T_BHTT."))
        if bhtt < Decimal("0") or (tt > Decimal("0") and bhtt > tt + Decimal("1.0")):
            r48_v.append(RuleViolation(standard="4210", rule_code="48", rule_name="T_BHTT XML2 không hợp lệ",
                                       xml_table="XML2", field_name="T_BHTT", actual_value=str(bhtt),
                                       expected_condition=f"0 <= T_BHTT <= {tt}", message=f"Dòng thuốc #{idx+1}: T_BHTT không hợp lệ."))
        if bncct < Decimal("0") or (tt > Decimal("0") and bncct > tt + Decimal("1.0")):
            r49_v.append(RuleViolation(standard="4210", rule_code="49", rule_name="T_BNCCT XML2 không hợp lệ",
                                       xml_table="XML2", field_name="T_BNCCT", actual_value=str(bncct),
                                       expected_condition=f"0 <= T_BNCCT <= {tt}", message=f"Dòng thuốc #{idx+1}: T_BNCCT không hợp lệ."))
        if bntt < Decimal("0") or (tt > Decimal("0") and bntt > tt + Decimal("1.0")):
            r50_v.append(RuleViolation(standard="4210", rule_code="50", rule_name="T_BNTT XML2 không hợp lệ",
                                       xml_table="XML2", field_name="T_BNTT", actual_value=str(bntt),
                                       expected_condition=f"0 <= T_BNTT <= {tt}", message=f"Dòng thuốc #{idx+1}: T_BNTT không hợp lệ."))
        if tt >= Decimal("0") and (ngk < Decimal("0") or ngk > tt + Decimal("1.0")):
            r51_v.append(RuleViolation(standard="4210", rule_code="51", rule_name="T_NGUONKHAC XML2 không hợp lệ",
                                       xml_table="XML2", field_name="T_NGUONKHAC", actual_value=str(ngk),
                                       expected_condition=f"0 <= T_NGUONKHAC <= {tt}", message=f"Dòng thuốc #{idx+1}: T_NGUONKHAC không hợp lệ."))

    for code, name, v_list in [
        ("39", "Mã nhóm trong XML2 không hợp lệ", r39_v),
        ("40", "Phạm vi trong XML2 không hợp lệ", r40_v),
        ("42", "T_NGOAIDS trong XML2 không hợp lệ", r42_v),
        ("48", "T_BHTT trong XML2 không hợp lệ", r48_v),
        ("49", "T_BNCCT trong XML2 không hợp lệ", r49_v),
        ("50", "T_BNTT trong XML2 không hợp lệ", r50_v),
        ("51", "T_NGUONKHAC trong XML2 không hợp lệ", r51_v),
    ]:
        results.append(RuleResult(rule_code=code, standard="4210", rule_name=name,
                                  status=RuleStatus.VIOLATED if v_list else RuleStatus.PASSED, violations=v_list))

    r43_v, r44_v, r46_v, r53_v, r54_v, r55_v, r56_v = [], [], [], [], [], [], []
    valid_nhom3_4210 = {"1", "2", "3", "8", "9", "10", "11", "12", "13", "14", "15"}
    for idx, r in enumerate(xml3):
        nhom = str(r.get("MA_NHOM", "") or "").strip()
        if nhom and nhom not in valid_nhom3_4210:
            r43_v.append(RuleViolation(standard="4210", rule_code="43", rule_name="Mã nhóm XML3 không hợp lệ",
                                       xml_table="XML3", field_name="MA_NHOM", actual_value=nhom,
                                       expected_condition="Thuộc (1..3, 8..15)", message=f"Dòng DVKT #{idx+1}: MA_NHOM '{nhom}' sai."))
        pv = str(r.get("PHAM_VI", "") or "").strip()
        if pv and pv not in ["1", "2"]:
            r44_v.append(RuleViolation(standard="4210", rule_code="44", rule_name="Phạm vi XML3 không hợp lệ",
                                       xml_table="XML3", field_name="PHAM_VI", actual_value=pv,
                                       expected_condition="Thuộc (1, 2)", message=f"Dòng DVKT #{idx+1}: PHAM_VI '{pv}' sai."))
        tt = to_decimal(r.get("THANH_TIEN", 0))
        bhtt = to_decimal(r.get("T_BHTT", 0))
        bncct = to_decimal(r.get("T_BNCCT", 0))
        bntt = to_decimal(r.get("T_BNTT", 0))
        ngk = to_decimal(r.get("T_NGUONKHAC", 0))
        nds = to_decimal(r.get("T_NGOAIDS", 0))
        if nds != Decimal("0") and nds != bhtt:
            r46_v.append(RuleViolation(standard="4210", rule_code="46", rule_name="T_NGOAIDS XML3 không hợp lệ",
                                       xml_table="XML3", field_name="T_NGOAIDS", actual_value=str(nds),
                                       expected_condition="Bằng 0 hoặc bằng T_BHTT", message=f"Dòng DVKT #{idx+1}: T_NGOAIDS khác 0 và khác T_BHTT."))
        if bhtt < Decimal("0") or (tt > Decimal("0") and bhtt > tt + Decimal("1.0")):
            r53_v.append(RuleViolation(standard="4210", rule_code="53", rule_name="T_BHTT XML3 không hợp lệ",
                                       xml_table="XML3", field_name="T_BHTT", actual_value=str(bhtt),
                                       expected_condition=f"0 <= T_BHTT <= {tt}", message=f"Dòng DVKT #{idx+1}: T_BHTT không hợp lệ."))
        if bncct < Decimal("0") or (tt > Decimal("0") and bncct > tt + Decimal("1.0")):
            r54_v.append(RuleViolation(standard="4210", rule_code="54", rule_name="T_BNCCT XML3 không hợp lệ",
                                       xml_table="XML3", field_name="T_BNCCT", actual_value=str(bncct),
                                       expected_condition=f"0 <= T_BNCCT <= {tt}", message=f"Dòng DVKT #{idx+1}: T_BNCCT không hợp lệ."))
        if bntt < Decimal("0") or (tt > Decimal("0") and bntt > tt + Decimal("1.0")):
            r55_v.append(RuleViolation(standard="4210", rule_code="55", rule_name="T_BNTT XML3 không hợp lệ",
                                       xml_table="XML3", field_name="T_BNTT", actual_value=str(bntt),
                                       expected_condition=f"0 <= T_BNTT <= {tt}", message=f"Dòng DVKT #{idx+1}: T_BNTT không hợp lệ."))
        if tt >= Decimal("0") and (ngk < Decimal("0") or ngk > tt + Decimal("1.0")):
            r56_v.append(RuleViolation(standard="4210", rule_code="56", rule_name="T_NGUONKHAC XML3 không hợp lệ",
                                       xml_table="XML3", field_name="T_NGUONKHAC", actual_value=str(ngk),
                                       expected_condition=f"0 <= T_NGUONKHAC <= {tt}", message=f"Dòng DVKT #{idx+1}: T_NGUONKHAC không hợp lệ."))

    for code, name, v_list in [
        ("43", "Mã nhóm trong XML3 không hợp lệ", r43_v),
        ("44", "Phạm vi trong XML3 không hợp lệ", r44_v),
        ("46", "T_NGOAIDS trong XML3 không hợp lệ", r46_v),
        ("53", "T_BHTT trong XML3 không hợp lệ", r53_v),
        ("54", "T_BNCCT trong XML3 không hợp lệ", r54_v),
        ("55", "T_BNTT trong XML3 không hợp lệ", r55_v),
        ("56", "T_NGUONKHAC trong XML3 không hợp lệ", r56_v),
    ]:
        results.append(RuleResult(rule_code=code, standard="4210", rule_name=name,
                                  status=RuleStatus.VIOLATED if v_list else RuleStatus.PASSED, violations=v_list))

    return results
