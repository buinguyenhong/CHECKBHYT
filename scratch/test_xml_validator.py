import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from lxml import etree

# Add web_app to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))
from xml_validator.rule_engine import XMLRuleEngine

def test_xml_rules():
    # Construct a dummy XML1
    xml1_content = """<?xml version="1.0" encoding="utf-8"?>
<TONG_HOP>
    <MA_LK>TEST_MA_LK</MA_LK>
    <MA_BENH_CHINH>I10</MA_BENH_CHINH>
    <NAM_QT>2026</NAM_QT>
    <LY_DO_VV>Người bệnh không KCB BHYT</LY_DO_VV>
    <NGAY_RA>202606251000</NGAY_RA>
</TONG_HOP>
"""
    
    # Construct a dummy XML7 with NGOAITRU_TUNGAY > NGAY_RA
    # NGAY_RA is 202606251000
    # NGOAITRU_TUNGAY is 202606261000 (which is greater than NGAY_RA)
    xml7_content = """<?xml version="1.0" encoding="utf-8"?>
<NGOAI_TRU>
    <MA_LK>TEST_MA_LK</MA_LK>
    <NGOAITRU_TUNGAY>202606261000</NGOAITRU_TUNGAY>
</NGOAI_TRU>
"""

    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    xml1_tree = etree.fromstring(xml1_content.encode('utf-8'), parser=parser)
    xml7_tree = etree.fromstring(xml7_content.encode('utf-8'), parser=parser)

    xml_files = {
        "XML1": [{"tree": xml1_tree}],
        "XML7": [{"tree": xml7_tree}]
    }

    engine = XMLRuleEngine()
    errors = engine.check_rules("TEST_MA_LK", xml_files)

    print("Errors found:")
    for err in errors:
        print(f"Rule: {err['rule_id']}, XML: {err['xml_type']}, Tag: {err['tag_name']}, Msg: '{err['message']}'")

    # Assertions
    # A17 must be in errors
    a17_found = any(err['rule_id'] == 'A17' for err in errors)
    # B2 must NOT be in errors
    b2_found = any(err['rule_id'] == 'B2' for err in errors)

    print(f"\nVerification Results:")
    print(f"A17 Rule (LY_DO_VV check) works: {a17_found} (Expected: True)")
    print(f"B2 Rule (NGOAITRU_TUNGAY check) disabled: {not b2_found} (Expected: True)")

    if a17_found and not b2_found:
        print("SUCCESS!")
    else:
        print("FAILURE!")

if __name__ == "__main__":
    test_xml_rules()
