import os
import sys
import tempfile
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add web_app to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from services.portal_automation import PortalAutomationService, add_portal_log, portal_logs

def test_portal_automation_logic():
    print("=== TEST 1: TEST PORTAL AUTOMATION INITIALIZATION & CONFIG UPDATE ===")
    service = PortalAutomationService(
        base_url="https://gdbhyt.baohiemxahoi.gov.vn/",
        ma_cskcb="66232",
        username="066091019320",
        password="TestPassword123"
    )
    assert service.ma_cskcb == "66232"
    assert service.username == "066091019320"
    assert service.password == "TestPassword123"

    service.update_config(ma_cskcb="99999", username="test_user")
    assert service.ma_cskcb == "99999"
    assert service.username == "test_user"
    print("-> PortalAutomationService config update PASSED!")

    print("\n=== TEST 2: TEST _merge_error_files EXCEL CONCATENATION ===")
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_file = os.path.join(tmp_dir, "HoSoLoiChiTiet.xlsx")

        # Create 3 dummy error excel files (emulating individual package downloads from portal)
        df1 = pd.DataFrame([
            {"Mã liên kết": "TN.001", "Mã lỗi": "XML1_01", "Nội dung lỗi": "Thiếu mã thẻ", "Ngày ra": "2026-08-01"},
            {"Mã liên kết": "TN.002", "Mã lỗi": "XML5_02", "Nội dung lỗi": "Thiếu diễn biến", "Ngày ra": "2026-08-02"}
        ])
        df2 = pd.DataFrame([
            {"MA_LK": "BA.101", "MALOI": "XML8_01", "MOTALOI": "Thiếu tóm tắt HSBA", "Ngày ra": "2026-08-03"}
        ])
        df3 = pd.DataFrame([
            {"Mã LK": "BA.102", "Mã lỗi": "XML3_05", "Chi tiết lỗi": "Sai giá thuốc", "NGAY_RA": "2026-08-04"}
        ])

        f1 = os.path.join(tmp_dir, "err_1.xlsx")
        f2 = os.path.join(tmp_dir, "err_2.xlsx")
        f3 = os.path.join(tmp_dir, "err_3.xlsx")

        df1.to_excel(f1, index=False)
        df2.to_excel(f2, index=False)
        df3.to_excel(f3, index=False)

        # Merge files
        count = service._merge_error_files(tmp_dir, dest_file)
        print(f"Merged error records count: {count}")
        assert count == 4, f"Expected 4 error records, got {count}"
        assert os.path.exists(dest_file), "Merged destination file should exist"

        merged_df = pd.read_excel(dest_file)
        print(f"Merged columns: {list(merged_df.columns)}")
        assert "MA_LK" in merged_df.columns, "MA_LK should be normalized"
        assert "MALOI" in merged_df.columns, "MALOI should be normalized"
        assert "MOTALOI" in merged_df.columns, "MOTALOI should be normalized"
        assert len(merged_df) == 4, f"Expected 4 rows, got {len(merged_df)}"
        print("-> _merge_error_files PASSED!")

    print("\n=== TEST 3: TEST add_portal_log BUFFER ===")
    add_portal_log("Test message 1")
    add_portal_log("Test message 2")
    assert len(portal_logs) >= 2
    assert "Test message 2" in portal_logs[-1]
    print("-> add_portal_log PASSED!")

    print("\n=== ALL PORTAL AUTOMATION UNIT TESTS PASSED 100%! ===")

if __name__ == "__main__":
    test_portal_automation_logic()
