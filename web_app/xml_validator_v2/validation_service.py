import os
import json
import time
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .models import ValRun, ValCaseSnapshot, ValResult, ValidationError
from .db import ValSessionLocal, init_val_db
from .source_adapter import XmlSourceAdapter
from .rule_models import CaseXmlData
from .rule_engine import ValidationEngine

# Biến theo dõi tiến trình trong bộ nhớ để phục vụ giao diện
CURRENT_VALIDATION_PROGRESS = {
    "run_id": None,
    "run_code": "",
    "status": "IDLE",  # 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
    "percent": 0,
    "total_cases": 0,
    "processed_cases": 0,
    "has_error_cases": 0,
    "no_error_cases": 0,
    "missing_xml_cases": 0,
    "incomplete_cases": 0,
    "message": "",
    "started_at": None,
    "is_cancelled": False
}

def get_current_progress() -> dict:
    global CURRENT_VALIDATION_PROGRESS
    return CURRENT_VALIDATION_PROGRESS

def cancel_current_validation() -> bool:
    global CURRENT_VALIDATION_PROGRESS
    if CURRENT_VALIDATION_PROGRESS["status"] == "RUNNING":
        CURRENT_VALIDATION_PROGRESS["is_cancelled"] = True
        CURRENT_VALIDATION_PROGRESS["message"] = "Đang gửi yêu cầu hủy tiến trình..."
        return True
    return False

def run_validation_job(
    cases_meta: List[Dict[str, Any]],
    scope_type: str = "UNSENT_BATCH",
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
    username: str = "admin",
    xml_adapter: Optional[XmlSourceAdapter] = None
):
    """
    Thực thi đợt kiểm tra XML cho danh sách hồ sơ trong background worker.
    """
    global CURRENT_VALIDATION_PROGRESS
    init_val_db()
    db: Session = ValSessionLocal()

    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y%m%d_%H%M%S")
    run_code = f"RUN_{now_str}_{now_dt.microsecond // 1000:03d}"
    
    val_run = ValRun(
        run_code=run_code,
        created_by=username,
        scope_type=scope_type,
        from_date=from_date,
        to_date=to_date,
        total_cases=len(cases_meta),
        processed_cases=0,
        status="RUNNING",
        percent=0,
        log_message="Bắt đầu khởi tạo đợt kiểm tra XML..."
    )
    db.add(val_run)
    db.commit()
    db.refresh(val_run)

    CURRENT_VALIDATION_PROGRESS.clear()
    CURRENT_VALIDATION_PROGRESS.update({
        "run_id": val_run.id,
        "run_code": run_code,
        "status": "RUNNING",
        "percent": 0,
        "total_cases": len(cases_meta),
        "processed_cases": 0,
        "has_error_cases": 0,
        "no_error_cases": 0,
        "missing_xml_cases": 0,
        "incomplete_cases": 0,
        "message": f"Bắt đầu kiểm tra {len(cases_meta)} hồ sơ...",
        "started_at": datetime.datetime.now().isoformat(),
        "is_cancelled": False
    })

    adapter = xml_adapter or XmlSourceAdapter()
    engine = ValidationEngine()

    try:
        total = len(cases_meta)
        chunk_size = 50
        has_error_total = 0
        no_error_total = 0
        missing_xml_total = 0
        incomplete_total = 0

        for i in range(0, total, chunk_size):
            if CURRENT_VALIDATION_PROGRESS["is_cancelled"]:
                val_run.status = "CANCELLED"
                val_run.log_message = "Tiến trình đã bị người dùng hủy."
                db.commit()
                CURRENT_VALIDATION_PROGRESS["status"] = "CANCELLED"
                CURRENT_VALIDATION_PROGRESS["message"] = "Đã hủy tiến trình kiểm tra."
                return

            chunk = cases_meta[i:i + chunk_size]
            ma_lk_list = [c["ma_lk"] for c in chunk if c.get("ma_lk")]

            CURRENT_VALIDATION_PROGRESS["message"] = f"Đang truy vấn dữ liệu XML từ SQL Server ({i+1}-{min(i+chunk_size, total)}/{total})..."
            
            # 1. Truy vấn XML an toàn theo lô (Read-only)
            fetch_res = adapter.fetch_xml_batch(ma_lk_list)
            if isinstance(fetch_res, tuple) and len(fetch_res) == 2:
                xml_dict, table_status = fetch_res
            else:
                xml_dict, table_status = fetch_res, {}

            # 2. Xử lý từng hồ sơ trong lô
            for case_info in chunk:
                if CURRENT_VALIDATION_PROGRESS["is_cancelled"]:
                    break

                lk = case_info["ma_lk"]
                case_xml_tables = xml_dict.get(lk, {})

                # Tạo snapshot dữ liệu
                xml1_data = case_xml_tables.get("XML1", [{}])[0] if case_xml_tables.get("XML1") else None
                xml2_data = case_xml_tables.get("XML2", [])
                xml3_data = case_xml_tables.get("XML3", [])
                xml4_data = case_xml_tables.get("XML4", [])
                xml5_data = case_xml_tables.get("XML5", [])
                xml6_data = case_xml_tables.get("XML6", [])
                xml7_data = case_xml_tables.get("XML7", [])
                xml8_data = case_xml_tables.get("XML8", [])
                xml9_data = case_xml_tables.get("XML9", [])
                xml10_data = case_xml_tables.get("XML10", [])
                xml11_data = case_xml_tables.get("XML11", [])
                xml12_data = case_xml_tables.get("XML12", [])
                xml13_data = case_xml_tables.get("XML13", [])
                xml14_data = case_xml_tables.get("XML14", [])
                xml15_data = case_xml_tables.get("XML15", [])

                case_xml_obj = CaseXmlData(
                    ma_lk=lk,
                    ho_ten=case_info.get("ho_ten", ""),
                    loai_ca=case_info.get("loai_ca", ""),
                    ma_the=case_info.get("ma_the", ""),
                    ngay_ra_vien=str(case_info.get("ngay_ra_vien", "")),
                    xml1=xml1_data,
                    xml2=xml2_data,
                    xml3=xml3_data,
                    xml4=xml4_data,
                    xml5=xml5_data,
                    xml6=xml6_data,
                    xml7=xml7_data,
                    xml8=xml8_data,
                    xml9=xml9_data,
                    xml10=xml10_data,
                    xml11=xml11_data,
                    xml12=xml12_data,
                    xml13=xml13_data,
                    xml14=xml14_data,
                    xml15=xml15_data,
                    raw_tables=case_xml_tables,
                    table_fetch_status=table_status
                )

                # Lưu snapshot vào CSDL
                tbl_names_found = ",".join(case_xml_tables.keys())
                snapshot = ValCaseSnapshot(
                    run_id=val_run.id,
                    ma_lk=lk,
                    ho_ten=case_info.get("ho_ten", ""),
                    ma_the=case_info.get("ma_the", ""),
                    loai_ca=case_info.get("loai_ca", ""),
                    ma_y_te=case_info.get("ma_y_te", ""),
                    ngay_ra_vien=case_info.get("ngay_ra_vien") if isinstance(case_info.get("ngay_ra_vien"), datetime.date) else None,
                    xml_tables_found=tbl_names_found,
                    raw_snapshot_json=json.dumps(case_xml_tables, ensure_ascii=False)
                )
                db.add(snapshot)

                # Thực thi kiểm tra quy tắc
                eval_res = engine.validate_case(case_xml_obj)

                # Lưu kết quả tổng hợp
                res_model = ValResult(
                    run_id=val_run.id,
                    ma_lk=lk,
                    ho_ten=case_info.get("ho_ten", ""),
                    ma_the=case_info.get("ma_the", ""),
                    loai_ca=case_info.get("loai_ca", ""),
                    ma_y_te=case_info.get("ma_y_te", ""),
                    ngay_ra_vien=case_info.get("ngay_ra_vien") if isinstance(case_info.get("ngay_ra_vien"), datetime.date) else None,
                    applied_standard=eval_res["applied_standard"],
                    overall_status=eval_res["overall_status"],
                    violated_rules_count=eval_res["violated_count"],
                    passed_rules_count=eval_res["passed_count"],
                    incomplete_rules_count=eval_res["incomplete_count"],
                    not_applicable_count=eval_res["not_applicable_count"],
                    summary_text=eval_res["summary"],
                    execution_time_ms=eval_res["execution_time_ms"]
                )
                db.add(res_model)
                db.flush()  # Lấy ID của res_model để gán vào các vi phạm

                # Lưu từng vi phạm nếu có
                for v in eval_res["violations"]:
                    err_model = ValidationError(
                        run_id=val_run.id,
                        result_id=res_model.id,
                        ma_lk=lk,
                        standard=v.standard,
                        rule_code=v.rule_code,
                        rule_name=v.rule_name,
                        xml_table=v.xml_table,
                        field_name=v.field_name,
                        actual_value=str(v.actual_value),
                        expected_condition=str(v.expected_condition),
                        message=v.message,
                        severity=v.severity
                    )
                    db.add(err_model)

                # Cập nhật số đếm
                st = eval_res["overall_status"]
                if st == "HAS_ERRORS":
                    has_error_total += 1
                elif st == "NO_ERRORS_FOUND":
                    no_error_total += 1
                elif st == "MISSING_XML":
                    missing_xml_total += 1
                elif st == "INCOMPLETE_DATA":
                    incomplete_total += 1

                CURRENT_VALIDATION_PROGRESS["processed_cases"] += 1
                CURRENT_VALIDATION_PROGRESS["has_error_cases"] = has_error_total
                CURRENT_VALIDATION_PROGRESS["no_error_cases"] = no_error_total
                CURRENT_VALIDATION_PROGRESS["missing_xml_cases"] = missing_xml_total
                CURRENT_VALIDATION_PROGRESS["incomplete_cases"] = incomplete_total

            pct = int((CURRENT_VALIDATION_PROGRESS["processed_cases"] / total) * 100) if total > 0 else 100
            CURRENT_VALIDATION_PROGRESS["percent"] = pct
            val_run.processed_cases = CURRENT_VALIDATION_PROGRESS["processed_cases"]
            val_run.has_error_cases = has_error_total
            val_run.no_error_cases = no_error_total
            val_run.missing_xml_cases = missing_xml_total
            val_run.incomplete_cases = incomplete_total
            val_run.percent = pct
            db.commit()

        if CURRENT_VALIDATION_PROGRESS["is_cancelled"]:
            val_run.status = "CANCELLED"
            val_run.log_message = f"Tiến trình đã bị người dùng hủy. Đã xử lý {CURRENT_VALIDATION_PROGRESS['processed_cases']}/{total} hồ sơ."
            db.commit()
            CURRENT_VALIDATION_PROGRESS["status"] = "CANCELLED"
            CURRENT_VALIDATION_PROGRESS["message"] = val_run.log_message
            return

        val_run.status = "COMPLETED"
        val_run.percent = 100
        val_run.log_message = f"Hoàn tất kiểm tra {total} hồ sơ. Lỗi: {has_error_total}, Đạt: {no_error_total}, Thiếu XML: {missing_xml_total}."
        db.commit()

        CURRENT_VALIDATION_PROGRESS["status"] = "COMPLETED"
        CURRENT_VALIDATION_PROGRESS["percent"] = 100
        CURRENT_VALIDATION_PROGRESS["message"] = val_run.log_message

    except Exception as e:
        val_run.status = "FAILED"
        val_run.error_message = str(e)
        val_run.log_message = f"Gặp sự cố lỗi: {str(e)}"
        db.commit()
        CURRENT_VALIDATION_PROGRESS["status"] = "FAILED"
        CURRENT_VALIDATION_PROGRESS["message"] = f"Lỗi thực thi: {str(e)}"
        print(f"[!] Validation service error: {e}")

    finally:
        db.close()
