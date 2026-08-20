import sys
import os
import re
import time
import glob
import datetime
import pandas as pd
from typing import Callable, Optional

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
portal_logs = []

def add_portal_log(msg: str):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    portal_logs.append(entry)
    if len(portal_logs) > 200:
        portal_logs.pop(0)
    safe_print(f"[*] [PortalAutomation] {entry}")


def parse_date_info(date_val):
    """Parse date string into components and standard formats."""
    if not date_val:
        d_obj = datetime.date.today()
    elif isinstance(date_val, (datetime.date, datetime.datetime)):
        d_obj = date_val if isinstance(date_val, datetime.date) else date_val.date()
    else:
        clean = str(date_val).strip().replace('-', '/').replace('.', '/')
        d_obj = None
        for fmt in ["%Y/%m/%d", "%d/%m/%Y", "%Y%m%d"]:
            try:
                d_obj = datetime.datetime.strptime(clean, fmt).date()
                break
            except Exception:
                pass
        if not d_obj:
            d_obj = datetime.date.today()
            
    return {
        "year": d_obj.year,
        "month": d_obj.month, # 1-12
        "day": d_obj.day,
        "d_str": d_obj.strftime("%d/%m/%Y"), # 01/08/2026
        "iso": d_obj.strftime("%Y-%m-%d")    # 2026-08-01
    }


class PortalAutomationService:
    def __init__(
        self,
        base_url: str = "https://gdbhyt.baohiemxahoi.gov.vn/",
        ma_cskcb: str = "66232",
        username: str = "066091019320",
        password: str = "Nguyenhong123@"
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
            safe_print(f"[*] [PortalAutomation] {msg}")


        log("Đang truy cập Cổng BHYT...")
        page.goto(self.base_url, timeout=60000)
        page.wait_for_load_state("domcontentloaded")

        # Kiểm tra xem đã đăng nhập chưa (dựa vào URL và các phần tử giao diện trang chủ)
        try:
            current_url = page.url.lower()
            if "login" not in current_url and ("home" in current_url or "gdbhyt" in current_url):
                # Kiểm tra các phần tử chỉ xuất hiện khi đã đăng nhập
                is_logged_in = page.locator("#HeaderMenu").is_visible(timeout=3000) or \
                               page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible(timeout=3000) or \
                               page.locator("#HeaderMenu_DXME2_").is_visible(timeout=3000) or \
                               page.get_by_text("Hồ sơ XML").is_visible(timeout=3000) or \
                               page.locator("a:has-text('Đăng xuất')").is_visible(timeout=3000)
                if is_logged_in:
                    log("Phiên đăng nhập vẫn còn hiệu lực (Session Valid) ✅ -> Vào thẳng chức năng, KHÔNG cần đăng nhập lại!")
                    return
        except Exception:
            pass

        # Chưa đăng nhập -> Tự động điền form đăng nhập
        log("Cần đăng nhập tài khoản. Đang tự động điền Mã CSKCB, Tên đăng nhập & Mật khẩu...")
        
        try:
            # Điền Mã cơ sở KCB
            if page.get_by_role("textbox", name="Mã cơ sở KCB").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Mã cơ sở KCB").click()
                page.get_by_role("textbox", name="Mã cơ sở KCB").fill(self.ma_cskcb)
            
            # Điền Tên đăng nhập
            if page.get_by_role("textbox", name="Tên đăng nhập").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Tên đăng nhập").click()
                page.get_by_role("textbox", name="Tên đăng nhập").fill(self.username)
            
            # Điền Mật khẩu
            if page.get_by_role("textbox", name="Mật khẩu").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Mật khẩu").click()
                page.get_by_role("textbox", name="Mật khẩu").fill(self.password)
            
            # Focus vào ô Captcha để người dùng nhập
            if page.get_by_role("textbox", name="Gõ mã hiển thị").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Gõ mã hiển thị").click()
                log("Vui lòng nhìn mã CAPTCHA trên màn hình trình duyệt, nhập vào và bấm ĐĂNG NHẬP (Chờ tối đa 120 giây)...")
            
            # Chờ người dùng nhập captcha và đăng nhập thành công
            login_success = False
            start_wait = time.time()
            while time.time() - start_wait < 120:
                try:
                    # Kiểm tra các dấu hiệu đăng nhập thành công
                    if page.locator("#HeaderMenu").is_visible() or \
                       page.locator("#HeaderMenu_DXME2_").is_visible() or \
                       page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible() or \
                       page.get_by_text("Hồ sơ XML").is_visible() or \
                       page.locator("a:has-text('Đăng xuất')").is_visible():
                        login_success = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            if not login_success:
                raise Exception("Quá thời gian 120 giây chờ nhập Captcha hoặc chưa hoàn tất Đăng nhập.")

            log("Đăng nhập Cổng BHYT thành công! Đang lưu phiên làm việc...")
            
            # Lưu session state để dùng lại lần sau
            try:
                page.context.storage_state(path=SESSION_FILE)
            except Exception as se:
                log(f"Lưu storage state: {se}")

        except Exception as e:
            log(f"Lỗi đăng nhập: {str(e)}")
            raise Exception(f"Không thể đăng nhập Cổng BHYT hoặc quá thời gian chờ nhập Captcha: {str(e)}")

    def wait_devexpress_callback(self, page, control_name: str = "gvDSKetQuaGuiHoso", timeout_sec: int = 45):
        """
        Sử dụng trực tiếp DevExpress Client-Side API và InCallback() / EndCallback
        để đợi máy chủ Cổng BHYT hoàn tất nạp dữ liệu tức thì, chuẩn xác và không bị phụ thuộc vào sleep.
        """
        try:
            page.evaluate("""({ctrlName, timeoutMs}) => {
                return new Promise((resolve) => {
                    try {
                        const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                        const ctrl = cc ? cc.GetByName(ctrlName) : (window[ctrlName] || null);
                        
                        // Nếu không tìm thấy control, fallback kiểm tra loading DOM
                        if (!ctrl) {
                            const ld = document.querySelector(`#${ctrlName}_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxgvLoadingDiv`);
                            if (!ld || ld.offsetParent === null) return resolve({status: 'no_control_idle'});
                        }

                        // Nếu control đang không ở trạng thái callback
                        if (ctrl && typeof ctrl.InCallback === 'function' && !ctrl.InCallback()) {
                            const ld = document.querySelector(`#${ctrlName}_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxgvLoadingDiv`);
                            if (!ld || ld.offsetParent === null) return resolve({status: 'already_idle'});
                        }
                        
                        let resolved = false;
                        const timer = setTimeout(() => {
                            if (!resolved) {
                                resolved = true;
                                resolve({status: 'timeout'});
                            }
                        }, timeoutMs);

                        const onEnd = (s, e) => {
                            if (!resolved) {
                                resolved = true;
                                clearTimeout(timer);
                                try {
                                    if (ctrl && ctrl.EndCallback && typeof ctrl.EndCallback.RemoveHandler === 'function') {
                                        ctrl.EndCallback.RemoveHandler(onEnd);
                                    }
                                } catch(err) {}
                                resolve({status: 'end_callback_success'});
                            }
                        };

                        if (ctrl && ctrl.EndCallback && typeof ctrl.EndCallback.AddHandler === 'function') {
                            ctrl.EndCallback.AddHandler(onEnd);
                        } else {
                            // Polling fallback
                            const interval = setInterval(() => {
                                const isBusy = (ctrl && typeof ctrl.InCallback === 'function' && ctrl.InCallback()) ||
                                               Boolean(document.querySelector(`#${ctrlName}_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS`));
                                if (!isBusy) {
                                    clearInterval(interval);
                                    if (!resolved) {
                                        resolved = true;
                                        clearTimeout(timer);
                                        resolve({status: 'polled_idle'});
                                    }
                                }
                            }, 200);
                        }
                    } catch(e) {
                        resolve({status: 'error', error: e.toString()});
                    }
                });
            }""", {"ctrlName": control_name, "timeoutMs": timeout_sec * 1000})
        except Exception:
            pass

    def wait_portal_idle(self, page, timeout: int = 45000):
        """Chờ đợi tất cả các loading mask và indicator của DevExpress biến mất."""
        try:
            time.sleep(0.3)
            loading_selectors = [
                ".dxgvLoadingDiv",
                ".dxgvLoadingDiv_EIS",
                ".dxgvLoadingPanel_EIS",
                "#gvDSKetQuaGuiHoso_LD",
                ".dxp-loadingPanel",
                ".dxlpLoadingPanelWithContent"
            ]
            for sel in loading_selectors:
                try:
                    loaders = page.locator(sel)
                    if loaders.count() > 0:
                        loaders.first.wait_for(state="hidden", timeout=timeout)
                except Exception:
                    pass
            time.sleep(0.5)
        except Exception:
            pass

    def run_flow_b(self, from_date: str, to_date: str, log_func: Optional[Callable[[str], None]] = None) -> dict:
        """
        LUỒNG B: Tự động tải Danh sách đã gửi (listbh.xlsx) từ Cổng BHYT.
        """
        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func:
                log_func(msg)
            safe_print(f"[*] [Flow B] {msg}")

        log(f"Bắt đầu Luồng B (Tải danh sách đã gửi từ {from_date} đến {to_date})...")

        with sync_playwright() as p:
            # Khởi chạy trình duyệt headed để hiển thị cho người dùng thao tác captcha nếu cần
            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            try:
                browser = p.chromium.launch(headless=False)
            except Exception as launch_err:
                err_str = str(launch_err)
                if "Executable doesn't exist" in err_str or "playwright install" in err_str:
                    log("Chưa cài đặt trình duyệt Chromium cho Playwright trên máy chủ!")
                    raise Exception("Trình duyệt Chromium chưa được cài đặt trên máy chủ. Vui lòng chạy lệnh: playwright install chromium (hoặc bấm 'Cài riêng Chromium' trên tool LaunchWebBHYT).")
                try:
                    log(f"Thử khởi chạy Chromium chế độ ngầm (headless): {launch_err}")
                    browser = p.chromium.launch(headless=True)
                except Exception as h_err:
                    raise Exception(f"Không thể khởi chạy trình duyệt Chromium: {h_err}")

            context = browser.new_context(
                storage_state=storage_path,
                viewport={'width': 1366, 'height': 768},
                accept_downloads=True
            )
            page = context.new_page()

            try:
                # 1. Đảm bảo đã đăng nhập
                self._ensure_login(page, log_func=log)
                self.wait_portal_idle(page)

                # 2. Điều hướng vào menu Danh sách đề nghị thanh toán (Click trực tiếp, không hover)
                log("Đang điều hướng đến: Danh sách đề nghị thanh toán...")
                
                try:
                    top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                    if top_menu.is_visible(timeout=3000):
                        top_menu.click()
                        time.sleep(0.5)
                except Exception:
                    pass

                try:
                    xml_menu = page.locator("#HeaderMenu_DXME2_ div, #HeaderMenu div").filter(has_text="Hồ sơ XML")
                    if xml_menu.is_visible(timeout=3000):
                        xml_menu.first.click()
                        time.sleep(0.5)
                except Exception:
                    pass

                page.get_by_role("link", name="Danh sách đề nghị thanh toán").click(timeout=15000)
                page.wait_for_load_state("domcontentloaded")
                self.wait_portal_idle(page)
                time.sleep(1.0)

                # 3. Chọn Trạng thái: "Đã đề nghị thanh toán"
                log("Đang chọn trạng thái: Đã đề nghị thanh toán...")
                status_selected = False
                
                # Cách 1: Sử dụng DevExpress Client-Side API chính thức
                try:
                    js_res = page.evaluate("""() => {
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
                    if js_res:
                        status_selected = True
                        log("Đã chọn trạng thái: 'Đã đề nghị thanh toán' qua DevExpress API ✅")
                except Exception as js_err:
                    log(f"Lưu ý JS API trạng thái: {js_err}")

                # Cách 2: Mở dropdown và CLICK trực tiếp vào phần tử trong bảng
                try:
                    btn_cb = page.locator("#cb_TrangThaiTT_B-1, #cb_TrangThaiTT_B-1Img, td[id*='cb_TrangThaiTT_B-1']").first
                    if btn_cb.is_visible(timeout=3000):
                        btn_cb.click(force=True)
                        time.sleep(0.6)
                        
                        # Click trực tiếp vào cell có chữ "Đã đề nghị thanh toán" trong popup table
                        item = page.locator("#cb_TrangThaiTT_DDD_L_LBT td, tr.dxeListBoxItemRow_EIS td, .dxeListBoxItem").filter(has_text=re.compile(r"Đã đề nghị thanh toán", re.IGNORECASE)).first
                        if item.is_visible(timeout=3000):
                            item.click(force=True)
                            status_selected = True
                            log("Đã click chọn item 'Đã đề nghị thanh toán' trên giao diện ✅")
                except Exception as e:
                    log(f"Lưu ý click dropdown trạng thái: {e}")

                self.wait_portal_idle(page)
                time.sleep(0.8)

                # 4. Bấm Tìm kiếm (Sửa triệt để không click vào hidden input dxb-hb)
                log("Bấm Tìm kiếm dữ liệu...")
                searched = False
                
                # Cách 1: DevExpress API DoClick
                try:
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
                    if searched:
                        log("Đã kích hoạt nút Tìm kiếm qua DevExpress DoClick API ✅")
                except Exception:
                    pass

                # Cách 2: Click vào table hoặc span hiển thị của nút Tìm kiếm
                if not searched:
                    search_selectors = [
                        "#bt_TimKiem_CD",
                        "#bt_TimKiem_B",
                        "#bt_TimKiem",
                        "#btnTimKiem_CD",
                        "#btnTimKiem",
                        ".dxbButton:has-text('Tìm kiếm')",
                        "span:has-text('Tìm kiếm')",
                        "td.dxb:has-text('Tìm kiếm')"
                    ]
                    for s_sel in search_selectors:
                        try:
                            s_el = page.locator(s_sel).first
                            if s_el.is_visible(timeout=1500):
                                s_el.click(force=True)
                                searched = True
                                log(f"Đã bấm nút Tìm kiếm ({s_sel}) ✅")
                                break
                        except Exception:
                            pass

                if not searched:
                    page.evaluate("""() => {
                        const btns = Array.from(document.querySelectorAll('#bt_TimKiem, #bt_TimKiem_CD, .dxbButton, span, td')).filter(el => el.textContent && el.textContent.trim() === 'Tìm kiếm');
                        if (btns.length > 0) btns[0].click();
                    }""")
                
                self.wait_portal_idle(page, timeout=45000)
                time.sleep(1.5)

                # 5. Xuất Excel và tải file (Chỉ click vào mục con bên trong Popup Menu)
                log("Đang kích hoạt Xuất Excel danh sách đã gửi (hỗ trợ tối đa 5 phút vào ngày cao điểm)...")
                
                # Bước 5.1: Click nút cha "Xuất Excel" để mở menu lựa chọn
                log("Click nút cha 'Xuất Excel' để mở menu lựa chọn...")
                export_btn_selectors = [
                    "#HeaderMenu span:has-text('Xuất Excel')",
                    "#bt_XuatExcel_CD",
                    "#bt_XuatExcel",
                    ".dxbButton:has-text('Xuất Excel')",
                    "td.dxb:has-text('Xuất Excel')",
                    "span:has-text('Xuất Excel')"
                ]
                for x_sel in export_btn_selectors:
                    try:
                        x_el = page.locator(x_sel).first
                        if x_el.is_visible(timeout=2000):
                            x_el.click(force=True)
                            log(f"Đã click nút cha Xuất Excel ({x_sel}) ✅")
                            break
                    except Exception:
                        pass
                
                time.sleep(1.2)

                # Bước 5.2: Đợi menu popup hiển thị
                try:
                    page.wait_for_selector(".dxm-popup, div[id*='_DXME'], .dxm-shadow, table.dxm-item", timeout=5000)
                except Exception:
                    pass

                # Bước 5.3: Click CHÍNH XÁC vào mục con TRONG POPUP MENU (loại trừ nút cha dưới nền)
                log("Đang click vào mục 'Xuất excel' trong popup menu...")
                with page.expect_download(timeout=300000) as download_info:
                    clicked_sub = False
                    
                    # Cách 1: Tìm trực tiếp bên trong container popup (.dxm-popup hoặc div[id*='_DXME'])
                    popup_selectors = [
                        ".dxm-popup .dxm-item",
                        ".dxm-popup table.dxm-item",
                        ".dxm-popup td.dxm-item",
                        ".dxm-popup span",
                        "div[id*='_DXME'] .dxm-item",
                        "div[id*='_DXME'] span",
                        ".dxm-shadow .dxm-item",
                        ".dxm-shadow span"
                    ]
                    for p_sel in popup_selectors:
                        try:
                            p_items = page.locator(p_sel).filter(has_text=re.compile(r"Xuất excel", re.IGNORECASE))
                            if p_items.count() > 0:
                                p_items.first.click(force=True)
                                clicked_sub = True
                                log(f"Đã click mục con Xuất excel trong popup ({p_sel}) ✅")
                                break
                        except Exception:
                            pass

                    # Cách 2: JavaScript tìm đúng phần tử trong popup container đang hiển thị
                    if not clicked_sub:
                        clicked_sub = page.evaluate("""() => {
                            const popups = Array.from(document.querySelectorAll('.dxm-popup, div[id*="_DXME"], .dxm-shadow, .dxm-subMenuItem'));
                            for (const pop of popups) {
                                if (pop.offsetParent !== null) {
                                    const target = Array.from(pop.querySelectorAll('.dxm-item, span, td, a, tr')).find(e => e.textContent && e.textContent.trim().toLowerCase().includes('xuất excel'));
                                    if (target) {
                                        target.click();
                                        return true;
                                    }
                                }
                            }
                            const allItems = Array.from(document.querySelectorAll('.dxm-popup span, .dxm-item span, .dxm-item, span, td, a')).filter(e => e.textContent && e.textContent.trim().toLowerCase() === 'xuất excel');
                            if (allItems.length > 1) {
                                allItems[allItems.length - 1].click();
                                return true;
                            } else if (allItems.length === 1) {
                                allItems[0].click();
                                return true;
                            }
                            return false;
                        }""")
                        if clicked_sub:
                            log("Đã click mục con Xuất excel qua JS popup locator ✅")

                log("Cổng BHYT đã tạo tệp Excel xong! Đang tải về máy...")
                download = download_info.value
                dest_path = os.path.join(UPLOAD_DIR, "listbh.xlsx")
                download.save_as(dest_path)
                log(f"Tải tệp danh sách đã gửi thành công: {dest_path} ✅")

                # Lưu session mới nhất
                context.storage_state(path=SESSION_FILE)

                # Đọc số dòng của file tải về
                df = pd.read_excel(dest_path)
                row_count = len(df)
                log(f"Đã nạp file listbh.xlsx với {row_count} dòng dữ liệu.")

                return {
                    "status": "success",
                    "file_path": dest_path,
                    "rows": row_count,
                    "message": f"Tải thành công {row_count} bản ghi danh sách đã gửi."
                }

            except Exception as e:
                log(f"Lỗi thực thi Luồng B: {str(e)}")
                raise e
            finally:
                context.close()
                browser.close()

    def run_flow_c(self, from_date: str, to_date: str, log_func: Optional[Callable[[str], None]] = None) -> dict:
        """
        LUỒNG C: Tự động cào/tải Danh sách lỗi chi tiết từ QĐ 3176, gom thành HoSoLoiChiTiet.xlsx.
        """
        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func:
                log_func(msg)
            safe_print(f"[*] [Flow C] {msg}")

        log(f"Bắt đầu Luồng C (Tải danh sách lỗi chi tiết)...")

        # Xóa các file lỗi tạm cũ
        for old_f in glob.glob(os.path.join(TEMP_ERROR_DIR, "*.*")):
            try:
                os.remove(old_f)
            except Exception:
                pass

        with sync_playwright() as p:
            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            try:
                browser = p.chromium.launch(headless=False)
            except Exception as launch_err:
                err_str = str(launch_err)
                if "Executable doesn't exist" in err_str or "playwright install" in err_str:
                    log("Chưa cài đặt trình duyệt Chromium cho Playwright trên máy chủ!")
                    raise Exception("Trình duyệt Chromium chưa được cài đặt trên máy chủ. Vui lòng chạy lệnh: playwright install chromium (hoặc bấm 'Cài riêng Chromium' trên tool LaunchWebBHYT).")
                try:
                    log(f"Thử khởi chạy Chromium chế độ ngầm (headless): {launch_err}")
                    browser = p.chromium.launch(headless=True)
                except Exception as h_err:
                    raise Exception(f"Không thể khởi chạy trình duyệt Chromium: {h_err}")

            context = browser.new_context(
                storage_state=storage_path,
                viewport={'width': 1366, 'height': 768},
                accept_downloads=True
            )
            page = context.new_page()

            try:
                # 1. Đảm bảo đã đăng nhập
                self._ensure_login(page, log_func=log)
                self.wait_portal_idle(page)

                # 2. Điều hướng 4 bước trực tiếp: Click Cha -> Đợi Con -> Click Con (Hoàn toàn KHÔNG hover)
                log("Đang điều hướng cố định theo 4 bước trực tiếp: Hồ sơ ĐNTT > Hồ sơ XML > QĐ 3176 > Kết quả gửi hồ sơ XML...")
                
                # Bước 1: Click "Hồ sơ đề nghị thanh toán"
                log("  [1/4] Click 'Hồ sơ đề nghị thanh toán'...")
                try:
                    top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                    if top_menu.is_visible(timeout=3000):
                        top_menu.click()
                    else:
                        page.get_by_text("Hồ sơ đề nghị thanh toán").first.click(timeout=3000)
                except Exception as e:
                    log(f"Lưu ý click menu chính: {e}")
                time.sleep(0.6)

                # Bước 2: Click trực tiếp "Hồ sơ XML" (chờ hiển thị và click, không hover)
                log("  [2/4] Click 'Hồ sơ XML'...")
                try:
                    page.wait_for_selector("span.dx-vam, a, div, span", timeout=3000)
                    xml_item = page.locator("span.dx-vam, a, div, span").filter(has_text="Hồ sơ XML").first
                    xml_item.click(force=True)
                except Exception as e:
                    log(f"Lưu ý click Hồ sơ XML: {e}")
                time.sleep(0.6)

                # Bước 3: Click trực tiếp "Quyết định 3176/QĐ-BYT"
                log("  [3/4] Click 'Quyết định 3176/QĐ-BYT'...")
                try:
                    qd3176 = page.locator("span.dx-vam, a, div, span").filter(has_text=re.compile(r"3176")).first
                    qd3176.click(force=True)
                except Exception:
                    page.evaluate("""() => {
                        const spans = Array.from(document.querySelectorAll('span.dx-vam, a, div, span'));
                        const el = spans.find(s => s.textContent && s.textContent.includes('3176'));
                        if (el) { el.click(); }
                    }""")
                time.sleep(0.8)

                # Bước 4: Click trực tiếp "Kết quả gửi hồ sơ XML"
                log("  [4/4] Click 'Kết quả gửi hồ sơ XML'...")
                clicked_link = False
                try:
                    clicked_link = page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a')).filter(a => a.textContent && a.textContent.includes('Kết quả gửi hồ sơ XML'));
                        if (links.length > 1) {
                            links[1].click();
                            return true;
                        } else if (links.length === 1) {
                            links[0].click();
                            return true;
                        }
                        return false;
                    }""")
                except Exception:
                    pass

                if not clicked_link:
                    try:
                        page.get_by_role("link", name=re.compile(r"Kết quả gửi hồ sơ XML", re.IGNORECASE)).last.click(force=True)
                    except Exception as ex:
                        log(f"Lưu ý fallback link: {ex}")

                page.wait_for_load_state("domcontentloaded")
                self.wait_portal_idle(page)

                # Đợi bảng danh sách và gridview hiển thị sẵn sàng
                log("Đang chờ bảng danh sách Kết quả gửi hồ sơ XML hiển thị hoàn tất...")
                try:
                    page.wait_for_selector("#gvDSKetQuaGuiHoso, #gvDSKetQuaGuiHoso_DXMainTable, input[name*='TuNgay'], #deTuNgay_I", timeout=30000)
                    self.wait_portal_idle(page)
                except Exception as w_err:
                    log(f"Lưu ý chờ bảng: {w_err}")

                # 3. BƯỚC 1: ĐẶT NGÀY TODAY & TÌM KIẾM BẰNG DEVEXPRESS CLIENT API
                log("Đang đặt khoảng ngày tìm kiếm = TODAY qua DevExpress API...")
                date_set = False
                try:
                    date_set = page.evaluate("""() => {
                        try {
                            const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                            if (cc) {
                                const deTu = cc.GetByName('deTuNgay') || cc.GetByName('txtTuNgay') || cc.GetByName('TuNgay') || window.deTuNgay;
                                const deDen = cc.GetByName('deDenNgay') || cc.GetByName('txtDenNgay') || cc.GetByName('DenNgay') || window.deDenNgay;
                                const now = new Date();
                                if (deTu && typeof deTu.SetDate === 'function') deTu.SetDate(now);
                                if (deDen && typeof deDen.SetDate === 'function') deDen.SetDate(now);
                                return Boolean(deTu || deDen);
                            }
                        } catch(e) {}
                        return false;
                    }""")
                    if date_set:
                        log("Đã đặt Từ ngày và Đến ngày = Hôm nay qua DevExpress SetDate() API tức thì ✅")
                except Exception:
                    pass

                # Fallback nếu cần
                if not date_set:
                    try:
                        tu_btn = page.locator("#deTuNgay_B-1, #deTuNgay_B-1Img, td:has-text('Từ ngày') ~ td img").first
                        if tu_btn.is_visible(timeout=1500):
                            tu_btn.click(force=True)
                            time.sleep(0.3)
                            t_btn = page.locator(".dxeCalendarTodayButton_EIS, td[id*='_DDD_C_BT'], .dxbButton:has-text('Today'), td:has-text('Today')").first
                            if t_btn.is_visible(timeout=1500):
                                t_btn.click(force=True)
                    except Exception: pass

                # Bấm nút Tìm kiếm qua DevExpress DoClick API
                log("Bấm Tìm kiếm dữ liệu qua DevExpress API...")
                searched = False
                try:
                    searched = page.evaluate("""() => {
                        try {
                            const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                            const btn = window.btnTimKiem || window.bt_TimKiem || (cc ? (cc.GetByName('btnTimKiem') || cc.GetByName('bt_TimKiem')) : null);
                            if (btn && typeof btn.DoClick === 'function') {
                                btn.DoClick();
                                return true;
                            }
                        } catch(e) {}
                        return false;
                    }""")
                except Exception: pass

                if not searched:
                    for s_sel in ["#btnTimKiem_CD", "#btnTimKiem_B", "#btnTimKiem", "#bt_TimKiem_CD", "#bt_TimKiem", ".dxbButton:has-text('Tìm kiếm')", "span:has-text('Tìm kiếm')"]:
                        try:
                            s_btn = page.locator(s_sel).first
                            if s_btn.is_visible(timeout=2000):
                                s_btn.click(force=True)
                                searched = True
                                break
                        except Exception: pass

                # Chờ callback tìm kiếm hoàn tất tức thì qua DevExpress EndCallback
                log("Đang chờ máy chủ Cổng BHYT phản hồi dữ liệu tìm kiếm (DevExpress EndCallback)...")
                self.wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                self.wait_portal_idle(page)

                # 4. BƯỚC 2: CHỌN HIỂN THỊ 100 DÒNG / TRANG & CHỜ ENDCALLBACK
                log("Thiết lập hiển thị 100 bản ghi/trang...")
                try:
                    page.evaluate("""() => {
                        try {
                            const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                            const grid = cc ? cc.GetByName('gvDSKetQuaGuiHoso') : window.gvDSKetQuaGuiHoso;
                            if (grid && typeof grid.SetPageSize === 'function') {
                                grid.SetPageSize(100);
                                return true;
                            }
                        } catch(e) {}
                        return false;
                    }""")
                    
                    pager_img = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom_DDBImg, #gvDSKetQuaGuiHoso_DXPagerBottom .dxp-dropDownButton").first
                    if pager_img.is_visible(timeout=2000):
                        pager_img.click()
                        time.sleep(0.3)
                        page.get_by_text("100", exact=True).click(timeout=2000)
                    
                    self.wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                    self.wait_portal_idle(page)
                    log("Đã nạp xong hiển thị 100 bản ghi/trang ✅")
                except Exception as e:
                    log(f"Lưu ý chọn 100 dòng: {e}")

                # 5. BƯỚC 3: NHẬN DIỆN CỘT LỖI & ÁP DỤNG BỘ LỌC 1 TRỰC TIẾP QUA DEVEXPRESS API
                log("Đang áp dụng bộ lọc cột Lỗi = 1 qua DevExpress Client API...")
                filter_res = page.evaluate("""() => {
                    try {
                        const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                        const grid = cc ? cc.GetByName('gvDSKetQuaGuiHoso') : window.gvDSKetQuaGuiHoso;
                        
                        let errIdx = 5; // Mặc định cột 5
                        const table = document.querySelector('#gvDSKetQuaGuiHoso, #gvDSKetQuaGuiHoso_DXMainTable');
                        if (table) {
                            const headers = Array.from(table.querySelectorAll('.dxgvHeader_EIS, th, td[id*="_col"]')).map((h, i) => ({
                                index: i,
                                text: (h.textContent || '').trim().toLowerCase()
                            }));
                            for (const h of headers) {
                                if (h.text.includes('lỗi') || h.text.includes('không hợp lệ') || h.text.includes('số lỗi') || h.text.includes('chi tiết lỗi')) {
                                    errIdx = h.index;
                                    break;
                                }
                            }
                        }

                        // Cách A: Sử dụng hàm AutoFilterByColumn của DevExpress
                        if (grid && typeof grid.AutoFilterByColumn === 'function') {
                            const col = typeof grid.GetColumn === 'function' ? grid.GetColumn(errIdx) : null;
                            if (col) {
                                grid.AutoFilterByColumn(col, '1');
                                return { success: true, method: 'AutoFilterByColumn_object', colIdx: errIdx };
                            } else {
                                grid.AutoFilterByColumn(`col${errIdx}`, '1');
                                return { success: true, method: 'AutoFilterByColumn_string', colIdx: errIdx };
                            }
                        }

                        // Cách B: Nhập trực tiếp vào AutoFilter Editor DOM
                        const inp = document.querySelector(`#gvDSKetQuaGuiHoso_DXFREditorcol${errIdx}_I, #gvDSKetQuaGuiHoso_DXFREditorcol5_I, input[id*="DXFREditorcol5"]`);
                        if (inp) {
                            inp.value = '1';
                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                            inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
                            inp.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', keyCode: 13, bubbles: true }));
                            inp.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', keyCode: 13, bubbles: true }));
                            return { success: true, method: 'dom_input_events', colIdx: errIdx, inputId: inp.id };
                        }

                        return { success: false, colIdx: errIdx };
                    } catch(e) {
                        return { success: false, error: e.toString() };
                    }
                }""")
                log(f"Kết quả kích hoạt lọc cột lỗi = 1: {filter_res.get('method', 'DOM fallback')} (Cột #{filter_res.get('colIdx', 5)}) ✅")

                # Chờ bộ lọc áp dụng tức thì
                self.wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                self.wait_portal_idle(page)

                # 6. BƯỚC 4: LẶP QUA CÁC TRANG VÀ TẢI TỪNG FILE CHI TIẾT
                total_downloaded = 0
                page_idx = 1

                while True:
                    log(f"Đang quét danh sách hồ sơ lỗi tại Trang {page_idx}...")
                    self.wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 30)
                    self.wait_portal_idle(page)

                    # Lấy thông tin tất cả các dòng ca lỗi qua JS
                    rows_summary = page.evaluate("""() => {
                        const rows = Array.from(document.querySelectorAll('#gvDSKetQuaGuiHoso tr[id*="DXDataRow"], #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS, #gvDSKetQuaGuiHoso tr.dxgvDataRow'));
                        return rows.map((r, i) => {
                            const link = r.querySelector('td a, td span[onclick], td[onclick]');
                            return {
                                index: i,
                                id: r.id || `row_${i}`,
                                hasLink: Boolean(link),
                                text: (r.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 70)
                            };
                        });
                    }""")

                    log(f"Trang {page_idx}: Tìm thấy {len(rows_summary)} ca lỗi cần tải chi tiết.")

                    if len(rows_summary) == 0:
                        log("Không tìm thấy ca lỗi nào trên trang này.")
                        break

                    for idx, row_item in enumerate(rows_summary):
                        try:
                            log(f"[{total_downloaded + 1}/{total_downloaded + len(rows_summary) - idx}] Đang mở chi tiết ca lỗi dòng #{idx + 1}...")

                            # Click mở popup qua JavaScript tức thì
                            page.evaluate("""(rIdx) => {
                                const rows = Array.from(document.querySelectorAll('#gvDSKetQuaGuiHoso tr[id*="DXDataRow"], #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS, #gvDSKetQuaGuiHoso tr.dxgvDataRow'));
                                if (rIdx < rows.length) {
                                    const r = rows[rIdx];
                                    const link = r.querySelector('td a, td span[onclick], td[onclick]');
                                    if (link) { link.click(); return true; }
                                    r.click();
                                    return true;
                                }
                                return false;
                            }""", idx)

                            time.sleep(1.2)

                            # Chờ và click "Xuất Excel" trong popup
                            export_btn = page.locator("span, a, td, button").filter(has_text=re.compile(r"^Xuất Excel$", re.IGNORECASE)).first
                            if export_btn.is_visible(timeout=6000):
                                with page.expect_download(timeout=60000) as dl_info:
                                    export_btn.click(force=True)
                                
                                dl = dl_info.value
                                temp_file_path = os.path.join(TEMP_ERROR_DIR, f"err_p{page_idx}_{idx+1}_{int(time.time()*1000)}.xlsx")
                                dl.save_as(temp_file_path)
                                total_downloaded += 1
                                log(f"  -> Đã tải thành công tệp lỗi #{total_downloaded} ✅")
                            else:
                                log(f"  -> Lưu ý: Không thấy nút 'Xuất Excel' trong popup của dòng #{idx + 1}.")

                            # Đóng popup chi tiết lỗi tức thì qua DevExpress Hide() API
                            page.evaluate("""() => {
                                try {
                                    const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                                    const pop = window.PopupNhanChiTietLoiHS || (cc ? cc.GetByName('PopupNhanChiTietLoiHS') : null);
                                    if (pop && typeof pop.Hide === 'function') pop.Hide();
                                } catch(e) {}
                            }""")
                            
                            for c_sel in [".dxpc-closeBtn", "img[alt*='Close']", "img[title*='Close']", ".dxWeb_pcCloseButton_Youthful"]:
                                c_el = page.locator(c_sel).first
                                if c_el.is_visible(timeout=500):
                                    c_el.click(force=True)
                                    break
                            
                            time.sleep(0.4)

                        except Exception as row_err:
                            log(f"  Lỗi khi tải dòng #{idx+1}: {row_err}")
                            try:
                                page.evaluate("""() => {
                                    if (window.PopupNhanChiTietLoiHS && typeof window.PopupNhanChiTietLoiHS.Hide === 'function') {
                                        window.PopupNhanChiTietLoiHS.Hide();
                                    }
                                }""")
                            except Exception: pass

                    # Chuyển trang tiếp theo qua DevExpress NextPage() API hoặc click pager button
                    try:
                        moved_next = page.evaluate("""() => {
                            try {
                                const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                                const grid = cc ? cc.GetByName('gvDSKetQuaGuiHoso') : window.gvDSKetQuaGuiHoso;
                                if (grid && typeof grid.NextPage === 'function') {
                                    grid.NextPage();
                                    return true;
                                }
                            } catch(e) {}
                            return false;
                        }""")

                        if not moved_next:
                            next_page_btn = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom .dxp-button:has-text('>')").first
                            if next_page_btn.is_visible(timeout=2000) and "dxp-disabled" not in (next_page_btn.get_attribute("class") or ""):
                                next_page_btn.click()
                                moved_next = True

                        if moved_next:
                            log(f"Chuyển sang trang tiếp theo (Trang {page_idx + 1})...")
                            page_idx += 1
                            self.wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 30)
                            self.wait_portal_idle(page)
                        else:
                            log("Đã duyệt hết tất cả các trang.")
                            break

                    except Exception:
                        log("Hoàn thành duyệt các trang.")
                        break

                # 7. Gom tất cả các file Excel tải về thành HoSoLoiChiTiet.xlsx
                log(f"Đang tổng hợp {total_downloaded} tệp lỗi thành một file Excel duy nhất...")
                merged_dest = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
                total_error_records = self._merge_error_files(TEMP_ERROR_DIR, merged_dest, log_func=log)

                # Lưu session

                # 7. Gom tất cả các file Excel tải về thành HoSoLoiChiTiet.xlsx
                log(f"Đang tổng hợp {total_downloaded} tệp lỗi thành một file Excel duy nhất...")
                merged_dest = os.path.join(UPLOAD_DIR, "HoSoLoiChiTiet.xlsx")
                total_error_records = self._merge_error_files(TEMP_ERROR_DIR, merged_dest, log_func=log)

                # Lưu session
                context.storage_state(path=SESSION_FILE)

                return {
                    "status": "success",
                    "file_path": merged_dest,
                    "downloaded_files": total_downloaded,
                    "total_errors": total_error_records,
                    "message": f"Đã tải {total_downloaded} gói lỗi và tổng hợp thành công {total_error_records} dòng lỗi chi tiết vào HoSoLoiChiTiet.xlsx."
                }

            except Exception as e:
                log(f"Lỗi thực thi Luồng C: {str(e)}")
                raise e
            finally:
                context.close()
                browser.close()

    def _merge_error_files(self, source_dir: str, dest_path: str, log_func: Optional[Callable[[str], None]] = None) -> int:
        """Gom tất cả file Excel trong source_dir thành 1 file Excel duy nhất theo đúng cấu trúc HoSoLoiChiTiet."""
        files = glob.glob(os.path.join(source_dir, "*.xlsx")) + glob.glob(os.path.join(source_dir, "*.xls"))
        if not files:
            if log_func:
                log_func("Không có tệp lỗi nào được tải về để tổng hợp.")
            # Tạo DataFrame rỗng có cấu trúc
            empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"])
            empty_df.to_excel(dest_path, index=False)
            return 0

        all_dfs = []
        for f in files:
            try:
                # Đọc file excel chi tiết lỗi của cổng BHYT
                df = pd.read_excel(f)
                if not df.empty:
                    # Chuẩn hóa tên cột nếu có biến thể
                    col_map = {}
                    for c in df.columns:
                        c_str = str(c).strip().upper()
                        if "MA_LK" in c_str or "MÃ LIÊN KẾT" in c_str or "MÃ LK" in c_str:
                            col_map[c] = "MA_LK"
                        elif "MALOI" in c_str or "MÃ LỖI" in c_str:
                            col_map[c] = "MALOI"
                        elif "MOTALOI" in c_str or "MÔ TẢ" in c_str or "NỘI DUNG LỖI" in c_str or "CHI TIẾT LỖI" in c_str:
                            col_map[c] = "MOTALOI"
                        elif "NGAY_RA" in c_str or "NGÀY RA" in c_str:
                            col_map[c] = "Ngày ra"
                    
                    df = df.rename(columns=col_map)
                    all_dfs.append(df)
            except Exception as e:
                if log_func:
                    log_func(f"Lỗi đọc file {os.path.basename(f)}: {e}")

        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            # Bỏ trùng lặp dòng lỗi hoàn toàn giống nhau nếu có
            combined_df = combined_df.drop_duplicates()
            combined_df.to_excel(dest_path, index=False)
            if log_func:
                log_func(f"Đã lưu file tổng hợp {dest_path} ({len(combined_df)} dòng lỗi chi tiết).")
            return len(combined_df)
        else:
            empty_df = pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra"])
            empty_df.to_excel(dest_path, index=False)
            return 0


# Instance mặc định
portal_service = PortalAutomationService()
