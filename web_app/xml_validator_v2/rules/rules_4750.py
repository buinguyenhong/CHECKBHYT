import re
from decimal import Decimal
import datetime
from typing import List, Dict, Any
from ..rule_models import RuleResult, RuleStatus, RuleViolation, CaseXmlData, to_decimal, round_money

def check_rules_4750(case: CaseXmlData) -> List[RuleResult]:
    results: List[RuleResult] = []
    xml1 = case.xml1
    xml2 = case.xml2
    xml3 = case.xml3

    if not xml1:
        return results

    # ----------------------------------------------------
    # Rule 1: Sai lý do vào viện (Sai đối tượng KCB)
    # ----------------------------------------------------
    ly_do_vv = str(xml1.get("MA_LYDO_VVIEN", xml1.get("LY_DO_VV", ""))).strip()
    ma_dkbd = str(xml1.get("MA_DKBD", "")).strip().upper()
    ma_cskcb = str(xml1.get("MA_CSKCB", "")).strip().upper()

    r1_violations = []
    if ly_do_vv not in ["1", "2", "3", "4"]:
        r1_violations.append(RuleViolation(
            standard="4750", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=ly_do_vv,
            expected_condition="Thuộc danh sách (1, 2, 3, 4)",
            message=f"Mã lý do vào viện '{ly_do_vv}' không hợp lệ."
        ))
    elif ly_do_vv == "3" and ma_dkbd and ma_cskcb and ma_dkbd == ma_cskcb:
        r1_violations.append(RuleViolation(
            standard="4750", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=f"LYDO={ly_do_vv}, DKBD={ma_dkbd}, CSKCB={ma_cskcb}",
            expected_condition="Mã ĐKBĐ khác Mã CSKCB khi gửi trái tuyến (3)",
            message="Mã lý do vào viện = 3 (trái tuyến) nhưng Mã ĐKBĐ trùng CSKCB."
        ))
    results.append(RuleResult(rule_code="1", standard="4750", rule_name="Sai lý do vào viện",
                              status=RuleStatus.VIOLATED if r1_violations else RuleStatus.PASSED, violations=r1_violations))

    # ----------------------------------------------------
    # Rule 8: Sai thông tin thẻ (3 ký tự đầu, mã tỉnh, 10 ký tự số)
    # ----------------------------------------------------
    ma_the = str(xml1.get("MA_THE", xml1.get("SO_THE", ""))).strip().upper()
    r8_violations = []
    if not ma_the or len(ma_the) < 15:
        r8_violations.append(RuleViolation(
            standard="4750", rule_code="8", rule_name="Sai thông tin thẻ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="Mã thẻ BHYT đủ 15 ký tự", message="Mã thẻ BHYT không đủ 15 ký tự."
        ))
    else:
        suffix10 = ma_the[5:]
        if not suffix10.isdigit() or suffix10 == "0000000000":
            r8_violations.append(RuleViolation(
                standard="4750", rule_code="8", rule_name="Sai thông tin thẻ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="10 ký tự cuối phải là số và khác 0000000000",
                message=f"10 ký tự cuối của mã thẻ '{suffix10}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="8", standard="4750", rule_name="Sai thông tin thẻ",
                              status=RuleStatus.VIOLATED if r8_violations else RuleStatus.PASSED, violations=r8_violations))

    # ----------------------------------------------------
    # Rule 11: Không phát sinh chi phí Đề nghị thanh toán
    # ----------------------------------------------------
    t_bhtt_xml1 = to_decimal(xml1.get("T_BHTT", 0))
    r11_violations = []
    if t_bhtt_xml1 <= Decimal("0"):
        r11_violations.append(RuleViolation(
            standard="4750", rule_code="11", rule_name="Không phát sinh chi phí đề nghị thanh toán",
            xml_table="XML1", field_name="T_BHTT", actual_value=str(t_bhtt_xml1),
            expected_condition="T_BHTT > 0", message="Tiền đề nghị BHTT trống hoặc = 0."
        ))
    results.append(RuleResult(rule_code="11", standard="4750", rule_name="Không phát sinh chi phí BHTT",
                              status=RuleStatus.VIOLATED if r11_violations else RuleStatus.PASSED, violations=r11_violations))

    # ----------------------------------------------------
    # Rule 14: Stent động mạch vành phủ thuốc (tối đa 2 stent)
    # ----------------------------------------------------
    stent_count = Decimal("0")
    for r in xml3:
        ten_dv = str(r.get("TEN_DICH_VU", "")).upper()
        ma_dv = str(r.get("MA_DICH_VU", "")).upper()
        if "STENT" in ten_dv or "STENT" in ma_dv:
            stent_count += to_decimal(r.get("SO_LUONG", 0))
    r14_violations = []
    if stent_count > Decimal("2"):
        r14_violations.append(RuleViolation(
            standard="4750", rule_code="14", rule_name="Stent động mạch vành vượt quá số lượng cho phép",
            xml_table="XML3", field_name="SO_LUONG", actual_value=str(stent_count),
            expected_condition="Số lượng Stent <= 2 trong đợt điều trị",
            message=f"Số lượng stent thanh toán {stent_count} vượt quá quy định 2 stent."
        ))
    results.append(RuleResult(rule_code="14", standard="4750", rule_name="Stent động mạch vành tối đa 2",
                              status=RuleStatus.VIOLATED if r14_violations else RuleStatus.PASSED, violations=r14_violations))

    # ----------------------------------------------------
    # Rule 16: Giới tính không hợp lệ (1: Nam, 2: Nữ)
    # ----------------------------------------------------
    gioi_tinh = str(xml1.get("GIOI_TINH", "")).strip()
    r16_violations = []
    if gioi_tinh not in ["1", "2"]:
        r16_violations.append(RuleViolation(
            standard="4750", rule_code="16", rule_name="Giới tính không hợp lệ",
            xml_table="XML1", field_name="GIOI_TINH", actual_value=gioi_tinh,
            expected_condition="GIOI_TINH thuộc [1, 2]",
            message=f"Giới tính '{gioi_tinh}' không hợp lệ."
        ))
    results.append(RuleResult(rule_code="16", standard="4750", rule_name="Giới tính không hợp lệ",
                              status=RuleStatus.VIOLATED if r16_violations else RuleStatus.PASSED, violations=r16_violations))

    # ----------------------------------------------------
    # Rule 23, 24: Ngày vào, Ngày ra viện
    # ----------------------------------------------------
    ngay_vao = str(xml1.get("NGAY_VAO", "")).strip()
    ngay_ra = str(xml1.get("NGAY_RA", "")).strip()
    r23_violations = []
    r24_violations = []
    if not ngay_vao or len(ngay_vao) < 12 or not ngay_vao[:12].isdigit():
        r23_violations.append(RuleViolation(
            standard="4750", rule_code="23", rule_name="Ngày vào không hợp lệ",
            xml_table="XML1", field_name="NGAY_VAO", actual_value=ngay_vao,
            expected_condition="Định dạng YYYYMMDDHHMM", message="Ngày vào sai định dạng."
        ))
    if not ngay_ra or len(ngay_ra) < 12 or not ngay_ra[:12].isdigit():
        r24_violations.append(RuleViolation(
            standard="4750", rule_code="24", rule_name="Ngày ra không hợp lệ",
            xml_table="XML1", field_name="NGAY_RA", actual_value=ngay_ra,
            expected_condition="Định dạng YYYYMMDDHHMM", message="Ngày ra sai định dạng."
        ))
    elif ngay_vao and len(ngay_vao) >= 12 and ngay_ra < ngay_vao:
        r24_violations.append(RuleViolation(
            standard="4750", rule_code="24", rule_name="Ngày ra nhỏ hơn ngày vào",
            xml_table="XML1", field_name="NGAY_RA", actual_value=f"RA={ngay_ra}, VAO={ngay_vao}",
            expected_condition="Ngày ra >= Ngày vào", message=f"Ngày ra '{ngay_ra}' trước ngày vào '{ngay_vao}'."
        ))
    results.append(RuleResult(rule_code="23", standard="4750", rule_name="Ngày vào không hợp lệ",
                              status=RuleStatus.VIOLATED if r23_violations else RuleStatus.PASSED, violations=r23_violations))
    results.append(RuleResult(rule_code="24", standard="4750", rule_name="Ngày ra không hợp lệ",
                              status=RuleStatus.VIOLATED if r24_violations else RuleStatus.PASSED, violations=r24_violations))

    # ----------------------------------------------------
    # Rule 31: T_BHTT trong XML1 khác tổng cộng các T_BHTT trong XML2, XML3
    # ----------------------------------------------------
    sum_bhtt_xml2 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml2])
    sum_bhtt_xml3 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml3])
    sum_bhtt_23 = sum_bhtt_xml2 + sum_bhtt_xml3
    r31_violations = []
    if abs(t_bhtt_xml1 - sum_bhtt_23) > Decimal("1.0"):
        r31_violations.append(RuleViolation(
            standard="4750", rule_code="31", rule_name="T_BHTT XML1 khác tổng XML2, XML3",
            xml_table="XML1", field_name="T_BHTT", actual_value=str(t_bhtt_xml1),
            expected_condition=f"Tổng XML23 = {sum_bhtt_23}",
            message=f"T_BHTT XML1 ({t_bhtt_xml1}) khác tổng T_BHTT XML2+XML3 ({sum_bhtt_23})."
        ))
    results.append(RuleResult(rule_code="31", standard="4750", rule_name="T_BHTT XML1 khác tổng XML23",
                              status=RuleStatus.VIOLATED if r31_violations else RuleStatus.PASSED, violations=r31_violations))

    # ----------------------------------------------------
    # Rule 34: T_TONGCHI_BV trong XML1 khác tổng T_BNTT + T_BNCCT + T_BHTT + T_NGUONKHAC
    # ----------------------------------------------------
    t_tongchi_bv = to_decimal(xml1.get("T_TONGCHI_BV", xml1.get("T_TONGCHI", xml1.get("TONG_CHI", 0))))
    t_bntt = to_decimal(xml1.get("T_BNTT", 0))
    t_bncct = to_decimal(xml1.get("T_BNCCT", 0))
    t_bhtt = to_decimal(xml1.get("T_BHTT", 0))
    t_nguonkhac = to_decimal(xml1.get("T_NGUONKHAC", 0))
    sum_chi_tiet = t_bntt + t_bncct + t_bhtt + t_nguonkhac
    r34_violations = []
    if abs(t_tongchi_bv - sum_chi_tiet) > Decimal("1.0"):
        r34_violations.append(RuleViolation(
            standard="4750", rule_code="34", rule_name="T_TONGCHI_BV XML1 khác tổng chi tiết",
            xml_table="XML1", field_name="T_TONGCHI_BV", actual_value=str(t_tongchi_bv),
            expected_condition=f"Tổng = {sum_chi_tiet}",
            message=f"T_TONGCHI_BV ({t_tongchi_bv}) khác tổng BNTT+BNCCT+BHTT+NGUONKHAC ({sum_chi_tiet})."
        ))
    results.append(RuleResult(rule_code="34", standard="4750", rule_name="T_TONGCHI_BV XML1 khác tổng chi tiết",
                              status=RuleStatus.VIOLATED if r34_violations else RuleStatus.PASSED, violations=r34_violations))

    # ----------------------------------------------------
    # Rule 108: Năm sinh < 1900
    # Rule 109: ngay_sinh > ngay_vao
    # ----------------------------------------------------
    ngay_sinh = str(xml1.get("NGAY_SINH", "")).strip()
    r108_violations = []
    r109_violations = []
    if ngay_sinh and len(ngay_sinh) >= 4 and ngay_sinh[:4].isdigit():
        nam_sinh = int(ngay_sinh[:4])
        if nam_sinh < 1900:
            r108_violations.append(RuleViolation(
                standard="4750", rule_code="108", rule_name="Năm sinh < 1900",
                xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh,
                expected_condition="Năm sinh >= 1900", message=f"Năm sinh {nam_sinh} nhỏ hơn 1900."
            ))
        if ngay_vao and len(ngay_vao) >= 8 and ngay_sinh[:8].isdigit() and ngay_vao[:8].isdigit():
            if ngay_sinh[:8] > ngay_vao[:8]:
                r109_violations.append(RuleViolation(
                    standard="4750", rule_code="109", rule_name="Ngày sinh lớn hơn ngày vào viện",
                    xml_table="XML1", field_name="NGAY_SINH", actual_value=f"SINH={ngay_sinh}, VAO={ngay_vao}",
                    expected_condition="Ngày sinh <= Ngày vào viện", message="Ngày sinh sau ngày vào viện."
                ))
    results.append(RuleResult(rule_code="108", standard="4750", rule_name="Năm sinh < 1900",
                              status=RuleStatus.VIOLATED if r108_violations else RuleStatus.PASSED, violations=r108_violations))
    results.append(RuleResult(rule_code="109", standard="4750", rule_name="Ngày sinh > Ngày vào viện",
                              status=RuleStatus.VIOLATED if r109_violations else RuleStatus.PASSED, violations=r109_violations))

    # ----------------------------------------------------
    # Rule 112: Hưu trí (HT) nhỏ hơn 33 tuổi
    # ----------------------------------------------------
    r112_violations = []
    if ma_the.startswith("HT") and ngay_sinh and len(ngay_sinh) >= 4 and ngay_sinh[:4].isdigit():
        nam_sinh = int(ngay_sinh[:4])
        cur_year = datetime.datetime.now().year
        tuoi = cur_year - nam_sinh
        if tuoi < 33:
            r112_violations.append(RuleViolation(
                standard="4750", rule_code="112", rule_name="Hưu trí nhỏ hơn 33 tuổi",
                xml_table="XML1", field_name="MA_THE", actual_value=f"MA_THE={ma_the}, TUOI={tuoi}",
                expected_condition="Tuổi hưởng hưu trí >= 33", message=f"Đối tượng hưu trí (HT) có tuổi = {tuoi} (< 33 tuổi)."
            ))
    results.append(RuleResult(rule_code="112", standard="4750", rule_name="Hưu trí nhỏ hơn 33 tuổi",
                              status=RuleStatus.VIOLATED if r112_violations else RuleStatus.PASSED, violations=r112_violations))

    # ----------------------------------------------------
    # Rule 115: Hồ sơ khám bệnh có tiền giường
    # (Nếu MA_LOAI_KCB = 1 (khám bệnh) hoặc loại ngoại trú mà có tiền giường XML3 (nhóm 14, 15))
    # ----------------------------------------------------
    ma_loai_kcb = str(xml1.get("MA_LOAI_KCB", "")).strip()
    r115_violations = []
    if ma_loai_kcb in ["1", "01"]:
        tien_giuong = Decimal("0")
        for r in xml3:
            ma_nhom = str(r.get("MA_NHOM", "")).strip()
            if ma_nhom in ["14", "15"]:
                tien_giuong += to_decimal(r.get("THANH_TIEN", 0))
        if tien_giuong > Decimal("0"):
            r115_violations.append(RuleViolation(
                standard="4750", rule_code="115", rule_name="Hồ sơ khám bệnh có tiền giường",
                xml_table="XML3", field_name="THANH_TIEN", actual_value=str(tien_giuong),
                expected_condition="Khám bệnh (MA_LOAI_KCB=1) không được phát sinh tiền giường",
                message=f"Hồ sơ khám bệnh phát sinh tiền giường ({tien_giuong})."
            ))
    results.append(RuleResult(rule_code="115", standard="4750", rule_name="Hồ sơ khám bệnh có tiền giường",
                              status=RuleStatus.VIOLATED if r115_violations else RuleStatus.PASSED, violations=r115_violations))

    return results
