from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean
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
    sp_op = Column(String, default="dbo.sp_BCVP_095_DsDeNghiThanhToanBHYT_NgoaiTru_25a_CV5937")
    sp_ip = Column(String, default="dbo.sp_BCVP_096_DsDeNghiThanhToanBHYT_NoiTru_26A_CV5937")
    listbh_key_col = Column(String, default="Mã liên kết")
    listbh_date_col = Column(String, default="Ngày ra")
    auto_sync_enabled = Column(Boolean, default=False)
    auto_sync_time = Column(String, default="00:30")

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
    
    ngay_doi_soat = Column(Date, index=True, nullable=False)  # Ngày thực hiện đối soát
    status = Column(String, default="PENDING")  # 'PENDING' | 'WAITING_REVIEW' | 'RESOLVED'
    type_group = Column(String, default="FAIL")  # 'LOI' (Danh sách lỗi) | 'FAIL' (Danh sách fail)
    
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
