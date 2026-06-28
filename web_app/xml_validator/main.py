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

PROGRESS = {
    "status": "idle",
    "total_files": 0,
    "processed_files": 0,
    "percent": 0,
    "message": ""
}

def update_progress(processed, total, msg=""):
    global PROGRESS
    PROGRESS["total_files"] = total
    PROGRESS["processed_files"] = processed
    # Tải tệp tin chiếm 60% tổng tiến trình, kiểm tra quy tắc chiếm 30%, kết xuất chiếm 10%
    PROGRESS["percent"] = int((processed / total) * 100) if total > 0 else 0
    PROGRESS["message"] = msg

def perform_validation_scan():
    """
    Thực hiện quét thư mục Input, chạy các quy tắc và ghi kết quả vào Output.
    """
    global PROGRESS
    try:
        PROGRESS["status"] = "scanning"
        update_progress(0, 0, "Khởi động tiến trình quét...")
        print(f"[*] Starting XML scan in dir: {input_dir}")
        
        if not os.path.exists(input_dir):
            PROGRESS["status"] = "idle"
            update_progress(0, 0, "Thư mục đầu vào không tồn tại.")
            return {"success": False, "error": "Thư mục đầu vào không tồn tại."}
            
        def progress_cb(idx, total, filename_msg):
            # Scale đến 60%
            pct = int((idx / total) * 60) if total > 0 else 0
            PROGRESS["total_files"] = total
            PROGRESS["processed_files"] = idx
            PROGRESS["percent"] = pct
            PROGRESS["message"] = f"[{idx}/{total}] {filename_msg}"
            
        grouped_data, invalid_files = group_xml_files(input_dir, progress_callback=progress_cb)
        
        PROGRESS["percent"] = 60
        PROGRESS["message"] = "Đang áp dụng 26 quy tắc kiểm tra cấu trúc BHYT..."
        
        rule_errors = []
        engine = XMLRuleEngine()
        total_p = len(grouped_data)
        
        for idx, (ma_lk, xmls) in enumerate(grouped_data.items()):
            errors = engine.check_rules(ma_lk, xmls)
            rule_errors.extend(errors)
            # Scale kiểm tra quy tắc từ 60% đến 90%
            pct_rules = 60 + int((idx / total_p) * 30) if total_p > 0 else 90
            PROGRESS["percent"] = pct_rules
            PROGRESS["message"] = f"Đang đối chiếu quy tắc cho bệnh nhân: {ma_lk} ({idx}/{total_p})"
            
        PROGRESS["percent"] = 90
        PROGRESS["message"] = "Đang khởi tạo tệp báo cáo Excel và JSON..."
        
        excel_path, json_path = generate_reports(grouped_data, rule_errors, invalid_files, output_dir)
        print(f"[*] Scan complete. Report saved to {excel_path} and {json_path}")
        
        PROGRESS["status"] = "completed"
        PROGRESS["percent"] = 100
        PROGRESS["message"] = f"Hoàn tất! Quét xong {total_p} bệnh nhân. Tìm thấy {len(rule_errors) + len(invalid_files)} lỗi."
        
        return {
            "success": True,
            "patients_scanned": len(grouped_data),
            "errors_found": len(rule_errors) + len(invalid_files),
            "invalid_files_count": len(invalid_files)
        }
    except Exception as e:
        print(f"[!] Scan error: {str(e)}")
        PROGRESS["status"] = "error"
        PROGRESS["percent"] = 0
        PROGRESS["message"] = f"Gặp sự cố lỗi: {str(e)}"
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

@app.get("/api/validator/progress")
def get_progress():
    """
    Lấy tiến độ đọc và xử lý XML hiện tại.
    """
    return PROGRESS

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

@app.get("/api/validator/config")
def get_config():
    """
    Lấy cấu hình thư mục từ config.json (đường dẫn tuyệt đối đang sử dụng).
    """
    return {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "api_port": config.get("api_port", 8001)
    }

@app.post("/api/validator/config")
def update_config(new_config: dict):
    """
    Cập nhật cấu hình thư mục, ghi vào config.json và reload watcher.
    """
    global input_dir, output_dir, watcher
    
    config["input_dir"] = new_config.get("input_dir", config.get("input_dir", "Input"))
    config["output_dir"] = new_config.get("output_dir", config.get("output_dir", "Output"))
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        
    # Phân giải lại các đường dẫn tuyệt đối
    input_dir = os.path.abspath(os.path.join(BASE_DIR, config.get("input_dir", "Input")))
    output_dir = os.path.abspath(os.path.join(BASE_DIR, config.get("output_dir", "Output")))
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Restart Watcher với thư mục input mới
    was_running = watcher.get_status()
    watcher.stop()
    watcher.watch_dir = input_dir
    
    if was_running:
        watcher.start()
        
    return {
        "status": "success",
        "input_dir": input_dir,
        "output_dir": output_dir,
        "watcher_running": watcher.get_status()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=api_port)
