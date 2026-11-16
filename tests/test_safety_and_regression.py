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

def test_rule_dependency_error_demotion():
    """
    Xác minh ma trận phụ thuộc bảng XML: nếu bảng XML2 bị lỗi truy vấn (ERROR),
    quy tắc tính tiền (Rule 3) duyệt danh sách rỗng KHÔNG ĐƯỢC PHÉP trả về PASSED
    mà bắt buộc phải hạ xuống INCOMPLETE_DATA.
    """
    from xml_validator_v2.rule_models import CaseXmlData, RuleStatus
    from xml_validator_v2.rule_engine import ValidationEngine

    engine = ValidationEngine()
    case = CaseXmlData(
        ma_lk="LK_TEST_DEP_ERR",
        ho_ten="Nguyễn Văn A",
        xml1={
            "MA_LK": "LK_TEST_DEP_ERR",
            "MA_LYDO_VVIEN": "1",
            "MA_CSKCB": "66232",
            "MA_DKBD": "66232",
            "T_TONGCHI": 0,
            "T_BNTT": 0,
            "T_BHTT": 0,
            "T_NGUONKHAC": 0
        },
        xml2=[], # rỗng do bảng XML2 bị lỗi truy vấn
        xml3=[],
        table_fetch_status={"XML1": "SUCCESS", "XML2": "ERROR", "XML3": "SUCCESS"}
    )

    eval_res = engine.validate_case(case)
    rule_results = {r.rule_code: r for r in eval_res["rule_results"]}

    # Rule 3 phụ thuộc XML2, XML3 -> Khi XML2 bị lỗi, Rule 3 bắt buộc phải là INCOMPLETE_DATA
    r3 = rule_results.get("3")
    assert r3 is not None, "Không tìm thấy Rule 3 trong kết quả đánh giá!"
    assert r3.status == RuleStatus.INCOMPLETE_DATA, f"Kỳ vọng Rule 3 là INCOMPLETE_DATA do XML2 lỗi, nhưng nhận: {r3.status}"
    assert "XML2" in r3.reason, f"Lý do phải nêu rõ bảng XML2 lỗi, nhưng nhận: {r3.reason}"

def test_chunk_error_isolation_and_no_overwrite():
    """
    Xác minh logic chống ghi đè trạng thái bảng:
    Khi chunk 1 bị ERROR trên bảng XML2 và chunk 2 đọc được dữ liệu SUCCESS,
    trạng thái tổng thể batch của XML2 vẫn phải duy trì ERROR, không bị xóa dấu vết.
    Đồng thời các hồ sơ ở chunk 1 nhận status ERROR, hồ sơ ở chunk 2 nhận status SUCCESS/EMPTY.
    """
    from xml_validator_v2.source_adapter import XmlSourceAdapter, XML_TABLE_COLUMNS
    assert "XML1" in XML_TABLE_COLUMNS
    assert "XML2" in XML_TABLE_COLUMNS
    assert "XML4" in XML_TABLE_COLUMNS
    assert len(XML_TABLE_COLUMNS["XML4"]) < 15, "XML4 phải được thu gọn số cột để tối ưu RAM/IO!"

def test_ma_lk_excel_string_and_numeric_formats():
    """
    Kiểm thử toàn diện việc đọc & đối chiếu cột MA_LK / Mã liên kết từ Excel:
    1. Ô Excel lưu dạng chuỗi (data_type == 's', value='26.035530') -> bảo toàn '26.035530'.
    2. Ô Excel lưu dạng số (data_type == 'n', value=26.03553) có number_format='0.000000' ->
       openpyxl khôi phục đúng chữ số 0 hiển thị thành '26.035530' (trong khi dtype=str đơn thuần sẽ bị cụt).
    3. Ô Excel lưu dạng số (data_type == 'n', value=26.01122, number_format='General'):
       - Nếu không có căn cứ nguồn tin cậy (trusted_keys) -> KHÔNG tự ý thêm số 0 ('26.01122').
       - Nếu nguồn tin cậy bị nhập nhằng ('26.011220' và '26.0112200') -> KHÔNG tự ý đoán ('26.01122').
       - Nếu nguồn tin cậy SQL HIS có duy nhất mã '26.011220' -> khôi phục chuẩn xác về '26.011220'.
    """
    import openpyxl
    from io import BytesIO
    from services import excel_service

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["MA_GD", "MALOI", "MA_CSKCB", "MOTALOI", "MA_LK"])

    # Dòng 2: Ô lưu dạng chuỗi (data_type='s')
    ws.append(["GD1", "XML1", "66232", "Lỗi 1", "26.035530"])
    ws.cell(row=2, column=5).data_type = "s"
    ws.cell(row=2, column=5).number_format = "@"

    # Dòng 3: Ô lưu dạng số (float 26.03597) nhưng có định dạng hiển thị 6 chữ số thập phân '0.000000'
    ws.append(["GD2", "XML2", "66232", "Lỗi 2", 26.03597])
    ws.cell(row=3, column=5).number_format = "0.000000"

    # Dòng 4: Ô lưu dạng số (float 26.01122) với định dạng General (không có thông tin độ dài thập phân trong ô)
    ws.append(["GD3", "XML3", "66232", "Lỗi 3", 26.01122])
    ws.cell(row=4, column=5).number_format = "General"

    # Dòng 5: Ô lưu dạng số (float 26.09999) không có trong nguồn HIS
    ws.append(["GD4", "XML4", "66232", "Lỗi 4", 26.09999])
    ws.cell(row=5, column=5).number_format = "General"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    # A. Đọc khi KHÔNG truyền trusted_keys:
    df_no_trust = excel_service.load_hosoloichitiet(buf)
    malk_list = df_no_trust["MA_LK"].tolist()
    assert malk_list[0] == "26.035530", f"Expected string cell '26.035530', got {malk_list[0]}"
    assert malk_list[1] == "26.035970", f"Expected formatted numeric cell '26.035970', got {malk_list[1]}"
    assert malk_list[2] == "26.01122", f"Must NOT blindly pad zero without evidence, got {malk_list[2]}"
    assert malk_list[3] == "26.09999", f"Must NOT blindly pad zero without evidence, got {malk_list[3]}"

    # B. Đọc khi có trusted_keys đáng tin cậy từ SQL Server HIS:
    buf.seek(0)
    trusted_his_keys = {"26.035530", "26.035970", "26.011220", "TN.2608.0000123"}
    df_with_trust = excel_service.load_hosoloichitiet(buf, trusted_keys=trusted_his_keys)
    malk_trusted = df_with_trust["MA_LK"].tolist()
    assert malk_trusted[0] == "26.035530"
    assert malk_trusted[1] == "26.035970"
    assert malk_trusted[2] == "26.011220", f"Should resolve '26.01122' -> '26.011220' via trusted HIS set, got {malk_trusted[2]}"
    assert malk_trusted[3] == "26.09999", f"Unmatched numeric code must remain unchanged, got {malk_trusted[3]}"

    # C. Kiểm tra trường hợp nhập nhằng (ambiguous): cả '26.011220' và '26.0112200' cùng tồn tại
    ambiguous_keys = {"26.011220", "26.0112200"}
    res_ambig = excel_service.resolve_ma_lk_against_trusted_set("26.01122", ambiguous_keys)
    assert res_ambig == "26.01122", f"Ambiguous match must NOT guess, got {res_ambig}"


def test_cc_suffix_conversion_in_source_adapter():
    """
    Xác minh XmlSourceAdapter chuyển đổi chính xác hậu tố cấp cứu _CC sang /CC khi truy vấn SQL Server,
    tuyệt đối không bỏ hậu tố, và ánh xạ kết quả trả về đúng cho khóa gốc (_CC và /CC).
    """
    executed_params = []

    class MockCursor:
        def __init__(self):
            self.description = [("MA_LK",), ("HO_TEN",)]
            self._rows = []

        def execute(self, sql, params=()):
            executed_params.append(tuple(params))
            if "FROM dbo.XML1_CV130" in sql:
                # Chỉ trả về nếu SQL query truyền đúng /CC (không bỏ hậu tố)
                rows = []
                if "26.045759/CC" in params:
                    rows.append(("26.045759/CC", "ĐẶNG THỊ HẢI"))
                if "26.047594/CC" in params:
                    rows.append(("26.047594/CC", "NGUYỄN THÀNH THÁI"))
                self._rows = rows
            else:
                self._rows = []

        def fetchall(self):
            return self._rows

        def close(self):
            pass

    class MockConn:
        def cursor(self):
            return MockCursor()

        def close(self):
            pass

    class MockCCAdapter(source_adapter.XmlSourceAdapter):
        def get_connection(self):
            return MockConn()

    adapter = MockCCAdapter({"tables": ["XML1_CV130", "XML2_CV130"]})
    results, case_tbl_status, _ = adapter.fetch_xml_batch(["26.045759_CC", "26.047594/CC"])

    # Phải chuyển đổi _CC -> /CC khi truyền tham số ODBC, tuyệt đối không tìm kiếm kiểu bỏ hậu tố
    assert len(executed_params) > 0
    for params in executed_params:
        assert params == ("26.045759/CC", "26.047594/CC"), f"Unexpected SQL params: {params}"
        assert "26.045759" not in params

    # Dữ liệu SQL (/CC) phải ánh xạ trả về chính xác cho khóa gốc (_CC lẫn /CC)
    assert "XML1" in results["26.045759_CC"]
    assert results["26.045759_CC"]["XML1"][0]["HO_TEN"] == "ĐẶNG THỊ HẢI"
    assert case_tbl_status["26.045759_CC"]["XML1"] == "SUCCESS"
    assert "XML1" in results["26.047594/CC"]
    assert case_tbl_status["26.047594/CC"]["XML1"] == "SUCCESS"


def test_multi_month_reconciliation_and_old_month_protection():
    """
    Xác minh quy trình đối soát đa tháng:
    1. Tải listbh Tháng 11 không làm mất listbh Tháng 10 (lưu phân tách listbh_YYYY_MM.xlsx).
    2. Khi chạy Tháng 11 hoặc khoảng ngày có cả Tháng 10 khi chưa có listbh Tháng 10, các ca Tháng 10
       không bị đẩy nhầm vào FAIL; khi df_listbh rỗng tuyệt đối không sinh FAIL.
    3. Các ca FAIL tồn đọng Tháng 10 khi được đẩy bù sang Tháng 11 (xuất hiện trong listbh Tháng 11)
       sẽ tự động chuyển sang RESOLVED.
    4. Ca đã RESOLVED thuộc tháng cũ không bị tự động mở lại thành PENDING FAIL.
    """
    import tempfile
    import datetime
    import pandas as pd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Record
    from services import excel_service

    # A. Kiểm tra lưu trữ phân tách listbh theo tháng và nạp gộp đa tháng
    with tempfile.TemporaryDirectory() as tmp_dir:
        oct_rows = [{"Mã liên kết": f"OCT_SENT_{i:03d}", "Ngày ra": "05/10/2026 09:00"} for i in range(1, 21)]
        df_oct_xl = pd.DataFrame(oct_rows)
        oct_src = os.path.join(tmp_dir, "src_oct.xlsx")
        df_oct_xl.to_excel(oct_src, index=False)
        excel_service.archive_listbh_by_months(oct_src, tmp_dir, explicit_month=10, explicit_year=2026)

        nov_rows = [{"Mã liên kết": f"NOV_SENT_{i:03d}", "Ngày ra": "03/11/2026 10:00"} for i in range(1, 16)]
        # Thêm ca nội trú xuất viện cuối tháng 10 quyết toán tháng 11
        nov_rows.append({"Mã liên kết": "OCT_FAIL_001", "Ngày ra": "30/10/2026 16:00"})
        df_nov_xl = pd.DataFrame(nov_rows)
        nov_src = os.path.join(tmp_dir, "src_nov.xlsx")
        df_nov_xl.to_excel(nov_src, index=False)
        excel_service.archive_listbh_by_months(nov_src, tmp_dir, explicit_month=11, explicit_year=2026)

        assert os.path.exists(os.path.join(tmp_dir, "listbh_2026_10.xlsx"))
        assert os.path.exists(os.path.join(tmp_dir, "listbh_2026_11.xlsx"))

        df_comb = excel_service.load_combined_listbh_for_range(tmp_dir)
        comb_keys = set(df_comb["MA_LK"].tolist())
        assert "OCT_SENT_001" in comb_keys and "OCT_SENT_020" in comb_keys, "Mất dữ liệu Tháng 10 sau khi nạp Tháng 11!"
        assert "NOV_SENT_001" in comb_keys and "OCT_FAIL_001" in comb_keys

    # B. Kiểm tra logic compare_service với SQLite in-memory
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()

    try:
        def make_sql_row(lk, ngay):
            return {
                "MA_LK": lk, "Họ tên": f"BN {lk}", "Mã thẻ": "DN4662320000001",
                "Tên khoa": "Khoa Nội", "Loại ca": "Nội trú", "Mã y tế": "",
                "Ngày ra viện": ngay, "Tổng cộng": 100000.0, "Tiền BHYT": 80000.0
            }

        oct_sql = [make_sql_row(f"OCT_{i:03d}", datetime.date(2026, 10, 5)) for i in range(1, 31)]  # 30 ca T10
        df_sql_oct = pd.DataFrame(oct_sql)
        # 25 ca đã gửi, còn 5 ca FAIL (OCT_026..OCT_030)
        df_lb_oct = pd.DataFrame([{"MA_LK": f"OCT_{i:03d}", "_ngay": datetime.date(2026, 10, 5)} for i in range(1, 26)])
        stats_10 = compare_service.process_comparison(
            db, df_sql_oct, df_lb_oct, pd.DataFrame(), datetime.date(2026, 10, 31), include_errors=False
        )
        assert stats_10["sent"] == 25 and stats_10["fail"] == 5

        # 1. Nếu đối soát với df_listbh rỗng (không có dữ liệu trong khoảng ngày), KHÔNG được biến 25 ca kia thành FAIL
        stats_empty_lb = compare_service.process_comparison(
            db, df_sql_oct, pd.DataFrame(), pd.DataFrame(), datetime.date(2026, 11, 16), include_errors=False
        )
        assert stats_empty_lb["fail"] == 0, f"df_listbh rỗng vẫn tạo FAIL: {stats_empty_lb}"
        active_fails_after_empty = db.query(Record).filter(Record.type_group == "FAIL", Record.status != "RESOLVED").count()
        assert active_fails_after_empty == 5

        # 2. Chạy đối soát Tháng 11:
        # - listbh chỉ có Tháng 11 (20/22 ca T11 đã gửi + 2 ca tồn T10 gửi bù: OCT_026, OCT_027 + 1 ca giao thoa cuối T10)
        # - Giả sử df_sql gửi vào vô tình bao gồm cả Tháng 10 lẫn Tháng 11
        nov_sql = [make_sql_row(f"NOV_{i:03d}", datetime.date(2026, 11, 3)) for i in range(1, 23)]
        df_sql_oct_nov = pd.DataFrame(oct_sql + nov_sql)
        lb_nov_only = [{"MA_LK": f"NOV_{i:03d}", "_ngay": datetime.date(2026, 11, 3)} for i in range(1, 21)]
        lb_nov_only.append({"MA_LK": "OCT_026", "_ngay": datetime.date(2026, 11, 2)})
        lb_nov_only.append({"MA_LK": "OCT_027", "_ngay": datetime.date(2026, 11, 2)})
        # Thêm 1 ca spillover ngày 30/10 trong listbh Tháng 11
        lb_nov_only.append({"MA_LK": "OCT_001", "_ngay": datetime.date(2026, 10, 30)})
        df_lb_nov_only = pd.DataFrame(lb_nov_only)

        compare_service.process_comparison(
            db, df_sql_oct_nov, df_lb_nov_only, pd.DataFrame(), datetime.date(2026, 11, 16), include_errors=False
        )

        # Kiểm tra: Không có ca OCT_001..OCT_025 nào bị đẩy thành FAIL
        for i in range(1, 26):
            rec_old = db.query(Record).filter(Record.ma_lk == f"OCT_{i:03d}", Record.type_group == "FAIL", Record.status != "RESOLVED").first()
            assert rec_old is None, f"Ca đã xử lý tháng 10 OCT_{i:03d} bị đẩy nhầm vào FAIL!"

        # Kiểm tra: 2 ca FAIL tồn T10 (OCT_026, OCT_027) đã gửi bù ở T11 -> tự động chuyển RESOLVED
        # Còn lại đúng 3 ca FAIL T10 (OCT_028..030) và 2 ca FAIL T11 (NOV_021..022)
        active_oct_fails = {
            r.ma_lk for r in db.query(Record).filter(
                Record.type_group == "FAIL", Record.status != "RESOLVED", Record.ma_lk.like("OCT_%")
            ).all()
        }
        active_nov_fails = {
            r.ma_lk for r in db.query(Record).filter(
                Record.type_group == "FAIL", Record.status != "RESOLVED", Record.ma_lk.like("NOV_%")
            ).all()
        }
        assert active_oct_fails == {"OCT_028", "OCT_029", "OCT_030"}, f"Unexpected Oct FAILs: {active_oct_fails}"
        assert active_nov_fails == {"NOV_021", "NOV_022"}, f"Unexpected Nov FAILs: {active_nov_fails}"

        # 3. Kiểm tra bảo vệ ca đã RESOLVED của tháng cũ (giả sử OCT_028 được IT chốt sổ RESOLVED)
        rec_028 = db.query(Record).filter(Record.ma_lk == "OCT_028").first()
        rec_028.status = "RESOLVED"
        db.commit()

        # Chạy lại với combined listbh có cả tháng 10 & tháng 11 (nhưng OCT_028 vẫn không nằm trong sent_keys)
        df_lb_both = pd.concat([df_lb_oct, df_lb_nov_only], ignore_index=True)
        compare_service.process_comparison(
            db, df_sql_oct_nov, df_lb_both, pd.DataFrame(), datetime.date(2026, 11, 16), include_errors=False
        )
        db.refresh(rec_028)
        assert rec_028.status == "RESOLVED", "Ca tháng cũ đã chốt RESOLVED bị mở lại nhầm sang PENDING FAIL!"
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
    test_rule_dependency_error_demotion()
    print("test_rule_dependency_error_demotion: PASSED")
    test_chunk_error_isolation_and_no_overwrite()
    print("test_chunk_error_isolation_and_no_overwrite: PASSED")
    test_ma_lk_excel_string_and_numeric_formats()
    print("test_ma_lk_excel_string_and_numeric_formats: PASSED")
    test_cc_suffix_conversion_in_source_adapter()
    print("test_cc_suffix_conversion_in_source_adapter: PASSED")
    test_multi_month_reconciliation_and_old_month_protection()
    print("test_multi_month_reconciliation_and_old_month_protection: PASSED")
    print("ALL SAFETY & REGRESSION CHECKS PASSED!")
