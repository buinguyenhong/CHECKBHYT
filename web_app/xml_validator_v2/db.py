import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import BaseVal

VAL_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "xml_validation_v2.db")
VAL_DB_URL = f"sqlite:///{os.path.abspath(VAL_DB_FILE)}"

val_engine = create_engine(
    VAL_DB_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

ValSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=val_engine)

def get_val_db():
    db = ValSessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_val_db():
    """Tự động khởi tạo cấu trúc bảng SQLite riêng nếu chưa có"""
    BaseVal.metadata.create_all(bind=val_engine)
    return True
