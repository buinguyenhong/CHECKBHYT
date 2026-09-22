import sys
import os
import re
import time
import glob
import datetime
from typing import Callable, Optional, Dict, Any, List
import pandas as pd

# Tự động cấu hình mã hóa UTF-8 cho stdout/stderr tránh lỗi charmap trên Windows Server
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def safe_print(msg: str):
    try:
        print(msg)
    except Exception:
        try:
            print(msg.encode('ascii', 'replace').decode('ascii'))
        except Exception:
            pass

import base64
import threading

# Thư mục lưu trữ phiên đăng nhập và các tệp tải lên
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "browser_session")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files")
TEMP_ERROR_DIR = os.path.join(UPLOAD_DIR, "temp_errors")

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_ERROR_DIR, exist_ok=True)

SESSION_FILE = os.path.join(SESSION_DIR, "portal_storage_state.json")

# Danh sách log thời gian thực với số thứ tự tăng dần duy nhất (Monotonic sequence)
_portal_log_lock = threading.Lock()
_portal_log_seq: int = 0
portal_logs: List[Dict[str, Any]] = []

def add_portal_log(msg: str):
    global _portal_log_seq
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    with _portal_log_lock:
        _portal_log_seq += 1
        seq = _portal_log_seq
        portal_logs.append({"id": seq, "text": entry})
        if len(portal_logs) > 600:
            portal_logs.pop(0)
    safe_print(f"[*] [PortalAutomation] {entry}")

def get_portal_logs_since(last_id: int) -> Tuple[List[str], int]:
    with _portal_log_lock:
        new_entries = [item for item in portal_logs if item["id"] > last_id]
        new_last_id = portal_logs[-1]["id"] if portal_logs else last_id
        return [item["text"] for item in new_entries], new_last_id


def launch_native_browser(playwright_instance, headless: bool = False):
    """
    Khởi chạy Google Chrome hoặc Microsoft Edge có sẵn trên Windows.
    Ép cửa sổ luôn hiển thị nổi bật lên màn hình (Foreground & Maximized).
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
            browser = playwright_instance.chromium.launch(
                channel=channel,
                headless=headless,
                args=browser_args
            )
            safe_print(f"[*] Đã khởi chạy trình duyệt: {channel.upper()} có sẵn trên máy.")
            return browser
        except Exception:
            continue

    # Fallback nếu không có Chrome/Edge channel
    return playwright_instance.chromium.launch(
        headless=headless,
        args=browser_args
    )


# =========================================================================
# CAPTCHA MANAGER (AUTO-OCR + REMOTE WORKSTATION CAPTCHA BRIDGE)
# =========================================================================
import base64
import threading

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
                safe_print("[*] Đã kích hoạt thư viện Auto-OCR ddddocr thành công!")
            except Exception as e:
                safe_print(f"[*] Auto-OCR không khả dụng: {e}")
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


class PortalAutomationService:
    def __init__(
        self,
        base_url: str = "https://gdbhyt.baohiemxahoi.gov.vn/",
        ma_cskcb: str = "66232",
        username: str = "066091019320",
        password: str = ""
    ):
        self.base_url = base_url
        self.ma_cskcb = ma_cskcb
        self.username = username
        self.password = password
        self.is_busy: bool = False
        self.current_flow: str = ""
        self.current_client_token: str = ""
        self.stop_requested: bool = False
        self._current_browser = None
        self._current_context = None

    def update_config(self, base_url: str = "", ma_cskcb: str = "", username: str = "", password: str = ""):
        if base_url: self.base_url = base_url
        if ma_cskcb: self.ma_cskcb = ma_cskcb
        if username: self.username = username
        if password: self.password = password

    def stop_current_flow(self) -> bool:
        """Yêu cầu dừng ngay lập tức luồng đang chạy"""
        if not self.is_busy and not self._current_browser:
            return False
        self.stop_requested = True
        captcha_mgr.reset()
        add_portal_log("🛑 ĐÃ NHẬN LỆNH DỪNG TIẾN TRÌNH! Đang hủy các tác vụ và đóng trình duyệt...")
        try:
            if self._current_browser:
                self._current_browser.close()
        except Exception:
            pass
        return True

    def _ensure_login(self, page, log_func: Optional[Callable[[str], None]] = None):
        """
        Đảm bảo đăng nhập vào Cổng BHYT.
        Hỗ trợ:
        1. Kiểm tra session cũ còn hạn -> Bỏ qua không cần đăng nhập.
        2. Tự động điền Mã cơ sở, Tài khoản, Mật khẩu.
        3. Tự động giải Captcha bằng Auto-OCR (ddddocr).
        4. Nếu cần, chụp ảnh Captcha gửi trực tiếp về màn hình máy trạm để người dùng nhập từ xa.
        """
        def log(msg: str):
            if log_func:
                log_func(msg)
            safe_print(f"[*] [Login] {msg}")

        log("Đang truy cập Cổng BHYT: https://gdbhyt.baohiemxahoi.gov.vn/ ...")
        page.goto(self.base_url, timeout=90000, wait_until="load")
        time.sleep(1.0)

        # Đóng các popup thông báo nếu có
        try:
            btn_close_pop = page.locator(".dxpc-closeBtn, #btnKhong_CD, #btnKhong, input[value='Không']").first
            if btn_close_pop.is_visible(timeout=1500):
                btn_close_pop.click(force=True)
                time.sleep(0.5)
        except Exception:
            pass

        # 1. Kiểm tra xem phiên cũ còn hiệu lực không
        try:
            has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible(timeout=2000)
            has_menu = page.locator("#HeaderMenu").is_visible(timeout=2000) or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible(timeout=2000)
            has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible(timeout=2000)
            
            if (has_logout or has_menu) and not has_login_btn:
                log("Phiên đăng nhập vẫn còn hiệu lực (Session Valid) ✅ -> Vào thẳng chức năng, KHÔNG cần đăng nhập lại!")
                return
        except Exception:
            pass

        # 2. Chưa đăng nhập -> Tự động điền form đăng nhập
        log(f"Điền mã cơ sở: {self.ma_cskcb}, tài khoản: {self.username}...")
        try:
            ma_inp = page.locator("#macskcb, input[name*='MaCSKCB'], input[id*='txtMaCSKCB'], input[placeholder*='Mã cơ sở']").first
            if ma_inp.is_visible(timeout=3000):
                ma_inp.fill(self.ma_cskcb)

            user_inp = page.locator("#username, input[name*='UserName'], input[id*='txtUserName'], input[placeholder*='Tên đăng nhập']").first
            if user_inp.is_visible(timeout=3000):
                user_inp.fill(self.username)

            if self.password:
                pass_inp = page.locator("#password, input[type='password'], input[name*='Password'], input[id*='txtPassword']").first
                if pass_inp.is_visible(timeout=3000):
                    pass_inp.fill(self.password)
        except Exception as fe:
            log(f"Điền thông tin đăng nhập: {fe}")

        # Helper lấy ảnh Captcha Base64
        def grab_captcha_b64() -> Optional[str]:
            for sel in ["#Captcha_IMG1", "img[src*='Captcha']", "img[src*='captcha']", "img[id*='Captcha']"]:
                try:
                    c_el = page.locator(sel).first
                    if c_el.is_visible(timeout=2000):
                        src = c_el.get_attribute("src") or ""
                        if "base64," in src:
                            return src.split("base64,")[1]
                        raw = c_el.screenshot()
                        return base64.b64encode(raw).decode('utf-8')
                except Exception:
                    pass
            return None

        login_success = False
        start_wait = time.time()
        last_log_t = start_wait
        captcha_mgr.reset()

        # 3.1: Thử tự động giải Captcha bằng ddddocr
        b64 = grab_captcha_b64()
        ocr = captcha_mgr.get_ocr()
        ocr_result = ""
        if ocr and b64:
            try:
                ocr_result = ocr.classification(base64.b64decode(b64)).strip()
                if len(ocr_result) >= 4:
                    log(f"🤖 [Auto-OCR] Nhận diện được mã Captcha: '{ocr_result}'. Đang thử tự động đăng nhập...")
                    cap_inp = page.locator("#Captcha_TB_I, input[name*='Captcha'], input[placeholder*='mã hiển thị']").first
                    if cap_inp.is_visible(timeout=2000):
                        cap_inp.fill(ocr_result)
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
                            log(f"🎉 TỰ ĐỘNG GIẢI CAPTCHA THÀNH CÔNG ('{ocr_result}')! Đã đăng nhập vào Cổng BHYT ✅")
                            login_success = True
                        else:
                            log("⚠️ Mã Auto-OCR chưa chuẩn. Đang chuyển sang chế độ Popup chụp ảnh gửi về máy trạm...")
            except Exception as oe:
                log(f"Lưu ý Auto-OCR: {oe}")

        # 3.2: Nếu Auto-OCR chưa được -> Chụp ảnh Captcha gửi về giao diện Web máy trạm (Modal)
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

            token_tag = f":{self.current_client_token}" if self.current_client_token else ""
            # Gửi lệnh mở Modal Captcha trên màn hình máy trạm
            log(f"[CAPTCHA_REQUIRED{token_tag}] data:image/png;base64,{b64}###{ocr_text}")
            log("👉 ĐÃ CHỤP ẢNH CAPTCHA VÀ GỬI VỀ MÀN HÌNH MÁY TRẠM. Vui lòng gõ mã trên Popup hiển thị...")

            while time.time() - start_wait < 180:
                if self.stop_requested:
                    log("🛑 Đã dừng chờ Captcha theo yêu cầu người dùng.")
                    captcha_mgr.reset()
                    break

                # Kiểm tra yêu cầu đổi mã Captcha từ máy trạm
                if captcha_mgr.refresh_event.is_set():
                    captcha_mgr.refresh_event.clear()
                    log("🔄 Đang đổi mã Captcha mới trên Cổng BHYT...")
                    try:
                        page.locator("#Captcha_IMG1, a:has-text('Đổi mã'), .dxeCaptcha_EIS").first.click(force=True)
                        time.sleep(1.0)
                    except Exception:
                        pass
                    b64 = grab_captcha_b64()
                    ocr_text = ocr.classification(base64.b64decode(b64)).strip() if ocr and b64 else ""
                    captcha_mgr.current_captcha_b64 = b64
                    captcha_mgr.current_captcha_ocr = ocr_text
                    log(f"[CAPTCHA_REQUIRED{token_tag}] data:image/png;base64,{b64}###{ocr_text}")

                # Kiểm tra nhận mã Captcha từ máy trạm gửi lên
                if captcha_mgr.waiting_event.is_set():
                    captcha_mgr.waiting_event.clear()
                    user_val = captcha_mgr.user_captcha_value
                    log(f"📥 Đã nhận mã Captcha từ máy trạm: '{user_val}'. Đang điền và đăng nhập...")
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
                            log("🎉 ĐĂNG NHẬP THÀNH CÔNG! ✅")
                            log(f"[CAPTCHA_SUCCESS{token_tag}]")
                            login_success = True
                            captcha_mgr.reset()
                            break
                        else:
                            log("⚠️ Mã Captcha không chính xác. Đang chụp lại ảnh mới gửi về máy trạm...")
                            time.sleep(1.0)
                            b64 = grab_captcha_b64()
                            ocr_text = ocr.classification(base64.b64decode(b64)).strip() if ocr and b64 else ""
                            captcha_mgr.current_captcha_b64 = b64
                            captcha_mgr.current_captcha_ocr = ocr_text
                            log(f"[CAPTCHA_REQUIRED{token_tag}] data:image/png;base64,{b64}###{ocr_text}")
                    except Exception as le:
                        log(f"Lỗi đăng nhập: {le}")

                # Kiểm tra nếu đăng nhập trực tiếp trên trình duyệt
                try:
                    has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible()
                    has_menu = page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible()
                    has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible()
                    if (has_logout or has_menu) and not has_login_btn:
                        log("🎉 ĐĂNG NHẬP THÀNH CÔNG! ✅")
                        log(f"[CAPTCHA_SUCCESS{token_tag}]")
                        login_success = True
                        captcha_mgr.reset()
                        break
                except Exception:
                    pass

                now = time.time()
                if now - last_log_t >= 15:
                    elapsed = int(now - start_wait)
                    remaining = max(0, 180 - elapsed)
                    log(f"⏳ Đang chờ xác nhận Captcha... (Đã chờ {elapsed}s / còn lại {remaining}s)")
                    last_log_t = now

                time.sleep(0.5)

        captcha_mgr.reset()
        if self.stop_requested:
            raise Exception("Tiến trình đã bị dừng theo yêu cầu người dùng.")

        if not login_success:
            raise Exception("Quá thời gian 180 giây chờ nhập Captcha hoặc chưa hoàn tất Đăng nhập.")

        log("ĐĂNG NHẬP THÀNH CÔNG! ✅ Hệ thống đang lưu phiên làm việc...")
        try:
            page.context.storage_state(path=SESSION_FILE)
            log("💾 Đã lưu phiên làm việc (Session) thành công!")
        except Exception as se:
            log(f"Lưu storage state: {se}")

    def _wait_for_grid_ready(self, page, timeout_ms: int = 600000, log_func: Optional[Callable[[str], None]] = None):
        """
        Chờ DevExpress Grid hoàn tất nạp dữ liệu (InCallback = false và các loading panels biến mất).
        Hỗ trợ timeout lên đến 10 phút (600,000ms), thông báo tiến trình mỗi 15s.
        """
        start_time = time.time()
        time.sleep(1.0)
        last_report = start_time

        while (time.time() - start_time) * 1000 < timeout_ms:
            if self.stop_requested:
                if log_func: log_func("🛑 Đã dừng chờ dữ liệu theo yêu cầu.")
                return False

            is_busy = False
            try:
                is_busy = page.evaluate("""() => {
                    // 1. Kiểm tra DevExpress Grid InCallback
                    const grid = window.gvDSKetQuaGuiHoso || window.gvDanhSachHoSo;
                    if (grid && typeof grid.InCallback === 'function' && grid.InCallback()) {
                        return true;
                    }

                    // Kiểm tra tất cả control DevExpress
                    const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                    if (cc && typeof cc.ForEachControl === 'function') {
                        let active = false;
                        cc.ForEachControl(c => {
                            if (c && typeof c.InCallback === 'function' && c.InCallback()) active = true;
                        });
                        if (active) return true;
                    }

                    // 2. Kiểm tra Grid Loading Panel
                    const gridLp = document.getElementById('gvDSKetQuaGuiHoso_LP') || document.getElementById('gvDanhSachHoSo_LP');
                    if (gridLp) {
                        const style = window.getComputedStyle(gridLp);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && (gridLp.offsetWidth > 0 || gridLp.offsetHeight > 0)) {
                            return true;
                        }
                    }

                    // 3. Kiểm tra Loading Panel chung
                    const genLp = document.getElementById('_Loading');
                    if (genLp) {
                        const style = window.getComputedStyle(genLp);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && (genLp.offsetWidth > 0 || genLp.offsetHeight > 0)) {
                            return true;
                        }
                    }

                    // 4. Loading mask chung
                    const masks = document.querySelectorAll('.dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxlpLoadingPanelWithContent');
                    for (const m of masks) {
                        if (m.offsetParent !== null && window.getComputedStyle(m).display !== 'none') return true;
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
                if log_func:
                    log_func(f"⏳ Máy chủ BHYT đang xử lý dữ liệu... (Đã chờ {elapsed}s / {int(timeout_ms/1000)}s)...")
                last_report = time.time()

            time.sleep(0.8)

        if log_func:
            log_func(f"⚠️ Cảnh báo: Đã chờ tối đa {int(timeout_ms/1000)}s. Tiếp tục các thao tác...")
        return False

    def _extract_records_from_grid(self, page) -> List[Dict[str, Any]]:
        """
        Quét toàn bộ danh sách mã giao dịch (maGD) và STT trên bảng hiện tại.
        Kết hợp 3 cơ chế quét: Quét hàng DevExpress Grid, Quét liên kết <a>, Quét ô <td>.
        """
        try:
            return page.evaluate("""() => {
                const records = [];

                // Cách 1: Quét trực tiếp các hàng dữ liệu của bảng DevExpress
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

                        if (!records.some(r => r.maGD === maGD)) {
                            records.push({ stt, maGD });
                        }
                    }
                }

                if (records.length > 0) return records;

                // Cách 2: Quét tất cả các thẻ <a> (href, onclick, text)
                const allLinks = Array.from(document.querySelectorAll('a'));
                for (const a of allLinks) {
                    const rawText = (a.innerText || a.textContent || '').replace(/[\\r\\n\\t]/g, '').trim();
                    const onclick = a.getAttribute('onclick') || '';
                    const href = a.getAttribute('href') || '';
                    const combined = href + ' ' + onclick + ' ' + rawText;

                    const match = combined.match(/HSKCB[0-9A-Za-z_]+/);
                    if (match) {
                        const maGD = match[0];
                        const tr = a.closest('tr');
                        let stt = 0;
                        if (tr && tr.cells && tr.cells.length > 0) {
                            const parsed = parseInt((tr.cells[0].innerText || '').trim(), 10);
                            if (!isNaN(parsed) && parsed > 0) stt = parsed;
                        }
                        if (!stt) stt = records.length + 1;

                        if (!records.some(r => r.maGD === maGD)) {
                            records.push({ stt, maGD });
                        }
                    }
                }

                if (records.length > 0) return records;

                // Cách 3: Quét bất kỳ ô <td> nào có chứa chuỗi HSKCB
                const allCells = Array.from(document.querySelectorAll('td'));
                for (const td of allCells) {
                    const match = (td.innerText || '').match(/HSKCB[0-9A-Za-z_]+/);
                    if (match) {
                        const maGD = match[0];
                        const tr = td.closest('tr');
                        let stt = 0;
                        if (tr && tr.cells && tr.cells.length > 0) {
                            const parsed = parseInt((tr.cells[0].innerText || '').trim(), 10);
                            if (!isNaN(parsed) && parsed > 0) stt = parsed;
                        }
                        if (!stt) stt = records.length + 1;

                        if (!records.some(r => r.maGD === maGD)) {
                            records.push({ stt, maGD });
                        }
                    }
                }

                return records;
            }""")
        except Exception as e:
            safe_print(f"[*] Lỗi extract records: {e}")
            return []

    def _download_direct_record(
        self,
        page,
        ma_gd: str,
        stt: int,
        save_dir: str,
        log_func: Optional[Callable[[str], None]] = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Tải file trực tiếp qua Direct HTTP Endpoint: ExportExcelKPG_New?maGd={maGD}.
        Sử dụng page.request.get() với session cookie hiện tại của trình duyệt.
        """
        def log(msg: str):
            if log_func: log_func(msg)
            safe_print(f"[*] [DownloadDirect] {msg}")

        download_url = f"https://gdbhyt.baohiemxahoi.gov.vn/DanhSachKetQuaGuiHoSoQD130/ExportExcelKPG_New?maGd={ma_gd}"
        file_name = f"STT_{str(stt).zfill(4)}_{ma_gd}.xlsx"
        file_path = os.path.join(save_dir, file_name)

        # Nếu file đã có và dung lượng hợp lệ (> 1KB) thì bỏ qua
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
            log(f"✅ [STT {stt}] Đã có sẵn file: {file_name}, bỏ qua không tải lại.")
            return file_path

        for attempt in range(1, max_retries + 1):
            try:
                log(f"⚡ [STT {stt}] Đang tải hồ sơ {ma_gd} (Lần {attempt})...")
                response = page.request.get(download_url, timeout=60000)
                
                if not response.ok:
                    raise Exception(f"HTTP Status {response.status}: {response.status_text}")

                body = response.body()
                if not body or len(body) < 500:
                    raise Exception(f"Dữ liệu tải về quá nhỏ ({len(body) if body else 0} bytes), có thể do phiên hết hạn.")

                with open(file_path, "wb") as f:
                    f.write(body)

                kb_size = round(len(body) / 1024, 1)
                log(f"✅ [STT {stt}] Tải thành công ({kb_size} KB) -> {file_name}")
                return file_path
            except Exception as err:
                log(f"⚠️ [STT {stt}] Lỗi tải lần {attempt}: {err}")
                if attempt < max_retries:
                    time.sleep(2.0 * attempt)
                else:
                    log(f"❌ [STT {stt}] Thất bại sau {max_retries} lần thử: {ma_gd}")
                    return None

    def merge_excel_files(
        self,
        download_dir: str,
        output_file_path: str,
        log_func: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Gộp tất cả các file .xlsx trong download_dir thành 1 file Excel duy nhất
        và loại bỏ các dòng dữ liệu trùng lặp (chuẩn theo logic merger.js).
        """
        def log(msg: str):
            if log_func: log_func(msg)
            safe_print(f"[*] [MergeExcel] {msg}")

        if not os.path.exists(download_dir):
            raise Exception(f"Thư mục {download_dir} không tồn tại.")

        files = [
            os.path.join(download_dir, f)
            for f in os.listdir(download_dir)
            if f.endswith('.xlsx') and not f.startswith('~$') and not f.startswith('KetQua_TongHop')
        ]

        if not files:
            # Tạo file rỗng nếu chưa có dữ liệu
            empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"])
            empty_df.to_excel(output_file_path, index=False)
            return {
                "total_files": 0,
                "total_records": 0,
                "unique_records": 0,
                "duplicates_removed": 0,
                "output_path": output_file_path
            }

        log(f"📊 Bắt đầu quét {len(files)} file Excel để gộp và khử trùng dữ liệu...")

        all_dfs = []
        total_data_rows = 0

        for i, file_p in enumerate(files):
            try:
                df = pd.read_excel(file_p)
                if not df.empty:
                    total_data_rows += len(df)
                    all_dfs.append(df)
                if (i + 1) % 15 == 0 or i == len(files) - 1:
                    log(f"  -> Đang đọc file {i + 1}/{len(files)} ({os.path.basename(file_p)})...")
            except Exception as e:
                log(f"⚠️ Không thể đọc file {os.path.basename(file_p)}: {e}")

        if not all_dfs:
            empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"])
            empty_df.to_excel(output_file_path, index=False)
            return {
                "total_files": len(files),
                "total_records": 0,
                "unique_records": 0,
                "duplicates_removed": 0,
                "output_path": output_file_path
            }

        combined_df = pd.concat(all_dfs, ignore_index=True)

        # Khử trùng dữ liệu dựa trên tất cả các cột trừ cột STT đầu tiên nếu có
        subset_cols = [c for c in combined_df.columns if str(c).strip().upper() not in ["STT", "TT"]]
        if not subset_cols:
            subset_cols = list(combined_df.columns)

        unique_df = combined_df.drop_duplicates(subset=subset_cols, keep='first')
        unique_data_rows = len(unique_df)
        duplicates_removed = total_data_rows - unique_data_rows

        log(f"💾 Đang ghi file Excel tổng hợp ra: {output_file_path}...")
        unique_df.to_excel(output_file_path, index=False)

        log("🎉 GỘP HOÀN TẤT:")
        log(f"   - Tổng số file xử lý: {len(files)} file")
        log(f"   - Tổng số dòng đọc được: {total_data_rows} dòng")
        log(f"   - Số dòng giữ lại (duy nhất): {unique_data_rows} dòng")
        log(f"   - Số dòng trùng lặp đã loại bỏ: {duplicates_removed} dòng")
        log(f"   - File kết quả: {output_file_path}")

        return {
            "total_files": len(files),
            "total_records": total_data_rows,
            "unique_records": unique_data_rows,
            "duplicates_removed": duplicates_removed,
            "output_path": output_file_path
        }

    # =========================================================================
    # LUỒNG C MỚI (CÔNG NGHỆ DIRECT URL DOWNLOAD & KHÔNG MỞ POPUP)
    # =========================================================================
    def run_flow_c(
        self,
        from_stt: int = 1,
        to_stt: int = 100,
        filter_col5: str = "1",
        log_func: Optional[Callable[[str], None]] = None,
        client_token: str = ""
    ) -> Dict[str, Any]:
        """
        LUỒNG C MỚI: Tự động tải Danh sách lỗi chi tiết QĐ 3176 siêu tốc.
        - Chạy Chrome/Edge native có sẵn trên máy.
        - Lọc Today, Cột 5 = 1, Hiển thị 100 dòng, sắp xếp Thời gian mới nhất lên đầu.
        - Tải trực tiếp bằng Direct HTTP URL: ExportExcelKPG_New?maGd={maGD} (Không mở Popup).
        - Gộp file và lọc trùng dòng dữ liệu sạch sẽ thành HoSoLoiChiTiet.xlsx.
        """
        if self.is_busy:
            raise Exception(f"Hệ thống đang thực thi một tác vụ khác (Luồng {self.current_flow}). Vui lòng chờ hoặc bấm 'Dừng' trước khi chạy mới.")
        self.is_busy = True
        self.current_flow = "C"
        self.current_client_token = client_token
        self.stop_requested = False

        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func: log_func(msg)
            safe_print(f"[*] [Flow C] {msg}")

        log(f"🚀 Khởi động Luồng C Mới (Direct URL Download) - Phạm vi STT: {from_stt} đến {to_stt}...")

        # Xóa các file tạm cũ trong temp_errors để chuẩn bị phiên mới
        for old_f in glob.glob(os.path.join(TEMP_ERROR_DIR, "*.*")):
            try:
                os.remove(old_f)
            except Exception:
                pass

        with sync_playwright() as p:
            log("🌐 Đang khởi động trình duyệt (Google Chrome / Microsoft Edge)...")
            browser = launch_native_browser(p, headless=False)
            self._current_browser = browser

            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            context = browser.new_context(
                storage_state=storage_path,
                viewport=None,
                accept_downloads=True
            )
            self._current_context = context
            page = context.new_page()
            page.set_default_timeout(600000)
            page.set_default_navigation_timeout(600000)
            try:
                page.bring_to_front()
            except Exception:
                pass

            try:
                # 1. Đảm bảo đăng nhập
                self._ensure_login(page, log_func=log)
                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}

                # 2. Điều hướng vào màn hình QĐ 3176
                log("📌 Đang điều hướng đến: Kết quả gửi hồ sơ XML (/DanhSachKetQuaGuiHoSoQD130/Index)...")
                target_url = f"{self.base_url.rstrip('/')}/DanhSachKetQuaGuiHoSoQD130/Index"
                try:
                    page.goto(target_url, timeout=90000, wait_until="load")
                except Exception as e:
                    log(f"Truy cập URL trực tiếp: {e}, đang thử click Menu...")
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
                self._wait_for_grid_ready(page, timeout_ms=90000, log_func=log)

                # 3. Đặt ngày = Today
                log("📅 Thiết lập bộ lọc: Chọn ngày 'Today'...")
                try:
                    page.evaluate("""() => {
                        const now = new Date();
                        if (window.dt_TuNgay && typeof window.dt_TuNgay.SetValue === 'function') {
                            window.dt_TuNgay.SetValue(now);
                        }
                        if (window.dt_DenNgay && typeof window.dt_DenNgay.SetValue === 'function') {
                            window.dt_DenNgay.SetValue(now);
                        }
                    }""")
                    # Thử click nút Today trên popup nếu có
                    drop_btn = page.locator("#dt_TuNgay_B-1, #dt_TuNgay_B-1Img, table#dt_TuNgay img").first
                    if drop_btn.is_visible(timeout=1000):
                        drop_btn.click(force=True)
                        time.sleep(0.3)
                        today_cell = page.get_by_role("cell", name="Today", exact=True).or_(page.locator("td.dxeCalendarToday_EIS, td:has-text('Today')")).first
                        if today_cell.is_visible(timeout=1000):
                            today_cell.click(force=True)
                except Exception:
                    pass

                # Bấm nút "Tìm kiếm"
                log("🔍 Bấm nút 'Tìm kiếm' và chờ máy chủ phản hồi (tối đa 10 phút)...")
                search_btn = page.locator("span").filter(has_text=re.compile(r"^Tìm kiếm$")).first
                if search_btn.is_visible(timeout=3000):
                    search_btn.click(force=True)
                else:
                    page.evaluate("if (window.btnTimKiem && typeof window.btnTimKiem.DoClick === 'function') window.btnTimKiem.DoClick();")

                self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                log("✅ Bảng dữ liệu đã nạp xong theo ngày Today!")

                # 4. Lọc Cột 5 (Lỗi = 1)
                if filter_col5:
                    log(f"🔎 Nhập bộ lọc Cột 5 = '{filter_col5}'...")
                    col5_inp = page.locator("#gvDSKetQuaGuiHoso_DXFREditorcol5_I")
                    if col5_inp.is_visible(timeout=5000):
                        col5_inp.click()
                        col5_inp.fill(filter_col5)
                        col5_inp.press("Enter")
                    else:
                        page.evaluate(f"if (window.gvDSKetQuaGuiHoso) window.gvDSKetQuaGuiHoso.AutoFilterByColumn(5, '{filter_col5}');")
                    self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                    log("✅ Lọc Cột 5 hoàn tất!")

                # 5. Chọn Page size = 100
                log("📄 Thiết lập kích thước trang: 100 dòng/trang...")
                try:
                    page_size_inp = page.get_by_role("textbox", name="Page size:")
                    if page_size_inp.is_visible(timeout=2000):
                        page_size_inp.click()
                        time.sleep(0.4)
                        page.get_by_text("100", exact=True).first.click()
                        self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                        log("✅ Đã chọn hiển thị 100 dòng/trang!")
                except Exception:
                    pass

                # 6. Sắp xếp giảm dần theo Thời gian (Click 2 lần header Thời gian)
                log("⏱️ Sắp xếp cột 'Thời gian' (Click 2 lần để mới nhất lên đầu)...")
                try:
                    thoi_gian_hdr = page.get_by_role("cell", name="Thời gian", exact=True).or_(page.get_by_text("Thời gian", exact=True)).first
                    if thoi_gian_hdr.is_visible(timeout=3000):
                        thoi_gian_hdr.click(force=True)
                        self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                        time.sleep(0.5)
                        thoi_gian_hdr.click(force=True)
                        self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                        log("✅ Bảng đã được sắp xếp giảm dần theo thời gian!")
                except Exception as s_err:
                    log(f"Lưu ý sắp xếp: {s_err}")

                # 7. VÒNG LẶP DUYỆT VÀ TẢI THEO DẢI STT BẰNG DIRECT URL
                log(f"🎯 BẮT ĐẦU TẢI CÁC HỒ SƠ TỪ STT {from_stt} ĐẾN STT {to_stt} (DIRECT URL DOWNLOAD)...")
                current_stt = from_stt
                downloaded_count = 0
                current_page_num = 1

                while current_stt <= to_stt:
                    if self.stop_requested:
                        log("🛑 Tiến trình Luồng C đã bị dừng theo yêu cầu người dùng.")
                        break

                    log(f"\n📑 Đang quét dữ liệu tại Trang {current_page_num}...")
                    self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                    if self.stop_requested:
                        break

                    records = self._extract_records_from_grid(page)
                    if not records:
                        log("⚠️ Không tìm thấy bản ghi nào trên trang hiện tại. Đã hết dữ liệu.")
                        break

                    log(f"📋 Tìm thấy {len(records)} bản ghi trên Trang {current_page_num}. Đầu trang: STT {records[0].get('stt')} | {records[0].get('maGD')}")

                    records_to_dl = [r for r in records if r.get('stt', 0) >= current_stt and r.get('stt', 0) <= to_stt]

                    if not records_to_dl:
                        records_to_dl = [
                            {"stt": (current_page_num - 1) * 100 + (i + 1), "maGD": r.get('maGD')}
                            for i, r in enumerate(records)
                            if (current_page_num - 1) * 100 + (i + 1) >= current_stt and (current_page_num - 1) * 100 + (i + 1) <= to_stt
                        ]

                    log(f"⚡ Sẽ tải {len(records_to_dl)} bản ghi trên trang này...")

                    for rec in records_to_dl:
                        if self.stop_requested:
                            log("🛑 Đã nhận lệnh dừng! Ngừng tải tiếp các bản ghi...")
                            break
                        fp = self._download_direct_record(
                            page=page,
                            ma_gd=rec['maGD'],
                            stt=rec['stt'],
                            save_dir=TEMP_ERROR_DIR,
                            log_func=log
                        )
                        if fp:
                            downloaded_count += 1
                        current_stt = rec['stt'] + 1
                        time.sleep(0.2)  # Nghỉ 200ms để server không bị nghẽn

                    if self.stop_requested or current_stt > to_stt:
                        if current_stt > to_stt:
                            log(f"🎉 Đã tải hoàn tất đến STT {to_stt}!")
                        break

                    # Chuyển sang trang tiếp theo
                    current_page_num += 1
                    log(f"➡️ Chuyển sang Trang {current_page_num} tại thanh phân trang...")
                    pager = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom")
                    next_page_btn = pager.get_by_text(str(current_page_num), exact=True)

                    if next_page_btn.count() > 0:
                        next_page_btn.first.click(force=True)
                        log(f"⏳ Chờ Trang {current_page_num} nạp dữ liệu...")
                        self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)
                    else:
                        log(f"⚠️ Không tìm thấy nút Trang {current_page_num}. Đã đến trang cuối.")
                        break

                if self.stop_requested:
                    log(f"🛑 TIẾN TRÌNH LUỒNG C ĐÃ BỊ DỪNG LẠI THEO YÊU CẦU! Đã tải {downloaded_count} gói lỗi.")
                    return {
                        "status": "stopped",
                        "downloaded_count": downloaded_count,
                        "message": f"Tiến trình đã được dừng theo yêu cầu. Đã tải {downloaded_count} gói lỗi."
                    }

                log(f"\n📦 ĐÃ TẢI XONG TỔNG CỘNG {downloaded_count} FILE HỒ SƠ LỖI.")

                # 8. GỘP FILE EXCEL VÀ LỌC DÒNG TRÙNG
                log("📊 Đang tiến hành gộp dữ liệu các file Excel và loại bỏ các dòng trùng lặp...")
                final_output_file = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
                summary = self.merge_excel_files(TEMP_ERROR_DIR, final_output_file, log_func=log)

                # Lưu context session
                context.storage_state(path=SESSION_FILE)

                log("🌟 QUY TRÌNH LUỒNG C MỚI ĐÃ HOÀN TẤT TRỌN VẸN!")
                return {
                    "status": "success",
                    "downloaded_count": downloaded_count,
                    "file_path": final_output_file,
                    "summary": summary,
                    "message": f"Tải thành công {downloaded_count} gói lỗi, tổng hợp thành {summary['unique_records']} bản ghi duy nhất."
                }

            except Exception as e:
                log(f"❌ Lỗi thực thi Luồng C: {str(e)}")
                raise e
            finally:
                self.is_busy = False
                self.current_flow = ""
                self.current_client_token = ""
                self.stop_requested = False
                self._current_browser = None
                self._current_context = None
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass

    # =========================================================================
    # LUỒNG B MỚI (NATIVE BROWSER & TIMEOUT 600S)
    # =========================================================================
    def run_flow_b(
        self,
        log_func: Optional[Callable[[str], None]] = None,
        client_token: str = ""
    ) -> Dict[str, Any]:
        """
        LUỒNG B MỚI: Tự động tải Danh sách đã gửi (listbh.xlsx) từ Cổng BHYT.
        - Chạy Chrome/Edge native trên Windows.
        - Chọn 'Đã đề nghị thanh toán', Tìm kiếm và xuất file listbh.xlsx.
        - Timeout 1200s (20 phút) để xử lý file dung lượng lớn.
        """
        if self.is_busy:
            raise Exception(f"Hệ thống đang thực thi một tác vụ khác (Luồng {self.current_flow}). Vui lòng chờ hoặc bấm 'Dừng' trước khi chạy mới.")
        self.is_busy = True
        self.current_flow = "B"
        self.current_client_token = client_token
        self.stop_requested = False

        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func: log_func(msg)
            safe_print(f"[*] [Flow B] {msg}")

        log("🚀 Khởi động Luồng B Mới (Tải danh sách đã gửi listbh.xlsx)...")

        with sync_playwright() as p:
            log("🌐 Đang khởi động trình duyệt (Google Chrome / Microsoft Edge)...")
            browser = launch_native_browser(p, headless=False)
            self._current_browser = browser

            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            context = browser.new_context(
                storage_state=storage_path,
                viewport=None,
                accept_downloads=True
            )
            self._current_context = context
            page = context.new_page()
            page.set_default_timeout(1200000)
            page.set_default_navigation_timeout(1200000)
            try:
                page.bring_to_front()
            except Exception:
                pass

            try:
                # 1. Đảm bảo đăng nhập
                self._ensure_login(page, log_func=log)
                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}

                # 2. Điều hướng vào Danh sách đề nghị thanh toán
                log("📌 Đang điều hướng đến: Danh sách đề nghị thanh toán (/DanhSachHSKCB/Index)...")
                target_url = f"{self.base_url.rstrip('/')}/DanhSachHSKCB/Index"
                try:
                    page.goto(target_url, timeout=90000, wait_until="load")
                except Exception as e:
                    log(f"Truy cập URL trực tiếp: {e}")

                page.wait_for_selector("#gvDanhSachHoSo, #bt_TimKiem, #btnExport, #cb_TrangThaiTT", timeout=60000)
                self._wait_for_grid_ready(page, timeout_ms=60000, log_func=log)
                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}

                # 3. Chọn Trạng thái: 'Đã đề nghị thanh toán'
                log("🏷️ Đang chọn trạng thái: 'Đã đề nghị thanh toán'...")
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
                    } catch(err) {}
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

                log("✅ Đã chọn trạng thái 'Đã đề nghị thanh toán'!")
                self._wait_for_grid_ready(page, timeout_ms=30000, log_func=log)
                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}

                # 4. Bấm Tìm kiếm
                log("🔍 Bấm nút Tìm kiếm dữ liệu...")
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
                    if s_el.is_visible(timeout=2000):
                        s_el.click(force=True)

                log("⏳ Đang chờ máy chủ Cổng BHYT nạp dữ liệu danh sách đề nghị thanh toán cả tháng (tối đa 20 phút)...")
                self._wait_for_grid_ready(page, timeout_ms=1200000, log_func=log)
                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}
                log("✅ Dữ liệu danh sách hồ sơ cả tháng đã nạp xong!")

                # 5. Xuất Excel và tải file listbh.xlsx
                log("📥 Đang kích hoạt Xuất Excel danh sách đã gửi (toàn bộ cả tháng)...")
                
                # Bước 5.1: Mở popup Export
                page.evaluate("""() => {
                    try {
                        const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                        const btn = window.btnExport || (cc ? cc.GetByName('btnExport') : null);
                        if (btn && typeof btn.DoClick === 'function') btn.DoClick();
                    } catch(e) {}
                }""")
                time.sleep(1.5)

                if self.stop_requested:
                    return {"status": "stopped", "message": "Tiến trình đã bị dừng theo yêu cầu."}

                # Bước 5.2: Bấm nút "Xuất excel" trong Popup và nhận luồng Download với Heartbeat
                log("⚡ Đang bấm nút 'Xuất excel' để tải file listbh.xlsx (Thời gian chờ tối đa 20 phút kèm Heartbeat)...")
                dest_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")

                import threading
                stop_hb = threading.Event()

                def heartbeat_worker():
                    start_t = time.time()
                    while not stop_hb.wait(10.0) and not self.stop_requested:
                        elapsed = int(time.time() - start_t)
                        log(f"⏳ [Heartbeat] Đang chờ Cổng BHYT xử lý xuất file cả tháng... (Đã chờ {elapsed}s / tối đa 1200s - Kết nối bình thường)")

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
                            if btn_d.is_visible(timeout=5000):
                                btn_d.click(force=True)

                    download = download_info.value
                    download.save_as(dest_path)
                finally:
                    stop_hb.set()
                    try:
                        hb_thread.join(timeout=1.0)
                    except Exception:
                        pass

                if self.stop_requested:
                    log("🛑 Tiến trình Luồng B đã bị dừng lại theo yêu cầu người dùng.")
                    return {
                        "status": "stopped",
                        "message": "Tiến trình đã được dừng bởi người dùng."
                    }

                log(f"✅ Tải tệp danh sách đã gửi thành công: {dest_path}")

                context.storage_state(path=SESSION_FILE)

                # Đọc số dòng của file tải về
                row_count = 0
                try:
                    df = pd.read_excel(dest_path)
                    row_count = len(df)
                    log(f"📊 Đã nạp file listbh.xlsx với {row_count} dòng dữ liệu.")
                except Exception as de:
                    log(f"Đọc file Excel: {de}")

                return {
                    "status": "success",
                    "file_path": dest_path,
                    "rows": row_count,
                    "message": f"Tải thành công {row_count} bản ghi danh sách đã gửi."
                }

            except Exception as e:
                log(f"❌ Lỗi thực thi Luồng B: {str(e)}")
                raise e
            finally:
                self.is_busy = False
                self.current_flow = ""
                self.current_client_token = ""
                self.stop_requested = False
                self._current_browser = None
                self._current_context = None
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass


portal_service = PortalAutomationService()
