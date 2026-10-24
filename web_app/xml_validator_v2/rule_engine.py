import time
from typing import Dict, Any, List, Tuple
from .rule_models import CaseXmlData, RuleResult, RuleStatus, RuleViolation
from .rules import check_rules_9324, check_rules_4210, check_rules_4750, check_rules_4750_ctn
from .catalog import get_rule_catalog, get_rule_required_tables

class ValidationEngine:
    """
    Bộ máy thực thi kiểm tra quy tắc XML độc lập cho từng hồ sơ.
    Hỗ trợ đa chuẩn: 9324, 4210, 4750.
    """
    def __init__(self, default_standard: str = "AUTO"):
        self.default_standard = default_standard

    def detect_standard(self, case: CaseXmlData) -> str:
        """
        Nhận diện bộ quy tắc áp dụng dựa trên dữ liệu XML1 và các bảng liên quan.
        Không tự ý đoán nếu không có bất kỳ căn cứ nào.
        """
        xml1 = case.xml1
        if not xml1:
            return "UNDETERMINED"

        # Dấu hiệu nhận biết chuẩn 4750 / CV 130:
        # Trường T_TONGCHI_BV, MA_LOAI_KCB định dạng mới, hoặc các trường đặc thù CV 130
        keys_4750 = ["T_TONGCHI_BV", "MA_TAI_NAN", "CAN_NANG", "SO_CCCD", "MA_THE_TAM"]
        if any(k in xml1 for k in keys_4750) or "XML11" in case.raw_tables or "XML13" in case.raw_tables or "XML14" in case.raw_tables:
            return "4750"

        # Dấu hiệu nhận biết chuẩn 4210:
        keys_4210 = ["TONG_CHI", "T_BNCCT", "NAM_QT", "THANG_QT"]
        if any(k in xml1 for k in keys_4210):
            return "4210"

        # Dấu hiệu chuẩn 9324:
        if "T_TONGCHI" in xml1 and "T_BNCCT" not in xml1:
            return "9324"

        # Nếu người dùng có cấu hình chuẩn chỉ định rõ ràng:
        if self.default_standard in ["9324", "4210", "4750"]:
            return self.default_standard

        return "UNDETERMINED"

    def validate_case(self, case: CaseXmlData) -> Dict[str, Any]:
        """
        Thực hiện kiểm tra toàn diện cho một hồ sơ bệnh nhân.
        Trả về dict chi tiết kết quả và trạng thái tổng hợp.
        """
        start_time = time.time()
        
        # 1. Kiểm tra sự tồn tại của XML
        if not case.xml1 and not case.xml2 and not case.xml3 and not case.raw_tables:
            return {
                "ma_lk": case.ma_lk,
                "ho_ten": case.ho_ten,
                "loai_ca": case.loai_ca,
                "ma_the": case.ma_the,
                "ngay_ra_vien": case.ngay_ra_vien,
                "applied_standard": "UNDETERMINED",
                "overall_status": "MISSING_XML",
                "violated_count": 0,
                "passed_count": 0,
                "incomplete_count": 0,
                "not_applicable_count": 0,
                "violations": [],
                "rule_results": [],
                "summary": "Không tìm thấy dữ liệu XML của hồ sơ trên SQL Server.",
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        # 2. Nhận diện chuẩn
        standard = self.detect_standard(case)
        if standard == "UNDETERMINED":
            return {
                "ma_lk": case.ma_lk,
                "ho_ten": case.ho_ten,
                "loai_ca": case.loai_ca,
                "ma_the": case.ma_the,
                "ngay_ra_vien": case.ngay_ra_vien,
                "applied_standard": "UNDETERMINED",
                "overall_status": "RULESET_UNDETERMINED",
                "violated_count": 0,
                "passed_count": 0,
                "incomplete_count": 0,
                "not_applicable_count": 0,
                "violations": [],
                "rule_results": [],
                "summary": "Chưa xác định được bộ quy tắc áp dụng (9324, 4210 hay 4750) từ dữ liệu XML.",
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        # 3. Thực thi bộ quy tắc tương ứng
        try:
            if standard == "9324":
                results = check_rules_9324(case)
            elif standard == "4210":
                results = check_rules_4210(case)
            else:  # 4750
                results = check_rules_4750(case) + check_rules_4750_ctn(case)

            # 3.1. Đối chiếu danh mục quy tắc để ghi nhận các quy tắc chưa triển khai code
            evaluated_codes = {r.rule_code for r in results}
            catalog = get_rule_catalog()
            std_catalog_rules = [r for r in catalog if r["standard"] == standard]

            for cat_r in std_catalog_rules:
                c_code = cat_r["rule_code"]
                if c_code not in evaluated_codes:
                    results.append(RuleResult(
                        rule_code=c_code,
                        standard=standard,
                        rule_name=cat_r["rule_name"],
                        status=RuleStatus.INCOMPLETE_DATA,
                        reason="Quy tắc chưa có mã thực thi trong phiên bản hiện tại hoặc thiếu nguồn danh mục chuẩn."
                    ))

            # 3.2. BẢO VỆ XUYÊN SUỐT: Kiểm tra bảng XML phụ thuộc đối với mọi quy tắc (Chặn False Negative)
            # Nếu quy tắc dự kiến PASSED nhưng bất kỳ bảng phụ thuộc nào bị lỗi truy vấn -> Buộc hạ xuống INCOMPLETE_DATA
            for r in results:
                if r.status == RuleStatus.PASSED:
                    required_tables = get_rule_required_tables(r.standard, r.rule_code)
                    errored_tables = [tbl for tbl in required_tables if case.is_table_error(tbl)]
                    if errored_tables:
                        r.status = RuleStatus.INCOMPLETE_DATA
                        r.reason = f"Bảng phụ thuộc {', '.join(errored_tables)} gặp sự cố truy vấn từ CSDL SQL Server, chưa đủ dữ liệu để kết luận hợp lệ."

        except Exception as ex:
            return {
                "ma_lk": case.ma_lk,
                "ho_ten": case.ho_ten,
                "loai_ca": case.loai_ca,
                "ma_the": case.ma_the,
                "ngay_ra_vien": case.ngay_ra_vien,
                "applied_standard": standard,
                "overall_status": "VALIDATION_FAILED",
                "violated_count": 0,
                "passed_count": 0,
                "incomplete_count": 0,
                "not_applicable_count": 0,
                "violations": [],
                "rule_results": [],
                "summary": f"Lỗi kỹ thuật trong quá trình kiểm tra quy tắc: {str(ex)}",
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        # 4. Tổng hợp kết quả
        all_violations: List[RuleViolation] = []
        violated_count = 0
        passed_count = 0
        incomplete_count = 0
        not_applicable_count = 0

        for r in results:
            if r.status == RuleStatus.VIOLATED:
                violated_count += 1
                all_violations.extend(r.violations)
            elif r.status == RuleStatus.PASSED:
                passed_count += 1
            elif r.status == RuleStatus.INCOMPLETE_DATA:
                incomplete_count += 1
            elif r.status == RuleStatus.NOT_APPLICABLE:
                not_applicable_count += 1

        # Xác định trạng thái tổng hợp:
        # - Có lỗi vi phạm -> HAS_ERRORS
        # - Không có lỗi nhưng còn quy tắc chưa đánh giá -> INCOMPLETE_DATA (tránh báo sạch sai)
        # - Không có lỗi, tất cả quy tắc đều PASSED -> NO_ERRORS_FOUND
        if violated_count > 0:
            overall_status = "HAS_ERRORS"
            summary = f"Phát hiện {violated_count} lỗi vi phạm theo chuẩn {standard} (đã kiểm tra {passed_count + violated_count} quy tắc)."
        elif incomplete_count > 0:
            overall_status = "INCOMPLETE_DATA"
            summary = f"Đã kiểm tra {passed_count} quy tắc (không phát hiện lỗi); còn {incomplete_count} quy tắc chưa đủ điều kiện đánh giá."
        else:
            overall_status = "NO_ERRORS_FOUND"
            summary = f"Đạt chuẩn {standard}! Đã kiểm tra đầy đủ {passed_count} quy tắc và không phát hiện lỗi."

        execution_ms = int((time.time() - start_time) * 1000)

        return {
            "ma_lk": case.ma_lk,
            "ho_ten": case.ho_ten,
            "loai_ca": case.loai_ca,
            "ma_the": case.ma_the,
            "ngay_ra_vien": case.ngay_ra_vien,
            "applied_standard": standard,
            "overall_status": overall_status,
            "violated_count": violated_count,
            "passed_count": passed_count,
            "incomplete_count": incomplete_count,
            "not_applicable_count": not_applicable_count,
            "violations": all_violations,
            "rule_results": results,
            "summary": summary,
            "execution_time_ms": execution_ms
        }
