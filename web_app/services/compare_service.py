import pandas as pd
import datetime
from sqlalchemy.orm import Session
from models import Record, RecordLog
from services.his_service import chuan_hoa_ma_lk

def process_comparison(
    db: Session,
    df_sql: pd.DataFrame,
    df_listbh: pd.DataFrame,
    df_hsloi: pd.DataFrame,
    ngay_doi_soat: datetime.date
) -> dict:
    """
    Thực hiện đối soát giữa SQL HIS, danh sách gửi BHYT và file báo cáo lỗi.
    Áp dụng các quy tắc tự động duyệt và kế thừa ghi chú xử lý.
    """
    if df_sql.empty:
        return {"total": 0, "loi": 0, "fail": 0, "sent": 0}

    # 1. Chuyển tập hợp danh sách đã gửi thành set để tìm kiếm nhanh O(1)
    sent_keys = set()
    if not df_listbh.empty:
        sent_keys = set(df_listbh["MA_LK"].dropna().astype(str).map(chuan_hoa_ma_lk))

    # 2. Xây dựng bản đồ lỗi (ma_lk -> DANH SÁCH các dòng lỗi chi tiết)
    error_map = {}
    if not df_hsloi.empty:
        for _, row in df_hsloi.iterrows():
            lk = chuan_hoa_ma_lk(row["MA_LK"])
            if lk:
                if lk not in error_map:
                    error_map[lk] = []
                error_map[lk].append({
                    "maloi": str(row.get("MALOI", "")).strip(),
                    "motaloi": str(row.get("MOTALOI", "")).strip(),
                    "ngay_ra": row.get("Ngày ra", None) if not pd.isna(row.get("Ngày ra")) else None
                })

    stats = {"total": len(df_sql), "loi": 0, "fail": 0, "sent": 0}

    # Danh mục lỗi đã biết (cho việc tự động thu thập lỗi mới)
    from models import ErrorDefinition
    known_defs = {(ed.error_code, ed.keyword) for ed in db.query(ErrorDefinition).all()}
    KEYWORDS = ["DIEN_BIEN_LS", "TOMTAT_KQ", "NGAY_TH_YL", "MA_TTDV", "PP_DIEUTRI", "MA_BENH_CHINh", "CHAN_DOAN_RV", "NAM_QT", "THANG_QT", "NGAY_RA", "NGUOI_THUC_HIEN", "MA_LOAI_KCB", "XML1", "XML2", "XML3", "XML4", "XML5", "XML7", "XML8"]

    # 3. Quét từng hồ sơ trong CSDL HIS
    for _, row in df_sql.iterrows():
        ma_lk = chuan_hoa_ma_lk(row["MA_LK"])
        if not ma_lk:
            continue

        # Kiểm tra xem ca này đã được gửi BHYT thành công hay chưa
        is_sent = (ma_lk in sent_keys)
        has_error = (ma_lk in error_map)

        # Dữ liệu đối soát hành chính với cơ chế fallback thông minh nếu bị NaN/nan
        loai_ca_val = row.get("Loại ca")
        if pd.isna(loai_ca_val) or str(loai_ca_val).strip().lower() in ["nan", "", "none"]:
            loai_ca = "Ngoại trú" if str(ma_lk).startswith("TN.") else "Nội trú"
        else:
            loai_ca = str(loai_ca_val).strip()

        ho_ten = str(row.get("Họ tên", ""))
        ma_the = str(row.get("Mã thẻ", ""))
        ten_khoa = str(row.get("Tên khoa", ""))
        ma_y_te = str(row.get("Mã y tế", ""))
        ngay_ra_vien = row.get("Ngày ra viện", None) if not pd.isna(row.get("Ngày ra viện")) else None

        if is_sent:
            # Quy tắc 4: Tự động chuyển thành RESOLVED cho toàn bộ bản ghi lỗi/fail cũ của ma_lk này
            existing_records = db.query(Record).filter(Record.ma_lk == ma_lk).all()
            for rec in existing_records:
                if rec.status != "RESOLVED":
                    rec.status = "RESOLVED"
                    rec.his_unlock_status = "NORMAL" # Reset trạng thái mở khóa khi đã gửi thành công
                    log = RecordLog(
                        record_id=rec.id,
                        username="system",
                        action="CHANGE_STATUS",
                        note="He thong tu dong duyet: Ca benh da gui thanh cong len cong BHYT"
                    )
                    db.add(log)
            stats["sent"] += 1
        else:
            # Chưa gửi thành công:
            if not has_error:
                # Không có lỗi chi tiết -> Bản ghi hành chính thuộc nhóm FAIL (IT xử lý)
                type_group = "FAIL"
                stats["fail"] += 1
                
                existing_record = db.query(Record).filter(
                    Record.ma_lk == ma_lk,
                    Record.type_group == "FAIL"
                ).first()
                
                if existing_record:
                    existing_record.ho_ten = ho_ten
                    existing_record.ma_the = ma_the
                    existing_record.ten_khoa = ten_khoa
                    existing_record.ma_y_te = ma_y_te
                    existing_record.ngay_ra_vien = ngay_ra_vien
                    existing_record.loai_ca = loai_ca
                    existing_record.ngay_doi_soat = ngay_doi_soat
                    
                    # Nếu ca FAIL này trước đó đã gửi thành công nay bị mở lại
                    if existing_record.status == "RESOLVED":
                        existing_record.status = "PENDING"
                        log = RecordLog(
                            record_id=existing_record.id,
                            username="system",
                            action="CHANGE_STATUS",
                            note="He thong tu dong mo lai: Ca benh chua gui duoc cong BHYT"
                        )
                        db.add(log)
                else:
                    new_rec = Record(
                        ma_lk=ma_lk,
                        ho_ten=ho_ten,
                        ma_the=ma_the,
                        ten_khoa=ten_khoa,
                        ma_y_te=ma_y_te,
                        ngay_ra_vien=ngay_ra_vien,
                        loai_ca=loai_ca,
                        ngay_doi_soat=ngay_doi_soat,
                        status="PENDING",
                        type_group="FAIL",
                        maloi="",
                        motaloi="",
                        ngay_ra=None,
                        note=""
                    )
                    db.add(new_rec)
                    db.flush()
                    
                    log_entry = RecordLog(
                        record_id=new_rec.id,
                        username="system",
                        action="CREATE",
                        note=f"Khoi tao doi soat ngay {ngay_doi_soat.strftime('%d/%m/%Y')}. Nhom: FAIL"
                    )
                    db.add(log_entry)
            else:
                # Có lỗi chi tiết -> TẠO 1 BẢN GHI RIÊNG BIỆT CHO MỖI DÒNG LỖI!
                # Khi đã có lỗi chi tiết, hồ sơ không còn thuộc định nghĩa FAIL
                # (có trong SQL, chưa có listbh, và chưa có danh sách lỗi).
                existing_fail_records = db.query(Record).filter(
                    Record.ma_lk == ma_lk,
                    Record.type_group == "FAIL",
                    Record.status != "RESOLVED"
                ).all()
                for fail_rec in existing_fail_records:
                    fail_rec.status = "RESOLVED"
                    log = RecordLog(
                        record_id=fail_rec.id,
                        username="system",
                        action="CHANGE_STATUS",
                        note="He thong tu dong dong nhom FAIL: Ho so da co trong danh sach loi chi tiet BHYT"
                    )
                    db.add(log)

                for err_detail in error_map[ma_lk]:
                    maloi = err_detail["maloi"]
                    motaloi = err_detail["motaloi"]
                    ngay_ra = err_detail["ngay_ra"]
                    
                    stats["loi"] += 1
                    
                    # A. Tự động thu thập mẫu lỗi mới chưa có trong danh mục hướng dẫn
                    kw = None
                    for k in KEYWORDS:
                        if k in motaloi:
                            kw = k
                            break
                    if (maloi, kw) not in known_defs and (maloi or kw):
                        new_def = ErrorDefinition(
                            error_code=maloi,
                            keyword=kw,
                            root_cause="Chưa rõ nguyên nhân (Hệ thống tự động quét)",
                            resolution="Chờ phòng IT bổ sung hướng dẫn chi tiết",
                            requires_his_reset=False
                        )
                        db.add(new_def)
                        db.flush()
                        known_defs.add((maloi, kw))

                    # B. Tìm hoặc tạo Record cho dòng lỗi cụ thể này
                    existing_record = db.query(Record).filter(
                        Record.ma_lk == ma_lk,
                        Record.maloi == maloi,
                        Record.motaloi == motaloi
                    ).first()
                    
                    if existing_record:
                        existing_record.ho_ten = ho_ten
                        existing_record.ma_the = ma_the
                        existing_record.ten_khoa = ten_khoa
                        existing_record.ma_y_te = ma_y_te
                        existing_record.ngay_ra_vien = ngay_ra_vien
                        existing_record.loai_ca = loai_ca
                        existing_record.ngay_doi_soat = ngay_doi_soat
                        existing_record.type_group = "LOI"
                        
                        if existing_record.status == "RESOLVED":
                            existing_record.status = "PENDING"
                            log = RecordLog(
                                record_id=existing_record.id,
                                username="system",
                                action="CHANGE_STATUS",
                                note="He thong tu dong mo lai: Loi chua duoc khac phuc va chua gui thanh cong"
                            )
                            db.add(log)
                    else:
                        new_rec = Record(
                            ma_lk=ma_lk,
                            ho_ten=ho_ten,
                            ma_the=ma_the,
                            ten_khoa=ten_khoa,
                            ma_y_te=ma_y_te,
                            ngay_ra_vien=ngay_ra_vien,
                            loai_ca=loai_ca,
                            ngay_doi_soat=ngay_doi_soat,
                            status="PENDING",
                            type_group="LOI",
                            maloi=maloi,
                            motaloi=motaloi,
                            ngay_ra=ngay_ra,
                            note=""
                        )
                        db.add(new_rec)
                        db.flush()
                        
                        log_entry = RecordLog(
                            record_id=new_rec.id,
                            username="system",
                            action="CREATE",
                            note=f"Khoi tao doi soat ngay {ngay_doi_soat.strftime('%d/%m/%Y')}. Nhom: LOI (Ma loi: {maloi})"
                        )
                        db.add(log_entry)

    db.commit()
    return stats
