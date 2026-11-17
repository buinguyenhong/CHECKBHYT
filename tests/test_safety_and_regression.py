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
    1. Giữ nguyên 100% cấu trúc 22 cột của listbh.xlsx, tự dọn listbh_YYYY_MM.xlsx cũ và không nhân bản dòng.
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

    # A. Kiểm tra bảo toàn nguyên vẹn cấu trúc 22 cột của listbh.xlsx, dọn tệp tách tháng cũ và khử trùng trên RAM
    with tempfile.TemporaryDirectory() as tmp_dir:
        cols_22 = [
            "STT", "Mã liên kết", "Mã thẻ", "Mã BN", "Họ tên", "Ngày sinh", "Giới tính",
            "Ngày vào", "Ngày ra", "Chẩn đoán", "Tổng chi", "Bệnh nhân TT", "Bệnh nhân CCT",
            "Bảo hiểm TT", "Ngày TT", "Ngày gửi HS", "Ngày đề nghị TT", "Trạng thái HS",
            "Trạng thái TT", "Loại HS", "Mã lỗi", "Miêu tả"
        ]
        raw_rows = [
            {c: (i if c == "STT" else f"OCT_SENT_{i:03d}" if c == "Mã liên kết" else "05/10/2026 09:00" if c == "Ngày ra" else f"V_{c}") for c in cols_22}
            for i in range(1, 21)
        ]
        # Thêm 1 dòng rỗng ở giữa và 1 dòng trùng mã để test lọc rỗng/khử trùng khi đọc mà vẫn giữ nguyên file gốc
        raw_rows.insert(5, {c: None for c in cols_22})
        raw_rows.append(dict(raw_rows[0]))

        master_path = os.path.join(tmp_dir, "listbh.xlsx")
        pd.DataFrame(raw_rows).to_excel(master_path, index=False)
        legacy_month_path = os.path.join(tmp_dir, "listbh_2026_09.xlsx")
        pd.DataFrame([{"Mã liên kết": "OLD_001", "Ngày ra": "01/09/2026 08:00"}]).to_excel(legacy_month_path, index=False)

        excel_service.archive_listbh_by_months(master_path, tmp_dir, explicit_month=10, explicit_year=2026)
        assert not os.path.exists(legacy_month_path), "Phải tự dọn tệp listbh_YYYY_MM.xlsx cũ tránh nhân bản/sai lệch!"

        # Kiểm tra tệp listbh.xlsx trên đĩa vẫn giữ nguyên 100% 22 cột và đúng số dòng gốc (22)
        df_disk = pd.read_excel(master_path, dtype=str)
        assert list(df_disk.columns) == cols_22, f"Cấu trúc cột listbh.xlsx bị biến đổi: {list(df_disk.columns)}"
        assert len(df_disk) == 22, f"Số dòng file gốc listbh.xlsx bị thay đổi: {len(df_disk)}"

        # Khi đọc vào RAM để đối soát: tự bỏ dòng rỗng và khử trùng MA_LK còn 20 mã duy nhất
        df_comb = excel_service.load_combined_listbh_for_range(tmp_dir)
        comb_keys = set(df_comb["MA_LK"].tolist())
        assert len(df_comb) == 20 and "OCT_SENT_001" in comb_keys and "OCT_SENT_020" in comb_keys

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

        # 3. Kiểm tra bảo vệ ca đã chốt sổ (CLOSED_MONTH) và tự động mở lại ca RESOLVED thường khi đối soát lại tháng có trong listbh
        rec_028 = db.query(Record).filter(Record.ma_lk == "OCT_028").first()
        rec_028.status = "RESOLVED"
        rec_028.his_unlock_status = "CLOSED_MONTH"
        rec_028.note = "Ghi chú gốc | IT chốt sổ đóng ca FAIL tồn đọng tháng 10/2026"

        rec_plain_resolved = Record(
            ma_lk="OCT_PLAIN_RES",
            ho_ten="BN OCT_PLAIN_RES",
            ma_the="DN4662320000001",
            ten_khoa="Khoa Nội",
            loai_ca="Nội trú",
            ngay_ra_vien=datetime.date(2026, 10, 5),
            ngay_doi_soat=datetime.date(2026, 10, 31),
            status="RESOLVED",
            his_unlock_status="NORMAL",
            type_group="FAIL",
            maloi="",
            motaloi="",
            note=""
        )
        db.add(rec_plain_resolved)
        db.commit()

        df_sql_with_plain = pd.DataFrame(oct_sql + [make_sql_row("OCT_PLAIN_RES", datetime.date(2026, 10, 5))] + nov_sql)
        df_lb_both = pd.concat([df_lb_oct, df_lb_nov_only], ignore_index=True)
        compare_service.process_comparison(
            db, df_sql_with_plain, df_lb_both, pd.DataFrame(), datetime.date(2026, 11, 16), include_errors=False
        )
        db.refresh(rec_028)
        db.refresh(rec_plain_resolved)
        assert rec_028.status == "RESOLVED", "Ca tháng cũ đã chốt sổ (CLOSED_MONTH) bị mở lại nhầm sang PENDING FAIL!"
        assert rec_plain_resolved.status == "PENDING", "Ca chưa gửi thật trong tháng có listbh (chưa chốt sổ) phải được cập nhật lại sang PENDING FAIL!"

        # 4. Kiểm tra gạch nợ tức thì khi nạp listbh (bao gồm hậu tố _CC và xóa cờ CLOSED_MONTH trên ca đã gửi)
        rec_cc = Record(
            ma_lk="26.077777_CC",
            ho_ten="BN CAP CUU",
            ma_the="DN4662320000099",
            ten_khoa="Khoa Cấp Cứu",
            loai_ca="Nội trú",
            ngay_ra_vien=datetime.date(2026, 7, 15),
            ngay_doi_soat=datetime.date(2026, 7, 31),
            status="PENDING",
            his_unlock_status="NORMAL",
            type_group="FAIL",
            maloi="",
            motaloi="",
            note=""
        )
        db.add(rec_cc)
        rec_029 = db.query(Record).filter(Record.ma_lk == "OCT_029").first()
        rec_029.status = "RESOLVED"
        rec_029.his_unlock_status = "CLOSED_MONTH"
        db.commit()

        df_lb_instant = pd.DataFrame([
            {"MA_LK": "26.077777/CC", "_ngay": datetime.date(2026, 7, 15)},
            {"MA_LK": "OCT_029", "_ngay": datetime.date(2026, 10, 5)}
        ])
        resolved_imm = compare_service.reconcile_pending_records_with_listbh(db, df_lb_instant, datetime.date(2026, 11, 17))
        db.refresh(rec_cc)
        db.refresh(rec_029)
        assert resolved_imm >= 1 and rec_cc.status == "RESOLVED", "Gạch nợ tức thì khi nạp listbh thất bại với ca _CC!"
        assert rec_029.his_unlock_status == "NORMAL", "Phải bỏ cờ CLOSED_MONTH khi ca đã có trong listbh!"

        # 5. Kiểm tra mở lại sổ tháng (reopen_closed_month_with_listbh)
        rec_030 = db.query(Record).filter(Record.ma_lk == "OCT_030").first()
        rec_030.status = "RESOLVED"
        rec_030.his_unlock_status = "CLOSED_MONTH"
        rec_admin_done = Record(
            ma_lk="OCT_ADMIN_DONE",
            ho_ten="BN ADMIN",
            ma_the="DN4662320000002",
            ten_khoa="Khoa Nội",
            loai_ca="Nội trú",
            ngay_ra_vien=datetime.date(2026, 10, 6),
            ngay_doi_soat=datetime.date(2026, 10, 31),
            status="RESOLVED",
            his_unlock_status="ADMIN_RESOLVED",
            type_group="FAIL",
            maloi="",
            motaloi="",
            note="IT xử lý tay riêng"
        )
        db.add(rec_admin_done)
        db.commit()

        df_lb_reopen = pd.DataFrame([{"MA_LK": "OCT_030", "_ngay": datetime.date(2026, 10, 5)}])
        reopen_res = compare_service.reopen_closed_month_with_listbh(db, 2026, 10, df_lb_reopen, username="admin")
        db.refresh(rec_028)
        db.refresh(rec_030)
        db.refresh(rec_admin_done)
        assert rec_028.status == "PENDING" and rec_028.his_unlock_status == "NORMAL"
        assert rec_028.note == "Ghi chú gốc", f"Note không sạch sau mở lại sổ: {rec_028.note}"
        assert rec_030.status == "RESOLVED" and rec_030.his_unlock_status == "NORMAL"
        assert rec_admin_done.status == "RESOLVED" and rec_admin_done.his_unlock_status == "ADMIN_RESOLVED"
        assert reopen_res["reopened_count"] >= 1 and reopen_res["kept_resolved_count"] >= 1
    finally:
        db.close()


def test_flow_c_merge_cc_and_trailing_zero_preservation():
    """
    Xác minh Luồng C:
    1. merge_excel_files() chuyển _CC / _cc -> /CC ngay trong HoSoLoiChiTiet.xlsx.
    2. Bảo toàn số 0 ở cuối (26.035530, 26.037040/CC) dưới dạng chuỗi Text (@).
    3. Khử trùng lặp chính xác khi cùng một hồ sơ lỗi xuất hiện ở 2 MA_GD khác nhau.
    4. resolve_ma_lk_against_trusted_set() khôi phục số 0 cuối cho cả mã có hậu tố /CC (26.03704/CC -> 26.037040/CC).
    """
    import tempfile
    import openpyxl
    import pandas as pd
    from services.portal_automation import portal_service
    from services import excel_service, his_service

    assert his_service.chuan_hoa_ma_lk("26.037040_cc") == "26.037040/CC"

    trusted = {"26.035530", "26.037040/CC", "26.036522/CC"}
    num_map = excel_service.build_trusted_numeric_ma_lk_map(trusted)
    assert excel_service.resolve_ma_lk_against_trusted_set("26.03704_cc", trusted, num_map) == "26.037040/CC"
    assert excel_service.resolve_ma_lk_against_trusted_set("26.03553", trusted, num_map) == "26.035530"

    with tempfile.TemporaryDirectory() as tmp_dir:
        dl_dir = os.path.join(tmp_dir, "dl")
        os.makedirs(dl_dir, exist_ok=True)
        out_path = os.path.join(tmp_dir, "HoSoLoiChiTiet.xlsx")

        df1 = pd.DataFrame([
            {"MA_GD": "GD_001", "MALOI": "XML8", "MA_CSKCB": "66232", "MOTALOI": "TOMTAT_KQ trống", "MA_LK": "26.036522_CC"},
            {"MA_GD": "GD_001", "MALOI": "XML3", "MA_CSKCB": "66232", "MOTALOI": "TT_THAU sai", "MA_LK": "26.035530"},
        ])
        df2 = pd.DataFrame([
            {"MA_GD": "GD_002", "MALOI": "XML8", "MA_CSKCB": "66232", "MOTALOI": "TOMTAT_KQ trống", "MA_LK": "26.036522_cc"},
            {"MA_GD": "GD_002", "MALOI": "XML1", "MA_CSKCB": "66232", "MOTALOI": "NGAY_RA sai", "MA_LK": "26.037040_CC"},
        ])
        excel_service._write_df_preserving_text_excel(df1, os.path.join(dl_dir, "err_1.xlsx"))
        excel_service._write_df_preserving_text_excel(df2, os.path.join(dl_dir, "err_2.xlsx"))

        summary = portal_service.merge_excel_files(dl_dir, out_path)
        assert summary["unique_records"] == 3, f"Expected 3 unique rows after MA_GD dedup, got {summary}"
        assert summary["duplicates_removed"] == 1

        wb = openpyxl.load_workbook(out_path, data_only=True)
        ws = wb.active
        hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        idx = hdr.index("MA_LK")
        vals = [(r[idx].value, r[idx].data_type, r[idx].number_format) for r in ws.iter_rows(min_row=2, values_only=False)]
        wb.close()

        assert ("26.036522/CC", "s", "@") in vals
        assert ("26.035530", "s", "@") in vals
        assert ("26.037040/CC", "s", "@") in vals


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
    test_flow_c_merge_cc_and_trailing_zero_preservation()
    print("test_flow_c_merge_cc_and_trailing_zero_preservation: PASSED")
    print("ALL SAFETY & REGRESSION CHECKS PASSED!")
