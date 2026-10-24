from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web_app"))

from xml_validator_v2.rule_models import CaseXmlData, RuleStatus
from xml_validator_v2.rule_engine import ValidationEngine
from xml_validator_v2.rules import check_rules_9324, check_rules_4210, check_rules_4750

def test_missing_xml():
    engine = ValidationEngine()
    case = CaseXmlData(ma_lk="TEST_MISSING")
    res = engine.validate_case(case)
    assert res["overall_status"] == "MISSING_XML"
    assert res["violated_count"] == 0

def test_ruleset_undetermined():
    engine = ValidationEngine(default_standard="NONE")
    # Hồ sơ có XML1 nhưng không có bất kỳ trường nào để nhận diện
    case = CaseXmlData(ma_lk="TEST_UNDET", xml1={"MA_LK": "TEST_UNDET"})
    res = engine.validate_case(case)
    assert res["overall_status"] == "RULESET_UNDETERMINED"

def test_rules_9324_valid_and_errors():
    # 1. Trường hợp hợp lệ chuẩn 9324
    valid_xml1 = {
        "MA_LK": "LK9324_01",
        "MA_LYDO_VVIEN": "1",
        "MA_CSKCB": "66232",
        "MA_DKBD": "66232",
        "MA_THE": "DN4662320123456",
        "T_TONGCHI": 300000,
        "T_BNTT": 50000,
        "T_BHTT": 250000,
        "T_NGUONKHAC": 0
    }
    valid_xml2 = [
        {"SO_LUONG": 2, "DON_GIA": 50000, "TYLE_TT": 100, "THANH_TIEN": 100000}
    ]
    valid_xml3 = [
        {"SO_LUONG": 1, "DON_GIA": 200000, "TYLE_TT": 100, "THANH_TIEN": 200000, "TEN_DICH_VU": "XÉT NGHIỆM MÁU"}
    ]
    case_valid = CaseXmlData(ma_lk="LK9324_01", xml1=valid_xml1, xml2=valid_xml2, xml3=valid_xml3)
    results = check_rules_9324(case_valid)
    violated = [r for r in results if r.status == RuleStatus.VIOLATED]
    assert len(violated) == 0, f"Expected 0 violations but got: {[v.violations for v in violated]}"

    # 2. Trường hợp vi phạm chuẩn 9324: TONGCHI không khớp thành phần
    invalid_xml1 = valid_xml1.copy()
    invalid_xml1["T_TONGCHI"] = 500000  # Lệch lớn so với 50.000 + 250.000 = 300.000
    case_invalid = CaseXmlData(ma_lk="LK9324_02", xml1=invalid_xml1, xml2=valid_xml2, xml3=valid_xml3)
    results_inv = check_rules_9324(case_invalid)
    v_codes = [r.rule_code for r in results_inv if r.status == RuleStatus.VIOLATED]
    assert "4" in v_codes  # Sai so với XML2, XML3
    assert "5" in v_codes  # Sai so với BNTT + BHTT

def test_rules_4210_arithmetic_and_format():
    # Trường hợp vi phạm: Ngày vào > Ngày ra, Giới tính sai, BHTT XML1 != XML23
    xml1 = {
        "MA_LK": "LK4210_01",
        "TONG_CHI": 100000,
        "T_BNTT": 20000,
        "T_BNCCT": 0,
        "T_BHTT": 80000,
        "T_NGUONKHAC": 0,
        "GIOI_TINH": "5",  # Sai (chỉ 1 hoặc 2)
        "NGAY_VAO": "202610251000",
        "NGAY_RA": "202610200800",  # Ngày ra trước ngày vào
        "NGAY_SINH": "20000101",
        "NAM_QT": "2026",
        "THANG_QT": "10",
        "MA_THE": "DN4662320123456"
    }
    xml2 = [{"SO_LUONG": 1, "DON_GIA": 50000, "TYLE_TT": 100, "THANH_TIEN": 50000, "T_BHTT": 40000, "T_BNTT": 10000, "T_BNCCT": 0, "T_NGUONKHAC": 0, "T_NGOAIDS": 0}]
    xml3 = [{"SO_LUONG": 1, "DON_GIA": 50000, "TYLE_TT": 100, "THANH_TIEN": 50000, "T_BHTT": 20000, "T_BNTT": 30000, "T_BNCCT": 0, "T_NGUONKHAC": 0, "T_NGOAIDS": 0}]
    # Tổng BHTT XML23 = 60.000 != T_BHTT XML1 (80.000)

    case = CaseXmlData(ma_lk="LK4210_01", xml1=xml1, xml2=xml2, xml3=xml3)
    results = check_rules_4210(case)
    v_codes = [r.rule_code for r in results if r.status == RuleStatus.VIOLATED]
    assert "16" in v_codes  # Giới tính
    assert "24" in v_codes  # Ngày ra < Ngày vào
    assert "31" in v_codes  # BHTT XML1 != XML23

def test_rules_4750_specific_rules():
    # Kiểm tra Rule 115: Khám bệnh (MA_LOAI_KCB = 1) nhưng có tiền giường (nhóm 14, 15)
    xml1 = {
        "MA_LK": "LK4750_01",
        "T_TONGCHI_BV": 150000,
        "T_BNTT": 0,
        "T_BNCCT": 0,
        "T_BHTT": 150000,
        "T_NGUONKHAC": 0,
        "MA_LOAI_KCB": "1",  # Khám bệnh ngoại trú
        "GIOI_TINH": "1",
        "NGAY_VAO": "202610200800",
        "NGAY_RA": "202610201100",
        "NGAY_SINH": "19900510",
        "MA_THE": "DN4662320123456"
    }
    xml3 = [
        {"MA_NHOM": "14", "SO_LUONG": 1, "DON_GIA": 150000, "TYLE_TT": 100, "THANH_TIEN": 150000, "T_BHTT": 150000}
    ]
    case = CaseXmlData(ma_lk="LK4750_01", xml1=xml1, xml3=xml3)
    results = check_rules_4750(case)
    v_codes = [r.rule_code for r in results if r.status == RuleStatus.VIOLATED]
    assert "115" in v_codes  # Khám bệnh có tiền giường

def test_validation_engine_status_has_errors():
    engine = ValidationEngine()
    xml1 = {
        "MA_LK": "LK_ERR",
        "T_TONGCHI_BV": 100000,
        "T_BNTT": 100000,
        "T_BNCCT": 0,
        "T_BHTT": 0,  # Vi phạm: T_BHTT = 0
        "T_NGUONKHAC": 0,
        "GIOI_TINH": "1",
        "NGAY_VAO": "202610200800",
        "NGAY_RA": "202610201100",
        "NGAY_SINH": "19900510",
        "MA_THE": "DN4662320123456"
    }
    case = CaseXmlData(ma_lk="LK_ERR", xml1=xml1)
    eval_res = engine.validate_case(case)
    assert eval_res["overall_status"] == "HAS_ERRORS"
    assert eval_res["violated_count"] > 0

def test_ctn_4750_rules():
    from xml_validator_v2.rules import check_rules_4750_ctn

    # 1. Test CCCD sai định dạng & thiếu trường bắt buộc
    xml1 = {
        "MA_LK": "LK_CTN_01",
        "MA_CSKCB": "66232",
        "HO_TEN": "NGUYEN VAN A",
        "NGAY_SINH": "19900101",
        "GIOI_TINH": "1",
        "SO_CCCD": "12345",  # Sai (chỉ có 5 ký tự)
        # Thiếu: DIA_CHI, NGAY_VAO, NGAY_RA, MA_LOAI_KCB, MA_BENH_CHINH...
    }
    # XML7 có họ tên khác XML1
    xml7 = [{"HO_TEN": "TRAN VAN B", "NGAY_SINH": "19900101", "GIOI_TINH": "1"}]
    # Bảng 14 hẹn khám lại <= ngày ra
    raw_tables = {
        "XML14": [{"NGAY_HEN_KL": "202610200800"}]
    }
    xml1["NGAY_RA"] = "202610250800"  # Ngày ra sau ngày hẹn khám lại

    case = CaseXmlData(ma_lk="LK_CTN_01", xml1=xml1, xml7=xml7, raw_tables=raw_tables)
    results = check_rules_4750_ctn(case)
    v_codes = [r.rule_code for r in results if r.status == RuleStatus.VIOLATED]

    assert "CTN_REQ_XML1" in v_codes  # Thiếu trường bắt buộc
    assert "CTN_CCCD_FORMAT" in v_codes  # Sai định dạng CCCD
    assert "CTN_CROSS_CONSISTENCY" in v_codes  # Họ tên XML7 khác XML1
    assert "CTN_XML14_APPOINTMENT_DATE" in v_codes  # Ngày hẹn <= ngày ra

