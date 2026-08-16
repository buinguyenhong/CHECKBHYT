from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin' (IT) | 'user' (Khoa phòng)
    department_name = Column(String, index=True, nullable=True)  # ví dụ: 'Ngoại', 'Nội', 'Khám bệnh', v.v.

class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True)
    driver = Column(String, default="ODBC Driver 17 for SQL Server")
    server = Column(String, default="")
    database = Column(String, default="")
    auth = Column(String, default="Windows Auth")
    user = Column(String, default="")
    password = Column(String, default="")
    sp_op = Column(String, default="dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NgoaiTru_Optimized")
    sp_ip = Column(String, default="dbo.sp_BCVP_DsDeNghiThanhToanBHYT_NoiTru_Optimized")
    listbh_key_col = Column(String, default="Mã liên kết")
    listbh_date_col = Column(String, default="Ngày ra")
    auto_sync_enabled = Column(Boolean, default=False)
    auto_sync_time = Column(String, default="00:30")
    last_sync_date = Column(Date, nullable=True)
    last_tong_sql = Column(Integer, default=0)
    last_tong_bh = Column(Integer, default=0)
    last_da_gui = Column(Integer, default=0)
    last_loi = Column(Integer, default=0)
    last_fail = Column(Integer, default=0)
    last_resolved = Column(Integer, default=0)

    # Cấu hình tự động hóa Cổng BHYT (Playwright RPA)
    portal_url = Column(String, default="https://gdbhyt.baohiemxahoi.gov.vn/")
    portal_ma_cskcb = Column(String, default="66232")
    portal_username = Column(String, default="066091019320")
    portal_password = Column(String, default="Nguyenhong123@")

class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    ma_lk = Column(String, index=True, nullable=False)
    ho_ten = Column(String, default="")
    ma_the = Column(String, default="")
    ten_khoa = Column(String, index=True, default="")
    ma_y_te = Column(String, default="")
    ngay_ra_vien = Column(Date, nullable=True)
    loai_ca = Column(String, default="Ngoại trú")  # 'Ngoại trú' | 'Nội trú'
    
    tong_tien = Column(Float, default=0.0)      # Tổng cộng chi phí ca bệnh (Tongcong từ SP)
    tien_bhyt = Column(Float, default=0.0)      # Tiền BHYT chi trả (QuyBHYT_ChiTra từ SP)

    ngay_doi_soat = Column(Date, index=True, nullable=False)  # Ngày thực hiện đối soát
    status = Column(String, default="PENDING")  # 'PENDING' | 'WAITING_RESEND' | 'RESOLVED'
    type_group = Column(String, default="FAIL")  # 'LOI' (Danh sách lỗi) | 'FAIL' (Danh sách fail)
    his_unlock_status = Column(String, default="NORMAL") # 'NORMAL' (Bình thường) | 'UNLOCKED' (Đang được trả về khoa)
    
    maloi = Column(String, default="")
    motaloi = Column(String, default="")
    ngay_ra = Column(Date, nullable=True)
    note = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    logs = relationship("RecordLog", back_populates="record", cascade="all, delete-orphan")

class RecordLog(Base):
    __tablename__ = "record_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("records.id", ondelete="CASCADE"), nullable=False)
    username = Column(String, nullable=False)
    action = Column(String, nullable=False)  # 'CREATE', 'ADD_NOTE', 'CHANGE_STATUS'
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    record = relationship("Record", back_populates="logs")


class ErrorDefinition(Base):
    __tablename__ = "error_definitions"

    id = Column(Integer, primary_key=True, index=True)
    error_code = Column(String, index=True, nullable=False)       # MALOI (ví dụ: XML3, XML5)
    keyword = Column(String, index=True, nullable=True)           # Từ khóa trong MOTALOI (ví dụ: DIEN_BIEN_LS)
    root_cause = Column(String, nullable=True)                    # Nguyên nhân
    resolution = Column(String, nullable=True)                    # Cách xử lý
    requires_his_reset = Column(Boolean, default=False)           # Cờ đánh dấu có cần Reset HIS hay không


class ErrorHistoryArchive(Base):
    __tablename__ = "error_history_archive"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, nullable=True, index=True)
    ma_lk = Column(String, index=True, nullable=False)
    ho_ten = Column(String, default="")
    ma_the = Column(String, default="")
    ten_khoa = Column(String, index=True, default="")
    loai_ca = Column(String, default="Ngoại trú")
    ma_y_te = Column(String, default="")
    ngay_ra_vien = Column(Date, nullable=True)

    tong_tien = Column(Float, default=0.0)      # Tổng cộng chi phí ca bệnh (Tongcong từ SP)
    tien_bhyt = Column(Float, default=0.0)      # Tiền BHYT chi trả (QuyBHYT_ChiTra từ SP)

    maloi = Column(String, index=True, default="")
    motaloi = Column(Text, default="")
    ngay_doi_soat = Column(Date, index=True, nullable=False)
    thang_doi_soat = Column(String, index=True, nullable=False)  # Định dạng 'YYYY-MM'
    status = Column(String, index=True, default="PENDING")  # 'PENDING' | 'WAITING_REVIEW' | 'WAITING_RESEND' | 'RESOLVED'

    first_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    note_history = Column(Text, default="")


