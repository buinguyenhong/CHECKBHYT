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
        
        print("[*] All tests completed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_reconciliation_logic()
