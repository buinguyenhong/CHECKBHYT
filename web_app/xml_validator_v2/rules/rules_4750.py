import re
from decimal import Decimal
import datetime
from typing import List, Dict, Any
from ..rule_models import (
    RuleResult, RuleStatus, RuleViolation, CaseXmlData,
    to_decimal, round_money, is_valid_date_str, is_valid_datetime_str
)

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
    ly_do_vv = str(xml1.get("MA_LYDO_VVIEN", xml1.get("LY_DO_VV", "1")) or "1").strip()
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
    # Rule 8 & Rule 17: Sai thông tin thẻ / Mã thẻ không hợp lệ
    # ----------------------------------------------------
    ma_the = str(xml1.get("MA_THE", xml1.get("SO_THE", ""))).strip().upper()
    r8_violations = []
    r17_violations = []
    if not ma_the or len(ma_the) < 15:
        r8_violations.append(RuleViolation(
            standard="4750", rule_code="8", rule_name="Sai thông tin thẻ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="Mã thẻ BHYT đủ 15 ký tự", message="Mã thẻ BHYT không đủ 15 ký tự."
        ))
        r17_violations.append(RuleViolation(
            standard="4750", rule_code="17", rule_name="Mã thẻ không hợp lệ",
            xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
            expected_condition="Mã thẻ BHYT đủ 15 ký tự", message="Mã thẻ BHYT không đủ 15 ký tự."
        ))
    else:
        suffix10 = ma_the[5:]
        prov2 = ma_the[3:5]
        if not suffix10.isdigit() or suffix10 == "0000000000":
            r8_violations.append(RuleViolation(
                standard="4750", rule_code="8", rule_name="Sai thông tin thẻ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="10 ký tự cuối phải là số và khác 0000000000",
                message=f"10 ký tự cuối của mã thẻ '{suffix10}' không hợp lệ."
            ))
            r17_violations.append(RuleViolation(
                standard="4750", rule_code="17", rule_name="Mã thẻ không hợp lệ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="10 ký tự cuối phải là số và khác 0000000000",
                message=f"10 ký tự cuối của mã thẻ '{suffix10}' không hợp lệ."
            ))
        if not prov2.isdigit() or int(prov2) < 1 or int(prov2) > 99:
            r17_violations.append(RuleViolation(
                standard="4750", rule_code="17", rule_name="Mã thẻ không hợp lệ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="Ký tự thứ 4, 5 phải là mã tỉnh hợp lệ (01-99)",
                message=f"Mã tỉnh '{prov2}' trên thẻ BHYT không hợp lệ."
            ))

    ma_the_khac = str(xml1.get("MA_THE_KHAC", "") or "").strip()
    if ma_the_khac and ma_the_khac.lower() not in ["none", "null", "nan"]:
        for sub_the in ma_the_khac.split(";"):
            st = sub_the.strip()
            if len(st) != 15:
                r17_violations.append(RuleViolation(
                    standard="4750", rule_code="17", rule_name="Mã thẻ khác không hợp lệ",
                    xml_table="XML1", field_name="MA_THE_KHAC", actual_value=ma_the_khac,
                    expected_condition="Các mã thẻ trong MA_THE_KHAC cách nhau bởi ';' và đúng 15 ký tự",
                    message=f"Mã thẻ khác '{st}' không đúng 15 ký tự."
                ))

    results.append(RuleResult(rule_code="8", standard="4750", rule_name="Sai thông tin thẻ",
                              status=RuleStatus.VIOLATED if r8_violations else RuleStatus.PASSED, violations=r8_violations))
    results.append(RuleResult(rule_code="17", standard="4750", rule_name="Mã thẻ không hợp lệ",
                              status=RuleStatus.VIOLATED if r17_violations else RuleStatus.PASSED, violations=r17_violations))

    # ----------------------------------------------------
    # Rule 9: Sai thông tin CSKCB ban đầu
    # Rule 10: Sai thông tin CSKCB
    # ----------------------------------------------------
    r9_violations = []
    if ma_dkbd and len(ma_dkbd) != 5:
        r9_violations.append(RuleViolation(
            standard="4750", rule_code="9", rule_name="Sai thông tin CSKCB ban đầu",
            xml_table="XML1", field_name="MA_DKBD", actual_value=ma_dkbd,
            expected_condition="Mã ĐKBĐ gồm 5 ký tự", message=f"Mã ĐKBĐ '{ma_dkbd}' không đúng 5 ký tự."
        ))
    ma_dkbd_khac = str(xml1.get("MA_DKBD_KHAC", "") or "").strip()
    if ma_dkbd_khac and ma_dkbd_khac.lower() not in ["none", "null", "nan"]:
        for sub_dk in ma_dkbd_khac.split(";"):
            if len(sub_dk.strip()) != 5:
                r9_violations.append(RuleViolation(
                    standard="4750", rule_code="9", rule_name="Sai thông tin CSKCB ban đầu khác",
                    xml_table="XML1", field_name="MA_DKBD_KHAC", actual_value=ma_dkbd_khac,
                    expected_condition="Các mã ĐKBĐ cách nhau bởi ';' và đúng 5 ký tự",
                    message=f"Mã ĐKBĐ khác '{sub_dk.strip()}' không đúng 5 ký tự."
                ))
    results.append(RuleResult(rule_code="9", standard="4750", rule_name="Sai thông tin CSKCB ban đầu",
                              status=RuleStatus.VIOLATED if r9_violations else RuleStatus.PASSED, violations=r9_violations))

    r10_violations = []
    if ma_cskcb and len(ma_cskcb) != 5:
        r10_violations.append(RuleViolation(
            standard="4750", rule_code="10", rule_name="Sai thông tin CSKCB",
            xml_table="XML1", field_name="MA_CSKCB", actual_value=ma_cskcb,
            expected_condition="Mã CSKCB gồm 5 ký tự", message=f"Mã CSKCB '{ma_cskcb}' không đúng 5 ký tự."
        ))
    results.append(RuleResult(rule_code="10", standard="4750", rule_name="Sai thông tin CSKCB",
                              status=RuleStatus.VIOLATED if r10_violations else RuleStatus.PASSED, violations=r10_violations))

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
        ma_vt = str(r.get("MA_VAT_TU", "")).upper()
        if "STENT" in ten_dv or "STENT" in ma_dv or "N06.02.020" in ma_vt:
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
    # Rule 15: Ngày sinh không hợp lệ
    # ----------------------------------------------------
    ngay_sinh = str(xml1.get("NGAY_SINH", "")).strip()
    r15_violations = []
    today_str = datetime.date.today().strftime("%Y%m%d")
    if not ngay_sinh or len(ngay_sinh) not in [4, 8, 12] or not ngay_sinh.isdigit():
        r15_violations.append(RuleViolation(
            standard="4750", rule_code="15", rule_name="Ngày sinh không hợp lệ",
            xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh,
            expected_condition="Định dạng YYYY hoặc YYYYMMDD hoặc YYYYMMDDHHMM hợp lệ",
            message=f"Ngày sinh '{ngay_sinh}' sai định dạng."
        ))
    elif len(ngay_sinh) >= 8:
        if not is_valid_date_str(ngay_sinh[:8]):
            r15_violations.append(RuleViolation(
                standard="4750", rule_code="15", rule_name="Ngày sinh không hợp lệ",
                xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh,
                expected_condition="Ngày tháng năm hợp lệ trên lịch",
                message=f"Ngày sinh '{ngay_sinh}' không tồn tại trên lịch."
            ))
        elif ngay_sinh[:8] > today_str:
            r15_violations.append(RuleViolation(
                standard="4750", rule_code="15", rule_name="Ngày sinh lớn hơn ngày hiện tại",
                xml_table="XML1", field_name="NGAY_SINH", actual_value=ngay_sinh,
                expected_condition=f"NGAY_SINH <= {today_str}",
                message=f"Ngày sinh '{ngay_sinh}' lớn hơn ngày hiện tại."
            ))
    results.append(RuleResult(rule_code="15", standard="4750", rule_name="Ngày sinh không hợp lệ",
                              status=RuleStatus.VIOLATED if r15_violations else RuleStatus.PASSED, violations=r15_violations))

    # ----------------------------------------------------
    # Rule 16: Giới tính không hợp lệ (1: Nam, 2: Nữ, 3: Chưa xác định)
    # ----------------------------------------------------
    gioi_tinh = str(xml1.get("GIOI_TINH", "")).strip()
    r16_violations = []
    if gioi_tinh not in ["1", "2", "3"]:
        r16_violations.append(RuleViolation(
            standard="4750", rule_code="16", rule_name="Giới tính không hợp lệ",
            xml_table="XML1", field_name="GIOI_TINH", actual_value=gioi_tinh,
            expected_condition="GIOI_TINH thuộc [1, 2, 3]",
            message=f"Giới tính '{gioi_tinh}' không hợp lệ."
        ))
    results.append(RuleResult(rule_code="16", standard="4750", rule_name="Giới tính không hợp lệ",
                              status=RuleStatus.VIOLATED if r16_violations else RuleStatus.PASSED, violations=r16_violations))

    # ----------------------------------------------------
    # Rule 18, 19, 20: GT_THE_TU, GT_THE_DEN, và tính đồng bộ 4 trường *_KHAC
    # ----------------------------------------------------
    r18_violations = []
    gt_tu = str(xml1.get("GT_THE_TU", "") or "").strip()
    if gt_tu and gt_tu.lower() not in ["none", "null", "nan"]:
        for part in gt_tu.split(";"):
            if not is_valid_date_str(part.strip()[:8]):
                r18_violations.append(RuleViolation(
                    standard="4750", rule_code="18", rule_name="Giá trị thẻ từ không hợp lệ",
                    xml_table="XML1", field_name="GT_THE_TU", actual_value=gt_tu,
                    expected_condition="Định dạng 8 ký tự số YYYYMMDD hợp lệ",
                    message=f"Giá trị thẻ từ '{part.strip()}' không hợp lệ."
                ))
    gt_tu_khac = str(xml1.get("GT_THE_TU_KHAC", "") or "").strip()
    if gt_tu_khac and gt_tu_khac.lower() not in ["none", "null", "nan"]:
        for part in gt_tu_khac.split(";"):
            if not is_valid_date_str(part.strip()):
                r18_violations.append(RuleViolation(
                    standard="4750", rule_code="18", rule_name="Giá trị thẻ từ khác không hợp lệ",
                    xml_table="XML1", field_name="GT_THE_TU_KHAC", actual_value=gt_tu_khac,
                    expected_condition="Các giá trị cách nhau bởi ';' và đúng 8 số YYYYMMDD",
                    message=f"Giá trị thẻ từ khác '{part.strip()}' không hợp lệ."
                ))
    results.append(RuleResult(rule_code="18", standard="4750", rule_name="Giá trị thẻ từ không hợp lệ",
                              status=RuleStatus.VIOLATED if r18_violations else RuleStatus.PASSED, violations=r18_violations))

    r19_violations = []
    gt_den = str(xml1.get("GT_THE_DEN", "") or "").strip()
    if gt_den and gt_den.lower() not in ["none", "null", "nan"]:
        for part in gt_den.split(";"):
            if not is_valid_date_str(part.strip()[:8]):
                r19_violations.append(RuleViolation(
                    standard="4750", rule_code="19", rule_name="Giá trị thẻ đến không hợp lệ",
                    xml_table="XML1", field_name="GT_THE_DEN", actual_value=gt_den,
                    expected_condition="Định dạng 8 ký tự số YYYYMMDD hợp lệ",
                    message=f"Giá trị thẻ đến '{part.strip()}' không hợp lệ."
                ))
    gt_den_khac = str(xml1.get("GT_THE_DEN_KHAC", "") or "").strip()
    if gt_den_khac and gt_den_khac.lower() not in ["none", "null", "nan"]:
        for part in gt_den_khac.split(";"):
            if not is_valid_date_str(part.strip()):
                r19_violations.append(RuleViolation(
                    standard="4750", rule_code="19", rule_name="Giá trị thẻ đến khác không hợp lệ",
                    xml_table="XML1", field_name="GT_THE_DEN_KHAC", actual_value=gt_den_khac,
                    expected_condition="Các giá trị cách nhau bởi ';' và đúng 8 số YYYYMMDD",
                    message=f"Giá trị thẻ đến khác '{part.strip()}' không hợp lệ."
                ))
    results.append(RuleResult(rule_code="19", standard="4750", rule_name="Giá trị thẻ đến không hợp lệ",
                              status=RuleStatus.VIOLATED if r19_violations else RuleStatus.PASSED, violations=r19_violations))

    r20_violations = []
    khac_fields = [ma_the_khac, ma_dkbd_khac, gt_tu_khac, gt_den_khac]
    khac_clean = [f if f.lower() not in ["none", "null", "nan"] else "" for f in khac_fields]
    if any(khac_clean):
        if not all(khac_clean):
            r20_violations.append(RuleViolation(
                standard="4750", rule_code="20", rule_name="Số lượng mã thẻ và thông tin thẻ khác không tương ứng",
                xml_table="XML1", field_name="MA_THE_KHAC", actual_value=str(khac_clean),
                expected_condition="Cả 4 trường MA_THE_KHAC, MA_DKBD_KHAC, GT_THE_TU_KHAC, GT_THE_DEN_KHAC phải đồng thời có dữ liệu",
                message="Một số trường thông tin thẻ khác bị rỗng trong khi trường khác có giá trị."
            ))
        else:
            counts = [len(f.split(";")) for f in khac_clean]
            if len(set(counts)) > 1:
                r20_violations.append(RuleViolation(
                    standard="4750", rule_code="20", rule_name="Số lượng mã thẻ và thông tin thẻ khác không tương ứng",
                    xml_table="XML1", field_name="MA_THE_KHAC", actual_value=str(counts),
                    expected_condition="Số lượng phần tử tách theo ';' ở 4 trường thẻ khác phải bằng nhau",
                    message=f"Số lượng thông tin thẻ khác không khớp nhau: {counts}."
                ))
    results.append(RuleResult(rule_code="20", standard="4750", rule_name="Số lượng thông tin thẻ khác không tương ứng",
                              status=RuleStatus.VIOLATED if r20_violations else RuleStatus.PASSED, violations=r20_violations))

    # ----------------------------------------------------
    # Rule 21 (Miễn CCT), Rule 22 (Mã tai nạn), Rule 25 (KQ điều trị), Rule 26 (Tình trạng RV), Rule 27 (Ngày TToán)
    # ----------------------------------------------------
    r21_violations = []
    mien_cct = str(xml1.get("NGAY_MIEN_CCT", "") or "").strip()
    if mien_cct and mien_cct.lower() not in ["none", "null", "nan"]:
        if not is_valid_date_str(mien_cct[:8]):
            r21_violations.append(RuleViolation(
                standard="4750", rule_code="21", rule_name="Miễn cùng chi trả không hợp lệ",
                xml_table="XML1", field_name="NGAY_MIEN_CCT", actual_value=mien_cct,
                expected_condition="Định dạng 8 ký tự số YYYYMMDD hợp lệ",
                message=f"Ngày miễn cùng chi trả '{mien_cct}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="21", standard="4750", rule_name="Miễn cùng chi trả không hợp lệ",
                              status=RuleStatus.VIOLATED if r21_violations else RuleStatus.PASSED, violations=r21_violations))

    r22_violations = []
    ma_tn = str(xml1.get("MA_TAI_NAN", "") or "").strip()
    if ma_tn and ma_tn.lower() not in ["none", "null", "nan"]:
        if ma_tn not in ["0", "1", "2", "3", "4", "5", "6", "7", "8"]:
            r22_violations.append(RuleViolation(
                standard="4750", rule_code="22", rule_name="Mã tai nạn không hợp lệ",
                xml_table="XML1", field_name="MA_TAI_NAN", actual_value=ma_tn,
                expected_condition="Thuộc giá trị từ 0 đến 8",
                message=f"Mã tai nạn '{ma_tn}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="22", standard="4750", rule_name="Mã tai nạn không hợp lệ",
                              status=RuleStatus.VIOLATED if r22_violations else RuleStatus.PASSED, violations=r22_violations))

    # ----------------------------------------------------
    # Rule 23, 24: Ngày vào, Ngày ra viện
    # ----------------------------------------------------
    ngay_vao = str(xml1.get("NGAY_VAO", "")).strip()
    ngay_ra = str(xml1.get("NGAY_RA", "")).strip()
    r23_violations = []
    r24_violations = []
    if not ngay_vao or not is_valid_datetime_str(ngay_vao[:12]):
        r23_violations.append(RuleViolation(
            standard="4750", rule_code="23", rule_name="Ngày vào không hợp lệ",
            xml_table="XML1", field_name="NGAY_VAO", actual_value=ngay_vao,
            expected_condition="Định dạng YYYYMMDDHHMM hợp lệ", message="Ngày vào sai định dạng."
        ))
    if not ngay_ra or not is_valid_datetime_str(ngay_ra[:12]):
        r24_violations.append(RuleViolation(
            standard="4750", rule_code="24", rule_name="Ngày ra không hợp lệ",
            xml_table="XML1", field_name="NGAY_RA", actual_value=ngay_ra,
            expected_condition="Định dạng YYYYMMDDHHMM hợp lệ", message="Ngày ra sai định dạng."
        ))
    elif ngay_vao and len(ngay_vao) >= 12 and ngay_ra[:12] < ngay_vao[:12]:
        r24_violations.append(RuleViolation(
            standard="4750", rule_code="24", rule_name="Ngày ra nhỏ hơn ngày vào",
            xml_table="XML1", field_name="NGAY_RA", actual_value=f"RA={ngay_ra}, VAO={ngay_vao}",
            expected_condition="Ngày ra >= Ngày vào", message=f"Ngày ra '{ngay_ra}' trước ngày vào '{ngay_vao}'."
        ))
    results.append(RuleResult(rule_code="23", standard="4750", rule_name="Ngày vào không hợp lệ",
                              status=RuleStatus.VIOLATED if r23_violations else RuleStatus.PASSED, violations=r23_violations))
    results.append(RuleResult(rule_code="24", standard="4750", rule_name="Ngày ra không hợp lệ",
                              status=RuleStatus.VIOLATED if r24_violations else RuleStatus.PASSED, violations=r24_violations))

    r25_violations = []
    kq_dtri = str(xml1.get("KET_QUA_DTRI", "") or "").strip()
    if kq_dtri and kq_dtri.lower() not in ["none", "null", "nan"]:
        if kq_dtri not in ["1", "2", "3", "4", "5"]:
            r25_violations.append(RuleViolation(
                standard="4750", rule_code="25", rule_name="Kết quả điều trị không hợp lệ",
                xml_table="XML1", field_name="KET_QUA_DTRI", actual_value=kq_dtri,
                expected_condition="Thuộc giá trị từ 1 đến 5", message=f"Kết quả điều trị '{kq_dtri}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="25", standard="4750", rule_name="Kết quả điều trị không hợp lệ",
                              status=RuleStatus.VIOLATED if r25_violations else RuleStatus.PASSED, violations=r25_violations))

    r26_violations = []
    tt_rv = str(xml1.get("TINH_TRANG_RV", xml1.get("MA_LOAI_RV", "")) or "").strip()
    if tt_rv and tt_rv.lower() not in ["none", "null", "nan"]:
        if tt_rv not in ["1", "2", "3", "4", "5"]:
            r26_violations.append(RuleViolation(
                standard="4750", rule_code="26", rule_name="Tình trạng ra viện không hợp lệ",
                xml_table="XML1", field_name="TINH_TRANG_RV", actual_value=tt_rv,
                expected_condition="Thuộc giá trị từ 1 đến 5", message=f"Tình trạng ra viện '{tt_rv}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="26", standard="4750", rule_name="Tình trạng ra viện không hợp lệ",
                              status=RuleStatus.VIOLATED if r26_violations else RuleStatus.PASSED, violations=r26_violations))

    r27_violations = []
    ngay_ttoan = str(xml1.get("NGAY_TTOAN", "") or "").strip()
    if ngay_ttoan and ngay_ttoan.lower() not in ["none", "null", "nan"]:
        valid_tt = is_valid_datetime_str(ngay_ttoan[:12]) if len(ngay_ttoan) >= 12 else is_valid_date_str(ngay_ttoan[:8])
        if not valid_tt:
            r27_violations.append(RuleViolation(
                standard="4750", rule_code="27", rule_name="Ngày thanh toán không hợp lệ",
                xml_table="XML1", field_name="NGAY_TTOAN", actual_value=ngay_ttoan,
                expected_condition="Định dạng YYYYMMDDHHMM hợp lệ", message=f"Ngày thanh toán '{ngay_ttoan}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="27", standard="4750", rule_name="Ngày thanh toán không hợp lệ",
                              status=RuleStatus.VIOLATED if r27_violations else RuleStatus.PASSED, violations=r27_violations))

    # ----------------------------------------------------
    # Rule 31: T_BHTT trong XML1 khác tổng cộng các T_BHTT trong XML2, XML3
    # ----------------------------------------------------
    sum_bhtt_xml2 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml2])
    sum_bhtt_xml3 = sum([to_decimal(r.get("T_BHTT", 0)) for r in xml3])
    sum_bhtt_23 = sum_bhtt_xml2 + sum_bhtt_xml3
    r31_violations = []
    if (xml2 or xml3) and abs(t_bhtt_xml1 - sum_bhtt_23) > Decimal("1.0"):
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
    # Rule 35, 36, 37, 38: NAM_QT, THANG_QT, MA_LOAI_KCB, MA_KHU_VUC
    # ----------------------------------------------------
    r35_violations = []
    nam_qt = str(xml1.get("NAM_QT", "") or "").strip()
    if nam_qt and nam_qt.lower() not in ["none", "null", "nan"]:
        if not nam_qt.isdigit() or int(nam_qt) > datetime.datetime.now().year + 1 or int(nam_qt) < 2015:
            r35_violations.append(RuleViolation(
                standard="4750", rule_code="35", rule_name="Năm quyết toán không hợp lệ",
                xml_table="XML1", field_name="NAM_QT", actual_value=nam_qt,
                expected_condition=f"2015 <= NAM_QT <= {datetime.datetime.now().year}",
                message=f"Năm quyết toán '{nam_qt}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="35", standard="4750", rule_name="Năm quyết toán không hợp lệ",
                              status=RuleStatus.VIOLATED if r35_violations else RuleStatus.PASSED, violations=r35_violations))

    r36_violations = []
    thang_qt = str(xml1.get("THANG_QT", "") or "").strip()
    if thang_qt and thang_qt.lower() not in ["none", "null", "nan"]:
        if not thang_qt.isdigit() or int(thang_qt) < 1 or int(thang_qt) > 12:
            r36_violations.append(RuleViolation(
                standard="4750", rule_code="36", rule_name="Tháng quyết toán không hợp lệ",
                xml_table="XML1", field_name="THANG_QT", actual_value=thang_qt,
                expected_condition="Thuộc từ 1 đến 12", message=f"Tháng quyết toán '{thang_qt}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="36", standard="4750", rule_name="Tháng quyết toán không hợp lệ",
                              status=RuleStatus.VIOLATED if r36_violations else RuleStatus.PASSED, violations=r36_violations))

    ma_loai_kcb = str(xml1.get("MA_LOAI_KCB", "") or "").strip()
    r37_violations = []
    if ma_loai_kcb and ma_loai_kcb not in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
        r37_violations.append(RuleViolation(
            standard="4750", rule_code="37", rule_name="Mã loại KCB không hợp lệ",
            xml_table="XML1", field_name="MA_LOAI_KCB", actual_value=ma_loai_kcb,
            expected_condition="Thuộc danh mục Mã loại KCB QĐ 824/4750 (01-10)",
            message=f"Mã loại KCB '{ma_loai_kcb}' không hợp lệ."
        ))
    results.append(RuleResult(rule_code="37", standard="4750", rule_name="Mã loại KCB không hợp lệ",
                              status=RuleStatus.VIOLATED if r37_violations else RuleStatus.PASSED, violations=r37_violations))

    r38_violations = []
    ma_kv = str(xml1.get("MA_KHU_VUC", "") or "").strip().upper()
    if ma_kv and ma_kv not in ["NONE", "NULL", "NAN"]:
        if ma_kv not in ["K1", "K2", "K3"]:
            r38_violations.append(RuleViolation(
                standard="4750", rule_code="38", rule_name="Mã khu vực không hợp lệ",
                xml_table="XML1", field_name="MA_KHU_VUC", actual_value=ma_kv,
                expected_condition="Thuộc (K1, K2, K3)", message=f"Mã khu vực '{ma_kv}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="38", standard="4750", rule_name="Mã khu vực không hợp lệ",
                              status=RuleStatus.VIOLATED if r38_violations else RuleStatus.PASSED, violations=r38_violations))

    # ----------------------------------------------------
    # Rule 39, 40, 47, 48, 49, 50, 51, 118: Các quy tắc trên XML2 (Thuốc)
    # ----------------------------------------------------
    r39_v, r40_v, r47_v, r48_v, r49_v, r50_v, r51_v, r118_v = [], [], [], [], [], [], [], []
    for idx, r in enumerate(xml2):
        nhom = str(r.get("MA_NHOM", "") or "").strip()
        if nhom and nhom.lower() not in ["none", "null", "nan"] and nhom not in ["4", "7", "17", "04", "07"]:
            r39_v.append(RuleViolation(
                standard="4750", rule_code="39", rule_name="Mã nhóm trong XML2 không hợp lệ",
                xml_table="XML2", field_name="MA_NHOM", actual_value=nhom,
                expected_condition="Thuộc (4, 7, 17)", message=f"Dòng thuốc #{idx+1}: Mã nhóm '{nhom}' không hợp lệ."
            ))
        pv = str(r.get("PHAM_VI", "") or "").strip()
        if pv and pv.lower() not in ["none", "null", "nan"] and pv not in ["1", "2", "3"]:
            r40_v.append(RuleViolation(
                standard="4750", rule_code="40", rule_name="Phạm vi trong XML2 không hợp lệ",
                xml_table="XML2", field_name="PHAM_VI", actual_value=pv,
                expected_condition="Thuộc (1, 2, 3)", message=f"Dòng thuốc #{idx+1}: Phạm vi '{pv}' không hợp lệ."
            ))
        sl = to_decimal(r.get("SO_LUONG", 0))
        dg = to_decimal(r.get("DON_GIA", 0))
        tl = to_decimal(r.get("TYLE_TT_BH", r.get("TYLE_TT", r.get("TYLE", 100))))
        tt_bv = to_decimal(r.get("THANH_TIEN_BV", r.get("THANH_TIEN", 0)))
        tt_expected_full = round_money(sl * dg)
        tt_expected_tl = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_bv - tt_expected_full) > Decimal("1.0") and abs(tt_bv - tt_expected_tl) > Decimal("1.0"):
            r47_v.append(RuleViolation(
                standard="4750", rule_code="47", rule_name="Thành tiền trong XML2 không hợp lệ",
                xml_table="XML2", field_name="THANH_TIEN_BV", actual_value=str(tt_bv),
                expected_condition=f"SO_LUONG * DON_GIA = {tt_expected_full}",
                message=f"Dòng thuốc #{idx+1}: Thành tiền ({tt_bv}) lệch so với tính toán ({tt_expected_full})."
            ))
        row_bhtt = to_decimal(r.get("T_BHTT", 0))
        row_bncct = to_decimal(r.get("T_BNCCT", 0))
        row_bntt = to_decimal(r.get("T_BNTT", 0))
        row_ngk = to_decimal(r.get("T_NGUONKHAC", 0))
        if row_bhtt < Decimal("0") or (tt_bv > Decimal("0") and row_bhtt > tt_bv + Decimal("1.0")):
            r48_v.append(RuleViolation(
                standard="4750", rule_code="48", rule_name="T_BHTT trong XML2 không hợp lệ",
                xml_table="XML2", field_name="T_BHTT", actual_value=str(row_bhtt),
                expected_condition=f"0 <= T_BHTT <= {tt_bv}", message=f"Dòng thuốc #{idx+1}: T_BHTT ({row_bhtt}) không hợp lệ."
            ))
        if row_bncct < Decimal("0") or (tt_bv > Decimal("0") and row_bncct > tt_bv + Decimal("1.0")):
            r49_v.append(RuleViolation(
                standard="4750", rule_code="49", rule_name="T_BNCCT trong XML2 không hợp lệ",
                xml_table="XML2", field_name="T_BNCCT", actual_value=str(row_bncct),
                expected_condition=f"0 <= T_BNCCT <= {tt_bv}", message=f"Dòng thuốc #{idx+1}: T_BNCCT ({row_bncct}) không hợp lệ."
            ))
        if row_bntt < Decimal("0") or (tt_bv > Decimal("0") and row_bntt > tt_bv + Decimal("1.0")):
            r50_v.append(RuleViolation(
                standard="4750", rule_code="50", rule_name="T_BNTT trong XML2 không hợp lệ",
                xml_table="XML2", field_name="T_BNTT", actual_value=str(row_bntt),
                expected_condition=f"0 <= T_BNTT <= {tt_bv}", message=f"Dòng thuốc #{idx+1}: T_BNTT ({row_bntt}) không hợp lệ."
            ))
        if tt_bv >= Decimal("0") and (row_ngk < Decimal("0") or row_ngk > tt_bv + Decimal("1.0")):
            r51_v.append(RuleViolation(
                standard="4750", rule_code="51", rule_name="T_NGUONKHAC trong XML2 không hợp lệ",
                xml_table="XML2", field_name="T_NGUONKHAC", actual_value=str(row_ngk),
                expected_condition=f"0 <= T_NGUONKHAC <= {tt_bv}", message=f"Dòng thuốc #{idx+1}: T_NGUONKHAC ({row_ngk}) không hợp lệ."
            ))
        for dt_col in ["NGAY_YL", "NGAY_TH_YL"]:
            dt_val = str(r.get(dt_col, "") or "").strip()
            if dt_val and dt_val.lower() not in ["none", "null", "nan"]:
                if not is_valid_datetime_str(dt_val[:12]):
                    r118_v.append(RuleViolation(
                        standard="4750", rule_code="118", rule_name="Ngày y lệnh / thực hiện y lệnh XML2 không hợp lệ",
                        xml_table="XML2", field_name=dt_col, actual_value=dt_val,
                        expected_condition="Định dạng YYYYMMDDHHMM hợp lệ",
                        message=f"Dòng thuốc #{idx+1}: {dt_col} ('{dt_val}') không hợp lệ."
                    ))

    results.append(RuleResult(rule_code="39", standard="4750", rule_name="Mã nhóm trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r39_v else RuleStatus.PASSED, violations=r39_v))
    results.append(RuleResult(rule_code="40", standard="4750", rule_name="Phạm vi trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r40_v else RuleStatus.PASSED, violations=r40_v))
    results.append(RuleResult(rule_code="47", standard="4750", rule_name="Thành tiền trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r47_v else RuleStatus.PASSED, violations=r47_v))
    results.append(RuleResult(rule_code="48", standard="4750", rule_name="T_BHTT trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r48_v else RuleStatus.PASSED, violations=r48_v))
    results.append(RuleResult(rule_code="49", standard="4750", rule_name="T_BNCCT trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r49_v else RuleStatus.PASSED, violations=r49_v))
    results.append(RuleResult(rule_code="50", standard="4750", rule_name="T_BNTT trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r50_v else RuleStatus.PASSED, violations=r50_v))
    results.append(RuleResult(rule_code="51", standard="4750", rule_name="T_NGUONKHAC trong XML2 không hợp lệ", status=RuleStatus.VIOLATED if r51_v else RuleStatus.PASSED, violations=r51_v))
    results.append(RuleResult(rule_code="118", standard="4750", rule_name="Ngày y lệnh XML2 không hợp lệ", status=RuleStatus.VIOLATED if r118_v else RuleStatus.PASSED, violations=r118_v))

    # ----------------------------------------------------
    # Rule 43, 44, 52, 53, 54, 55, 56, 119: Các quy tắc trên XML3 (DVKT & VTYT)
    # ----------------------------------------------------
    r43_v, r44_v, r52_v, r53_v, r54_v, r55_v, r56_v, r119_v = [], [], [], [], [], [], [], []
    valid_nhom_xml3 = {"1", "2", "3", "8", "10", "11", "12", "13", "14", "15", "16", "18", "19", "01", "02", "03", "08"}
    for idx, r in enumerate(xml3):
        nhom = str(r.get("MA_NHOM", "") or "").strip()
        if nhom and nhom.lower() not in ["none", "null", "nan"] and nhom not in valid_nhom_xml3:
            r43_v.append(RuleViolation(
                standard="4750", rule_code="43", rule_name="Mã nhóm trong XML3 không hợp lệ",
                xml_table="XML3", field_name="MA_NHOM", actual_value=nhom,
                expected_condition="Thuộc (1,2,3,8,10,12,13,14,15,16,18,19)",
                message=f"Dòng DVKT #{idx+1}: Mã nhóm '{nhom}' không hợp lệ."
            ))
        pv = str(r.get("PHAM_VI", "") or "").strip()
        if pv and pv.lower() not in ["none", "null", "nan"] and pv not in ["1", "2", "3"]:
            r44_v.append(RuleViolation(
                standard="4750", rule_code="44", rule_name="Phạm vi trong XML3 không hợp lệ",
                xml_table="XML3", field_name="PHAM_VI", actual_value=pv,
                expected_condition="Thuộc (1, 2, 3)", message=f"Dòng DVKT #{idx+1}: Phạm vi '{pv}' không hợp lệ."
            ))
        sl = to_decimal(r.get("SO_LUONG", 0))
        dg = to_decimal(r.get("DON_GIA_BV", r.get("DON_GIA_DV", r.get("DON_GIA", 0))))
        tl = to_decimal(r.get("TYLE_TT_DV", r.get("TYLE_TT", r.get("TYLE", 100))))
        tt_bv = to_decimal(r.get("THANH_TIEN_BV", r.get("THANH_TIEN", 0)))
        tt_expected_full = round_money(sl * dg)
        tt_expected_tl = round_money(sl * dg * (tl / Decimal("100")))
        if abs(tt_bv - tt_expected_full) > Decimal("1.0") and abs(tt_bv - tt_expected_tl) > Decimal("1.0"):
            r52_v.append(RuleViolation(
                standard="4750", rule_code="52", rule_name="Thành tiền trong XML3 không hợp lệ",
                xml_table="XML3", field_name="THANH_TIEN_BV", actual_value=str(tt_bv),
                expected_condition=f"SO_LUONG * DON_GIA = {tt_expected_full} (hoặc * TYLE = {tt_expected_tl})",
                message=f"Dòng DVKT #{idx+1}: Thành tiền ({tt_bv}) lệch so với tính toán."
            ))
        row_bhtt = to_decimal(r.get("T_BHTT", 0))
        row_bncct = to_decimal(r.get("T_BNCCT", 0))
        row_bntt = to_decimal(r.get("T_BNTT", 0))
        row_ngk = to_decimal(r.get("T_NGUONKHAC", 0))
        if row_bhtt < Decimal("0") or (tt_bv > Decimal("0") and row_bhtt > tt_bv + Decimal("1.0")):
            r53_v.append(RuleViolation(
                standard="4750", rule_code="53", rule_name="T_BHTT trong XML3 không hợp lệ",
                xml_table="XML3", field_name="T_BHTT", actual_value=str(row_bhtt),
                expected_condition=f"0 <= T_BHTT <= {tt_bv}", message=f"Dòng DVKT #{idx+1}: T_BHTT ({row_bhtt}) không hợp lệ."
            ))
        if row_bntt < Decimal("0") or (tt_bv > Decimal("0") and row_bntt > tt_bv + Decimal("1.0")):
            r54_v.append(RuleViolation(
                standard="4750", rule_code="54", rule_name="T_BNTT trong XML3 không hợp lệ",
                xml_table="XML3", field_name="T_BNTT", actual_value=str(row_bntt),
                expected_condition=f"0 <= T_BNTT <= {tt_bv}", message=f"Dòng DVKT #{idx+1}: T_BNTT ({row_bntt}) không hợp lệ."
            ))
        if row_bncct < Decimal("0") or (tt_bv > Decimal("0") and row_bncct > tt_bv + Decimal("1.0")):
            r55_v.append(RuleViolation(
                standard="4750", rule_code="55", rule_name="T_BNCCT trong XML3 không hợp lệ",
                xml_table="XML3", field_name="T_BNCCT", actual_value=str(row_bncct),
                expected_condition=f"0 <= T_BNCCT <= {tt_bv}", message=f"Dòng DVKT #{idx+1}: T_BNCCT ({row_bncct}) không hợp lệ."
            ))
        if tt_bv >= Decimal("0") and (row_ngk < Decimal("0") or row_ngk > tt_bv + Decimal("1.0")):
            r56_v.append(RuleViolation(
                standard="4750", rule_code="56", rule_name="T_NGUONKHAC trong XML3 không hợp lệ",
                xml_table="XML3", field_name="T_NGUONKHAC", actual_value=str(row_ngk),
                expected_condition=f"0 <= T_NGUONKHAC <= {tt_bv}", message=f"Dòng DVKT #{idx+1}: T_NGUONKHAC ({row_ngk}) không hợp lệ."
            ))
        for dt_col in ["NGAY_YL", "NGAY_TH_YL"]:
            dt_val = str(r.get(dt_col, "") or "").strip()
            if dt_val and dt_val.lower() not in ["none", "null", "nan"]:
                if not is_valid_datetime_str(dt_val[:12]):
                    r119_v.append(RuleViolation(
                        standard="4750", rule_code="119", rule_name="Ngày y lệnh / thực hiện y lệnh XML3 không hợp lệ",
                        xml_table="XML3", field_name=dt_col, actual_value=dt_val,
                        expected_condition="Định dạng YYYYMMDDHHMM hợp lệ",
                        message=f"Dòng DVKT #{idx+1}: {dt_col} ('{dt_val}') không hợp lệ."
                    ))

    results.append(RuleResult(rule_code="43", standard="4750", rule_name="Mã nhóm trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r43_v else RuleStatus.PASSED, violations=r43_v))
    results.append(RuleResult(rule_code="44", standard="4750", rule_name="Phạm vi trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r44_v else RuleStatus.PASSED, violations=r44_v))
    results.append(RuleResult(rule_code="52", standard="4750", rule_name="Thành tiền trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r52_v else RuleStatus.PASSED, violations=r52_v))
    results.append(RuleResult(rule_code="53", standard="4750", rule_name="T_BHTT trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r53_v else RuleStatus.PASSED, violations=r53_v))
    results.append(RuleResult(rule_code="54", standard="4750", rule_name="T_BNTT trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r54_v else RuleStatus.PASSED, violations=r54_v))
    results.append(RuleResult(rule_code="55", standard="4750", rule_name="T_BNCCT trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r55_v else RuleStatus.PASSED, violations=r55_v))
    results.append(RuleResult(rule_code="56", standard="4750", rule_name="T_NGUONKHAC trong XML3 không hợp lệ", status=RuleStatus.VIOLATED if r56_v else RuleStatus.PASSED, violations=r56_v))
    results.append(RuleResult(rule_code="119", standard="4750", rule_name="Ngày y lệnh XML3 không hợp lệ", status=RuleStatus.VIOLATED if r119_v else RuleStatus.PASSED, violations=r119_v))

    # ----------------------------------------------------
    # Rule 108: Năm sinh < 1900
    # Rule 109: ngay_sinh > ngay_vao
    # ----------------------------------------------------
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
    # Rule 110: Thẻ Bộ CA cấp không phải thẻ CA5 (mã tỉnh 98)
    # Rule 111: Thẻ TQ/QN sai mã tỉnh trên thẻ (mã tỉnh 97)
    # ----------------------------------------------------
    r110_violations = []
    r111_violations = []
    if len(ma_the) >= 5:
        p3 = ma_the[:3]
        p2 = ma_the[:2]
        prov = ma_the[3:5]
        if (prov == "98" and p3 != "CA5") or (p3 == "CA5" and prov != "98"):
            r110_violations.append(RuleViolation(
                standard="4750", rule_code="110", rule_name="Thẻ Bộ CA cấp không phải thẻ CA5",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="Mã đơn vị 98 phải đi kèm đầu thẻ CA5",
                message=f"Mã thẻ '{ma_the}' không khớp quy tắc thẻ Công an (CA5 - 98)."
            ))
        valid_97_prefixes = {"BT", "DN", "HC", "HS", "LS", "QN", "SV", "TE", "TQ", "TV", "TY", "XK"}
        if (prov != "97" and p2 in ("QN", "TQ")) or (prov == "97" and p2 not in valid_97_prefixes):
            r111_violations.append(RuleViolation(
                standard="4750", rule_code="111", rule_name="Thẻ TQ/QN sai mã tỉnh trên thẻ",
                xml_table="XML1", field_name="MA_THE", actual_value=ma_the,
                expected_condition="Đầu thẻ QN/TQ phải có mã đơn vị 97",
                message=f"Mã thẻ '{ma_the}' sai quy tắc mã đơn vị 97 của Quân đội."
            ))
    results.append(RuleResult(rule_code="110", standard="4750", rule_name="Thẻ Bộ CA cấp không phải thẻ CA",
                              status=RuleStatus.VIOLATED if r110_violations else RuleStatus.PASSED, violations=r110_violations))
    results.append(RuleResult(rule_code="111", standard="4750", rule_name="Thẻ TQ/QN sai mã tỉnh trên thẻ",
                              status=RuleStatus.VIOLATED if r111_violations else RuleStatus.PASSED, violations=r111_violations))

    # ----------------------------------------------------
    # Rule 112: Hưu trí (HT) nhỏ hơn 33 tuổi
    # Rule 113: Thẻ CT phải đủ 80 tuổi
    # Tính tuổi theo SUBSTR(NGAY_VAO, 1, 4) - SUBSTR(NGAY_SINH, 1, 4)
    # ----------------------------------------------------
    r112_violations = []
    r113_violations = []
    if ngay_sinh and len(ngay_sinh) >= 4 and ngay_sinh[:4].isdigit():
        nam_sinh = int(ngay_sinh[:4])
        ref_year = int(ngay_vao[:4]) if (ngay_vao and len(ngay_vao) >= 4 and ngay_vao[:4].isdigit()) else datetime.datetime.now().year
        tuoi = ref_year - nam_sinh
        if ma_the.startswith("HT") and tuoi < 33:
            r112_violations.append(RuleViolation(
                standard="4750", rule_code="112", rule_name="Hưu trí nhỏ hơn 33 tuổi",
                xml_table="XML1", field_name="MA_THE", actual_value=f"MA_THE={ma_the}, TUOI={tuoi}",
                expected_condition="Tuổi hưởng hưu trí (NAM_VAO - NAM_SINH) >= 33",
                message=f"Đối tượng hưu trí (HT) có tuổi = {tuoi} (< 33 tuổi)."
            ))
        if ma_the.startswith("CT") and tuoi < 80:
            r113_violations.append(RuleViolation(
                standard="4750", rule_code="113", rule_name="Thẻ CT phải đủ 80 tuổi",
                xml_table="XML1", field_name="MA_THE", actual_value=f"MA_THE={ma_the}, TUOI={tuoi}",
                expected_condition="Tuổi đối tượng CT (NAM_VAO - NAM_SINH) >= 80",
                message=f"Đối tượng thẻ CT có tuổi = {tuoi} (< 80 tuổi)."
            ))
    results.append(RuleResult(rule_code="112", standard="4750", rule_name="Hưu trí nhỏ hơn 33 tuổi",
                              status=RuleStatus.VIOLATED if r112_violations else RuleStatus.PASSED, violations=r112_violations))
    results.append(RuleResult(rule_code="113", standard="4750", rule_name="Thẻ CT phải đủ 80 tuổi",
                              status=RuleStatus.VIOLATED if r113_violations else RuleStatus.PASSED, violations=r113_violations))

    # ----------------------------------------------------
    # Rule 114: Trẻ em sử dụng thẻ tạm (Mã tỉnh trên thẻ <> Mã tỉnh tại mã ĐKBĐ)
    # ----------------------------------------------------
    r114_violations = []
    ma_the_tam = str(xml1.get("MA_THE_TAM", "") or "").strip()
    is_temp_te = (ma_the_tam == "1") or (ma_the.startswith("TE") and len(ma_the) >= 10 and ma_the[7:10] == "000")
    if is_temp_te and len(ma_the) >= 5 and len(ma_dkbd) >= 2:
        if ma_the[3:5] != ma_dkbd[:2]:
            r114_violations.append(RuleViolation(
                standard="4750", rule_code="114", rule_name="Trẻ em sử dụng thẻ tạm sai mã tỉnh ĐKBĐ",
                xml_table="XML1", field_name="MA_DKBD", actual_value=f"MA_THE={ma_the}, MA_DKBD={ma_dkbd}",
                expected_condition="Mã tỉnh trên thẻ tạm phải khớp 2 ký tự đầu của MA_DKBD",
                message=f"Trẻ em dùng thẻ tạm có mã tỉnh thẻ ({ma_the[3:5]}) khác mã tỉnh ĐKBĐ ({ma_dkbd[:2]})."
            ))
    results.append(RuleResult(rule_code="114", standard="4750", rule_name="Trẻ em sử dụng thẻ tạm",
                              status=RuleStatus.VIOLATED if r114_violations else RuleStatus.PASSED, violations=r114_violations))

    # ----------------------------------------------------
    # Rule 115: Hồ sơ khám bệnh có tiền giường
    # ----------------------------------------------------
    r115_violations = []
    if ma_loai_kcb in ["1", "01", "7", "07"]:
        tien_giuong = to_decimal(xml1.get("T_GIUONG", xml1.get("TIEN_GIUONG", 0)))
        for r in xml3:
            ma_nhom = str(r.get("MA_NHOM", "")).strip()
            if ma_nhom in ["14", "15"]:
                tien_giuong += to_decimal(r.get("THANH_TIEN_BV", r.get("THANH_TIEN", 0)))
        if tien_giuong > Decimal("0"):
            r115_violations.append(RuleViolation(
                standard="4750", rule_code="115", rule_name="Hồ sơ khám bệnh có tiền giường",
                xml_table="XML3", field_name="THANH_TIEN", actual_value=str(tien_giuong),
                expected_condition="Khám bệnh (MA_LOAI_KCB=1,7) không được phát sinh tiền giường",
                message=f"Hồ sơ khám bệnh phát sinh tiền giường ({tien_giuong})."
            ))
    results.append(RuleResult(rule_code="115", standard="4750", rule_name="Hồ sơ khám bệnh có tiền giường",
                              status=RuleStatus.VIOLATED if r115_violations else RuleStatus.PASSED, violations=r115_violations))

    # ----------------------------------------------------
    # Rule 116: Có tiền vận chuyển nhưng tien_ngoaids <= 0
    # Rule 117: NAM_NAM_LIEN_TUC không hợp lệ
    # ----------------------------------------------------
    r116_violations = []
    t_vanchuyen = to_decimal(xml1.get("T_VANCHUYEN", xml1.get("T_VAN_CHUYEN", 0)))
    t_ngoaids = to_decimal(xml1.get("T_NGOAIDS", xml1.get("TIEN_NGOAI_DS", xml1.get("T_NGOAIDM", 0))))
    if t_vanchuyen > Decimal("0") and t_ngoaids <= Decimal("0"):
        r116_violations.append(RuleViolation(
            standard="4750", rule_code="116", rule_name="Có tiền vận chuyển nhưng tiền ngoài định suất <= 0",
            xml_table="XML1", field_name="T_NGOAIDS", actual_value=f"T_VANCHUYEN={t_vanchuyen}, T_NGOAIDS={t_ngoaids}",
            expected_condition="Khi T_VANCHUYEN > 0 thì T_NGOAIDS phải > 0",
            message="Hồ sơ có chi phí vận chuyển nhưng tiền ngoài định suất <= 0."
        ))
    results.append(RuleResult(rule_code="116", standard="4750", rule_name="Có tiền vận chuyển nhưng tien_ngoaids <= 0",
                              status=RuleStatus.VIOLATED if r116_violations else RuleStatus.PASSED, violations=r116_violations))

    r117_violations = []
    nam_lt = str(xml1.get("NAM_NAM_LIEN_TUC", "") or "").strip()
    if nam_lt and nam_lt.lower() not in ["none", "null", "nan"]:
        if not is_valid_date_str(nam_lt[:8]):
            r117_violations.append(RuleViolation(
                standard="4750", rule_code="117", rule_name="Ngày đủ 5 năm liên tục không hợp lệ",
                xml_table="XML1", field_name="NAM_NAM_LIEN_TUC", actual_value=nam_lt,
                expected_condition="Định dạng 8 ký tự số YYYYMMDD hợp lệ",
                message=f"Giá trị NAM_NAM_LIEN_TUC '{nam_lt}' không hợp lệ."
            ))
    results.append(RuleResult(rule_code="117", standard="4750", rule_name="Năm năm liên tục không hợp lệ",
                              status=RuleStatus.VIOLATED if r117_violations else RuleStatus.PASSED, violations=r117_violations))

    return results
