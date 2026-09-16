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

# Thư mục lưu trữ phiên đăng nhập và các tệp tải lên
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "browser_session")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files")
TEMP_ERROR_DIR = os.path.join(UPLOAD_DIR, "temp_errors")

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_ERROR_DIR, exist_ok=True)

SESSION_FILE = os.path.join(SESSION_DIR, "portal_storage_state.json")

# Danh sách log thời gian thực để UI có thể hiển thị
portal_logs: List[str] = []

def add_portal_log(msg: str):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    portal_logs.append(entry)
    if len(portal_logs) > 300:
        portal_logs.pop(0)
    safe_print(f"[*] [PortalAutomation] {entry}")


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

    def update_config(self, base_url: str = "", ma_cskcb: str = "", username: str = "", password: str = ""):
        if base_url: self.base_url = base_url
        if ma_cskcb: self.ma_cskcb = ma_cskcb
        if username: self.username = username
        if password: self.password = password

    def _ensure_login(self, page, log_func: Optional[Callable[[str], None]] = None):
        """
        Kiểm tra và thực hiện đăng nhập vào Cổng Giám định BHYT.
        Tự động điền Mã cơ sở KCB, Tên đăng nhập, Mật khẩu và chờ người dùng nhập Captcha.
        """
        def log(msg: str):
            if log_func:
                log_func(msg)
            safe_print(f"[*] [Login] {msg}")

        log("Đang truy cập Cổng BHYT: https://gdbhyt.baohiemxahoi.gov.vn/ ...")
        page.goto(self.base_url, timeout=90000, wait_until="load")
        time.sleep(1.0)

        # Đóng các popup thông báo hoặc OTP nếu có
        try:
            btn_close_pop = page.locator(".dxpc-closeBtn, #btnKhong_CD, #btnKhong, input[value='Không']").first
            if btn_close_pop.is_visible(timeout=1500):
                btn_close_pop.click(force=True)
                time.sleep(0.5)
        except Exception:
            pass

        # Kiểm tra xem đã đăng nhập chưa
        try:
            has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible(timeout=2000)
            has_login_btn = page.locator("a:has-text('Đăng nhập'), input[value='Đăng nhập'], #btnLogin, #btnDangNhap, input[name*='UserName']").is_visible(timeout=2000)
            
            if has_logout and not has_login_btn:
                log("Phiên đăng nhập vẫn còn hiệu lực (Session Valid) ✅ -> Vào thẳng chức năng, KHÔNG cần đăng nhập lại!")
                return
        except Exception:
            pass

        # Chưa đăng nhập -> Tự động điền form đăng nhập
        log(f"Điền mã cơ sở: {self.ma_cskcb}, tài khoản: {self.username}...")
        
        try:
            # Điền Mã cơ sở KCB
            ma_inp = page.locator("input[name*='MaCSKCB'], input[id*='txtMaCSKCB'], input[placeholder*='Mã cơ sở']").first
            if ma_inp.is_visible(timeout=3000):
                ma_inp.click()
                ma_inp.fill(self.ma_cskcb)
            elif page.get_by_role("textbox", name="Mã cơ sở KCB").is_visible(timeout=2000):
                page.get_by_role("textbox", name="Mã cơ sở KCB").fill(self.ma_cskcb)
            
            # Điền Tên đăng nhập
            user_inp = page.locator("input[name*='UserName'], input[id*='txtUserName'], input[placeholder*='Tên đăng nhập']").first
            if user_inp.is_visible(timeout=3000):
                user_inp.click()
                user_inp.fill(self.username)
            elif page.get_by_role("textbox", name="Tên đăng nhập").is_visible(timeout=2000):
                page.get_by_role("textbox", name="Tên đăng nhập").fill(self.username)
            
            # Điền Mật khẩu (nếu có)
            if self.password:
                pass_inp = page.locator("input[type='password'], input[name*='Password'], input[id*='txtPassword']").first
                if pass_inp.is_visible(timeout=3000):
                    pass_inp.click()
                    pass_inp.fill(self.password)
                elif page.get_by_role("textbox", name="Mật khẩu").is_visible(timeout=2000):
                    page.get_by_role("textbox", name="Mật khẩu").fill(self.password)
            
            # Focus vào ô Captcha để người dùng nhập
            cap_inp = page.locator("input[name*='Captcha'], input[id*='Captcha'], input[placeholder*='mã hiển thị']").first
            if cap_inp.is_visible(timeout=3000):
                cap_inp.click()
                cap_inp.focus()
            
            log("👉 VUI LÒNG NHÌN VÀ NHẬP MÃ HIỂN THỊ (CAPTCHA), SAU ĐÓ BẤM ĐĂNG NHẬP TRÊN TRÌNH DUYỆT...")
            
            # Chờ người dùng nhập captcha và đăng nhập thành công
            login_success = False
            start_wait = time.time()
            while time.time() - start_wait < 180:
                try:
                    if page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible():
                        login_success = True
                        break
                    if page.locator("#HeaderMenu, #roundPanel, #MainPane").is_visible() and not page.locator("input[name*='UserName']").is_visible():
                        login_success = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            if not login_success:
                raise Exception("Quá thời gian 180 giây chờ nhập Captcha hoặc chưa hoàn tất Đăng nhập.")

            log("ĐĂNG NHẬP THÀNH CÔNG! ✅ Hệ thống đang lưu phiên làm việc...")
            
            # Lưu session state để dùng lại lần sau
            try:
                page.context.storage_state(path=SESSION_FILE)
            except Exception as se:
                log(f"Lưu storage state: {se}")

        except Exception as e:
            log(f"Lỗi đăng nhập: {str(e)}")
            raise Exception(f"Không thể đăng nhập Cổng BHYT: {str(e)}")

    def _wait_for_grid_ready(self, page, timeout_ms: int = 600000, log_func: Optional[Callable[[str], None]] = None):
        """
        Chờ DevExpress Grid hoàn tất nạp dữ liệu (InCallback = false và các loading panels biến mất).
        Hỗ trợ timeout lên đến 10 phút (600,000ms), thông báo tiến trình mỗi 15s.
        """
        start_time = time.time()
        time.sleep(1.0)
        last_report = start_time

        while (time.time() - start_time) * 1000 < timeout_ms:
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
        log_func: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        LUỒNG C MỚI: Tự động tải Danh sách lỗi chi tiết QĐ 3176 siêu tốc.
        - Chạy Chrome/Edge native có sẵn trên máy.
        - Lọc Today, Cột 5 = 1, Hiển thị 100 dòng, sắp xếp Thời gian mới nhất lên đầu.
        - Tải trực tiếp bằng Direct HTTP URL: ExportExcelKPG_New?maGd={maGD} (Không mở Popup).
        - Gộp file và lọc trùng dòng dữ liệu sạch sẽ thành HoSoLoiChiTiet.xlsx.
        """
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

            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            context = browser.new_context(
                storage_state=storage_path,
                viewport=None,
                accept_downloads=True
            )
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
                    log(f"\n📑 Đang quét dữ liệu tại Trang {current_page_num}...")
                    self._wait_for_grid_ready(page, timeout_ms=600000, log_func=log)

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
                context.close()
                browser.close()

    # =========================================================================
    # LUỒNG B MỚI (NATIVE BROWSER & TIMEOUT 600S)
    # =========================================================================
    def run_flow_b(
        self,
        log_func: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        LUỒNG B MỚI: Tự động tải Danh sách đã gửi (listbh.xlsx) từ Cổng BHYT.
        - Chạy Chrome/Edge native trên Windows.
        - Chọn 'Đã đề nghị thanh toán', Tìm kiếm và xuất file listbh.xlsx.
        - Timeout 600s (10 phút) để xử lý file dung lượng lớn.
        """
        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func: log_func(msg)
            safe_print(f"[*] [Flow B] {msg}")

        log("🚀 Khởi động Luồng B Mới (Tải danh sách đã gửi listbh.xlsx)...")

        with sync_playwright() as p:
            log("🌐 Đang khởi động trình duyệt (Google Chrome / Microsoft Edge)...")
            browser = launch_native_browser(p, headless=False)

            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            context = browser.new_context(
                storage_state=storage_path,
                viewport=None,
                accept_downloads=True
            )
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

                # 2. Điều hướng vào Danh sách đề nghị thanh toán
                log("📌 Đang điều hướng đến: Danh sách đề nghị thanh toán (/DanhSachHSKCB/Index)...")
                target_url = f"{self.base_url.rstrip('/')}/DanhSachHSKCB/Index"
                try:
                    page.goto(target_url, timeout=90000, wait_until="load")
                except Exception as e:
                    log(f"Truy cập URL trực tiếp: {e}")

                page.wait_for_selector("#gvDanhSachHoSo, #bt_TimKiem, #btnExport, #cb_TrangThaiTT", timeout=60000)
                self._wait_for_grid_ready(page, timeout_ms=60000, log_func=log)

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

                # Bước 5.2: Bấm nút "Xuất excel" trong Popup và nhận luồng Download với Heartbeat
                log("⚡ Đang bấm nút 'Xuất excel' để tải file listbh.xlsx (Thời gian chờ tối đa 20 phút kèm Heartbeat)...")
                dest_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")

                import threading
                stop_hb = threading.Event()

                def heartbeat_worker():
                    start_t = time.time()
                    while not stop_hb.wait(10.0):
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
                context.close()
                browser.close()


portal_service = PortalAutomationService()
