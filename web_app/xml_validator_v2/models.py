import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Boolean, Float, Index
from sqlalchemy.orm import declarative_base, relationship

BaseVal = declarative_base()

class ValRun(BaseVal):
    __tablename__ = "val_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_by = Column(String, default="admin")
    scope_type = Column(String, default="UNSENT_BATCH")  # 'UNSENT_BATCH' | 'DATE_RANGE' | 'MANUAL_LIST'
    from_date = Column(Date, nullable=True)
    to_date = Column(Date, nullable=True)
    
    total_cases = Column(Integer, default=0)
    processed_cases = Column(Integer, default=0)
    has_error_cases = Column(Integer, default=0)
    no_error_cases = Column(Integer, default=0)
    missing_xml_cases = Column(Integer, default=0)
    incomplete_cases = Column(Integer, default=0)
    
    status = Column(String, default="PENDING")  # 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
    percent = Column(Integer, default=0)
    log_message = Column(Text, default="")
    error_message = Column(Text, default="")

    results = relationship("ValResult", back_populates="run", cascade="all, delete-orphan")
    snapshots = relationship("ValCaseSnapshot", back_populates="run", cascade="all, delete-orphan")
    errors = relationship("ValidationError", back_populates="run", cascade="all, delete-orphan")


class ValCaseSnapshot(BaseVal):
    __tablename__ = "val_case_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("val_runs.id"), index=True, nullable=False)
    ma_lk = Column(String, index=True, nullable=False)
    ho_ten = Column(String, default="")
    ma_the = Column(String, default="")
    loai_ca = Column(String, default="")
    ma_y_te = Column(String, default="")
    ngay_ra_vien = Column(Date, nullable=True)
    
    xml_tables_found = Column(String, default="")  # Ví dụ: "XML1,XML2,XML3"
    raw_snapshot_json = Column(Text, default="{}")  # Dữ liệu JSON các bảng XML
    snapshot_at = Column(DateTime, default=datetime.datetime.utcnow)

    run = relationship("ValRun", back_populates="snapshots")


class ValResult(BaseVal):
    __tablename__ = "val_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("val_runs.id"), index=True, nullable=False)
    ma_lk = Column(String, index=True, nullable=False)
    ho_ten = Column(String, default="")
    ma_the = Column(String, default="")
    loai_ca = Column(String, default="")
    ma_y_te = Column(String, default="")
    ngay_ra_vien = Column(Date, nullable=True)
    
    applied_standard = Column(String, default="UNDETERMINED")  # '9324' | '4210' | '4750' | 'UNDETERMINED'
    standard_version = Column(String, default="1.0")
    
    # 7 trạng thái kết quả theo đặc tả
    overall_status = Column(String, index=True, nullable=False)
    # 'HAS_ERRORS' | 'NO_ERRORS_FOUND' | 'MISSING_XML' | 'INCOMPLETE_DATA' | 'RULESET_UNDETERMINED' | 'VALIDATION_FAILED' | 'PARTIAL'

    violated_rules_count = Column(Integer, default=0)
    passed_rules_count = Column(Integer, default=0)
    incomplete_rules_count = Column(Integer, default=0)
    not_applicable_count = Column(Integer, default=0)
    
    summary_text = Column(Text, default="")
    execution_time_ms = Column(Integer, default=0)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)

    run = relationship("ValRun", back_populates="results")
    errors = relationship("ValidationError", back_populates="result", cascade="all, delete-orphan")


class ValidationError(BaseVal):
    __tablename__ = "val_errors"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("val_runs.id"), index=True, nullable=False)
    result_id = Column(Integer, ForeignKey("val_results.id"), index=True, nullable=True)
    ma_lk = Column(String, index=True, nullable=False)
    
    standard = Column(String, nullable=False)  # '9324' | '4210' | '4750'
    rule_code = Column(String, index=True, nullable=False)
    rule_name = Column(String, default="")
    
    xml_table = Column(String, default="")      # Ví dụ: 'XML1', 'XML2', 'XML3'
    field_name = Column(String, default="")     # Ví dụ: 'THANH_TIEN', 'T_BHTT'
    actual_value = Column(Text, default="")
    expected_condition = Column(Text, default="")
    message = Column(Text, default="")
    severity = Column(String, default="ERROR")   # 'ERROR' | 'WARNING'
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    run = relationship("ValRun", back_populates="errors")
    result = relationship("ValResult", back_populates="errors")


class ValRuleCatalog(BaseVal):
    __tablename__ = "val_rule_catalog"

    id = Column(Integer, primary_key=True, index=True)
    standard = Column(String, index=True, nullable=False)  # '9324' | '4210' | '4750'
    rule_code = Column(String, index=True, nullable=False)
    rule_name = Column(String, nullable=False)
    description = Column(Text, default="")
    table_target = Column(String, default="")
    fields_target = Column(String, default="")
    category = Column(String, default="FORMAT_LOGIC")  # 'ARITHMETIC' | 'FORMAT_LOGIC' | 'CATALOG_LOOKUP' | 'CROSS_RECORD_DUP'
    is_active = Column(Boolean, default=True)
    implementation_status = Column(String, default="IMPLEMENTED")  # 'IMPLEMENTED' | 'PARTIAL' | 'PENDING_LOOKUP'
