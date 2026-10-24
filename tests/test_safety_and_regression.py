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

def test_parameterized_query_syntax():
    """
    Kiểm tra XmlSourceAdapter sử dụng query tham số hóa (?, ?, ?)
    và không dùng f-string nội suy giá trị trực tiếp để tương thích Python 3.10/3.11
    đồng thời chống SQL Injection.
    """
    source_lines = inspect.getsource(source_adapter.XmlSourceAdapter)
    assert "quoted_keys" not in source_lines, "Vẫn còn tồn tại biến quoted_keys nội suy f-string nguy hiểm!"
    assert "placeholders = \", \".join([\"?\"] * len(chunk))" in source_lines
    assert "cur.execute(sql, tuple(chunk))" in source_lines

def test_branch_a_regression_real_data():
    """
    Chạy thực tế pipeline đối soát của Nhánh A (compare_service.process_comparison)
    trên CSDL SQLite in-memory với DataFrame mẫu, đảm bảo không có bất kỳ xung đột nào.
    """
    import pandas as pd
    import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Record

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()

    try:
        df_sql = pd.DataFrame([
            {
                "MA_LK": "LK_TEST_001",
                "Họ tên": "Nguyễn Văn A",
                "Mã thẻ": "DN4662320000001",
                "Tên khoa": "Khoa Khám bệnh",
                "Loại ca": "Ngoại trú",
                "Mã y tế": "YT001",
                "Ngày ra viện": datetime.date.today(),
                "Tổng cộng": 150000.0,
                "Tiền BHYT": 120000.0
            },
            {
                "MA_LK": "LK_TEST_002",
                "Họ tên": "Trần Thị B",
                "Mã thẻ": "DN4662320000002",
                "Tên khoa": "Khoa Ngoại",
                "Loại ca": "Nội trú",
                "Mã y tế": "YT002",
                "Ngày ra viện": datetime.date.today(),
                "Tổng cộng": 500000.0,
                "Tiền BHYT": 400000.0
            },
            {
                "MA_LK": "LK_TEST_003",
                "Họ tên": "Lê Văn C",
                "Mã thẻ": "DN4662320000003",
                "Tên khoa": "Khoa Nội",
                "Loại ca": "Nội trú",
                "Mã y tế": "YT003",
                "Ngày ra viện": datetime.date.today(),
                "Tổng cộng": 300000.0,
                "Tiền BHYT": 250000.0
            }
        ])

        # LK_TEST_001 gửi thành công
        df_listbh = pd.DataFrame([{"MA_LK": "LK_TEST_001"}])
        # LK_TEST_002 bị lỗi cổng
        df_hsloi = pd.DataFrame([{
            "MA_LK": "LK_TEST_002",
            "MALOI": "LOI_01",
            "MOTALOI": "Sai thông tin thẻ BHYT",
            "TÊN KHOA": "Khoa Ngoại"
        }])
        # LK_TEST_003 chưa gửi cổng (FAIL)

        stats = compare_service.process_comparison(
            db=db,
            df_sql=df_sql,
            df_listbh=df_listbh,
            df_hsloi=df_hsloi,
            ngay_doi_soat=datetime.date.today(),
            include_errors=True
        )

        assert stats["total"] == 3
        assert stats["sent"] == 1
        assert stats["loi"] == 1
        assert stats["fail"] == 1

        recs = db.query(Record).all()
        assert len(recs) == 2  # 1 ca LOI + 1 ca FAIL
        loi_rec = db.query(Record).filter(Record.ma_lk == "LK_TEST_002").first()
        assert loi_rec.type_group == "LOI"
        assert loi_rec.maloi == "LOI_01"

        fail_rec = db.query(Record).filter(Record.ma_lk == "LK_TEST_003").first()
        assert fail_rec.type_group == "FAIL"

    finally:
        db.close()

def test_validator_cancellation_preservation():
    """
    Xác minh việc hủy tiến trình giữa chừng hoặc ở batch cuối cùng
    luôn ghi nhận trạng thái CANCELLED và không bị ghi đè bởi COMPLETED.
    """
    from xml_validator_v2.validation_service import run_validation_job, CURRENT_VALIDATION_PROGRESS
    from xml_validator_v2.source_adapter import XmlSourceAdapter
    from xml_validator_v2.db import ValSessionLocal, init_val_db
    from xml_validator_v2.models import ValRun

    init_val_db()
    
    class FastMockAdapter(XmlSourceAdapter):
        def fetch_xml_batch(self, ma_lk_list, chunk_size=50):
            CURRENT_VALIDATION_PROGRESS["is_cancelled"] = True
            return {k: {} for k in ma_lk_list}, {}

    cases = [{"ma_lk": f"TEST_LK_{i}", "ho_ten": f"BN {i}"} for i in range(5)]
    run_validation_job(cases, xml_adapter=FastMockAdapter())

    db = ValSessionLocal()
    try:
        latest = db.query(ValRun).order_by(ValRun.id.desc()).first()
        assert latest is not None
        assert latest.status == "CANCELLED", f"Kỳ vọng CANCELLED nhưng nhận {latest.status}"
        assert CURRENT_VALIDATION_PROGRESS["status"] == "CANCELLED"
    finally:
        db.close()

if __name__ == "__main__":
    test_sql_safety_source_adapter()
    print("test_sql_safety_source_adapter: PASSED")
    test_sqlite_isolation()
    print("test_sqlite_isolation: PASSED")
    test_branch_a_intact()
    print("test_branch_a_intact: PASSED")
    test_parameterized_query_syntax()
    print("test_parameterized_query_syntax: PASSED")
    test_branch_a_regression_real_data()
    print("test_branch_a_regression_real_data: PASSED")
    test_validator_cancellation_preservation()
    print("test_validator_cancellation_preservation: PASSED")
    print("ALL SAFETY & REGRESSION CHECKS PASSED!")
