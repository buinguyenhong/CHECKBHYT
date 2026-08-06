import pandas as pd
import datetime
import re
from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Record, RecordLog
from services.his_service import chuan_hoa_ma_lk

def clean_error_desc(text: str) -> str:
    """Chuẩn hóa chuỗi mô tả lỗi: xóa khoảng trắng thừa, newline, tab và chuyển thành chuỗi sạch."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def deduplicate_database_records(db: Session):
    """
    Quét và loại bỏ các bản ghi trùng lặp (trùng ma_lk, maloi, motaloi sau khi chuẩn hóa)
    trong bảng records. Giữ lại bản ghi tốt nhất và xóa các bản ghi trùng khác.
    """
    try:
        # Lấy tất cả records nhóm LOI
        records = db.query(Record).filter(Record.type_group == "LOI").all()
        
        # Nhóm theo (ma_lk, normalized_maloi, normalized_motaloi)
        grouped = {}
        for rec in records:
            ma_lk = chuan_hoa_ma_lk(rec.ma_lk).upper()
            maloi = str(rec.maloi or "").strip().upper()
            motaloi = clean_error_desc(str(rec.motaloi or "")).lower()
            
            key = (ma_lk, maloi, motaloi)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(rec)
        
        deleted_count = 0
        modified_count = 0
        for key, rec_list in grouped.items():
            if len(rec_list) > 1:
                # Sắp xếp ưu tiên: PENDING trước, rồi đến ngày cập nhật mới nhất
                rec_list.sort(key=lambda r: (1 if r.status == "PENDING" else 0, r.updated_at or datetime.datetime.min), reverse=True)
                
                keep_rec = rec_list[0]
                for dup_rec in rec_list[1:]:
                    if dup_rec.note and not keep_rec.note:
                        keep_rec.note = dup_rec.note
                    db.delete(dup_rec)
                    deleted_count += 1
            else:
                keep_rec = rec_list[0]
                
            # Chuẩn hóa thông tin bản ghi được giữ lại
            normalized_maloi = key[1]
            normalized_motaloi = clean_error_desc(keep_rec.motaloi or "")
            normalized_ma_lk = keep_rec.ma_lk.upper()
            
            if keep_rec.maloi != normalized_maloi or keep_rec.motaloi != normalized_motaloi or keep_rec.ma_lk != normalized_ma_lk:
                keep_rec.maloi = normalized_maloi
                keep_rec.motaloi = normalized_motaloi
                keep_rec.ma_lk = normalized_ma_lk
                modified_count += 1
                    
        if deleted_count > 0 or modified_count > 0:
            db.commit()
            print(f"[DEDUPLICATE] Da tu dong xoa {deleted_count} ban ghi va chuan hoa {modified_count} ban ghi trong DB.")
    except Exception as e:
        print(f"[DEDUPLICATE] Loi khi don dep trung lap: {str(e)}")
        db.rollback()

def process_comparison(
    db: Session,
    df_sql: pd.DataFrame,
    df_listbh: pd.DataFrame,
    df_hsloi: pd.DataFrame,
    ngay_doi_soat: datetime.date,
    include_errors: bool = False
) -> dict:
    """
    Thực hiện đối soát giữa SQL HIS, danh sách gửi BHYT và file báo cáo lỗi.
    Áp dụng các quy tắc tự động duyệt và kế thừa ghi chú xử lý.
    """
    # Tự động dọn dẹp các bản ghi trùng lặp trong DB trước khi chạy đối soát mới
    deduplicate_database_records(db)

    if df_sql.empty:
        return {"total": 0, "loi": 0, "fail": 0, "sent": 0}

    # Dọn dẹp các ca FAIL cũ/mã lỗi từ lượt chạy trước thuộc cùng khoảng ngày nhưng không thuộc SQL HIS hiện tại
    current_sql_keys = set(df_sql["MA_LK"].dropna().astype(str).map(lambda x: chuan_hoa_ma_lk(x).upper()))
    sql_dates = [d for d in df_sql["Ngày ra viện"].dropna() if hasattr(d, "year") or isinstance(d, datetime.date)]
    if sql_dates:
        min_d = min(sql_dates)
        max_d = max(sql_dates)
        if isinstance(min_d, datetime.datetime):
            min_d = min_d.date()
        if isinstance(max_d, datetime.datetime):
            max_d = max_d.date()
            
        obsolete_fails = db.query(Record).filter(
            Record.type_group == "FAIL",
            Record.status != "RESOLVED",
            Record.ngay_ra_vien >= min_d,
            Record.ngay_ra_vien <= max_d
        ).all()
        
        for obs in obsolete_fails:
            if obs.ma_lk not in current_sql_keys:
                db.delete(obs)
        db.commit()

    # 1. Chuyển tập hợp danh sách đã gửi thành set để tìm kiếm nhanh O(1)
    sent_keys = set()
    if not df_listbh.empty:
        sent_keys = set(df_listbh["MA_LK"].dropna().astype(str).map(lambda x: chuan_hoa_ma_lk(x).upper()))

    # 2. Xây dựng bản đồ lỗi (ma_lk -> DANH SÁCH các dòng lỗi chi tiết đã lọc trùng)
    error_map = {}
    if not df_hsloi.empty:
        for _, row in df_hsloi.iterrows():
            lk = chuan_hoa_ma_lk(row["MA_LK"]).upper()
            if lk:
                maloi = str(row.get("MALOI", "")).strip().upper()
                motaloi = clean_error_desc(str(row.get("MOTALOI", "")))
                ngay_ra = row.get("Ngày ra", None) if not pd.isna(row.get("Ngày ra")) else None
                
                if lk not in error_map:
                    error_map[lk] = []
                
                # Tránh trùng lặp ngay trong danh sách đầu vào từ file Excel của cùng 1 hồ sơ
                if not any(item["maloi"] == maloi and item["motaloi"].lower() == motaloi.lower() for item in error_map[lk]):
                    error_map[lk].append({
                        "maloi": maloi,
                        "motaloi": motaloi,
                        "ngay_ra": ngay_ra
                    })

    stats = {"total": len(df_sql), "loi": 0, "fail": 0, "sent": 0}

    # Danh mục lỗi đã biết (cho việc tự động thu thập lỗi mới)
    from models import ErrorDefinition
    known_defs = {(ed.error_code, ed.keyword) for ed in db.query(ErrorDefinition).all()}
    KEYWORDS = ["DIEN_BIEN_LS", "TOMTAT_KQ", "NGAY_TH_YL", "MA_TTDV", "PP_DIEUTRI", "MA_BENH_CHINh", "CHAN_DOAN_RV", "NAM_QT", "THANG_QT", "NGAY_RA", "NGUOI_THUC_HIEN", "MA_LOAI_KCB", "XML1", "XML2", "XML3", "XML4", "XML5", "XML7", "XML8"]

    # 3. Quét từng hồ sơ trong CSDL HIS
    for _, row in df_sql.iterrows():
        ma_lk = chuan_hoa_ma_lk(row["MA_LK"]).upper()
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
                    d_cu_str = rec.ngay_doi_soat.strftime('%d/%m/%Y') if rec.ngay_doi_soat else "trước đó"
                    d_moi_str = ngay_doi_soat.strftime('%d/%m/%Y')
                    log_text = f"Hệ thống tự động duyệt: Ca bệnh đã gửi thành công lên cổng BHYT (đối soát ngày {d_moi_str})."
                    if rec.type_group == "LOI" and rec.maloi:
                        log_text += f" Lỗi [{rec.maloi}] (xuất hiện đợt {d_cu_str}) đã được sửa thành công."
                    else:
                        log_text += f" Ca FAIL (đợt {d_cu_str}) đã được khắc phục."
                    log = RecordLog(
                        record_id=rec.id,
                        username="system",
                        action="CHANGE_STATUS",
                        note=log_text
                    )
                    db.add(log)
            stats["sent"] += 1
        else:
            # Chưa gửi thành công:
            if not has_error:
                # Nếu không có tệp listbh đầu vào (hoặc rỗng), ta chưa đánh dấu FAIL lúc này, tránh sai lệch.
                if df_listbh is None or df_listbh.empty:
                    continue
                # Không có lỗi chi tiết -> Bản ghi hành chính thuộc nhóm FAIL (IT xử lý)
                type_group = "FAIL"
                stats["fail"] += 1
                
                # Biến cờ đánh dấu nếu ca này từng có lỗi cũ được sửa
                had_previous_active_errors = False
                prev_error_dates = []
                
                if include_errors:
                    existing_loi_records = db.query(Record).filter(
                        Record.ma_lk == ma_lk,
                        Record.type_group == "LOI",
                        Record.status != "RESOLVED"
                    ).all()
                    if existing_loi_records:
                        had_previous_active_errors = True
                        for loi_rec in existing_loi_records:
                            loi_rec.status = "RESOLVED"
                            d_cu_str = loi_rec.ngay_doi_soat.strftime('%d/%m/%Y') if loi_rec.ngay_doi_soat else "trước đó"
                            prev_error_dates.append(d_cu_str)
                            log = RecordLog(
                                record_id=loi_rec.id,
                                username="system",
                                action="CHANGE_STATUS",
                                note=f"Đã sửa lỗi cũ (đợt đối soát {d_cu_str}): Lỗi [{loi_rec.maloi}] không còn xuất hiện trong tệp lỗi chi tiết. Ca chuyển sang danh sách FAIL chờ đẩy lại."
                            )
                            db.add(log)
                
                existing_record = db.query(Record).filter(
                    Record.ma_lk == ma_lk,
                    Record.type_group == "FAIL"
                ).first()
                
                dates_str = ", ".join(sorted(list(set(prev_error_dates))))
                note_val = f"đã sửa lỗi cũ (đợt {dates_str})" if had_previous_active_errors else ""
                
                if existing_record:
                    existing_record.ho_ten = ho_ten
                    existing_record.ma_the = ma_the
                    existing_record.ten_khoa = ten_khoa
                    existing_record.ma_y_te = ma_y_te
                    existing_record.ngay_ra_vien = ngay_ra_vien
                    existing_record.loai_ca = loai_ca
                    existing_record.ngay_doi_soat = ngay_doi_soat
                    if note_val:
                        existing_record.note = note_val
                    
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
                        note=note_val
                    )
                    db.add(new_rec)
                    db.flush()
                    
                    log_entry = RecordLog(
                        record_id=new_rec.id,
                        username="system",
                        action="CREATE",
                        note=f"Khoi tao doi soat ngay {ngay_doi_soat.strftime('%d/%m/%Y')}. Nhom: FAIL" + (f" ({note_val})" if note_val else "")
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
 
                # Load tất cả bản ghi LOI đã có của ma_lk này để so khớp mềm dẻo trên bộ nhớ (tránh trùng do hoa thường/khoảng trắng)
                existing_loi_records = db.query(Record).filter(
                    Record.ma_lk == ma_lk,
                    Record.type_group == "LOI"
                ).all()
 
                if include_errors:
                    # Tự động đóng các bản ghi lỗi cũ không còn xuất hiện trong danh sách lỗi mới
                    for rec in existing_loi_records:
                        if rec.status != "RESOLVED":
                            rec_maloi = str(rec.maloi or "").strip().upper()
                            rec_motaloi = clean_error_desc(str(rec.motaloi or ""))
                            
                            found_in_new = False
                            for err_detail in error_map[ma_lk]:
                                new_maloi = err_detail["maloi"]
                                new_motaloi = err_detail["motaloi"]
                                if rec_maloi == new_maloi and rec_motaloi.lower() == new_motaloi.lower():
                                    found_in_new = True
                                    break
                            
                            if not found_in_new:
                                rec.status = "RESOLVED"
                                d_cu_str = rec.ngay_doi_soat.strftime('%d/%m/%Y') if rec.ngay_doi_soat else "trước đó"
                                new_codes = ", ".join(sorted(list(set([e["maloi"] for e in error_map[ma_lk] if e["maloi"]]))))
                                log = RecordLog(
                                    record_id=rec.id,
                                    username="system",
                                    action="CHANGE_STATUS",
                                    note=f"Đã sửa lần 1: Lỗi [{rec.maloi}] (từ đợt đối soát {d_cu_str}) đã khắc phục. Đợt này phát sinh lỗi mới: [{new_codes}]."
                                )
                                db.add(log)

                stats["loi"] += 1
                for err_detail in error_map[ma_lk]:
                    maloi = err_detail["maloi"]
                    motaloi = err_detail["motaloi"]
                    ngay_ra = err_detail["ngay_ra"]
                    
                    # A. Tự động thu thập mẫu lỗi mới chưa có trong danh mục hướng dẫn
                    kw = None
                    for k in KEYWORDS:
                        if k in motaloi:
                            kw = k
                            break
                    
                    is_known = False
                    maloi_clean = re.sub(r'[^A-Z0-9]', '', maloi.upper())
                    for ed_code, ed_kw in known_defs:
                        ed_clean = re.sub(r'[^A-Z0-9]', '', str(ed_code or "").upper())
                        if (ed_clean == maloi_clean or ed_clean.startswith(maloi_clean)) and ed_kw == kw:
                            is_known = True
                            break
                            
                    if not is_known and (maloi or kw):
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

                    # B. Tìm hoặc tạo Record cho dòng lỗi cụ thể này bằng cách so khớp mềm trên bộ nhớ
                    existing_record = None
                    for rec in existing_loi_records:
                        rec_maloi = str(rec.maloi or "").strip().upper()
                        rec_motaloi = clean_error_desc(str(rec.motaloi or ""))
                        if rec_maloi == maloi and rec_motaloi.lower() == motaloi.lower():
                            existing_record = rec
                            # Cập nhật và chuẩn hóa luôn thông tin lỗi trong DB
                            rec.maloi = maloi
                            rec.motaloi = motaloi
                            break
                    
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
                        
                        # Thêm bản ghi mới vào existing_loi_records để tránh tạo trùng nếu lặp lại
                        existing_loi_records.append(new_rec)
                        
                        log_entry = RecordLog(
                            record_id=new_rec.id,
                            username="system",
                            action="CREATE",
                            note=f"Khoi tao doi soat ngay {ngay_doi_soat.strftime('%d/%m/%Y')}. Nhom: LOI (Ma loi: {maloi})"
                        )
                        db.add(log_entry)

    db.commit()
    return stats
