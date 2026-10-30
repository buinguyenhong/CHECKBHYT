import os
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from auth import require_admin
from models import User, AppConfig
from database import get_db
from .models import ValRun, ValResult, ValidationError, ValCaseSnapshot
from .db import get_val_db, init_val_db
from .validation_service import get_current_progress, cancel_current_validation, run_validation_job
from .catalog import get_rule_catalog
from .source_adapter import load_xml_db_config, save_xml_db_config, XmlSourceAdapter
from .report_exporter import export_run_to_excel

router = APIRouter(prefix="/api/admin/xml-v2", tags=["XML Validator V2"])

@router.get("/progress")
def get_validation_progress(user: User = Depends(require_admin)):
    """Lấy tiến trình kiểm tra XML thời gian thực"""
    return get_current_progress()

@router.post("/cancel")
def cancel_validation(user: User = Depends(require_admin)):
    """Hủy đợt kiểm tra đang chạy"""
    success = cancel_current_validation()
    return {"success": success, "message": "Đã gửi lệnh hủy tiến trình." if success else "Không có tiến trình nào đang chạy."}

@router.get("/runs")
def list_validation_runs(
    limit: int = 20,
    db: Session = Depends(get_val_db),
    user: User = Depends(require_admin)
):
    """Lấy danh sách các đợt kiểm tra đã thực hiện"""
    init_val_db()
    runs = db.query(ValRun).order_by(desc(ValRun.id)).limit(limit).all()
    return [{
        "id": r.id,
        "run_code": r.run_code,
        "created_at": r.created_at.strftime("%d/%m/%Y %H:%M:%S") if r.created_at else "",
        "created_by": r.created_by,
        "scope_type": r.scope_type,
        "from_date": r.from_date.strftime("%d/%m/%Y") if r.from_date else "",
        "to_date": r.to_date.strftime("%d/%m/%Y") if r.to_date else "",
        "total_cases": r.total_cases,
        "processed_cases": r.processed_cases,
        "has_error_cases": r.has_error_cases,
        "no_error_cases": r.no_error_cases,
        "missing_xml_cases": r.missing_xml_cases,
        "incomplete_cases": r.incomplete_cases,
        "status": r.status,
        "log_message": r.log_message
    } for r in runs]

@router.get("/results")
def get_validation_results(
    run_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_val_db),
    user: User = Depends(require_admin)
):
    """Lấy danh sách hồ sơ kiểm tra theo đợt chạy (hỗ trợ lọc theo trạng thái và tìm kiếm MA_LK)"""
    init_val_db()
    # Nếu không truyền run_id, lấy đợt chạy mới nhất
    if not run_id:
        latest = db.query(ValRun).order_by(desc(ValRun.id)).first()
        if not latest:
            return {"run": None, "total": 0, "page": page, "page_size": page_size, "items": []}
        run_id = latest.id

    run = db.query(ValRun).filter(ValRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt kiểm tra.")

    query = db.query(ValResult).filter(ValResult.run_id == run_id)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(ValResult.overall_status == status_filter.upper())
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((ValResult.ma_lk.ilike(s)) | (ValResult.ho_ten.ilike(s)))

    total_items = query.count()
    items = query.order_by(desc(ValResult.violated_rules_count), ValResult.id).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "run": {
            "id": run.id,
            "run_code": run.run_code,
            "status": run.status,
            "total_cases": run.total_cases,
            "has_error_cases": run.has_error_cases,
            "no_error_cases": run.no_error_cases,
            "missing_xml_cases": run.missing_xml_cases,
            "incomplete_cases": run.incomplete_cases,
            "created_at": run.created_at.strftime("%d/%m/%Y %H:%M:%S") if run.created_at else ""
        },
        "total": total_items,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": r.id,
            "ma_lk": r.ma_lk,
            "ho_ten": r.ho_ten,
            "loai_ca": r.loai_ca,
            "ma_the": r.ma_the,
            "ma_y_te": r.ma_y_te,
            "ngay_ra_vien": r.ngay_ra_vien.strftime("%d/%m/%Y") if r.ngay_ra_vien else "",
            "applied_standard": r.applied_standard,
            "overall_status": r.overall_status,
            "violated_count": r.violated_rules_count,
            "passed_count": r.passed_rules_count,
            "incomplete_count": r.incomplete_rules_count,
            "summary": r.summary_text,
            "execution_time_ms": r.execution_time_ms
        } for r in items]
    }

@router.get("/case-detail")
def get_case_detail(
    run_id: int,
    ma_lk: str,
    db: Session = Depends(get_val_db),
    user: User = Depends(require_admin)
):
    """Lấy chi tiết vi phạm và snapshot dữ liệu của 1 hồ sơ"""
    res = db.query(ValResult).filter(ValResult.run_id == run_id, ValResult.ma_lk == ma_lk).first()
    if not res:
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả của hồ sơ này.")

    errors = db.query(ValidationError).filter(ValidationError.run_id == run_id, ValidationError.ma_lk == ma_lk).all()
    snapshot = db.query(ValCaseSnapshot).filter(ValCaseSnapshot.run_id == run_id, ValCaseSnapshot.ma_lk == ma_lk).first()

    return {
        "case_info": {
            "ma_lk": res.ma_lk,
            "ho_ten": res.ho_ten,
            "loai_ca": res.loai_ca,
            "ma_the": res.ma_the,
            "ma_y_te": res.ma_y_te,
            "ngay_ra_vien": res.ngay_ra_vien.strftime("%d/%m/%Y") if res.ngay_ra_vien else "",
            "applied_standard": res.applied_standard,
            "overall_status": res.overall_status,
            "violated_count": res.violated_rules_count,
            "passed_count": res.passed_rules_count,
            "summary": res.summary_text
        },
        "xml_tables_found": snapshot.xml_tables_found if snapshot else "",
        "errors": [{
            "id": e.id,
            "standard": e.standard,
            "rule_code": e.rule_code,
            "rule_name": e.rule_name,
            "xml_table": e.xml_table,
            "field_name": e.field_name,
            "actual_value": e.actual_value,
            "expected_condition": e.expected_condition,
            "message": e.message,
            "severity": e.severity
        } for e in errors]
    }

@router.get("/catalog")
def get_catalog_rules(user: User = Depends(require_admin)):
    """Lấy danh mục 123 quy tắc kiểm tra XML (gồm 116 quy tắc logic gốc + 7 nhóm quy tắc CTN 4750) để tra cứu"""
    return get_rule_catalog()

@router.get("/export-excel")
def export_results_excel(
    run_id: int,
    db: Session = Depends(get_val_db),
    user: User = Depends(require_admin)
):
    """Xuất file Excel báo cáo lỗi chi tiết"""
    run = db.query(ValRun).filter(ValRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Không tìm thấy đợt kiểm tra.")

    export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"BaoCao_ValidateXML_{run.run_code}.xlsx"
    filepath = os.path.join(export_dir, filename)

    export_run_to_excel(db, run_id, filepath)

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

@router.get("/config")
def get_xml_config(user: User = Depends(require_admin)):
    """Xem cấu hình kết nối CSDL XML"""
    cfg = load_xml_db_config()
    # Ẩn password
    safe_cfg = {**cfg, "password": "******" if cfg.get("password") else ""}
    return safe_cfg

@router.post("/config")
def update_xml_config(new_cfg: dict, user: User = Depends(require_admin)):
    """Cập nhật thông số kết nối CSDL XML (chỉ lưu cấu hình, không sửa DB)"""
    curr = load_xml_db_config()
    for k in ["driver", "server", "database", "auth", "user"]:
        if k in new_cfg and new_cfg[k] is not None:
            curr[k] = new_cfg[k]
    if new_cfg.get("password") and new_cfg["password"] != "******":
        curr["password"] = new_cfg["password"]
    if "use_nolock" in new_cfg and new_cfg["use_nolock"] is not None:
        curr["use_nolock"] = bool(new_cfg["use_nolock"])
    save_xml_db_config(curr)
    return {"status": "success", "message": "Đã lưu cấu hình kết nối CSDL XML."}

@router.post("/test-connection")
def test_xml_db_connection(payload: Optional[dict] = None, user: User = Depends(require_admin)):
    """Kiểm tra kết nối Read-Only tới SQL Server XML"""
    cfg = load_xml_db_config()
    if payload:
        for k in ["driver", "server", "database", "auth", "user"]:
            if k in payload and payload[k] is not None and str(payload[k]).strip() != "":
                cfg[k] = payload[k]
        if payload.get("password") and payload["password"] != "******":
            cfg["password"] = payload["password"]
    adapter = XmlSourceAdapter(cfg)
    ok, msg = adapter.test_connection()
    if ok:
        return {"status": "success", "message": msg}
    raise HTTPException(status_code=400, detail=msg)

@router.post("/run")
def trigger_validation_run(
    background_tasks: BackgroundTasks,
    payload: dict,
    user: User = Depends(require_admin),
    app_db: Session = Depends(get_db)
):
    """
    Kích hoạt đợt kiểm tra XML mới.
    Hỗ trợ 2 chế độ:
    1. use_current_unsent: lấy các hồ sơ chưa gửi cổng từ đợt đối soát hiện tại (bảng records có type_group='FAIL' hoặc 'LOI').
    2. cases: danh sách hồ sơ gửi trực tiếp từ client.
    """
    prog = get_current_progress()
    if prog["status"] == "RUNNING":
        return {"status": "error", "message": "Đang có một đợt kiểm tra khác đang chạy. Vui lòng đợi hoặc bấm Hủy."}

    cases_to_check = []
    use_unsent = payload.get("use_current_unsent", False)
    
    if use_unsent:
        # Lấy danh sách hồ sơ chưa gửi cổng từ đợt đối soát gần nhất trong bảng records (chỉ đọc)
        # BẮT BUỘC: chỉ lấy các ca chưa thành công (status != 'RESOLVED') thuộc đợt đối soát chỉ định hoặc gần nhất
        from models import Record
        from sqlalchemy import func, or_

        target_date_str = payload.get("doi_soat_date")
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.datetime.strptime(target_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Ngày đối soát không đúng định dạng YYYY-MM-DD.")

        unsent_filter = or_(Record.status != "RESOLVED", Record.status.is_(None))
        query = app_db.query(Record).filter(
            Record.type_group.in_(["FAIL", "LOI"]),
            unsent_filter
        )

        if not target_date:
            latest_date = app_db.query(func.max(Record.ngay_doi_soat)).filter(
                Record.type_group.in_(["FAIL", "LOI"]),
                unsent_filter
            ).scalar()
            target_date = latest_date

        if target_date:
            query = query.filter(Record.ngay_doi_soat == target_date)

        unsent_records = query.all()
        # Loại bỏ trùng MA_LK
        seen = set()
        for rec in unsent_records:
            lk = str(rec.ma_lk or "").strip()
            if lk and lk not in seen:
                seen.add(lk)
                cases_to_check.append({
                    "ma_lk": lk,
                    "ho_ten": rec.ho_ten or "",
                    "loai_ca": rec.loai_ca or "",
                    "ma_the": rec.ma_the or "",
                    "ma_y_te": rec.ma_y_te or "",
                    "ngay_ra_vien": rec.ngay_ra_vien
                })
    else:
        cases_to_check = payload.get("cases", [])

    if not cases_to_check:
        raise HTTPException(status_code=400, detail="Không có hồ sơ nào được chọn để kiểm tra XML.")

    background_tasks.add_task(
        run_validation_job,
        cases_meta=cases_to_check,
        scope_type=payload.get("scope_type", "UNSENT_BATCH"),
        from_date=None,
        to_date=None,
        username=user.username
    )

    return {
        "status": "success",
        "message": f"Đã bắt đầu kiểm tra XML cho {len(cases_to_check)} hồ sơ trong nền.",
        "total_cases": len(cases_to_check)
    }
