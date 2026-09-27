import os
import sys
import datetime
import pandas as pd

# Add web_app to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from database import Base, SessionLocal, engine
from models import Record, RecordLog, ErrorDefinition
from services import compare_service

def test_reconciliation_logic():
    print("[*] Running reconciliation business logic tests...")
    
    # Force recreation of test tables in the SQLite database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Seed an ErrorDefinition
        ed1 = ErrorDefinition(
            error_code="XML7",
            keyword="NGAY_CT",
            root_cause="Test cause",
            resolution="Test resolution",
            requires_his_reset=True
        )
        db.add(ed1)
        db.commit()
        
        # Test Case 1: Old active LOI records are resolved and FAIL is created/updated with note
        # Patient MA_LK = '12345'
        # Old state: patient has active LOI record for 'XML7' in database
        loi_rec = Record(
            ma_lk="12345",
            ho_ten="Nguyen Van A",
            ma_the="DN401010101",
            ten_khoa="Khoa Ngoai",
            ma_y_te="YT123",
            ngay_ra_vien=datetime.date(2026, 6, 1),
            loai_ca="Nội trú",
            ngay_doi_soat=datetime.date(2026, 6, 2),
            status="PENDING",
            type_group="LOI",
            maloi="XML7",
            motaloi="Lỗi NGAY_CT thiếu thông tin ký",
            note=""
        )
        db.add(loi_rec)
        db.commit()
        
        # New run inputs:
        # - df_sql: Patient is still in SQL HIS
        df_sql = pd.DataFrame([{
            "MA_LK": "12345",
            "Loại ca": "Nội trú",
            "Họ tên": "Nguyen Van A",
            "Mã thẻ": "DN401010101",
            "Tên khoa": "Khoa Ngoai",
            "Mã y tế": "YT123",
            "Ngày ra viện": datetime.date(2026, 6, 1)
        }])
        
        # - df_listbh: Empty (patient not sent)
        df_listbh = pd.DataFrame(columns=["MA_LK", "_ngay"])
        
        # - df_hsloi: Empty (patient no longer has errors)
        df_hsloi = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra"])
        
        # Run comparison with include_errors = True
        stats = compare_service.process_comparison(
            db=db,
            df_sql=df_sql,
            df_listbh=df_listbh,
            df_hsloi=df_hsloi,
            ngay_doi_soat=datetime.date(2026, 6, 5),
            include_errors=True
        )
        
        # Assertions
        # 1. The old LOI record should be RESOLVED
        updated_loi = db.query(Record).filter(Record.ma_lk == "12345", Record.type_group == "LOI").first()
        assert updated_loi.status == "RESOLVED", f"Expected old LOI record to be RESOLVED, got {updated_loi.status}"
        
        # 2. A FAIL record should be created/updated with status PENDING and note "đã sửa lỗi cũ"
        fail_rec = db.query(Record).filter(Record.ma_lk == "12345", Record.type_group == "FAIL").first()
        assert fail_rec is not None, "Expected FAIL record to be created"
        assert fail_rec.status == "PENDING", f"Expected FAIL record status to be PENDING, got {fail_rec.status}"
        assert fail_rec.note.startswith("đã sửa lỗi cũ"), f"Expected FAIL record note to start with 'đã sửa lỗi cũ', got '{fail_rec.note}'"
        
        print("[+] Test Case 1: Active LOI resolved and downgraded to FAIL with note passed! [OK]")
        
        
        # Test Case 2: Partial error resolution
        # Old state: Patient '67890' has 2 active errors: 'XML5' and 'XML8'
        # New run: Only 'XML8' is in the error file, 'XML5' is corrected.
        # Check: 'XML5' should be RESOLVED, 'XML8' should remain PENDING.
        db.query(Record).delete()
        db.commit()
        
        rec_xml5 = Record(
            ma_lk="67890",
            ho_ten="Tran Van B",
            ma_the="DN402020202",
            ten_khoa="Khoa Noi",
            ma_y_te="YT456",
            ngay_ra_vien=datetime.date(2026, 6, 10),
            loai_ca="Nội trú",
            ngay_doi_soat=datetime.date(2026, 6, 11),
            status="PENDING",
            type_group="LOI",
            maloi="XML5",
            motaloi="Loi dien bien lam sang",
            note=""
        )
        rec_xml8 = Record(
            ma_lk="67890",
            ho_ten="Tran Van B",
            ma_the="DN402020202",
            ten_khoa="Khoa Noi",
            ma_y_te="YT456",
            ngay_ra_vien=datetime.date(2026, 6, 10),
            loai_ca="Nội trú",
            ngay_doi_soat=datetime.date(2026, 6, 11),
            status="PENDING",
            type_group="LOI",
            maloi="XML8",
            motaloi="Loi tom tat kq",
            note=""
        )
        db.add(rec_xml5)
        db.add(rec_xml8)
        db.commit()
        
        df_sql_2 = pd.DataFrame([{
            "MA_LK": "67890",
            "Loại ca": "Nội trú",
            "Họ tên": "Tran Van B",
            "Mã thẻ": "DN402020202",
            "Tên khoa": "Khoa Noi",
            "Mã y tế": "YT456",
            "Ngày ra viện": datetime.date(2026, 6, 10)
        }])
        
        # Only XML8 is in the new error file
        df_hsloi_2 = pd.DataFrame([{
            "MA_LK": "67890",
            "MALOI": "XML8",
            "MOTALOI": "Loi tom tat kq",
            "Ngày ra": datetime.date(2026, 6, 10)
        }])
        
        stats_2 = compare_service.process_comparison(
            db=db,
            df_sql=df_sql_2,
            df_listbh=df_listbh, # Empty (not sent)
            df_hsloi=df_hsloi_2,
            ngay_doi_soat=datetime.date(2026, 6, 15),
            include_errors=True
        )
        
        # Assertions
        updated_xml5 = db.query(Record).filter(Record.ma_lk == "67890", Record.maloi == "XML5").first()
        updated_xml8 = db.query(Record).filter(Record.ma_lk == "67890", Record.maloi == "XML8").first()
        
        assert updated_xml5.status == "RESOLVED", f"Expected XML5 to be RESOLVED, got {updated_xml5.status}"
        assert updated_xml8.status == "PENDING", f"Expected XML8 to remain PENDING, got {updated_xml8.status}"
        
        print("[+] Test Case 2: Partial error resolution (resolved XML5, kept XML8) passed! [OK]")
        
        # Test Case 3: Orphan LOI records
        # Case 3A: Clean orphan LOI (not in df_sql, not in df_listbh, not in df_hsloi) -> auto RESOLVED
        # Case 3B: Lingering orphan LOI (not in df_sql, not in df_listbh, but STILL in df_hsloi) -> keeps PENDING & warning note
        from models import ErrorHistoryArchive
        orphan_clean = Record(
            ma_lk="99991",
            ho_ten="Orphan Patient Clean",
            ma_the="DN403030303",
            ten_khoa="Khoa Cap Cuu",
            ma_y_te="YT991",
            ngay_ra_vien=datetime.date(2026, 6, 12),
            loai_ca="Ngoại trú",
            ngay_doi_soat=datetime.date(2026, 6, 12),
            status="PENDING",
            type_group="LOI",
            maloi="XML1",
            motaloi="Loi thieu thong tin han the",
            note=""
        )
        orphan_lingering = Record(
            ma_lk="99992",
            ho_ten="Orphan Patient Lingering",
            ma_the="DN404040404",
            ten_khoa="Khoa Kham Benh",
            ma_y_te="YT992",
            ngay_ra_vien=datetime.date(2026, 6, 12),
            loai_ca="Ngoại trú",
            ngay_doi_soat=datetime.date(2026, 6, 12),
            status="PENDING",
            type_group="LOI",
            maloi="XML2",
            motaloi="Loi ngay thanh toan",
            note=""
        )
        db.add(orphan_clean)
        db.add(orphan_lingering)
        db.commit()

        # Run reconciliation for date range 2026-06-10 to 2026-06-15:
        # SQL HIS only has 67890 (neither 99991 nor 99992)
        # df_hsloi has XML8 for 67890 AND XML2 for 99992 (lingering on portal)
        df_hsloi_3 = pd.DataFrame([
            {
                "MA_LK": "67890",
                "MALOI": "XML8",
                "MOTALOI": "Loi tom tat kq",
                "Ngày ra": datetime.date(2026, 6, 10)
            },
            {
                "MA_LK": "99992",
                "MALOI": "XML2",
                "MOTALOI": "Loi ngay thanh toan",
                "Ngày ra": datetime.date(2026, 6, 12)
            }
        ])
        
        df_sql_3 = pd.DataFrame([
            {
                "MA_LK": "67890",
                "Loại ca": "Nội trú",
                "Họ tên": "Tran Van B",
                "Mã thẻ": "DN402020202",
                "Tên khoa": "Khoa Noi",
                "Mã y tế": "YT456",
                "Ngày ra viện": datetime.date(2026, 6, 10)
            },
            {
                "MA_LK": "77777",
                "Loại ca": "Nội trú",
                "Họ tên": "Le Van C",
                "Mã thẻ": "DN405050505",
                "Tên khoa": "Khoa Noi",
                "Mã y tế": "YT777",
                "Ngày ra viện": datetime.date(2026, 6, 15)
            }
        ])
        
        stats_3 = compare_service.process_comparison(
            db=db,
            df_sql=df_sql_3,
            df_listbh=pd.DataFrame(),
            df_hsloi=df_hsloi_3,
            ngay_doi_soat=datetime.date(2026, 6, 15),
            include_errors=True
        )

        res_clean = db.query(Record).filter(Record.ma_lk == "99991").first()
        res_lingering = db.query(Record).filter(Record.ma_lk == "99992").first()
        arch_clean = db.query(ErrorHistoryArchive).filter(ErrorHistoryArchive.ma_lk == "99991").first()

        assert res_clean.status == "RESOLVED", f"Expected orphan_clean to be RESOLVED, got {res_clean.status}"
        assert arch_clean is not None and arch_clean.status == "RESOLVED", "Expected arch_clean to be archived as RESOLVED"
        assert res_lingering.status == "PENDING", f"Expected orphan_lingering to remain PENDING, got {res_lingering.status}"
        assert "Cảnh báo" in (res_lingering.note or ""), f"Expected warning note in orphan_lingering, got {res_lingering.note}"

        print("[+] Test Case 3: Orphan LOI auto-resolution and lingering portal warning passed! [OK]")
        
        print("[*] All tests completed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_reconciliation_logic()
