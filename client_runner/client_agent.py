import sys
import os
import re
import time
import glob
import json
import datetime
import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox

# Cấu hình UTF-8 cho Windows console
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

CONFIG_FILE = "client_config.json"
SESSION_DIR = "browser_session"
TEMP_DIR = "downloaded_temp"

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

SESSION_FILE = os.path.join(SESSION_DIR, "portal_storage_state.json")


class ClientRPAGui:
    def __init__(self, root):
        self.root = root
        self.root.title("CheckBHYT - Client RPA Runner")
        self.root.geometry("680x750")
        self.root.resizable(False, False)

        # Màu sắc Glassmorphic Dark-Theme
        self.bg_color = "#0b1329"
        self.card_bg = "#1e293b"
        self.text_main = "#f8fafc"
        self.text_sec = "#94a3b8"
        self.accent_blue = "#3b82f6"
        self.accent_green = "#10b981"
        self.accent_orange = "#f59e0b"
        self.accent_red = "#ef4444"

        self.root.configure(bg=self.bg_color)

        # Variables
        self.server_url = tk.StringVar(value="http://127.0.0.1:8000")
        self.from_date = tk.StringVar(value=datetime.date.today().replace(day=1).strftime("%Y-%m-%d"))
        self.to_date = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        self.status_msg = tk.StringVar(value="Sẵn sàng thực thi.")
        self.portal_cskcb = tk.StringVar(value="66232")
        self.portal_user = tk.StringVar(value="066091019320")
        self.portal_pass = tk.StringVar(value="Nguyenhong123@")
        self.portal_url = tk.StringVar(value="https://gdbhyt.baohiemxahoi.gov.vn/")

        self.load_config()
        self.create_widgets()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.server_url.set(cfg.get("server_url", "http://127.0.0.1:8000"))
                    self.from_date.set(cfg.get("from_date", self.from_date.get()))
                    self.to_date.set(cfg.get("to_date", self.to_date.get()))
                    self.portal_cskcb.set(cfg.get("portal_cskcb", "66232"))
                    self.portal_user.set(cfg.get("portal_user", "066091019320"))
                    self.portal_pass.set(cfg.get("portal_pass", "Nguyenhong123@"))
                    self.portal_url.set(cfg.get("portal_url", "https://gdbhyt.baohiemxahoi.gov.vn/"))
            except Exception:
                pass

    def save_config(self):
        cfg = {
            "server_url": self.server_url.get().strip(),
            "from_date": self.from_date.get().strip(),
            "to_date": self.to_date.get().strip(),
            "portal_cskcb": self.portal_cskcb.get().strip(),
            "portal_user": self.portal_user.get().strip(),
            "portal_pass": self.portal_pass.get().strip(),
            "portal_url": self.portal_url.get().strip(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def log(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.insert(tk.END, line)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def create_widgets(self):
        # Header
        hdr = tk.Frame(self.root, bg=self.bg_color)
        hdr.pack(fill=tk.X, padx=25, pady=(15, 10))

        tk.Label(hdr, text="CheckBHYT - Client RPA Runner", font=("Segoe UI", 16, "bold"), bg=self.bg_color, fg=self.accent_blue).pack(anchor=tk.W)
        tk.Label(hdr, text="Công cụ tự động hóa Cổng BHYT chạy trực tiếp trên Máy trạm & tự động đẩy file lên Server", font=("Segoe UI", 9), bg=self.bg_color, fg=self.text_sec).pack(anchor=tk.W)

        # Card 1: Server Config
        card1 = tk.Frame(self.root, bg=self.card_bg, padx=15, pady=12)
        card1.pack(fill=tk.X, padx=25, pady=(0, 10))

        tk.Label(card1, text="1. ĐỊA CHỈ MÁY CHỦ WEBAPP (SERVER LAN URL)", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.text_sec).pack(anchor=tk.W)
        
        srv_frame = tk.Frame(card1, bg=self.card_bg)
        srv_frame.pack(fill=tk.X, pady=(4, 0))

        ent_srv = tk.Entry(srv_frame, textvariable=self.server_url, font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#60a5fa", insertbackground=self.text_main, bd=1, relief=tk.SOLID)
        ent_srv.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        btn_fetch = tk.Button(srv_frame, text="Đồng bộ cấu hình từ Server", command=self.fetch_server_config, font=("Segoe UI", 8, "bold"), bg="#334155", fg=self.text_main, bd=0, cursor="hand2")
        btn_fetch.pack(side=tk.RIGHT, padx=(8, 0), ipady=4, ipadx=8)

        # Card 2: Date Range
        card2 = tk.Frame(self.root, bg=self.card_bg, padx=15, pady=12)
        card2.pack(fill=tk.X, padx=25, pady=(0, 10))

        tk.Label(card2, text="2. KHOẢNG NGÀY ĐỐI SOÁT (YYYY-MM-DD)", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.text_sec).pack(anchor=tk.W)

        date_frame = tk.Frame(card2, bg=self.card_bg)
        date_frame.pack(fill=tk.X, pady=(4, 0))

        tk.Label(date_frame, text="Từ ngày:", font=("Segoe UI", 9), bg=self.card_bg, fg=self.text_main).pack(side=tk.LEFT)
        tk.Entry(date_frame, textvariable=self.from_date, font=("Segoe UI", 10), bg="#0f172a", fg=self.text_main, insertbackground=self.text_main, bd=1, relief=tk.SOLID, width=14).pack(side=tk.LEFT, padx=(5, 15), ipady=3)

        tk.Label(date_frame, text="Đến ngày:", font=("Segoe UI", 9), bg=self.card_bg, fg=self.text_main).pack(side=tk.LEFT)
        tk.Entry(date_frame, textvariable=self.to_date, font=("Segoe UI", 10), bg="#0f172a", fg=self.text_main, insertbackground=self.text_main, bd=1, relief=tk.SOLID, width=14).pack(side=tk.LEFT, padx=(5, 0), ipady=3)

        # Card 3: Action Buttons
        card3 = tk.Frame(self.root, bg=self.card_bg, padx=15, pady=12)
        card3.pack(fill=tk.X, padx=25, pady=(0, 10))

        tk.Label(card3, text="3. KÍCH HOẠT TỰ ĐỘNG HÓA TẠI MÁY NÀY", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.accent_orange).pack(anchor=tk.W, pady=(0, 8))

        btn_box = tk.Frame(card3, bg=self.card_bg)
        btn_box.pack(fill=tk.X)

        self.btn_flow_b = tk.Button(
            btn_box, 
            text="🤖 Chạy Luồng B\n(Tải DS đã gửi & Đối soát)", 
            command=self.start_flow_b, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.accent_blue, 
            fg=self.text_main, 
            activebackground="#2563eb", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_flow_b.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 5))

        self.btn_flow_c = tk.Button(
            btn_box, 
            text="⚠️ Chạy Luồng C\n(Tải DS lỗi 3176 & Đối soát)", 
            command=self.start_flow_c, 
            font=("Segoe UI", 9, "bold"), 
            bg="#d97706", 
            fg=self.text_main, 
            activebackground="#b45309", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_flow_c.pack(side=tk.RIGHT, fill=tk.X, expand=True, ipady=8, padx=(5, 0))

        # Card 4: Realtime Log Console
        card4 = tk.Frame(self.root, bg=self.card_bg, padx=15, pady=10)
        card4.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 15))

        tk.Label(card4, text="TIẾN TRÌNH THỰC THI (LOG CONSOLE)", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.text_sec).pack(anchor=tk.W, pady=(0, 5))

        log_inner = tk.Frame(card4, bg=self.card_bg)
        log_inner.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(log_inner, height=10, bg="#0f172a", fg=self.accent_green, bd=1, relief=tk.SOLID, font=("Consolas", 9), wrap=tk.WORD)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sbar = tk.Scrollbar(log_inner, command=self.txt_log.yview)
        sbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.configure(yscrollcommand=sbar.set)

        self.log("CheckBHYT Client RPA Runner đã sẵn sàng.")
        self.log("Trình duyệt Chromium sẽ mở trực tiếp trên màn hình máy này khi bấm nút.")

    def fetch_server_config(self):
        srv = self.server_url.get().strip().rstrip("/")
        try:
            self.log(f"Đang kết nối đến máy chủ: {srv}...")
            r = requests.get(f"{srv}/api/client/config", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("portal_cskcb"): self.portal_cskcb.set(data["portal_cskcb"])
                if data.get("portal_username"): self.portal_user.set(data["portal_username"])
                if data.get("portal_password"): self.portal_pass.set(data["portal_password"])
                if data.get("portal_url"): self.portal_url.set(data["portal_url"])
                self.save_config()
                self.log("Đồng bộ cấu hình từ Server thành công! ✅")
                messagebox.showinfo("Thành công", "Đã đồng bộ thông tin tài khoản Cổng BHYT từ máy chủ!")
            else:
                self.log(f"Máy chủ phản hồi mã {r.status_code}.")
        except Exception as e:
            self.log(f"Lỗi kết nối máy chủ: {e}")
            messagebox.showwarning("Lỗi kết nối", f"Không thể kết nối tới {srv}. Vui lòng kiểm tra địa chỉ IP Server.")

    def _ensure_login(self, page):
        self.log("Đang mở Cổng Giám định BHYT...")
        page.goto(self.portal_url.get().strip(), timeout=60000)
        page.wait_for_load_state("domcontentloaded")

        try:
            current_url = page.url.lower()
            if "login" not in current_url and ("home" in current_url or "gdbhyt" in current_url):
                is_logged_in = page.locator("#HeaderMenu").is_visible(timeout=3000) or \
                               page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible(timeout=3000) or \
                               page.get_by_text("Hồ sơ XML").is_visible(timeout=3000)
                if is_logged_in:
                    self.log("Phiên đăng nhập cũ vẫn còn hiệu lực (Session Valid) ✅")
                    return
        except Exception:
            pass

        self.log("Đang tự động điền Mã CSKCB, Tên đăng nhập và Mật khẩu...")
        try:
            if page.get_by_role("textbox", name="Mã cơ sở KCB").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Mã cơ sở KCB").fill(self.portal_cskcb.get().strip())
            if page.get_by_role("textbox", name="Tên đăng nhập").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Tên đăng nhập").fill(self.portal_user.get().strip())
            if page.get_by_role("textbox", name="Mật khẩu").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Mật khẩu").fill(self.portal_pass.get().strip())

            if page.get_by_role("textbox", name="Gõ mã hiển thị").is_visible(timeout=5000):
                page.get_by_role("textbox", name="Gõ mã hiển thị").click()
                self.log(">> VUI LÒNG NHÌN MÃ CAPTCHA TRÊN MÀN HÌNH, GÕ VÀO VÀ BẤM ĐĂNG NHẬP (Chờ tối đa 120s)...")

            login_ok = False
            start_wait = time.time()
            while time.time() - start_wait < 120:
                try:
                    if page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible():
                        login_ok = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            if not login_ok:
                raise Exception("Quá thời gian chờ nhập Captcha hoặc chưa hoàn tất đăng nhập.")

            self.log("Đăng nhập thành công! Đang lưu phiên làm việc...")
            try:
                page.context.storage_state(path=SESSION_FILE)
            except Exception:
                pass
        except Exception as e:
            raise Exception(f"Lỗi đăng nhập Cổng: {e}")

    def start_flow_b(self):
        import threading
        self.save_config()
        self.btn_flow_b.configure(state=tk.DISABLED)
        self.btn_flow_c.configure(state=tk.DISABLED)
        threading.Thread(target=self._run_flow_b_worker, daemon=True).start()

    def _run_flow_b_worker(self):
        from playwright.sync_api import sync_playwright
        from_d = self.from_date.get().strip()
        to_d = self.to_date.get().strip()
        srv = self.server_url.get().strip().rstrip("/")

        self.log(f"=== BẮT ĐẦU LUỒNG B (TỪ {from_d} ĐẾN {to_d}) ===")

        try:
            with sync_playwright() as p:
                storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(storage_state=storage_path, viewport={'width': 1366, 'height': 768}, accept_downloads=True)
                page = context.new_page()

                try:
                    self._ensure_login(page)

                    # Điều hướng
                    self.log("Đang mở Danh sách đề nghị thanh toán...")
                    try:
                        top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                        if top_menu.is_visible(timeout=3000): top_menu.click()
                    except Exception:
                        pass
                    page.get_by_role("link", name="Danh sách đề nghị thanh toán").click(timeout=15000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1.0)

                    # Lọc trạng thái
                    self.log("Lọc trạng thái: Đã đề nghị thanh toán...")
                    try:
                        cb = page.locator("#cb_TrangThaiTT_B-1Img")
                        if cb.is_visible(timeout=5000):
                            cb.click()
                            page.get_by_role("cell", name="Đã đề nghị thanh toán", exact=True).click(timeout=5000)
                    except Exception as e:
                        self.log(f"Lưu ý trạng thái: {e}")

                    # Tìm kiếm
                    self.log("Bấm Tìm kiếm dữ liệu...")
                    try:
                        page.locator("span").filter(has_text=re.compile(r"^Tìm kiếm$")).first.click(timeout=10000)
                    except Exception:
                        page.get_by_role("button", name=re.compile(r"Tìm kiếm", re.IGNORECASE)).first.click(timeout=10000)

                    time.sleep(2.0)
                    try:
                        loading = page.locator(".dxgvLoadingDiv, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS")
                        if loading.count() > 0: loading.first.wait_for(state="hidden", timeout=45000)
                    except Exception:
                        pass
                    time.sleep(1.5)

                    # Xuất Excel
                    self.log("Đang kích hoạt Xuất Excel (chờ tối đa 5 phút)...")
                    try:
                        page.locator("span").filter(has_text=re.compile(r"^Xuất Excel$")).first.click(timeout=10000)
                        time.sleep(1.5)
                    except Exception:
                        pass

                    with page.expect_download(timeout=300000) as dl_info:
                        try:
                            sub_items = page.locator("span").filter(has_text=re.compile(r"^Xuất excel$"))
                            if sub_items.count() > 0: sub_items.first.click()
                            else: page.locator(".dxm-popup span").filter(has_text=re.compile(r"Xuất excel", re.IGNORECASE)).first.click(timeout=5000)
                        except Exception:
                            page.get_by_text("Xuất excel", exact=True).first.click(timeout=10000)

                    self.log("Đang tải file Excel về máy trạm...")
                    dl = dl_info.value
                    dest_file = os.path.join(TEMP_DIR, "listbh.xlsx")
                    dl.save_as(dest_file)
                    context.storage_state(path=SESSION_FILE)
                    self.log(f"Đã tải thành công: {dest_file} ✅")

                finally:
                    context.close()
                    browser.close()

            # Gửi file lên WebApp Server
            self.log(f"Đang đẩy file {dest_file} lên máy chủ {srv}...")
            with open(dest_file, "rb") as f:
                r_upload = requests.post(f"{srv}/api/upload/b", files={"file": ("listbh.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=60)

            if r_upload.status_code != 200:
                raise Exception(f"Lỗi tải file lên server: {r_upload.text}")

            self.log("Tải file lên server thành công! Đang kích hoạt Đối soát B với CSDL HIS...")
            clean_from = from_d.replace('-', '').replace('/', '')
            clean_to = to_d.replace('-', '').replace('/', '')
            r_sync = requests.post(f"{srv}/api/sync/start", json={"from_date": clean_from, "to_date": clean_to, "include_errors": False}, timeout=120)

            if r_sync.status_code == 200:
                res_data = r_sync.json()
                self.log("=== ĐỐI SOÁT B HOÀN TẤT THÀNH CÔNG! ✅ ===")
                self.log(f"Kết quả: {res_data.get('message', 'Thành công')}")
                messagebox.showinfo("Thành công", f"Đã hoàn thành Đối soát B trên máy chủ!\n{res_data.get('message', '')}")
            else:
                self.log(f"Lỗi đối soát: {r_sync.text}")
                messagebox.showerror("Lỗi đối soát", f"Máy chủ trả về lỗi: {r_sync.text}")

        except Exception as e:
            self.log(f"LỖI THỰC THI: {e}")
            messagebox.showerror("Lỗi", f"Lỗi Luồng B: {e}")
        finally:
            self.btn_flow_b.configure(state=tk.NORMAL)
            self.btn_flow_c.configure(state=tk.NORMAL)

    def start_flow_c(self):
        import threading
        self.save_config()
        self.btn_flow_b.configure(state=tk.DISABLED)
        self.btn_flow_c.configure(state=tk.DISABLED)
        threading.Thread(target=self._run_flow_c_worker, daemon=True).start()

    def _run_flow_c_worker(self):
        from playwright.sync_api import sync_playwright
        from_d = self.from_date.get().strip()
        to_d = self.to_date.get().strip()
        srv = self.server_url.get().strip().rstrip("/")

        self.log(f"=== BẮT ĐẦU LUỒNG C (TỪ {from_d} ĐẾN {to_d}) ===")

        # Xóa temp cũ
        for old_f in glob.glob(os.path.join(TEMP_DIR, "*.*")):
            try: os.remove(old_f)
            except Exception: pass

        try:
            with sync_playwright() as p:
                storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(storage_state=storage_path, viewport={'width': 1366, 'height': 768}, accept_downloads=True)
                page = context.new_page()

                try:
                    self._ensure_login(page)

                    # 4 bước điều hướng
                    self.log("Điều hướng: Hồ sơ ĐNTT > Hồ sơ XML > QĐ 3176 > Kết quả gửi XML...")
                    try:
                        top = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                        if top.is_visible(timeout=3000): top.click()
                    except Exception: pass
                    time.sleep(0.6)

                    try:
                        xml_item = page.locator("span.dx-vam, a, div, span").filter(has_text="Hồ sơ XML").first
                        xml_item.hover(timeout=3000)
                        xml_item.click(force=True)
                    except Exception: pass
                    time.sleep(0.6)

                    try:
                        qd = page.locator("span.dx-vam, a, div, span").filter(has_text=re.compile(r"3176")).first
                        qd.hover(timeout=3000)
                        qd.click(force=True)
                    except Exception:
                        page.evaluate("""() => {
                            const spans = Array.from(document.querySelectorAll('span.dx-vam, a, div, span'));
                            const el = spans.find(s => s.textContent && s.textContent.includes('3176'));
                            if (el) el.click();
                        }""")
                    time.sleep(0.8)

                    page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a')).filter(a => a.textContent && a.textContent.includes('Kết quả gửi hồ sơ XML'));
                        if (links.length > 1) links[1].click();
                        else if (links.length === 1) links[0].click();
                    }""")
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1.5)

                    def wait_grid(timeout=45):
                        start = time.time()
                        time.sleep(1.0)
                        while time.time() - start < timeout:
                            try:
                                if page.locator("#gvDSKetQuaGuiHoso_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS").is_visible():
                                    time.sleep(0.5)
                                    continue
                                if page.locator("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'], #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS").count() > 0:
                                    return True
                                if page.locator("#gvDSKetQuaGuiHoso tr.dxgvEmptyDataRow, #gvDSKetQuaGuiHoso td.dxgvEmptyDataRow").count() > 0:
                                    return False
                            except Exception: pass
                            time.sleep(0.5)
                        return False

                    self.log("Chờ bảng kết quả hiển thị...")
                    try:
                        page.wait_for_selector("#gvDSKetQuaGuiHoso", timeout=30000)
                        wait_grid(30)
                    except Exception: pass

                    # Điền ngày
                    self.log(f"Thiết lập khoảng ngày: {from_d} đến {to_d}...")
                    f_d, t_d = from_d, to_d
                    if "-" in from_d:
                        p_ = from_d.split("-")
                        if len(p_) == 3: f_d = f"{p_[2]}/{p_[1]}/{p_[0]}"
                    if "-" in to_d:
                        p_ = to_d.split("-")
                        if len(p_) == 3: t_d = f"{p_[2]}/{p_[1]}/{p_[0]}"

                    for tu_sel in ["#deTuNgay_I", "#txtTuNgay_I", "#TuNgay_I", "input[name*='TuNgay']"]:
                        el = page.locator(tu_sel).first
                        if el.is_visible(timeout=1000): el.click(); el.fill(f_d); break
                    for den_sel in ["#deDenNgay_I", "#txtDenNgay_I", "#DenNgay_I", "input[name*='DenNgay']"]:
                        el = page.locator(den_sel).first
                        if el.is_visible(timeout=1000): el.click(); el.fill(t_d); break

                    # Bấm tìm kiếm
                    try: page.locator(".dxbButton:has-text('Tìm kiếm'), #btnTimKiem, span:has-text('Tìm kiếm')").first.click(timeout=5000)
                    except Exception: pass
                    self.log("Đang chờ tải danh sách hồ sơ...")
                    wait_grid(45)

                    # Chọn 100 dòng
                    self.log("Thiết lập 100 bản ghi/trang...")
                    try:
                        p_img = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom_DDBImg")
                        if p_img.is_visible(timeout=5000):
                            p_img.click()
                            time.sleep(0.5)
                            page.get_by_text("100", exact=True).click(timeout=5000)
                            wait_grid(45)
                    except Exception: pass

                    # Lọc cột lỗi = 1
                    self.log("Lọc các hồ sơ có lỗi (cột lỗi = 1)...")
                    try:
                        col5 = page.locator("#gvDSKetQuaGuiHoso_DXFREditorcol5_I")
                        if col5.is_visible(timeout=5000):
                            col5.click(force=True)
                            col5.fill("1")
                            col5.press("Enter")
                            wait_grid(45)
                    except Exception: pass

                    # Tải các gói lỗi
                    total_dl = 0
                    p_idx = 1
                    while True:
                        self.log(f"Quét danh sách gói lỗi Trang {p_idx}...")
                        wait_grid(30)
                        row_links = page.locator("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'] td a, #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS td a").all()
                        if not row_links: row_links = page.locator("#gvDSKetQuaGuiHoso td a").all()

                        self.log(f"Tìm thấy {len(row_links)} gói trên trang {p_idx}.")
                        if len(row_links) == 0: break

                        for idx, link in enumerate(row_links):
                            try:
                                link.click()
                                time.sleep(1.5)
                                exp_btn = page.locator("span").filter(has_text="Xuất Excel").first
                                if exp_btn.is_visible(timeout=5000):
                                    with page.expect_download(timeout=60000) as d_info:
                                        exp_btn.click()
                                    dl = d_info.value
                                    t_path = os.path.join(TEMP_DIR, f"err_p{p_idx}_{idx+1}.xlsx")
                                    dl.save_as(t_path)
                                    total_dl += 1
                                    self.log(f"  -> Đã tải tệp lỗi #{total_dl} ✅")

                                try: page.get_by_role("img", name="[Close]").first.click(timeout=3000)
                                except Exception: page.locator(".dxpc-closeBtn").first.click(timeout=3000)
                                time.sleep(0.8)
                            except Exception as e_row:
                                self.log(f"Lỗi tải dòng #{idx+1}: {e_row}")

                        try:
                            next_btn = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom .dxp-button:has-text('>')").first
                            if next_btn.is_visible(timeout=3000) and "dxp-disabled" not in (next_btn.get_attribute("class") or ""):
                                next_btn.click()
                                p_idx += 1
                                time.sleep(1.5)
                                wait_grid(30)
                            else: break
                        except Exception: break

                    context.storage_state(path=SESSION_FILE)

                finally:
                    context.close()
                    browser.close()

            # Gom file
            merged_file = os.path.join(TEMP_DIR, "HoSoLoiChiTiet.xlsx")
            files = glob.glob(os.path.join(TEMP_DIR, "err_*.xlsx")) + glob.glob(os.path.join(TEMP_DIR, "err_*.xls"))
            if files:
                dfs = [pd.read_excel(f) for f in files if os.path.getsize(f) > 0]
                if dfs:
                    comb = pd.concat(dfs, ignore_index=True).drop_duplicates()
                    comb.to_excel(merged_file, index=False)
                    self.log(f"Tổng hợp thành công {len(comb)} dòng lỗi chi tiết vào {merged_file}.")
            else:
                self.log("Không có gói lỗi nào được tải về trong khoảng ngày này.")
                # Tạo file rỗng
                pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra"]).to_excel(merged_file, index=False)

            # Upload lên server
            self.log(f"Đang đẩy file {merged_file} lên máy chủ {srv}...")
            with open(merged_file, "rb") as f:
                r_upload = requests.post(f"{srv}/api/upload/c", files={"file": ("HoSoLoiChiTiet.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=60)

            if r_upload.status_code != 200:
                raise Exception(f"Lỗi tải file lỗi lên server: {r_upload.text}")

            self.log("Tải file lỗi lên server thành công! Đang kích hoạt Đối soát C với CSDL HIS...")
            clean_from = from_d.replace('-', '').replace('/', '')
            clean_to = to_d.replace('-', '').replace('/', '')
            r_sync = requests.post(f"{srv}/api/sync/start", json={"from_date": clean_from, "to_date": clean_to, "include_errors": True}, timeout=120)

            if r_sync.status_code == 200:
                res_data = r_sync.json()
                self.log("=== ĐỐI SOÁT C HOÀN TẤT THÀNH CÔNG! ✅ ===")
                self.log(f"Kết quả: {res_data.get('message', 'Thành công')}")
                messagebox.showinfo("Thành công", f"Đã hoàn thành Đối soát C trên máy chủ!\n{res_data.get('message', '')}")
            else:
                self.log(f"Lỗi đối soát: {r_sync.text}")
                messagebox.showerror("Lỗi đối soát", f"Máy chủ trả về lỗi: {r_sync.text}")

        except Exception as e:
            self.log(f"LỖI THỰC THI: {e}")
            messagebox.showerror("Lỗi", f"Lỗi Luồng C: {e}")
        finally:
            self.btn_flow_b.configure(state=tk.NORMAL)
            self.btn_flow_c.configure(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientRPAGui(root)
    root.mainloop()
