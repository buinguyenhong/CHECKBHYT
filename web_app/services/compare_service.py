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

    # 2. Xây dựng bản đồ lỗi (ma_lk -> error_detail)
    error_map = {}
    if not df_hsloi.empty:
        for _, row in df_hsloi.iterrows():
            lk = chuan_hoa_ma_lk(row["MA_LK"])
            if lk:
                error_map[lk] = {
                    "maloi": str(row.get("MALOI", "")).strip(),
                    "motaloi": str(row.get("MOTALOI", "")).strip(),
                    "ngay_ra": row.get("Ngày ra", None) if not pd.isna(row.get("Ngày ra")) else None
                }

    stats = {"total": len(df_sql), "loi": 0, "fail": 0, "sent": 0}

    # 3. Quét từng hồ sơ trong SQL HIS
    for _, row in df_sql.iterrows():
        ma_lk = chuan_hoa_ma_lk(row["MA_LK"])
        if not ma_lk:
            continue

        # Kiểm tra xem ca này đã được gửi BHYT thành công hay chưa
        is_sent = (ma_lk in sent_keys)
        
        # Xác định nhóm lỗi
        has_error = (ma_lk in error_map)
        
        # Kiểm tra xem bản ghi đối soát (ma_lk) đã tồn tại trong CSDL chưa
        existing_record = db.query(Record).filter(
            Record.ma_lk == ma_lk
        ).first()

        # Dữ liệu đối soát hành chính
        loai_ca = str(row.get("Loại ca", "Ngoại trú"))
        ho_ten = str(row.get("Họ tên", ""))
        ma_the = str(row.get("Mã thẻ", ""))
        ten_khoa = str(row.get("Tên khoa", ""))
        ma_y_te = str(row.get("Mã y tế", ""))
        ngay_ra_vien = row.get("Ngày ra viện", None) if not pd.isna(row.get("Ngày ra viện")) else None

        # Phân loại trạng thái mặc định
        if is_sent:
            status = "RESOLVED"
            type_group = "FAIL"
            stats["sent"] += 1
            maloi = ""
            motaloi = ""
            ngay_ra = None
        else:
            status = "PENDING"
            if has_error:
                type_group = "LOI"
                stats["loi"] += 1
                err_detail = error_map[ma_lk]
                maloi = err_detail["maloi"]
                motaloi = err_detail["motaloi"]
                ngay_ra = err_detail["ngay_ra"]
            else:
                type_group = "FAIL"
                stats["fail"] += 1
                maloi = ""
                motaloi = ""
                ngay_ra = None

        if existing_record:
            # 1. Cập nhật thông tin thô
            existing_record.ho_ten = ho_ten
            existing_record.ma_the = ma_the
            existing_record.ten_khoa = ten_khoa
            existing_record.ma_y_te = ma_y_te
            existing_record.ngay_ra_vien = ngay_ra_vien
            existing_record.loai_ca = loai_ca
            existing_record.ngay_doi_soat = ngay_doi_soat  # Cập nhật ngày đối soát hiện tại

            # Áp dụng Quy tắc 3: Note (ghi chú) được tự động bảo toàn và kế thừa (không thay đổi)

            # Áp dụng Quy tắc 4: Tự động chuyển thành RESOLVED nếu ca này đang chờ và nay đã gửi thành công
            if is_sent:
                if existing_record.status != "RESOLVED":
                    existing_record.status = "RESOLVED"
                    log = RecordLog(
                        record_id=existing_record.id,
                        username="system",
                        action="CHANGE_STATUS",
                        note="He thong tu dong duyet: Ca benh da gui thanh cong len cong BHYT"
                    )
                    db.add(log)
            else:
                # Nếu chưa gửi thành công và có mã lỗi mới, cập nhật lỗi
                if has_error:
                    existing_record.type_group = "LOI"
                    existing_record.maloi = maloi
                    existing_record.motaloi = motaloi
                    if ngay_ra:
                        existing_record.ngay_ra = ngay_ra
                else:
                    # Nếu là ca Fail và trạng thái cũ đã được đánh dấu RESOLVED trước đó, giữ nguyên
                    pass
        else:
            # Tạo bản ghi đối soát mới hoàn toàn
            new_rec = Record(
                ma_lk=ma_lk,
                ho_ten=ho_ten,
                ma_the=ma_the,
                ten_khoa=ten_khoa,
                ma_y_te=ma_y_te,
                ngay_ra_vien=ngay_ra_vien,
                loai_ca=loai_ca,
                ngay_doi_soat=ngay_doi_soat,
                status=status,
                type_group=type_group,
                maloi=maloi,
                motaloi=motaloi,
                ngay_ra=ngay_ra,
                note=""
            )
            db.add(new_rec)
            db.flush()

            # Lưu log hệ thống khởi tạo
            log_entry = RecordLog(
                record_id=new_rec.id,
                username="system",
                action="CREATE",
                note=f"Khoi tao doi soat ngay {ngay_doi_soat.strftime('%d/%m/%Y')}. Nhom: {type_group}"
            )
            db.add(log_entry)

    db.commit()
    return stats
