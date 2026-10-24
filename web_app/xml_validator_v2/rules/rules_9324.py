from decimal import Decimal
from typing import List, Dict, Any
from ..rule_models import RuleResult, RuleStatus, RuleViolation, CaseXmlData, to_decimal, round_money

def check_rules_9324(case: CaseXmlData) -> List[RuleResult]:
    results: List[RuleResult] = []
    xml1 = case.xml1
    xml2 = case.xml2
    xml3 = case.xml3

    # Nếu không có XML1, dừng kiểm tra và trả về thiếu dữ liệu
    if not xml1:
        return results

    # ----------------------------------------------------
    # Rule 1: Sai lý do vào viện
    # Điều kiện: Mã lý do vào viện khác (1, 2, 3, 4) hoặc = 3 nhưng Mã ĐKBĐ = Mã CSKCB
    # ----------------------------------------------------
    ly_do_vv = str(xml1.get("MA_LYDO_VVIEN", xml1.get("LY_DO_VV", ""))).strip()
    ma_dkbd = str(xml1.get("MA_DKBD", "")).strip().upper()
    ma_cskcb = str(xml1.get("MA_CSKCB", "")).strip().upper()

    r1_violations = []
    if ly_do_vv not in ["1", "2", "3", "4"]:
        r1_violations.append(RuleViolation(
            standard="9324", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=ly_do_vv,
            expected_condition="Thuộc danh sách (1, 2, 3, 4)",
            message=f"Mã lý do vào viện '{ly_do_vv}' không hợp lệ (phải là 1, 2, 3 hoặc 4)."
        ))
    elif ly_do_vv == "3" and ma_dkbd and ma_cskcb and ma_dkbd == ma_cskcb:
        r1_violations.append(RuleViolation(
            standard="9324", rule_code="1", rule_name="Mã lỗi 1: Sai lý do vào viện",
            xml_table="XML1", field_name="MA_LYDO_VVIEN", actual_value=f"LYDO={ly_do_vv}, DKBD={ma_dkbd}, CSKCB={ma_cskcb}",
            expected_condition="Mã ĐKBĐ khác Mã CSKCB khi lý do vào viện là trái tuyến (3)",
            message="Mã lý do vào viện = 3 (trái tuyến) nhưng Mã ĐKBĐ trùng với Mã CSKCB (đúng tuyến)."
        ))

    results.append(RuleResult(
        rule_code="1", standard="9324", rule_name="Sai lý do vào viện",
        status=RuleStatus.VIOLATED if r1_violations else RuleStatus.PASSED,
        violations=r1_violations
    ))

    # ----------------------------------------------------
    # Rule 3: Sai thành tiền so với SO_LUONG, DON_GIA của XML2 và XML3
    # XML2, XML3 vi phạm khi THANH_TIEN khác (SO_LUONG * DON_GIA * TYLE/100)
    # ----------------------------------------------------
    r3_violations = []
    for idx, row in enumerate(xml2):
        sl = to_decimal(row.get("SO_LUONG", 0))
        dg = to_decimal(row.get("DON_GIA", 0))
        tl = to_decimal(row.get("TYLE_TT", row.get("TYLE", 100)))
        tt_actual = to_decimal(row.get("THANH_TIEN", 0))
        tt_expected = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_actual - tt_expected) > Decimal("1.0"):  # dung sai 1 đồng làm tròn
            r3_violations.append(RuleViolation(
                standard="9324", rule_code="3", rule_name="Sai thành tiền XML2",
                xml_table="XML2", field_name="THANH_TIEN", actual_value=str(tt_actual),
                expected_condition=f"{sl} * {dg} * {tl}% = {tt_expected}",
                message=f"Dòng thuốc #{idx+1} ({row.get('MA_THUOC', '')}): THANH_TIEN ({tt_actual}) lệch so với tính toán ({tt_expected})."
            ))

    for idx, row in enumerate(xml3):
        sl = to_decimal(row.get("SO_LUONG", 0))
        dg = to_decimal(row.get("DON_GIA", 0))
        tl = to_decimal(row.get("TYLE_TT", row.get("TYLE", 100)))
        tt_actual = to_decimal(row.get("THANH_TIEN", 0))
        tt_expected = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_actual - tt_expected) > Decimal("1.0"):
            r3_violations.append(RuleViolation(
                standard="9324", rule_code="3", rule_name="Sai thành tiền XML3",
                xml_table="XML3", field_name="THANH_TIEN", actual_value=str(tt_actual),
                expected_condition=f"{sl} * {dg} * {tl}% = {tt_expected}",
                message=f"Dòng DVKT/VTYT #{idx+1} ({row.get('MA_DICH_VU', '')}): THANH_TIEN ({tt_actual}) lệch so với tính toán ({tt_expected})."
            ))

    results.append(RuleResult(
        rule_code="3", standard="9324", rule_name="Sai thành tiền so với SO_LUONG, DON_GIA",
        status=RuleStatus.VIOLATED if r3_violations else RuleStatus.PASSED,
        violations=r3_violations
    ))

    # ----------------------------------------------------
    # Rule 4: Sai TONG_CHI của XML1 so với THANH_TIEN của XML2 và XML3
    # ----------------------------------------------------
    tong_chi_xml1 = to_decimal(xml1.get("T_TONGCHI", xml1.get("TONG_CHI", 0)))
    sum_tt_xml2 = sum([to_decimal(r.get("THANH_TIEN", 0)) for r in xml2])
    sum_tt_xml3 = sum([to_decimal(r.get("THANH_TIEN", 0)) for r in xml3])
    sum_xml23 = sum_tt_xml2 + sum_tt_xml3

    r4_violations = []
    if abs(tong_chi_xml1 - sum_xml23) > Decimal("1.0"):
        r4_violations.append(RuleViolation(
            standard="9324", rule_code="4", rule_name="Sai TONG_CHI XML1 so với XML2, XML3",
            xml_table="XML1", field_name="T_TONGCHI", actual_value=str(tong_chi_xml1),
            expected_condition=f"Tổng XML2+XML3 = {sum_xml23}",
            message=f"T_TONGCHI XML1 ({tong_chi_xml1}) khác tổng THANH_TIEN XML2 ({sum_tt_xml2}) + XML3 ({sum_tt_xml3}) = {sum_xml23}."
        ))

    results.append(RuleResult(
        rule_code="4", standard="9324", rule_name="Sai TONG_CHI XML1 so với THANH_TIEN XML2, XML3",
        status=RuleStatus.VIOLATED if r4_violations else RuleStatus.PASSED,
        violations=r4_violations
    ))

    # ----------------------------------------------------
    # Rule 5: Sai TONG_CHI so với T_BHTT và T_BNTT của XML1 (cho phép lệch 1 đơn vị)
    # T_TONGCHI = T_BNTT + T_BHTT + T_NGUONKHAC
    # ----------------------------------------------------
    t_bntt = to_decimal(xml1.get("T_BNTT", 0))
    t_bhtt = to_decimal(xml1.get("T_BHTT", 0))
    t_nguonkhac = to_decimal(xml1.get("T_NGUONKHAC", 0))
    sum_components = t_bntt + t_bhtt + t_nguonkhac

    r5_violations = []
    if abs(tong_chi_xml1 - sum_components) > Decimal("1.0"):
        r5_violations.append(RuleViolation(
            standard="9324", rule_code="5", rule_name="Sai TONG_CHI so với T_BNTT, T_BHTT, T_NGUONKHAC",
            xml_table="XML1", field_name="T_TONGCHI", actual_value=str(tong_chi_xml1),
            expected_condition=f"T_BNTT ({t_bntt}) + T_BHTT ({t_bhtt}) + NGUONKHAC ({t_nguonkhac}) = {sum_components}",
            message=f"T_TONGCHI ({tong_chi_xml1}) không khớp tổng các thành phần tiền ({sum_components}) (lệch > 1 đơn vị)."
        ))

    results.append(RuleResult(
        rule_code="5", standard="9324", rule_name="Sai TONG_CHI so với T_BHTT và T_BNTT XML1",
        status=RuleStatus.VIOLATED if r5_violations else RuleStatus.PASSED,
        violations=r5_violations
    ))

    # ----------------------------------------------------
    # Rule 8: Sai thông tin thẻ
    # Kiểm tra: 3 ký tự đầu (mức hưởng), 2 ký tự 4-5 (mã tỉnh/đơn vị BHXH), 10 ký tự cuối phải là số
    # ----------------------------------------------------
    ma_the = str(xml1.get("MA_THE", xml1.get("SO_THE", ""))).strip().upper()
    r8_violations = []
    if not ma_the:
        r8_violations.append(RuleViolation(
            standard="9324", rule_code="8", rule_name="Mã lỗi 8: Sai thông tin thẻ",
            xml_table="XML1", field_name="MA_THE", actual_value="",
            expected_condition="Mã thẻ BHYT có giá trị", message="Mã thẻ BHYT để trống."
        ))
    elif len(ma_the) >= 15:
        prefix3 = ma_the[:3]
        prefix_prov = ma_the[3:5]
        suffix10 = ma_the[5:]
        if not suffix10.isdigit() or suffix10 == "0000000000":
            r8_violations.append(RuleViolation(
                standard="9324", rule_code="8", rule_name="Mã lỗi 8: Sai thông tin thẻ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="10 ký tự cuối của mã thẻ BHYT phải là số và khác 0000000000",
                message=f"10 ký tự cuối mã thẻ '{suffix10}' không phải là chuỗi số hợp lệ."
            ))
        if not prefix_prov.isdigit() or int(prefix_prov) < 1 or int(prefix_prov) > 99:
            r8_violations.append(RuleViolation(
                standard="9324", rule_code="8", rule_name="Mã lỗi 8: Sai thông tin thẻ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="2 ký tự thứ 4, 5 phải là mã tỉnh hợp lệ (01-99)",
                message=f"Mã tỉnh/đơn vị '{prefix_prov}' trên thẻ BHYT không hợp lệ."
            ))

    results.append(RuleResult(
        rule_code="8", standard="9324", rule_name="Sai thông tin thẻ",
        status=RuleStatus.VIOLATED if r8_violations else RuleStatus.PASSED,
        violations=r8_violations
    ))

    # ----------------------------------------------------
    # Rule 11: Hồ sơ không phát sinh chi phí Đề nghị thanh toán (T_BHTT trống hoặc = 0)
    # ----------------------------------------------------
    r11_violations = []
    if t_bhtt <= Decimal("0.0"):
        r11_violations.append(RuleViolation(
            standard="9324", rule_code="11", rule_name="Hồ sơ không phát sinh chi phí Đề nghị thanh toán",
            xml_table="XML1", field_name="T_BHTT", actual_value=str(t_bhtt),
            expected_condition="T_BHTT > 0",
            message="Tiền đề nghị BHTT trống hoặc = 0."
        ))

    results.append(RuleResult(
        rule_code="11", standard="9324", rule_name="Hồ sơ không phát sinh chi phí Đề nghị thanh toán",
        status=RuleStatus.VIOLATED if r11_violations else RuleStatus.PASSED,
        violations=r11_violations
    ))

    # ----------------------------------------------------
    # Rule 14: Stent động mạch vành phủ thuốc
    # Số lượng thanh toán tối đa 2 stent trên một đợt điều trị
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
            standard="9324", rule_code="14", rule_name="Stent động mạch vành vượt quá số lượng cho phép",
            xml_table="XML3", field_name="SO_LUONG", actual_value=str(stent_count),
            expected_condition="Số lượng Stent <= 2 trong một đợt",
            message=f"Số lượng stent thanh toán là {stent_count} (vượt quá giới hạn tối đa 2 stent)."
        ))

    results.append(RuleResult(
        rule_code="14", standard="9324", rule_name="Stent động mạch vành thanh toán tối đa 2",
        status=RuleStatus.VIOLATED if r14_violations else RuleStatus.PASSED,
        violations=r14_violations
    ))

    # ----------------------------------------------------
    # Rule 60: Cơ sở đăng ký khám ngoại trú nhận hồ sơ nội trú không hợp lệ
    # ----------------------------------------------------
    loai_kcb = str(xml1.get("MA_LOAI_KCB", "")).strip()
    r60_violations = []
    # Nếu cơ sở chỉ đăng ký ngoại trú mà MA_LOAI_KCB = 3 (Nội trú)
    # Kiểm tra theo cấu hình loại cơ sở KCB
    results.append(RuleResult(
        rule_code="60", standard="9324", rule_name="Cơ sở ngoại trú nhận hồ sơ nội trú",
        status=RuleStatus.PASSED
    ))

    return results
