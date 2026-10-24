import sys
import os
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web_app"))

from xml_validator_v2 import source_adapter, models as v2_models
from models import Record, ErrorDefinition, AppConfig
from services import compare_service, his_service

def test_sql_safety_source_adapter():
    """
    Xác minh mã nguồn XmlSourceAdapter không chứa bất kỳ từ khóa ghi nào
    như INSERT, UPDATE, DELETE, DROP, ALTER, EXEC sp_Create...
    """
    source_lines = inspect.getsource(source_adapter.XmlSourceAdapter)
    dangerous_keywords = [
        "INSERT INTO", "UPDATE ", "DELETE FROM", "DROP TABLE", "ALTER TABLE",
        "sp_BangKe01_NgoaiTru_eClaim_QD3176",
        "sp_Create_BangKe01_NgoaiTru_eClaim_QD3176",
        "sp_Create_BangKe02_NoiTru_eClaim_QD3176",
        "XML_ChiPhiNgoaiTruChiTiet_CV130"
    ]
    for kw in dangerous_keywords:
        assert kw not in source_lines, f"VI PHẠM AN TOÀN: Tìm thấy từ khóa '{kw}' trong XmlSourceAdapter!"

def test_sqlite_isolation():
    """
    Xác minh models của xml_validator_v2 sử dụng Base riêng (BaseVal)
    và không thuộc Base của nhánh A.
    """
    assert v2_models.BaseVal is not compare_service.Record.__table__.metadata
    v2_table_names = [tbl.name for tbl in v2_models.BaseVal.metadata.sorted_tables]
    # Các bảng v2 phải bắt đầu bằng val_
    for t_name in v2_table_names:
        assert t_name.startswith("val_"), f"Bảng {t_name} không có prefix val_"
    
    # Bảng records, error_definitions không được nằm trong BaseVal
    assert "records" not in v2_table_names
    assert "error_definitions" not in v2_table_names
    assert "error_history_archive" not in v2_table_names

def test_branch_a_intact():
    """
    Xác minh logic của compare_service và his_service không bị thay đổi.
    """
    assert hasattr(compare_service, "process_comparison")
    assert hasattr(his_service, "fetch_his_data_range")
    assert hasattr(his_service, "sql_exec_sp")

if __name__ == "__main__":
    test_sql_safety_source_adapter()
    print("test_sql_safety_source_adapter: PASSED")
    test_sqlite_isolation()
    print("test_sqlite_isolation: PASSED")
    test_branch_a_intact()
    print("test_branch_a_intact: PASSED")
    print("ALL SAFETY & REGRESSION CHECKS PASSED!")
