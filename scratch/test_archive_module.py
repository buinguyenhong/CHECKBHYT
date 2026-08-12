import sys
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_app'))

from database import Base
from models import Record, ErrorHistoryArchive
from services.compare_service import sync_archive_error, backfill_archive_from_records

def test_archive_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    print("[TEST 1] Testing Record creation and sync_archive_error...")
    rec = Record(
        ma_lk="260812_001",
        ho_ten="Nguyen Van A",
        ma_the="DN401010101010",
        ten_khoa="Khoa Ngoại",
        loai_ca="Nội trú",
        ma_y_te="BA12345",
        ngay_ra_vien=datetime.date(2026, 8, 12),
        ngay_doi_soat=datetime.date(2026, 8, 12),
        status="PENDING",
        type_group="LOI",
        maloi="XML 3",
        motaloi="NGUOI_THUC_HIEN khong duoc de trong",
        note="Ghi chu ban dau"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    sync_archive_error(db, rec, note="Ghi chu ban dau")
    db.commit()

    arch = db.query(ErrorHistoryArchive).filter(ErrorHistoryArchive.ma_lk == "260812_001").first()
    assert arch is not None, "ErrorHistoryArchive record should exist"
    assert arch.status == "PENDING"
    assert arch.thang_doi_soat == "2026-08"
    assert arch.ten_khoa == "Khoa Ngoại"
    print("-> Test 1 PASSED: Archive created successfully!")

    print("[TEST 2] Testing Status update to RESOLVED...")
    rec.status = "RESOLVED"
    sync_archive_error(db, rec, resolved=True, resolved_by="system", note="He thong tu dong duyet")
    db.commit()

    arch = db.query(ErrorHistoryArchive).filter(ErrorHistoryArchive.ma_lk == "260812_001").first()
    assert arch.status == "RESOLVED"
    assert arch.resolved_at is not None
    assert arch.resolved_by == "system"
    assert "He thong tu dong duyet" in arch.note_history
    print("-> Test 2 PASSED: Archive resolved status updated successfully!")

    print("[TEST 3] Testing backfill mechanism...")
    rec2 = Record(
        ma_lk="260812_002",
        ho_ten="Tran Thi B",
        ma_the="DN401020202020",
        ten_khoa="Khoa Sản",
        loai_ca="Ngoại trú",
        ngay_doi_soat=datetime.date(2026, 7, 15),
        status="PENDING",
        type_group="LOI",
        maloi="XML 5",
        motaloi="DIEN_BIEN_LS khong duoc de trong"
    )
    db.add(rec2)
    db.commit()

    # Clear archive table and run backfill
    db.query(ErrorHistoryArchive).delete()
    db.commit()

    backfill_archive_from_records(db)

    count = db.query(ErrorHistoryArchive).count()
    assert count == 2, f"Backfill should restore 2 records, got {count}"
    arch2 = db.query(ErrorHistoryArchive).filter(ErrorHistoryArchive.ma_lk == "260812_002").first()
    assert arch2.thang_doi_soat == "2026-07"
    print("-> Test 3 PASSED: Backfill completed successfully!")

    db.close()
    print("[ALL TESTS COMPLETED SUCCESSFULLY!]")

if __name__ == "__main__":
    test_archive_engine()
