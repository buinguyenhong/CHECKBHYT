import os
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from xml_parser import group_xml_files
from rule_engine import XMLRuleEngine
from report_generator import generate_reports
from watcher import XMLWatcher

# Thiết lập đường dẫn tương đối ổn định
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "config.json")

if not os.path.exists(config_path):
    # Cấu hình mặc định nếu chưa có
    config = {
        "input_dir": "Input",
        "output_dir": "Output",
        "api_port": 8001
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
else:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

input_dir = os.path.abspath(os.path.join(BASE_DIR, config.get("input_dir", "Input")))
output_dir = os.path.abspath(os.path.join(BASE_DIR, config.get("output_dir", "Output")))
api_port = int(config.get("api_port", 8001))

os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

app = FastAPI(title="XML Validator Service")

# Cho phép CORS chéo cổng local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def perform_validation_scan():
    """
    Thực hiện quét thư mục Input, chạy các quy tắc và ghi kết quả vào Output.
    """
    try:
        print(f"[*] Bắt đầu quét và phân tích XML trong thư mục: {input_dir}")
        grouped_data, invalid_files = group_xml_files(input_dir)
        
        rule_errors = []
        engine = XMLRuleEngine()
        
        for ma_lk, xmls in grouped_data.items():
            errors = engine.check_rules(ma_lk, xmls)
            rule_errors.extend(errors)
            
        excel_path, json_path = generate_reports(grouped_data, rule_errors, invalid_files, output_dir)
        print(f"[*] Quét hoàn tất. Báo cáo ghi nhận tại {excel_path} và {json_path}")
        return {
            "success": True,
            "patients_scanned": len(grouped_data),
            "errors_found": len(rule_errors) + len(invalid_files),
            "invalid_files_count": len(invalid_files)
        }
    except Exception as e:
        print(f"[!] Lỗi khi quét XML: {str(e)}")
        return {"success": False, "error": str(e)}

watcher = XMLWatcher(input_dir, perform_validation_scan)

@app.on_event("startup")
def startup_event():
    # Khởi động Watcher thư mục tự động
    watcher.start()

@app.on_event("shutdown")
def shutdown_event():
    # Tắt Watcher khi dừng app
    watcher.stop()

@app.post("/api/validator/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    """
    Yêu cầu quét thủ công thư mục Input (chạy nền bất đồng bộ).
    """
    background_tasks.add_task(perform_validation_scan)
    return {"status": "scanning", "message": "Tiến trình quét XML đã được kích hoạt chạy ngầm."}

@app.get("/api/validator/status")
def get_status():
    """
    Lấy trạng thái watcher và cấu hình thư mục.
    """
    return {
        "watcher_running": watcher.get_status(),
        "input_dir": input_dir,
        "output_dir": output_dir
    }

@app.post("/api/validator/watcher/toggle")
def toggle_watcher(enable: bool):
    """
    Bật hoặc tắt watcher giám sát thư mục tự động.
    """
    if enable:
        watcher.start()
    else:
        watcher.stop()
    return {"watcher_running": watcher.get_status()}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=api_port)
