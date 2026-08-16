import os
import re
import time
import glob
import datetime
import pandas as pd
from typing import Callable, Optional

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
    print(f"[*] [PortalAutomation] {entry}")

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
            print(f"[*] [PortalAutomation] {msg}")

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

    def run_flow_b(self, from_date: str, to_date: str, log_func: Optional[Callable[[str], None]] = None) -> dict:
        """
        LUỒNG B: Tự động tải Danh sách đã gửi (listbh.xlsx) từ Cổng BHYT.
        """
        from playwright.sync_api import sync_playwright

        def log(msg: str):
            if log_func:
                log_func(msg)
            print(f"[*] [Flow B] {msg}")

        log(f"Bắt đầu Luồng B (Tải danh sách đã gửi từ {from_date} đến {to_date})...")

        with sync_playwright() as p:
            # Khởi chạy trình duyệt headed để hiển thị cho người dùng thao tác captcha nếu cần
            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                storage_state=storage_path,
                viewport={'width': 1366, 'height': 768},
                accept_downloads=True
            )
            page = context.new_page()

            try:
                # 1. Đảm bảo đã đăng nhập
                self._ensure_login(page, log_func=log)

                # 2. Điều hướng vào menu Danh sách đề nghị thanh toán
                log("Đang điều hướng đến: Danh sách đề nghị thanh toán...")
                
                # Thử click menu Hồ sơ đề nghị thanh toán hoặc Hồ sơ XML
                try:
                    if page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible(timeout=4000):
                        page.get_by_text("Hồ sơ đề nghị thanh toán").click()
                except Exception:
                    pass

                try:
                    xml_menu = page.locator("#HeaderMenu_DXME2_ div").filter(has_text="Hồ sơ XML")
                    if xml_menu.is_visible(timeout=4000):
                        xml_menu.click()
                except Exception:
                    pass

                page.get_by_role("link", name="Danh sách đề nghị thanh toán").click(timeout=15000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1)

                # 3. Chọn Trạng thái: "Đã đề nghị thanh toán"
                log("Đang lọc trạng thái: Đã đề nghị thanh toán...")
                try:
                    cb_img = page.locator("#cb_TrangThaiTT_B-1Img")
                    if cb_img.is_visible(timeout=5000):
                        cb_img.click()
                        page.get_by_role("cell", name="Đã đề nghị thanh toán", exact=True).click(timeout=5000)
                except Exception as e:
                    log(f"Lưu ý chọn trạng thái: {e}")

                # 4. Bấm Tìm kiếm
                log("Bấm Tìm kiếm dữ liệu...")
                page.locator("span").filter(has_text=re.compile(r"^Tìm kiếm$")).first.click(timeout=10000)
                time.sleep(2)
                page.wait_for_load_state("networkidle", timeout=20000)

                # 5. Xuất Excel và tải file
                log("Đang kích hoạt Xuất Excel danh sách đã gửi (đang chờ Cổng BHYT xuất file, hỗ trợ tối đa 5 phút vào ngày cao điểm)...")
                
                # Bước 5.1: Click nút cha "Xuất Excel" để mở menu thả xuống
                try:
                    main_btn = page.locator("span").filter(has_text=re.compile(r"^Xuất Excel$")).first
                    main_btn.click(timeout=10000)
                    time.sleep(1.5)
                except Exception as e:
                    log(f"Lưu ý click nút Xuất Excel: {e}")

                # Bước 5.2: Click chính xác vào mục con "Xuất excel" (chữ e thường) trong popup và bắt download
                with page.expect_download(timeout=300000) as download_info:
                    clicked_sub = False
                    try:
                        # Ưu tiên tìm mục con có chữ "Xuất excel"
                        sub_items = page.locator("span").filter(has_text=re.compile(r"^Xuất excel$"))
                        if sub_items.count() > 0:
                            sub_items.first.click()
                            clicked_sub = True
                    except Exception:
                        pass

                    if not clicked_sub:
                        try:
                            # Tìm trong popup DevExpress
                            popup_item = page.locator(".dxm-popup span, .dxm-item span, tr.dxm-item span").filter(has_text=re.compile(r"Xuất excel", re.IGNORECASE)).first
                            popup_item.click(timeout=5000)
                            clicked_sub = True
                        except Exception as ex:
                            log(f"Lưu ý click popup item: {ex}")

                    if not clicked_sub:
                        page.get_by_text("Xuất excel", exact=True).first.click(timeout=10000)

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
            print(f"[*] [Flow C] {msg}")

        log(f"Bắt đầu Luồng C (Tải danh sách lỗi chi tiết từ {from_date} đến {to_date})...")

        # Xóa các file lỗi tạm cũ
        for old_f in glob.glob(os.path.join(TEMP_ERROR_DIR, "*.*")):
            try:
                os.remove(old_f)
            except Exception:
                pass

        with sync_playwright() as p:
            storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                storage_state=storage_path,
                viewport={'width': 1366, 'height': 768},
                accept_downloads=True
            )
            page = context.new_page()

            try:
                # 1. Đảm bảo đã đăng nhập
                self._ensure_login(page, log_func=log)

                # 2. Điều hướng vào menu: Hồ sơ đề nghị thanh toán -> Hồ sơ XML -> Quyết định 3176/QĐ-BYT -> Kết quả gửi hồ sơ XML
                log("Đang điều hướng cố định theo 4 bước: Hồ sơ đề nghị thanh toán > Hồ sơ XML > QĐ 3176 > Kết quả gửi hồ sơ XML...")
                
                # Bước 1: Mở "Hồ sơ đề nghị thanh toán"
                log("  [1/4] Mở 'Hồ sơ đề nghị thanh toán'...")
                try:
                    top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                    if top_menu.is_visible(timeout=3000):
                        top_menu.hover()
                        top_menu.click()
                    else:
                        page.get_by_text("Hồ sơ đề nghị thanh toán").first.click(timeout=3000)
                except Exception as e:
                    log(f"Lưu ý click menu chính: {e}")
                time.sleep(0.6)

                # Bước 2: Rê chuột và Click "Hồ sơ XML" để mở nhánh Quyết định
                log("  [2/4] Mở 'Hồ sơ XML'...")
                try:
                    xml_item = page.locator("span.dx-vam, a, div, span").filter(has_text="Hồ sơ XML").first
                    xml_item.hover(timeout=3000)
                    time.sleep(0.3)
                    xml_item.click(force=True)
                except Exception as e:
                    log(f"Lưu ý click Hồ sơ XML: {e}")
                time.sleep(0.6)

                # Bước 3: Rê chuột và Click "Quyết định 3176/QĐ-BYT"
                log("  [3/4] Mở 'Quyết định 3176/QĐ-BYT'...")
                try:
                    qd3176 = page.locator("span.dx-vam, a, div, span").filter(has_text=re.compile(r"3176")).first
                    qd3176.hover(timeout=3000)
                    time.sleep(0.3)
                    qd3176.click(force=True)
                except Exception:
                    # Fallback dùng JavaScript click trực tiếp trên DOM
                    page.evaluate("""() => {
                        const spans = Array.from(document.querySelectorAll('span.dx-vam, a, div, span'));
                        const el = spans.find(s => s.textContent && s.textContent.includes('3176'));
                        if (el) { el.click(); }
                    }""")
                time.sleep(0.8)

                # Bước 4: Click vào "Kết quả gửi hồ sơ XML" của QĐ 3176
                log("  [4/4] Click 'Kết quả gửi hồ sơ XML'...")
                clicked_link = False
                try:
                    # Dùng JavaScript click trực tiếp link thứ 2 thuộc QĐ 3176
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
                time.sleep(1.5)

                def wait_loading(timeout=45000):
                    try:
                        time.sleep(0.5)
                        loading = page.locator("#gvDSKetQuaGuiHoso_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxgvLoadingDiv")
                        if loading.count() > 0:
                            loading.first.wait_for(state="hidden", timeout=timeout)
                        time.sleep(1.0)
                    except Exception:
                        pass

                # Đợi bảng danh sách và gridview hiển thị sẵn sàng trên màn hình
                log("Đang chờ bảng danh sách Kết quả gửi hồ sơ XML hiển thị hoàn tất...")
                try:
                    page.wait_for_selector("#gvDSKetQuaGuiHoso, #gvDSKetQuaGuiHoso_DXMainTable, input[name*='TuNgay'], #deTuNgay_I", timeout=30000)
                    wait_loading()
                    time.sleep(1.5)
                except Exception as w_err:
                    log(f"Lưu ý chờ bảng: {w_err}")

                # 3. Lọc theo ngày và tìm kiếm
                log(f"Thiết lập điều kiện lọc từ ngày {from_date} đến {to_date}...")
                
                # Điền khoảng ngày nếu có các ô input ngày tháng DevExpress
                try:
                    f_d = from_date
                    t_d = to_date
                    if "-" in from_date:
                        p = from_date.split("-")
                        if len(p) == 3: f_d = f"{p[2]}/{p[1]}/{p[0]}"
                    if "-" in to_date:
                        p = to_date.split("-")
                        if len(p) == 3: t_d = f"{p[2]}/{p[1]}/{p[0]}"

                    for tu_sel in ["#deTuNgay_I", "#txtTuNgay_I", "#TuNgay_I", "input[name*='TuNgay']"]:
                        el = page.locator(tu_sel).first
                        if el.is_visible(timeout=1000):
                            el.click()
                            el.fill(f_d)
                            break
                    for den_sel in ["#deDenNgay_I", "#txtDenNgay_I", "#DenNgay_I", "input[name*='DenNgay']"]:
                        el = page.locator(den_sel).first
                        if el.is_visible(timeout=1000):
                            el.click()
                            el.fill(t_d)
                            break
                except Exception as d_err:
                    log(f"Lưu ý điền ngày: {d_err}")

                # Bấm nút Tìm kiếm
                searched = False
                search_selectors = [
                    "#btnTimKiem",
                    "#btnSearch",
                    ".dxbButton:has-text('Tìm kiếm')",
                    "input[value*='Tìm kiếm']",
                    "button:has-text('Tìm kiếm')",
                    "span:has-text('Tìm kiếm')",
                    "a:has-text('Tìm kiếm')"
                ]
                for s_sel in search_selectors:
                    try:
                        s_btn = page.locator(s_sel).first
                        if s_btn.is_visible(timeout=2000):
                            s_btn.click()
                            searched = True
                            log(f"Đã bấm Tìm kiếm bằng selector: {s_sel}")
                            break
                    except Exception:
                        pass

                if not searched:
                    try:
                        page.get_by_role("button", name=re.compile(r"Tìm kiếm", re.IGNORECASE)).first.click(timeout=5000)
                        searched = True
                    except Exception:
                        pass

                def wait_for_grid_data(timeout=45):
                    """Chờ máy chủ DevExpress trả về dữ liệu hoặc thông báo không có dữ liệu"""
                    start = time.time()
                    time.sleep(1.0)
                    while time.time() - start < timeout:
                        try:
                            # Nếu loading indicator còn hiển thị thì tiếp tục chờ
                            is_loading = page.locator("#gvDSKetQuaGuiHoso_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxgvLoadingDiv").is_visible()
                            if is_loading:
                                time.sleep(0.5)
                                continue
                            
                            # Kiểm tra xem có dòng dữ liệu hay không
                            data_rows = page.locator("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'], #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS, #gvDSKetQuaGuiHoso tr.dxgvDataRow")
                            if data_rows.count() > 0:
                                time.sleep(1.0)
                                return True

                            # Kiểm tra xem có dòng báo rỗng không
                            empty_rows = page.locator("#gvDSKetQuaGuiHoso tr.dxgvEmptyDataRow, #gvDSKetQuaGuiHoso td.dxgvEmptyDataRow, #gvDSKetQuaGuiHoso:has-text('Không có dữ liệu')")
                            if empty_rows.count() > 0:
                                time.sleep(0.5)
                                return False
                        except Exception:
                            pass
                        time.sleep(0.5)
                    return False

                # Bấm Tìm kiếm và chờ kết quả
                log("Đang chờ máy chủ Cổng BHYT xử lý và tải danh sách hồ sơ...")
                wait_for_grid_data(timeout=45)

                # 4. Chọn số lượng hiển thị 100 dòng / trang
                log("Thiết lập hiển thị 100 bản ghi/trang...")
                try:
                    pager_img = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom_DDBImg")
                    if pager_img.is_visible(timeout=5000):
                        pager_img.click()
                        time.sleep(0.5)
                        page.get_by_text("100", exact=True).click(timeout=5000)
                        log("Đang chờ tải lại 100 bản ghi/trang...")
                        wait_for_grid_data(timeout=45)
                except Exception as e:
                    log(f"Lưu ý chọn 100 dòng: {e}")

                # 5. Lọc cột lỗi có giá trị (ví dụ cột 5 điền 1 để lọc những gói có lỗi)
                log("Lọc danh sách các hồ sơ có lỗi (cột lỗi = 1)...")
                try:
                    col5_input = page.locator("#gvDSKetQuaGuiHoso_DXFREditorcol5_I")
                    if col5_input.is_visible(timeout=5000):
                        col5_input.click(force=True)
                        col5_input.fill("1")
                        col5_input.press("Enter")
                        log("Đang chờ lọc các gói có lỗi...")
                        wait_for_grid_data(timeout=45)
                except Exception as e:
                    log(f"Lưu ý lọc cột lỗi: {e}")

                # 6. Lặp qua các trang và tải từng file chi tiết
                total_downloaded = 0
                page_idx = 1

                while True:
                    log(f"Đang quét danh sách hồ sơ lỗi tại Trang {page_idx}...")
                    wait_for_grid_data(timeout=30)
                    
                    # Lấy tất cả các dòng dữ liệu có link xem chi tiết lỗi trong bảng gvDSKetQuaGuiHoso
                    row_links = page.locator("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'] td a, #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS td a, #gvDSKetQuaGuiHoso tr.dxgvDataRow td a").all()
                    if not row_links:
                        row_links = page.locator("#gvDSKetQuaGuiHoso td a").all()

                    log(f"Tìm thấy {len(row_links)} gói hồ sơ trên trang {page_idx}.")

                    if len(row_links) == 0:
                        log("Không tìm thấy gói hồ sơ lỗi nào trên trang này.")
                        break

                    for idx, link in enumerate(row_links):
                        try:
                            link_text = link.inner_text()
                            log(f"[{idx+1}/{len(row_links)}] Đang mở chi tiết gói: {link_text[:30]}...")
                            link.click()
                            time.sleep(1.5)

                            # Bấm Xuất Excel trong popup chi tiết
                            export_btn = page.locator("span").filter(has_text="Xuất Excel").first
                            if export_btn.is_visible(timeout=5000):
                                with page.expect_download(timeout=60000) as dl_info:
                                    export_btn.click()
                                
                                dl = dl_info.value
                                temp_file_path = os.path.join(TEMP_ERROR_DIR, f"err_p{page_idx}_{idx+1}_{int(time.time()*1000)}.xlsx")
                                dl.save_as(temp_file_path)
                                total_downloaded += 1
                                log(f"  -> Đã tải tệp lỗi #{total_downloaded} ✅")

                            # Đóng popup bằng nút [Close] hoặc icon đóng
                            close_btn = page.get_by_role("img", name="[Close]").first
                            if close_btn.is_visible(timeout=3000):
                                close_btn.click()
                            else:
                                page.locator(".dxpc-closeBtn, .dxWeb_pcCloseButton_Youthful").first.click(timeout=3000)
                            
                            time.sleep(0.8)

                        except Exception as row_err:
                            log(f"  Lỗi khi tải dòng #{idx+1}: {row_err}")
                            # Cố gắng đóng popup nếu còn mở
                            try:
                                page.get_by_role("img", name="[Close]").first.click(timeout=1000)
                            except Exception:
                                pass

                    # Kiểm tra nút Trang kế tiếp
                    try:
                        next_page_btn = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom .dxp-button:has-text('>')").first
                        if next_page_btn.is_visible(timeout=3000) and "dxp-disabled" not in (next_page_btn.get_attribute("class") or ""):
                            log("Chuyển sang trang tiếp theo...")
                            next_page_btn.click()
                            page_idx += 1
                            time.sleep(3)
                            page.wait_for_load_state("networkidle", timeout=15000)
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
