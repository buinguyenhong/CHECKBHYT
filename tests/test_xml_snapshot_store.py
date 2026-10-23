import os
import tempfile
import unittest

from web_app.xml_validator import sqlite_snapshot_store as store


class SnapshotStoreTests(unittest.TestCase):
    def test_snapshots_are_append_only_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "archive.sqlite")
            conn = store.connect(db_path)
            try:
                run_id = store.create_run(conn, "20261001", "20261023")
                count = store.save_rows(
                    conn,
                    run_id=run_id,
                    ma_lk="TN.123",
                    loai_ca="Ngoại trú",
                    tiep_nhan_id=123,
                    xac_nhan_chi_phi_id=456,
                    xml_type="XML1",
                    source_table="XML1_CV130",
                    rows=[{"_xml_text": "<XML1><MA_LK>TN.123</MA_LK><NAM_QT>2026</NAM_QT></XML1>"}],
                )
                self.assertEqual(count, 1)
                grouped = store.load_run_rows(conn, run_id)
                self.assertIn("TN.123", grouped)
                self.assertIn("XML1", grouped["TN.123"])
                self.assertEqual(
                    grouped["TN.123"]["XML1"][0]["tree"].xpath("string(//*[local-name()='MA_LK'])"),
                    "TN.123",
                )
                # A second run does not overwrite the first run's snapshots.
                run2 = store.create_run(conn, "20261001", "20261023")
                store.save_rows(
                    conn,
                    run_id=run2,
                    ma_lk="TN.123",
                    xml_type="XML1",
                    source_table="XML1_CV130",
                    rows=[{"_xml_text": "<XML1><MA_LK>TN.123</MA_LK></XML1>"}],
                )
                rows = conn.execute("SELECT COUNT(*) FROM xml_case_snapshots").fetchone()[0]
                self.assertEqual(rows, 2)
                store.finish_run(conn, run_id, status="completed", cases_seen=1, cases_snapshotted=1)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
