import sys
import os

sys.path.insert(0, os.path.abspath("web_app"))
from database import SessionLocal
from services import report_service

def main():
    db = SessionLocal()
    try:
        print("1. Testing get_daily_error_summary_data...")
        summary = report_service.get_daily_error_summary_data(db)
        print(f"   Total cases: {summary['total_cases']}, Total errors: {summary['total_errors']}, Total overdue: {summary['total_overdue']}")
        print(f"   Departments count: {len(summary['departments'])}")

        print("2. Testing generate_daily_error_html...")
        html = report_service.generate_daily_error_html(summary)
        assert len(html) > 500
        assert "390px" in html
        assert "844px" in html
        assert "Phòng Công nghệ Thông tin" in html
        print(f"   HTML generated successfully (length: {len(html)} bytes)")

        print("3. Testing generate_daily_error_excel...")
        upload_dir = os.path.abspath("web_app/uploaded_files")
        os.makedirs(upload_dir, exist_ok=True)
        excel_path = report_service.generate_daily_error_excel(db, upload_dir)
        assert os.path.exists(excel_path)
        print(f"   Daily Excel generated at: {excel_path} (size: {os.path.getsize(excel_path)} bytes)")

        print("4. Testing export_department_performance_multi_sheet...")
        dept_excel_path = report_service.export_department_performance_multi_sheet(db, upload_dir)
        assert os.path.exists(dept_excel_path)
        print(f"   Dept performance Excel generated at: {dept_excel_path} (size: {os.path.getsize(dept_excel_path)} bytes)")

        print("\n===> ALL REPORT TESTS PASSED PERFECTLY! <===")
    finally:
        db.close()

if __name__ == "__main__":
    main()
