import os
import sys
import datetime
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add web_app to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Record, ErrorHistoryArchive, AppConfig, User
from services.his_service import normalize_sql_list
from services.compare_service import process_comparison

def test_financial_fields_and_monthly_aggregation():
    print("=== TEST 1: TEST normalize_sql_list EXTRACTION ===")
    df_op = pd.DataFrame([
        {
            "column4": "TN.001",
            "TenBenhNhan": "Nguyen Van A",
            "SoBHYT": "DN4010123456789",
            "Ten_Phong_Kham": "Khám Nội",
            "ma_bn": "BN001",
            "NgayRa": "2026-08-01",
            "Tongcong": 1500000.0,
            "QuyBHYT_ChiTra": 1200000.0
        },
        {
            "column4": "TN.002",
            "TenBenhNhan": "Tran Thi B",
            "SoBHYT": "GD4010123456780",
            "Ten_Phong_Kham": "Khám Ngoại",
            "ma_bn": "BN002",
            "NgayRa": "2026-08-02",
            "Tongcong": 850000.0,
            "QuyBHYT_ChiTra": 680000.0
        }
    ])

    df_ip = pd.DataFrame([
        {
            "column4": "BA.101",
            "TenBenhNhan": "Le Van C",
            "SoBHYT": "HT4010123456781",
            "khoadieutri": "Khoa Ngoại",
            "ma_bn": "BN003",
            "NgayRa": "2026-08-03",
            "Tongcong": 5500000.0,
            "QuyBHYT_ChiTra": 4400000.0
        }
    ])

    df_norm = normalize_sql_list(df_op, df_ip)
    print(f"Normalized columns: {list(df_norm.columns)}")
    assert "Tổng cộng" in df_norm.columns, "Missing 'Tổng cộng' column in df_norm"
    assert "Tiền BHYT" in df_norm.columns, "Missing 'Tiền BHYT' column in df_norm"
    assert len(df_norm) == 3, f"Expected 3 rows, got {len(df_norm)}"
    assert df_norm.loc[df_norm["MA_LK"] == "TN.001", "Tổng cộng"].values[0] == 1500000.0
    assert df_norm.loc[df_norm["MA_LK"] == "TN.001", "Tiền BHYT"].values[0] == 1200000.0
    assert df_norm.loc[df_norm["MA_LK"] == "BA.101", "Tổng cộng"].values[0] == 5500000.0
    assert df_norm.loc[df_norm["MA_LK"] == "BA.101", "Tiền BHYT"].values[0] == 4400000.0
    print("-> normalize_sql_list test PASSED!")

    print("\n=== TEST 2: TEST process_comparison & RECORD FINANCIAL STORAGE ===")
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Create dummy listbh (TN.001 sent, TN.002 and BA.101 not sent)
    df_listbh = pd.DataFrame([
        {"MA_LK": "TN.001", "_ngay": datetime.date(2026, 8, 1)}
    ])

    # Create dummy hsloi: TN.002 has 2 errors! (XML3 and XML5)
    df_hsloi = pd.DataFrame([
        {"MA_LK": "TN.002", "MALOI": "XML3", "MOTALOI": "Lỗi thuốc", "Ngày ra": datetime.date(2026, 8, 2)},
        {"MA_LK": "TN.002", "MALOI": "XML5", "MOTALOI": "Lỗi diễn biến", "Ngày ra": datetime.date(2026, 8, 2)}
    ])

    stats = process_comparison(db, df_norm, df_listbh, df_hsloi, datetime.date(2026, 8, 5), include_errors=True)
    print(f"Comparison stats: {stats}")

    # Check records in DB
    recs = db.query(Record).all()
    print(f"Total records in DB: {len(recs)}")
    for r in recs:
        print(f"  Record ID={r.id}, MA_LK={r.ma_lk}, Type={r.type_group}, Maloi={r.maloi}, TongTien={r.tong_tien}, TienBHYT={r.tien_bhyt}")

    # BA.101 is FAIL
    fail_rec = db.query(Record).filter(Record.ma_lk == "BA.101").first()
    assert fail_rec is not None, "BA.101 should exist as FAIL"
    assert fail_rec.tong_tien == 5500000.0
    assert fail_rec.tien_bhyt == 4400000.0

    # TN.002 has 2 LOI records, each having Tongcong=850,000 and QuyBHYT=680,000
    loi_recs = db.query(Record).filter(Record.ma_lk == "TN.002").all()
    assert len(loi_recs) == 2, f"TN.002 should have 2 LOI records, got {len(loi_recs)}"
    for lr in loi_recs:
        assert lr.tong_tien == 850000.0
        assert lr.tien_bhyt == 680000.0

    # Check error_history_archive
    archs = db.query(ErrorHistoryArchive).filter(ErrorHistoryArchive.ma_lk == "TN.002").all()
    assert len(archs) == 2, f"Archive should have 2 records for TN.002, got {len(archs)}"
    for ar in archs:
        assert ar.tong_tien == 850000.0
        assert ar.tien_bhyt == 680000.0
    print("-> process_comparison & archive storage test PASSED!")

    print("\n=== TEST 3: TEST MULTI-ERROR CASE AGGREGATION (NO DUPLICATION) ===")
    # When calculating monthly summary:
    # Total cases in month: TN.001 (sent, from SQL), TN.002 (loi, from records), BA.101 (fail, from records)
    # TN.002 has 2 error rows. If summed naively, TN.002 amount would be 850,000 * 2 = 1,700,000.
    # Grouping by unique MA_LK should yield:
    # TN.002 amount = 850,000, TN.002 BHYT = 680,000.
    
    df_rec = pd.DataFrame([
        {
            "ma_lk": r.ma_lk,
            "type_group": r.type_group,
            "status": r.status,
            "maloi": r.maloi,
            "motaloi": r.motaloi,
            "tong_tien": float(r.tong_tien or 0.0),
            "tien_bhyt": float(r.tien_bhyt or 0.0),
            "month": "2026-08"
        }
        for r in recs
    ])

    df_rec_m = df_rec[df_rec["month"] == "2026-08"]
    lk_money_map = {}
    for _, row in df_rec_m.iterrows():
        lk = row["ma_lk"]
        tt = float(row.get("tong_tien", 0.0) or 0.0)
        tb = float(row.get("tien_bhyt", 0.0) or 0.0)
        if lk not in lk_money_map:
            lk_money_map[lk] = {"tong_tien": tt, "tien_bhyt": tb}
        else:
            if tt > lk_money_map[lk]["tong_tien"]:
                lk_money_map[lk]["tong_tien"] = tt
            if tb > lk_money_map[lk]["tien_bhyt"]:
                lk_money_map[lk]["tien_bhyt"] = tb

    # TN.002 has 2 errors in df_loi_m
    df_loi_m = df_rec_m[df_rec_m["type_group"] == "LOI"]
    loi_lks = set(df_loi_m["ma_lk"].unique())
    err_cases_val = len(loi_lks)
    err_amount_val = sum(lk_money_map.get(lk, {}).get("tong_tien", 0.0) for lk in loi_lks)
    err_bhyt_val = sum(lk_money_map.get(lk, {}).get("tien_bhyt", 0.0) for lk in loi_lks)

    print(f"LOI Unique Cases: {err_cases_val}")
    print(f"LOI Total Amount: {err_amount_val:,.0f} VNĐ (Expected: 850,000 VNĐ)")
    print(f"LOI BHYT Amount: {err_bhyt_val:,.0f} VNĐ (Expected: 680,000 VNĐ)")
    assert err_cases_val == 1, f"Expected 1 unique LOI case, got {err_cases_val}"
    assert err_amount_val == 850000.0, f"Expected 850,000 VNĐ, got {err_amount_val}"
    assert err_bhyt_val == 680000.0, f"Expected 680,000 VNĐ, got {err_bhyt_val}"

    # FAIL cases
    df_fail_m = df_rec_m[df_rec_m["type_group"] == "FAIL"]
    fail_lks = set(df_fail_m["ma_lk"].unique())
    fail_cases_val = len(fail_lks)
    fail_amount_val = sum(lk_money_map.get(lk, {}).get("tong_tien", 0.0) for lk in fail_lks)
    fail_bhyt_val = sum(lk_money_map.get(lk, {}).get("tien_bhyt", 0.0) for lk in fail_lks)

    print(f"FAIL Unique Cases: {fail_cases_val}")
    print(f"FAIL Total Amount: {fail_amount_val:,.0f} VNĐ (Expected: 5,500,000 VNĐ)")
    print(f"FAIL BHYT Amount: {fail_bhyt_val:,.0f} VNĐ (Expected: 4,400,000 VNĐ)")
    assert fail_cases_val == 1, f"Expected 1 unique FAIL case, got {fail_cases_val}"
    assert fail_amount_val == 5500000.0, f"Expected 5,500,000 VNĐ, got {fail_amount_val}"
    assert fail_bhyt_val == 4400000.0, f"Expected 4,400,000 VNĐ, got {fail_bhyt_val}"

    print("\n-> ALL TESTS PASSED SUCCESSFULLY! 100% OK")

if __name__ == "__main__":
    test_financial_fields_and_monthly_aggregation()
