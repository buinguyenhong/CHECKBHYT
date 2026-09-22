import os
import sys
import re
import time
import glob
import json
import datetime
import threading
import webbrowser
from typing import Optional, Dict, Any, List
import pandas as pd
import requests
import base64

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Cấu hình UTF-8 cho Windows Console
if hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
if hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SESSION_DIR = os.path.join(BASE_DIR, "browser_session")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

SESSION_FILE = os.path.join(SESSION_DIR, "portal_storage_state.json")
CONFIG_FILE = os.path.join(BASE_DIR, "tool_config.json")

_log_lock = threading.Lock()
_log_seq = 0
logs: List[Dict[str, Any]] = []

stop_requested: bool = False
active_browser = None
active_context = None

def add_log(msg: str):
    global _log_seq
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with _log_lock:
        _log_seq += 1
        logs.append({"id": _log_seq, "text": entry})
        if len(logs) > 500:
            logs.pop(0)
    print(f"[*] {entry}")

def get_logs_since(last_id: int = 0) -> List[Dict[str, Any]]:
    with _log_lock:
        if last_id <= 0:
            return list(logs[-200:])
        return [item for item in logs if item["id"] > last_id]

def stop_current_flow() -> bool:
    global stop_requested, active_browser, active_context
    if not is_busy:
        return False
    stop_requested = True
    add_log("🛑 Người dùng đã yêu cầu DỪNG tiến trình đang chạy!")
    try:
        if active_context:
            active_context.close()
    except Exception:
        pass
    try:
        if active_browser:
            active_browser.close()
    except Exception:
        pass
    return True

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "server_url": "http://127.0.0.1:8000",
        "ma_cskcb": "66232",
        "username": "066091019320",
        "password": "",
        "portal_url": "https://gdbhyt.baohiemxahoi.gov.vn/"
    }

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        add_log(f"Lỗi lưu cấu hình: {e}")

# =========================================================================
# PLAYWRIGHT BROWSER & AUTOMATION LOGIC
# =========================================================================

def launch_native_browser(playwright_instance, headless: bool = False):
    """
    Khởi chạy Google Chrome hoặc Microsoft Edge native trên Windows.
    Ép cửa sổ luôn bật nổi bật trên màn hình máy này (Foreground & Maximized).
    """
    browser_args = [
        "--start-maximized",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=CalculateNativeWinOcclusion",
        "--window-position=0,0",
        "--no-sandbox"
    ]
    for channel in ["chrome", "msedge"]:
        try:
            b = playwright_instance.chromium.launch(
                channel=channel,
                headless=headless,
                args=browser_args
            )
            add_log(f"Đã mở trình duyệt: {channel.upper()} trực tiếp trên máy tính của bạn ✅")
            return b
        except Exception:
            continue

    b = playwright_instance.chromium.launch(headless=headless, args=browser_args)
    add_log("Đã mở trình duyệt Chromium trực tiếp trên màn hình ✅")
    return b

# =========================================================================
# CAPTCHA MANAGER (AUTO-OCR + REMOTE WORKSTATION CAPTCHA BRIDGE)
# =========================================================================

class CaptchaManager:
    def __init__(self):
        self.waiting_event = threading.Event()
        self.refresh_event = threading.Event()
        self.current_captcha_b64: Optional[str] = None
        self.current_captcha_ocr: Optional[str] = None
        self.user_captcha_value: Optional[str] = None
        self.is_waiting: bool = False
        self.ocr_engine = None

    def get_ocr(self):
        if self.ocr_engine is None:
            try:
                import ddddocr
                self.ocr_engine = ddddocr.DdddOcr(show_ad=False)
                add_log("Đã kích hoạt thư viện Auto-OCR ddddocr thành công!")
            except Exception as e:
                add_log(f"Auto-OCR không khả dụng: {e}")
                self.ocr_engine = False
        return self.ocr_engine if self.ocr_engine is not False else None

    def reset(self):
        self.waiting_event.clear()
        self.refresh_event.clear()
        self.current_captcha_b64 = None
        self.current_captcha_ocr = None
        self.user_captcha_value = None
        self.is_waiting = False

captcha_mgr = CaptchaManager()

def ensure_login(page, base_url: str, ma_cskcb: str, username: str, password: str):
    add_log("Đang truy cập Cổng BHYT: https://gdbhyt.baohiemxahoi.gov.vn/ ...")
    page.goto(base_url, timeout=90000, wait_until="load")
    time.sleep(1.0)

    # Đóng popup quảng cáo hoặc thông báo nếu có
    try:
        btn_close = page.locator(".dxpc-closeBtn, #btnKhong_CD, #btnKhong, input[value='Không']").first
        if btn_close.is_visible(timeout=1500):
            btn_close.click(force=True)
            time.sleep(0.5)
    except Exception:
        pass

    # Kiểm tra phiên cũ
    try:
        has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible(timeout=2000)
        has_login_btn = page.locator("a:has-text('Đăng nhập'), input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible(timeout=2000)
        if has_logout and not has_login_btn:
            add_log("Phiên đăng nhập cũ vẫn còn hiệu lực (Session Valid) ✅ -> Vào thẳng chức năng!")
            return
    except Exception:
        pass

    add_log(f"Tự động điền Mã cơ sở: {ma_cskcb}, Tài khoản: {username}...")
    try:
        ma_inp = page.locator("#macskcb, input[name*='MaCSKCB'], input[id*='txtMaCSKCB'], input[placeholder*='Mã cơ sở']").first
        if ma_inp.is_visible(timeout=3000):
            ma_inp.click()
            ma_inp.fill(ma_cskcb)
        elif page.get_by_role("textbox", name="Mã cơ sở KCB").is_visible(timeout=2000):
            page.get_by_role("textbox", name="Mã cơ sở KCB").fill(ma_cskcb)

        user_inp = page.locator("#username, input[name*='UserName'], input[id*='txtUserName'], input[placeholder*='Tên đăng nhập']").first
        if user_inp.is_visible(timeout=3000):
            user_inp.click()
            user_inp.fill(username)
        elif page.get_by_role("textbox", name="Tên đăng nhập").is_visible(timeout=2000):
            page.get_by_role("textbox", name="Tên đăng nhập").fill(username)

        if password:
            pass_inp = page.locator("#password, input[type='password'], input[name*='Password'], input[id*='txtPassword']").first
            if pass_inp.is_visible(timeout=3000):
                pass_inp.click()
                pass_inp.fill(password)
            elif page.get_by_role("textbox", name="Mật khẩu").is_visible(timeout=2000):
                page.get_by_role("textbox", name="Mật khẩu").fill(password)

        cap_inp = page.locator("#Captcha_TB_I, input[name*='Captcha'], input[id*='Captcha'], input[placeholder*='mã hiển thị']").first
        if cap_inp.is_visible(timeout=3000):
            cap_inp.click()
            cap_inp.focus()

        def grab_captcha_b64() -> Optional[str]:
            try:
                img_loc = page.locator("#Captcha_IMG1, img[id*='Captcha'], img[src*='data:image']").first
                if img_loc.is_visible(timeout=2500):
                    src_val = img_loc.get_attribute("src") or ""
                    if "base64," in src_val:
                        return src_val.split("base64,")[1].strip()
                    else:
                        img_bytes = img_loc.screenshot()
                        return base64.b64encode(img_bytes).decode("ascii")
            except Exception as ge:
                add_log(f"Lỗi chụp ảnh Captcha: {ge}")
            return None

        login_success = False
        start_wait = time.time()
        last_log_t = start_wait

        # 1. Thử nhận diện Auto-OCR trước
        ocr = captcha_mgr.get_ocr()
        if ocr:
            try:
                time.sleep(0.5)
                b64 = grab_captcha_b64()
                if b64:
                    raw_bytes = base64.b64decode(b64)
                    ocr_result = ocr.classification(raw_bytes).strip()
                    add_log(f"🤖 Auto-OCR nhận diện Captcha: '{ocr_result}'. Đang tự động thử đăng nhập...")
                    if ocr_result and cap_inp.is_visible(timeout=2000):
                        cap_inp.click()
                        cap_inp.fill(ocr_result)
                        login_btn = page.locator(".dxbButton:has-text('Đăng nhập'), input[value='Đăng nhập'], #btnLogin, #btnDangNhap").first
                        if login_btn.is_visible(timeout=2000):
                            login_btn.click()
                        else:
                            cap_inp.press("Enter")
                        time.sleep(2.5)

                        has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible()
                        has_menu = page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible()
                        has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible()
                        has_pass_inp = page.locator("input[type='password']").is_visible()

                        if (has_logout or has_menu) and not has_login_btn and not has_pass_inp:
                            add_log(f"🎉 TỰ ĐỘNG GIẢI CAPTCHA THÀNH CÔNG ('{ocr_result}')! Đã đăng nhập vào Cổng BHYT ✅")
                            login_success = True
                        else:
                            add_log("⚠️ Mã Auto-OCR chưa chuẩn. Đang chuyển sang chế độ Popup chụp ảnh gửi về máy trạm...")
            except Exception as oe:
                add_log(f"Lưu ý Auto-OCR: {oe}")

        # 2. Nếu Auto-OCR chưa được -> Chụp ảnh Captcha gửi về giao diện Web máy trạm (Modal)
        if not login_success:
            b64 = grab_captcha_b64()
            ocr_text = ""
            if ocr and b64:
                try:
                    ocr_text = ocr.classification(base64.b64decode(b64)).strip()
                except Exception:
                    pass

            captcha_mgr.current_captcha_b64 = b64
            captcha_mgr.current_captcha_ocr = ocr_text
            captcha_mgr.is_waiting = True

            add_log(f"[CAPTCHA_REQUIRED] data:image/png;base64,{b64}###{ocr_text}")
            add_log("👉 ĐÃ CHỤP ẢNH CAPTCHA VÀ GỬI VỀ MÀN HÌNH MÁY TRẠM. Vui lòng gõ mã trên Popup hiển thị...")

            while time.time() - start_wait < 180:
                if stop_requested:
                    raise Exception("Tiến trình đã bị dừng bởi người dùng.")
                # Kiểm tra yêu cầu đổi mã Captcha từ máy trạm
                if captcha_mgr.refresh_event.is_set():
                    captcha_mgr.refresh_event.clear()
                    add_log("🔄 Đang đổi mã Captcha mới trên Cổng BHYT...")
                    try:
                        page.locator("#Captcha_IMG1, a:has-text('Đổi mã'), .dxeCaptcha_EIS").first.click(force=True)
                        time.sleep(1.0)
                    except Exception:
                        pass
                    b64 = grab_captcha_b64()
                    ocr_text = ocr.classification(base64.b64decode(b64)).strip() if ocr and b64 else ""
                    captcha_mgr.current_captcha_b64 = b64
                    captcha_mgr.current_captcha_ocr = ocr_text
                    add_log(f"[CAPTCHA_REQUIRED] data:image/png;base64,{b64}###{ocr_text}")

                # Kiểm tra nhận mã Captcha từ máy trạm gửi lên
                if captcha_mgr.waiting_event.is_set():
                    captcha_mgr.waiting_event.clear()
                    user_val = captcha_mgr.user_captcha_value
                    add_log(f"📥 Đã nhận mã Captcha từ máy trạm: '{user_val}'. Đang điền và đăng nhập...")
                    try:
                        cap_inp = page.locator("#Captcha_TB_I, input[name*='Captcha'], input[placeholder*='mã hiển thị']").first
                        cap_inp.click()
                        cap_inp.fill(user_val)
                        login_btn = page.locator(".dxbButton:has-text('Đăng nhập'), input[value='Đăng nhập'], #btnLogin").first
                        if login_btn.is_visible(timeout=2000):
                            login_btn.click()
                        else:
                            cap_inp.press("Enter")
                        time.sleep(2.0)

                        has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible()
                        has_menu = page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible()
                        has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible()
                        has_pass_inp = page.locator("input[type='password']").is_visible()

                        if (has_logout or has_menu) and not has_login_btn and not has_pass_inp:
                            add_log("🎉 ĐĂNG NHẬP THÀNH CÔNG! ✅")
                            add_log("[CAPTCHA_SUCCESS]")
                            login_success = True
                            captcha_mgr.reset()
                            break
                        else:
                            add_log("⚠️ Mã Captcha không chính xác. Đang chụp lại ảnh mới gửi về máy trạm...")
                            time.sleep(1.0)
                            b64 = grab_captcha_b64()
                            ocr_text = ocr.classification(base64.b64decode(b64)).strip() if ocr and b64 else ""
                            captcha_mgr.current_captcha_b64 = b64
                            captcha_mgr.current_captcha_ocr = ocr_text
                            add_log(f"[CAPTCHA_REQUIRED] data:image/png;base64,{b64}###{ocr_text}")
                    except Exception as le:
                        add_log(f"Lỗi đăng nhập: {le}")

                # Kiểm tra nếu đăng nhập trực tiếp trên trình duyệt
                try:
                    has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible()
                    has_menu = page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible()
                    has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible()
                    if (has_logout or has_menu) and not has_login_btn:
                        add_log("🎉 ĐĂNG NHẬP THÀNH CÔNG! ✅")
                        add_log("[CAPTCHA_SUCCESS]")
                        login_success = True
                        captcha_mgr.reset()
                        break
                except Exception:
                    pass

                now = time.time()
                if now - last_log_t >= 15:
                    elapsed = int(now - start_wait)
                    remaining = max(0, 180 - elapsed)
                    add_log(f"⏳ Đang chờ xác nhận Captcha... (Đã chờ {elapsed}s / còn lại {remaining}s)")
                    last_log_t = now

                time.sleep(0.5)

        captcha_mgr.reset()
        if not login_success:
            raise Exception("Quá thời gian 180 giây chờ nhập Captcha hoặc chưa hoàn tất Đăng nhập.")

        add_log("ĐĂNG NHẬP THÀNH CÔNG! ✅ Đang lưu phiên làm việc...")
        try:
            page.context.storage_state(path=SESSION_FILE)
            add_log("💾 Đã lưu phiên làm việc (Session) thành công!")
        except Exception:
            pass
    except Exception as e:
        raise Exception(f"Lỗi đăng nhập: {e}")

def wait_for_grid_ready(page, timeout_ms: int = 600000):
    start_time = time.time()
    time.sleep(1.0)
    last_report = start_time

    while (time.time() - start_time) * 1000 < timeout_ms:
        if stop_requested:
            raise Exception("Tiến trình đã bị dừng bởi người dùng.")
        is_busy = False
        try:
            is_busy = page.evaluate("""() => {
                const grid = window.gvDSKetQuaGuiHoso || window.gvDanhSachHoSo;
                if (grid && typeof grid.InCallback === 'function' && grid.InCallback()) return true;

                const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                if (cc && typeof cc.ForEachControl === 'function') {
                    let active = false;
                    cc.ForEachControl(c => {
                        if (c && typeof c.InCallback === 'function' && c.InCallback()) active = true;
                    });
                    if (active) return true;
                }

                const gridLp = document.getElementById('gvDSKetQuaGuiHoso_LP') || document.getElementById('gvDanhSachHoSo_LP');
                if (gridLp) {
                    const style = window.getComputedStyle(gridLp);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && (gridLp.offsetWidth > 0 || gridLp.offsetHeight > 0)) {
                        return true;
                    }
                }
                const genLp = document.getElementById('_Loading');
                if (genLp) {
                    const style = window.getComputedStyle(genLp);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && (genLp.offsetWidth > 0 || genLp.offsetHeight > 0)) {
                        return true;
                    }
                }
                return false;
            }""")
        except Exception:
            is_busy = True

        if not is_busy:
            time.sleep(0.8)
            return True

        if time.time() - last_report >= 15:
            elapsed = int(time.time() - start_time)
            add_log(f"⏳ Máy chủ BHYT đang xử lý dữ liệu... (Đã chờ {elapsed}s / {int(timeout_ms/1000)}s)...")
            last_report = time.time()

        time.sleep(0.8)

    add_log(f"⚠️ Cảnh báo: Đã chờ tối đa {int(timeout_ms/1000)}s. Tiếp tục các thao tác...")
    return False

def extract_records_from_grid(page) -> List[Dict[str, Any]]:
    try:
        return page.evaluate("""() => {
            const records = [];
            const dataRows = Array.from(document.querySelectorAll('.dxgvDataRow_EIS, tr[id*="DXDataRow"], tr.dxgvDataRow, #gvDSKetQuaGuiHoso tr'));
            for (let i = 0; i < dataRows.length; i++) {
                const row = dataRows[i];
                const rowText = (row.innerText || row.textContent || '');
                const match = rowText.match(/HSKCB[0-9A-Za-z_]+/);
                if (match) {
                    const maGD = match[0];
                    let stt = 0;
                    if (row.cells && row.cells.length > 0) {
                        const parsed = parseInt((row.cells[0].innerText || '').trim(), 10);
                        if (!isNaN(parsed) && parsed > 0) stt = parsed;
                    }
                    if (!stt) stt = records.length + 1;
                    if (!records.some(r => r.maGD === maGD)) records.push({ stt, maGD });
                }
            }
            if (records.length > 0) return records;

            const allLinks = Array.from(document.querySelectorAll('a'));
            for (const a of allLinks) {
                const combined = (a.getAttribute('href') || '') + ' ' + (a.getAttribute('onclick') || '') + ' ' + (a.innerText || '');
                const match = combined.match(/HSKCB[0-9A-Za-z_]+/);
                if (match) {
                    const maGD = match[0];
                    let stt = 0;
                    const tr = a.closest('tr');
                    if (tr && tr.cells && tr.cells.length > 0) {
                        const parsed = parseInt((tr.cells[0].innerText || '').trim(), 10);
                        if (!isNaN(parsed) && parsed > 0) stt = parsed;
                    }
                    if (!stt) stt = records.length + 1;
                    if (!records.some(r => r.maGD === maGD)) records.push({ stt, maGD });
                }
            }
            return records;
        }""")
    except Exception:
        return []

def download_direct_record(page, ma_gd: str, stt: int, save_dir: str, max_retries: int = 3) -> Optional[str]:
    download_url = f"https://gdbhyt.baohiemxahoi.gov.vn/DanhSachKetQuaGuiHoSoQD130/ExportExcelKPG_New?maGd={ma_gd}"
    file_name = f"STT_{str(stt).zfill(4)}_{ma_gd}.xlsx"
    file_path = os.path.join(save_dir, file_name)

    if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
        add_log(f"✅ [STT {stt}] Đã có sẵn file: {file_name}, bỏ qua không tải lại.")
        return file_path

    for attempt in range(1, max_retries + 1):
        try:
            add_log(f"⚡ [STT {stt}] Đang tải hồ sơ {ma_gd} (Lần {attempt})...")
            response = page.request.get(download_url, timeout=60000)
            if not response.ok:
                raise Exception(f"HTTP Status {response.status}: {response.status_text}")

            body = response.body()
            if not body or len(body) < 500:
                raise Exception(f"Dữ liệu tải về quá nhỏ ({len(body) if body else 0} bytes)")

            with open(file_path, "wb") as f:
                f.write(body)

            kb_size = round(len(body) / 1024, 1)
            add_log(f"✅ [STT {stt}] Tải thành công ({kb_size} KB) -> {file_name}")
            return file_path
        except Exception as err:
            add_log(f"⚠️ [STT {stt}] Lỗi tải lần {attempt}: {err}")
            if attempt < max_retries:
                time.sleep(2.0 * attempt)
            else:
                add_log(f"❌ [STT {stt}] Thất bại sau {max_retries} lần thử: {ma_gd}")
                return None

def merge_excel_files(download_dir: str, output_file_path: str) -> Dict[str, Any]:
    files = [
        os.path.join(download_dir, f)
        for f in os.listdir(download_dir)
        if f.endswith('.xlsx') and not f.startswith('~$') and not f.startswith('KetQua_TongHop')
    ]

    if not files:
        empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"])
        empty_df.to_excel(output_file_path, index=False)
        return {"total_files": 0, "total_records": 0, "unique_records": 0, "duplicates_removed": 0, "output_path": output_file_path}

    add_log(f"📊 Bắt đầu quét {len(files)} file Excel để gộp và khử trùng dữ liệu...")
    all_dfs = []
    total_data_rows = 0

    for i, file_p in enumerate(files):
        try:
            df = pd.read_excel(file_p)
            if not df.empty:
                total_data_rows += len(df)
                all_dfs.append(df)
            if (i + 1) % 15 == 0 or i == len(files) - 1:
                add_log(f"  -> Đang đọc file {i + 1}/{len(files)} ({os.path.basename(file_p)})...")
        except Exception as e:
            add_log(f"⚠️ Lỗi đọc file {os.path.basename(file_p)}: {e}")

    if not all_dfs:
        empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"])
        empty_df.to_excel(output_file_path, index=False)
        return {"total_files": len(files), "total_records": 0, "unique_records": 0, "duplicates_removed": 0, "output_path": output_file_path}

    combined_df = pd.concat(all_dfs, ignore_index=True)
    subset_cols = [c for c in combined_df.columns if str(c).strip().upper() not in ["STT", "TT"]]
    if not subset_cols:
        subset_cols = list(combined_df.columns)

    unique_df = combined_df.drop_duplicates(subset=subset_cols, keep='first')
    unique_data_rows = len(unique_df)
    duplicates_removed = total_data_rows - unique_data_rows

    add_log(f"💾 Đang ghi file Excel tổng hợp ra: {output_file_path}...")
    unique_df.to_excel(output_file_path, index=False)

    add_log("🎉 GỘP HOÀN TẤT:")
    add_log(f"   - Tổng số file xử lý: {len(files)} file")
    add_log(f"   - Tổng số dòng đọc được: {total_data_rows} dòng")
    add_log(f"   - Số dòng duy nhất: {unique_data_rows} dòng")
    add_log(f"   - Số dòng trùng lặp đã loại: {duplicates_removed} dòng")
    add_log(f"   - File kết quả: {output_file_path}")

    return {
        "total_files": len(files),
        "total_records": total_data_rows,
        "unique_records": unique_data_rows,
        "duplicates_removed": duplicates_removed,
        "output_path": output_file_path
    }

# =========================================================================
# LUỒNG C - TẢI HỒ SƠ LỖI QĐ 3176
# =========================================================================
def run_flow_c(params: dict) -> dict:
    from playwright.sync_api import sync_playwright

    ma_cskcb = params.get("maCoSoKCB", "66232")
    username = params.get("username", "066091019320")
    password = params.get("password", "")
    from_stt = int(params.get("fromSTT", 1))
    to_stt = int(params.get("toSTT", 100))
    filter_col5 = str(params.get("filterCol5", "1")).strip()
    base_url = "https://gdbhyt.baohiemxahoi.gov.vn/"

    add_log(f"🚀 KHỞI ĐỘNG LUỒNG C (DIRECT URL DOWNLOAD) - PHẠM VI STT: {from_stt} ĐẾN {to_stt}...")

    # Xóa file tạm cũ trong thư mục downloads
    for old_f in glob.glob(os.path.join(DOWNLOADS_DIR, "*.*")):
        try: os.remove(old_f)
        except Exception: pass

    with sync_playwright() as p:
        global active_browser, active_context, stop_requested
        stop_requested = False
        browser = launch_native_browser(p, headless=False)
        active_browser = browser
        storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        context = browser.new_context(storage_state=storage_path, viewport=None, accept_downloads=True)
        active_context = context
        page = context.new_page()
        page.set_default_timeout(600000)
        page.set_default_navigation_timeout(600000)
        try: page.bring_to_front()
        except Exception: pass

        try:
            # 1. Đăng nhập
            ensure_login(page, base_url, ma_cskcb, username, password)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 2. Vào màn hình QĐ 3176
            add_log("📌 Điều hướng đến: Kết quả gửi hồ sơ XML (/DanhSachKetQuaGuiHoSoQD130/Index)...")
            target_url = f"{base_url.rstrip('/')}/DanhSachKetQuaGuiHoSoQD130/Index"
            try:
                page.goto(target_url, timeout=90000, wait_until="load")
            except Exception:
                try:
                    page.get_by_text("Hồ sơ đề nghị thanh toán").click()
                    time.sleep(0.5)
                    page.locator("#HeaderMenu_DXME2_ div").filter(has_text="Hồ sơ XML").click()
                    time.sleep(0.5)
                    page.get_by_text("Quyết định 3176/QĐ-BYT").nth(1).click()
                    time.sleep(0.5)
                    page.get_by_role("link", name="Kết quả gửi hồ sơ XML").nth(1).click()
                except Exception:
                    pass

            page.wait_for_selector("#roundPanel, #gvDSKetQuaGuiHoso", timeout=90000)
            wait_for_grid_ready(page, timeout_ms=90000)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 3. Chọn ngày = Today
            add_log("📅 Đặt ngày tìm kiếm: Chọn ngày 'Today'...")
            try:
                page.evaluate("""() => {
                    const now = new Date();
                    if (window.dt_TuNgay && typeof window.dt_TuNgay.SetValue === 'function') window.dt_TuNgay.SetValue(now);
                    if (window.dt_DenNgay && typeof window.dt_DenNgay.SetValue === 'function') window.dt_DenNgay.SetValue(now);
                }""")
            except Exception:
                pass

            # Bấm nút Tìm kiếm
            add_log("🔍 Bấm nút 'Tìm kiếm' và chờ phản hồi...")
            search_btn = page.locator("span").filter(has_text=re.compile(r"^Tìm kiếm$")).first
            if search_btn.is_visible(timeout=3000):
                search_btn.click(force=True)
            else:
                page.evaluate("if (window.btnTimKiem && typeof window.btnTimKiem.DoClick === 'function') window.btnTimKiem.DoClick();")

            wait_for_grid_ready(page, timeout_ms=600000)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")
            add_log("✅ Bảng dữ liệu đã nạp xong!")

            # 4. Lọc Cột 5 = 1
            if filter_col5:
                add_log(f"🔎 Lọc Cột 5 = '{filter_col5}'...")
                col5_inp = page.locator("#gvDSKetQuaGuiHoso_DXFREditorcol5_I")
                if col5_inp.is_visible(timeout=5000):
                    col5_inp.click()
                    col5_inp.fill(filter_col5)
                    col5_inp.press("Enter")
                else:
                    page.evaluate(f"if (window.gvDSKetQuaGuiHoso) window.gvDSKetQuaGuiHoso.AutoFilterByColumn(5, '{filter_col5}');")
                wait_for_grid_ready(page, timeout_ms=600000)
                if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")
                add_log("✅ Lọc Cột 5 hoàn tất!")

            # 5. Page size = 100
            add_log("📄 Thiết lập 100 dòng/trang...")
            try:
                page_size_inp = page.get_by_role("textbox", name="Page size:")
                if page_size_inp.is_visible(timeout=2000):
                    page_size_inp.click()
                    time.sleep(0.4)
                    page.get_by_text("100", exact=True).first.click()
                    wait_for_grid_ready(page, timeout_ms=600000)
                    add_log("✅ Đã chọn 100 dòng/trang!")
            except Exception:
                pass
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 6. Sắp xếp Thời gian (2 lần click để mới nhất lên đầu)
            add_log("⏱️ Sắp xếp cột 'Thời gian' (2 lần click)...")
            try:
                thoi_gian_hdr = page.get_by_role("cell", name="Thời gian", exact=True).or_(page.get_by_text("Thời gian", exact=True)).first
                if thoi_gian_hdr.is_visible(timeout=3000):
                    thoi_gian_hdr.click(force=True)
                    wait_for_grid_ready(page, timeout_ms=600000)
                    time.sleep(0.5)
                    thoi_gian_hdr.click(force=True)
                    wait_for_grid_ready(page, timeout_ms=600000)
                    add_log("✅ Sắp xếp thời gian hoàn tất!")
            except Exception as s_err:
                add_log(f"Lưu ý sắp xếp: {s_err}")
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 7. Quét và tải dải STT bằng Direct URL
            add_log(f"🎯 BẮT ĐẦU TẢI CÁC HỒ SƠ TỪ STT {from_stt} ĐẾN {to_stt} (DIRECT URL)...")
            current_stt = from_stt
            downloaded_count = 0
            current_page_num = 1

            while current_stt <= to_stt:
                if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")
                add_log(f"\n📑 Đang quét Trang {current_page_num}...")
                wait_for_grid_ready(page, timeout_ms=600000)

                records = extract_records_from_grid(page)
                if not records:
                    add_log("⚠️ Không còn bản ghi nào trên trang hiện tại. Đã hết dữ liệu.")
                    break

                add_log(f"📋 Tìm thấy {len(records)} bản ghi trên Trang {current_page_num}.")
                records_to_dl = [r for r in records if r.get('stt', 0) >= current_stt and r.get('stt', 0) <= to_stt]

                if not records_to_dl:
                    records_to_dl = [
                        {"stt": (current_page_num - 1) * 100 + (i + 1), "maGD": r.get('maGD')}
                        for i, r in enumerate(records)
                        if (current_page_num - 1) * 100 + (i + 1) >= current_stt and (current_page_num - 1) * 100 + (i + 1) <= to_stt
                    ]

                for rec in records_to_dl:
                    if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")
                    fp = download_direct_record(page, rec['maGD'], rec['stt'], DOWNLOADS_DIR)
                    if fp: downloaded_count += 1
                    current_stt = rec['stt'] + 1
                    time.sleep(0.2)

                if current_stt > to_stt:
                    add_log(f"🎉 Đã tải hoàn tất đến STT {to_stt}!")
                    break

                current_page_num += 1
                add_log(f"➡️ Chuyển sang Trang {current_page_num}...")
                pager = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom")
                next_page_btn = pager.get_by_text(str(current_page_num), exact=True)
                if next_page_btn.count() > 0:
                    next_page_btn.first.click(force=True)
                    wait_for_grid_ready(page, timeout_ms=600000)
                else:
                    add_log(f"⚠️ Đã đến trang cuối cùng.")
                    break

            add_log(f"\n📦 ĐÃ TẢI XONG {downloaded_count} TỆP HỒ SƠ LỖI.")

            # 8. Gộp và lọc trùng
            add_log("📊 Đang tiến hành gộp dữ liệu và loại bỏ các dòng trùng lặp...")
            final_output = os.path.join(OUTPUT_DIR, "HoSoLoiChiTiet.xlsx")
            summary = merge_excel_files(DOWNLOADS_DIR, final_output)

            context.storage_state(path=SESSION_FILE)
            add_log("🌟 QUY TRÌNH LUỒNG C ĐÃ HOÀN TẤT TRỌN VẸN!")

            return {
                "status": "success",
                "flow": "C",
                "downloaded_count": downloaded_count,
                "file_path": final_output,
                "summary": summary
            }

        finally:
            try: context.close()
            except Exception: pass
            try: browser.close()
            except Exception: pass
            active_browser = None
            active_context = None

# =========================================================================
# LUỒNG B - TẢI DANH SÁCH ĐÃ GỬI (CẢ THÁNG, TIMEOUT 20 PHÚT, HEARTBEAT 10S)
# =========================================================================
def run_flow_b(params: dict) -> dict:
    from playwright.sync_api import sync_playwright

    ma_cskcb = params.get("maCoSoKCB", "66232")
    username = params.get("username", "066091019320")
    password = params.get("password", "")
    base_url = "https://gdbhyt.baohiemxahoi.gov.vn/"

    add_log("🚀 KHỞI ĐỘNG LUỒNG B (TẢI TOÀN BỘ DANH SÁCH ĐÃ GỬI CẢ THÁNG)...")

    with sync_playwright() as p:
        global active_browser, active_context, stop_requested
        stop_requested = False
        browser = launch_native_browser(p, headless=False)
        active_browser = browser
        storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        context = browser.new_context(storage_state=storage_path, viewport=None, accept_downloads=True)
        active_context = context
        page = context.new_page()
        page.set_default_timeout(1200000)
        page.set_default_navigation_timeout(1200000)
        try: page.bring_to_front()
        except Exception: pass

        try:
            # 1. Đăng nhập
            ensure_login(page, base_url, ma_cskcb, username, password)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 2. Vào Danh sách hồ sơ KCB
            add_log("📌 Điều hướng đến: Danh sách đề nghị thanh toán (/DanhSachHSKCB/Index)...")
            target_url = f"{base_url.rstrip('/')}/DanhSachHSKCB/Index"
            page.goto(target_url, timeout=90000, wait_until="load")

            page.wait_for_selector("#gvDanhSachHoSo, #bt_TimKiem, #btnExport, #cb_TrangThaiTT", timeout=60000)
            wait_for_grid_ready(page, timeout_ms=60000)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 3. Chọn Trạng thái: 'Đã đề nghị thanh toán'
            add_log("🏷️ Đang chọn trạng thái: 'Đã đề nghị thanh toán'...")
            status_selected = page.evaluate("""() => {
                try {
                    const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                    const cb = window.cb_TrangThaiTT || (cc ? cc.GetByName('cb_TrangThaiTT') : null);
                    if (cb) {
                        const count = typeof cb.GetItemCount === 'function' ? cb.GetItemCount() : 0;
                        for (let i = 0; i < count; i++) {
                            const it = cb.GetItem(i);
                            if (it && it.text && it.text.trim().toLowerCase().includes('đã đề nghị thanh toán')) {
                                cb.SetSelectedIndex(i);
                                if (typeof cb.ProcessItemClick === 'function') cb.ProcessItemClick(i);
                                if (typeof cb.HideDropDown === 'function') cb.HideDropDown();
                                return true;
                            }
                        }
                        cb.SetText('Đã đề nghị thanh toán');
                        if (typeof cb.SetValue === 'function') cb.SetValue('2');
                        if (typeof cb.HideDropDown === 'function') cb.HideDropDown();
                        return true;
                    }
                } catch(e) {}
                return false;
            }""")

            if not status_selected:
                btn_cb = page.locator("#cb_TrangThaiTT_B-1, #cb_TrangThaiTT_B-1Img").first
                if btn_cb.is_visible(timeout=2000):
                    btn_cb.click(force=True)
                    time.sleep(0.4)
                    item = page.locator("#cb_TrangThaiTT_DDD_L_LBT td, .dxeListBoxItem").filter(has_text=re.compile(r"Đã đề nghị thanh toán", re.IGNORECASE)).first
                    if item.is_visible(timeout=2000):
                        item.click(force=True)

            add_log("✅ Đã chọn trạng thái 'Đã đề nghị thanh toán'!")
            wait_for_grid_ready(page, timeout_ms=30000)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            # 4. Bấm Tìm kiếm (Không lọc ngày -> Tải toàn bộ cả tháng)
            add_log("🔍 Bấm nút Tìm kiếm (Tải toàn bộ hồ sơ cả tháng)...")
            searched = page.evaluate("""() => {
                try {
                    const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                    const btn = window.bt_TimKiem || (cc ? (cc.GetByName('bt_TimKiem') || cc.GetByName('btnTimKiem')) : null);
                    if (btn && typeof btn.DoClick === 'function') {
                        btn.DoClick();
                        return true;
                    }
                } catch(e) {}
                return false;
            }""")
            if not searched:
                s_el = page.locator("#bt_TimKiem_CD, #bt_TimKiem, #btnTimKiem").first
                if s_el.is_visible(timeout=2000): s_el.click(force=True)

            add_log("⏳ Đang chờ máy chủ Cổng BHYT nạp dữ liệu danh sách cả tháng (tối đa 20 phút)...")
            wait_for_grid_ready(page, timeout_ms=1200000)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")
            add_log("✅ Danh sách hồ sơ cả tháng đã nạp xong!")

            # 5. Xuất Excel
            add_log("📥 Đang kích hoạt Xuất Excel danh sách đã gửi cả tháng...")
            page.evaluate("""() => {
                try {
                    const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                    const btn = window.btnExport || (cc ? cc.GetByName('btnExport') : null);
                    if (btn && typeof btn.DoClick === 'function') btn.DoClick();
                } catch(e) {}
            }""")
            time.sleep(1.5)
            if stop_requested: raise Exception("Tiến trình đã bị dừng bởi người dùng.")

            add_log("⚡ Đang bấm nút 'Xuất excel' để tải file listbh.xlsx (Thời gian chờ tối đa 20 phút kèm Heartbeat)...")
            dest_path = os.path.join(OUTPUT_DIR, "listbh.xlsx")

            stop_hb = threading.Event()
            def heartbeat_worker():
                start_t = time.time()
                while not stop_hb.wait(10.0):
                    if stop_requested:
                        break
                    elapsed = int(time.time() - start_t)
                    add_log(f"⏳ [Heartbeat] Đang chờ Cổng BHYT xuất file cả tháng... (Đã chờ {elapsed}s / tối đa 1200s - Kết nối mạng ổn định)")

            hb_thread = threading.Thread(target=heartbeat_worker, daemon=True)
            hb_thread.start()

            try:
                with page.expect_download(timeout=1200000) as download_info:
                    clicked_exp = page.evaluate("""() => {
                        try {
                            const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                            const btn = window.btnExportExcel || (cc ? cc.GetByName('btnExportExcel') : null);
                            if (btn && typeof btn.DoClick === 'function') {
                                btn.DoClick();
                                return true;
                            }
                        } catch(e) {}
                        return false;
                    }""")
                    if not clicked_exp:
                        btn_d = page.locator("#btnExportExcel_CD, #btnExportExcel, .dxbButton:has-text('Xuất excel')").first
                        if btn_d.is_visible(timeout=5000): btn_d.click(force=True)

                download = download_info.value
                download.save_as(dest_path)
            finally:
                stop_hb.set()
                try: hb_thread.join(timeout=1.0)
                except Exception: pass

            add_log(f"✅ Tải tệp danh sách đã gửi thành công: {dest_path}")
            context.storage_state(path=SESSION_FILE)

            row_count = 0
            try:
                df = pd.read_excel(dest_path)
                row_count = len(df)
                add_log(f"📊 Đã nạp file listbh.xlsx với {row_count} dòng dữ liệu.")
            except Exception as de:
                add_log(f"Đọc file Excel: {de}")

            return {
                "status": "success",
                "flow": "B",
                "file_path": dest_path,
                "rows": row_count
            }

        finally:
            try: context.close()
            except Exception: pass
            try: browser.close()
            except Exception: pass
            active_browser = None
            active_context = None

# =========================================================================
# FASTAPI LOCAL SERVER
# =========================================================================
app = FastAPI(title="CheckBHYT Local Portal Downloader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

is_busy = False

@app.get("/", response_class=HTMLResponse)
def get_index():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>CheckBHYT Local Downloader Sẵn sàng.</h1>"

@app.get("/api/config")
def get_current_config():
    return load_config()

@app.post("/api/config")
def save_current_config(cfg: dict):
    save_config(cfg)
    return {"status": "success"}

@app.get("/api/logs")
async def get_logs_stream(request: Request):
    async def event_generator():
        last_id = 0
        while True:
            if await request.is_disconnected():
                break
            new_items = get_logs_since(last_id)
            if new_items:
                for it in new_items:
                    yield f"data: {it['text']}\n\n"
                    last_id = max(last_id, it["id"])
            import asyncio
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/stop")
async def handle_stop():
    stopped = stop_current_flow()
    return {"status": "success", "stopped": stopped, "message": "Đã gửi lệnh dừng tiến trình."}


@app.post("/api/flow-c")
async def handle_flow_c(data: dict):
    global is_busy
    if is_busy:
        raise HTTPException(status_code=400, detail="Hệ thống đang chạy một tác vụ khác. Vui lòng chờ hoàn thành!")
    is_busy = True
    save_config(data)
    try:
        import asyncio
        result = await asyncio.to_thread(run_flow_c, data)
        return result
    except Exception as e:
        add_log(f"❌ Lỗi thực thi Luồng C: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
    finally:
        is_busy = False

@app.post("/api/flow-b")
async def handle_flow_b(data: dict):
    global is_busy
    if is_busy:
        raise HTTPException(status_code=400, detail="Hệ thống đang chạy một tác vụ khác. Vui lòng chờ hoàn thành!")
    is_busy = True
    save_config(data)
    try:
        import asyncio
        result = await asyncio.to_thread(run_flow_b, data)
        return result
    except Exception as e:
        add_log(f"❌ Lỗi thực thi Luồng B: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
    finally:
        is_busy = False

@app.post("/api/submit-captcha")
async def handle_submit_captcha(data: dict):
    """Nhận mã Captcha do người dùng nhập từ giao diện web"""
    captcha_val = str(data.get("captcha", "")).strip()
    if not captcha_val:
        raise HTTPException(status_code=400, detail="Mã Captcha không được để trống")
    captcha_mgr.user_captcha_value = captcha_val
    captcha_mgr.waiting_event.set()
    return {"status": "success", "message": "Đã gửi mã Captcha"}

@app.post("/api/refresh-captcha")
async def handle_refresh_captcha():
    """Yêu cầu đổi mã Captcha mới trên Cổng BHYT"""
    captcha_mgr.refresh_event.set()
    return {"status": "success", "message": "Đã yêu cầu đổi mã Captcha"}

@app.post("/api/merge-only")
async def handle_merge_only():
    final_output = os.path.join(OUTPUT_DIR, "HoSoLoiChiTiet.xlsx")
    try:
        import asyncio
        summary = await asyncio.to_thread(merge_excel_files, DOWNLOADS_DIR, final_output)
        return {"status": "success", "summary": summary}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.get("/api/download-file")
def handle_download_file(file_type: str = "error_detail"):
    if file_type == "listbh":
        fp = os.path.join(OUTPUT_DIR, "listbh.xlsx")
        fn = "listbh.xlsx"
    else:
        fp = os.path.join(OUTPUT_DIR, "HoSoLoiChiTiet.xlsx")
        fn = "HoSoLoiChiTiet.xlsx"

    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail=f"Chưa có tệp {fn}. Vui lòng chạy tải trước.")

    return FileResponse(path=fp, filename=fn, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.post("/api/push-to-server")
async def handle_push_to_server(data: dict):
    """Gửi tệp đã tải lên máy chủ CHECKBHYT và kích hoạt đối soát tự động"""
    server_url = str(data.get("server_url", "")).strip().rstrip("/")
    flow = str(data.get("flow", "C")).upper()
    from_date = str(data.get("fromDate", "") or data.get("from_date", "")).strip()
    to_date = str(data.get("toDate", "") or data.get("to_date", "")).strip()

    if not server_url:
        server_url = "http://127.0.0.1:8000"

    target_filename = "listbh.xlsx" if flow == "B" else "HoSoLoiChiTiet.xlsx"
    file_path = os.path.join(OUTPUT_DIR, target_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp {target_filename} để gửi. Hãy chạy tải trước.")

    date_hint = f" (Đối soát CSDL: {from_date} đến {to_date})" if from_date and to_date else ""
    add_log(f"📤 Đang gửi tệp {target_filename} lên máy chủ CHECKBHYT ({server_url}){date_hint}...")

    upload_endpoint = f"{server_url}/api/automation/v2/upload-and-reconcile"

    def do_upload():
        with open(file_path, "rb") as f:
            files = {"file": (target_filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            form_payload = {
                "flow": flow,
                "fromDate": from_date,
                "toDate": to_date
            }
            resp = requests.post(upload_endpoint, files=files, data=form_payload, timeout=120)
            return resp

    try:
        import asyncio
        resp = await asyncio.to_thread(do_upload)
        if resp.status_code == 200:
            res_data = resp.json()
            add_log(f"✅ Gửi tệp thành công! Máy chủ đã hoàn tất đối soát CSDL: {res_data.get('message', '')}")
            return {"status": "success", "server_response": res_data}
        else:
            raise Exception(f"Máy chủ phản hồi mã {resp.status_code}: {resp.text}")
    except Exception as e:
        add_log(f"❌ Lỗi gửi tệp lên máy chủ: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8765")

if __name__ == "__main__":
    add_log("=======================================================")
    add_log("🚀 KHỞI ĐỘNG CÔNG CỤ TẢI & GỘP HỒ SƠ BHYT (CHẠY TRỰC TIẾP)")
    add_log("🌐 Giao diện trực quan sẵn sàng tại: http://localhost:8765")
    add_log("=======================================================")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
