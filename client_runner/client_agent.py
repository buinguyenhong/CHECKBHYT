import sys
import os
import re
import time
import glob
import json
import datetime
import requests
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
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

ACTIVE_CLIENT_GUI = None


class ClientAgentHTTPHandler(BaseHTTPRequestHandler):
    """
    HTTP Server cục bộ lắng nghe tại 127.0.0.1:8765 / 0.0.0.0:8765 cho phép WebApp trên trình duyệt
    tự động phát hiện và kích hoạt Chromium trực tiếp trên màn hình Máy trạm.
    """
    def log_message(self, format, *args):
        pass  # Tắt log stdout mặc định

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Access-Control-Request-Private-Network')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Max-Age', '86400')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        global ACTIVE_CLIENT_GUI
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        if path == '/api/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            is_running = ACTIVE_CLIENT_GUI.is_running if ACTIVE_CLIENT_GUI else False
            res = {
                "status": "ok",
                "app": "CheckBHYT Client Runner",
                "version": "2.0",
                "is_running": is_running,
                "server_url": ACTIVE_CLIENT_GUI.server_url.get() if ACTIVE_CLIENT_GUI else ""
            }
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))

        elif path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            logs = ACTIVE_CLIENT_GUI.recent_logs[-80:] if ACTIVE_CLIENT_GUI else []
            res = {"logs": logs}
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))

        elif path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            if ACTIVE_CLIENT_GUI:
                res = {
                    "is_running": ACTIVE_CLIENT_GUI.is_running,
                    "last_status": ACTIVE_CLIENT_GUI.last_status
                }
            else:
                res = {"is_running": False, "last_status": {"status": "idle"}}
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global ACTIVE_CLIENT_GUI
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            body = json.loads(post_data)
        except Exception:
            body = {}

        if path in ['/api/run-flow-b', '/api/run-flow-c']:
            if not ACTIVE_CLIENT_GUI:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Client GUI chưa sẵn sàng."}, ensure_ascii=False).encode('utf-8'))
                return

            if ACTIVE_CLIENT_GUI.is_running:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "busy", "message": "Tiến trình RPA đang chạy trên máy trạm. Vui lòng chờ hoàn thành."}, ensure_ascii=False).encode('utf-8'))
                return

            from_d = body.get("from_date", "").strip()
            to_d = body.get("to_date", "").strip()
            srv = body.get("server_url", "").strip()

            if path == '/api/run-flow-b':
                ACTIVE_CLIENT_GUI.trigger_flow_from_web('B', from_d, to_d, srv)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "started", "flow": "B", "message": "Đã khởi chạy Luồng B trên máy trạm!"}, ensure_ascii=False).encode('utf-8'))
            else:
                ACTIVE_CLIENT_GUI.trigger_flow_from_web('C', from_d, to_d, srv)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "started", "flow": "C", "message": "Đã khởi chạy Luồng C trên máy trạm!"}, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()


class ClientRPAGui:
    def __init__(self, root):
        global ACTIVE_CLIENT_GUI
        ACTIVE_CLIENT_GUI = self

        self.root = root
        self.root.title("CheckBHYT - Client RPA Runner (Local Web Bridge)")
        self.root.geometry("680x750")
        self.root.resizable(False, False)

        # Trạng thái thời gian thực phục vụ WebApp Bridge
        self.is_running = False
        self.recent_logs = []
        self.last_status = {"status": "idle", "flow": None, "message": "Sẵn sàng", "error": None}

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
        self.start_http_bridge()

    def start_http_bridge(self):
        """Khởi chạy HTTP Bridge Server nền tại cổng 8765"""
        def run_server():
            for host in ['0.0.0.0', '127.0.0.1']:
                try:
                    server = ThreadingHTTPServer((host, 8765), ClientAgentHTTPHandler)
                    self.log(f"Local Web Bridge đã sẵn sàng tại {host}:8765 ✅")
                    server.serve_forever()
                    break
                except Exception as e:
                    self.log(f"Lưu ý Local Bridge ({host}:8765): {e}")

        t = threading.Thread(target=run_server, daemon=True)
        t.start()

    def trigger_flow_from_web(self, flow_type: str, from_d: str, to_d: str, server_url: str):
        """WebApp kích hoạt chạy Luồng B hoặc C từ xa trên máy trạm này"""
        if from_d:
            self.root.after(0, lambda: self.from_date.set(from_d))
        if to_d:
            self.root.after(0, lambda: self.to_date.set(to_d))
        if server_url:
            self.root.after(0, lambda: self.server_url.set(server_url))

        self.save_config()
        self.root.after(0, lambda: self.btn_flow_b.configure(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_flow_c.configure(state=tk.DISABLED))

        self.is_running = True
        self.last_status = {
            "status": "running",
            "flow": flow_type,
            "message": f"Đang chạy Luồng {flow_type} từ WebApp...",
            "error": None
        }

        if flow_type == 'B':
            threading.Thread(target=self._run_flow_b_worker, kwargs={"is_from_web": True}, daemon=True).start()
        else:
            threading.Thread(target=self._run_flow_c_worker, kwargs={"is_from_web": True}, daemon=True).start()

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

    def _launch_native_browser(self, p):
        """Khởi chạy Google Chrome hoặc Microsoft Edge native trên Windows."""
        for ch in ["chrome", "msedge"]:
            try:
                b = p.chromium.launch(channel=ch, headless=False, args=["--start-maximized"])
                self.log(f"Đã mở trình duyệt {ch.upper()} có sẵn trên máy ✅")
                return b
            except Exception:
                pass
        return p.chromium.launch(headless=False, args=["--start-maximized"])

    def _extract_records_from_grid(self, page):
        """Quét danh sách maGD và STT trên bảng hiện tại."""
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
                return records;
            }""")
        except Exception:
            return []

    def _download_direct_record(self, page, ma_gd, stt, save_dir, max_retries=3):
        """Tải file trực tiếp qua endpoint ExportExcelKPG_New?maGd={maGD}."""
        portal_base = self.portal_url.get().strip().rstrip('/') if hasattr(self, 'portal_url') else "https://gdbhyt.baohiemxahoi.gov.vn"
        download_url = f"{portal_base}/DanhSachKetQuaGuiHoSoQD130/ExportExcelKPG_New?maGd={ma_gd}"
        file_name = f"STT_{str(stt).zfill(4)}_{ma_gd}.xlsx"
        file_path = os.path.join(save_dir, file_name)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 1024:
            self.log(f"✅ [STT {stt}] Đã có sẵn file: {file_name}, bỏ qua tải lại.")
            return file_path

        for attempt in range(1, max_retries + 1):
            try:
                self.log(f"⚡ [STT {stt}] Đang tải hồ sơ {ma_gd} (Lần {attempt})...")
                response = page.request.get(download_url, timeout=60000)
                if not response.ok:
                    raise Exception(f"HTTP Status {response.status}: {response.status_text}")
                body = response.body()
                if not body or len(body) < 500:
                    raise Exception(f"Dữ liệu tải về quá nhỏ ({len(body) if body else 0} bytes)")
                with open(file_path, "wb") as f:
                    f.write(body)
                kb_size = round(len(body) / 1024, 1)
                self.log(f"✅ [STT {stt}] Tải thành công ({kb_size} KB) -> {file_name}")
                return file_path
            except Exception as err:
                self.log(f"⚠️ [STT {stt}] Lỗi tải lần {attempt}: {err}")
                if attempt < max_retries:
                    time.sleep(2.0 * attempt)
                else:
                    self.log(f"❌ [STT {stt}] Thất bại sau {max_retries} lần thử: {ma_gd}")
                    return None

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
            last_log_t = start_wait

            while time.time() - start_wait < 180:
                try:
                    has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible()
                    has_menu = page.locator("#HeaderMenu").is_visible() or page.get_by_text("Hồ sơ đề nghị thanh toán").is_visible()
                    has_login_btn = page.locator("input[value='Đăng nhập'], #btnLogin, #btnDangNhap").is_visible()
                    has_pass_inp = page.locator("input[type='password']").is_visible()

                    if (has_logout or has_menu) and not has_login_btn and not has_pass_inp:
                        login_ok = True
                        break
                except Exception:
                    pass

                now = time.time()
                if now - last_log_t >= 10:
                    elapsed = int(now - start_wait)
                    remaining = max(0, 180 - elapsed)
                    self.log(f"⏳ Đang chờ bạn nhập Captcha và bấm Đăng nhập... (Đã chờ {elapsed}s / còn lại {remaining}s)")
                    last_log_t = now

                time.sleep(1)

            if not login_ok:
                raise Exception("Quá thời gian 180 giây chờ nhập Captcha hoặc chưa hoàn tất đăng nhập.")

            self.log("Đăng nhập thành công! Đang lưu phiên làm việc...")
            try:
                page.context.storage_state(path=SESSION_FILE)
            except Exception:
                pass
        except Exception as e:
            raise Exception(f"Lỗi đăng nhập Cổng: {e}")

    def _wait_devexpress_callback(self, page, control_name: str = "gvDSKetQuaGuiHoso", timeout_sec: int = 45):
        """
        Sử dụng trực tiếp DevExpress Client-Side API và InCallback() / EndCallback
        để đợi máy chủ Cổng BHYT hoàn tất nạp dữ liệu tức thì và chuẩn xác.
        """
        try:
            page.evaluate("""({ctrlName, timeoutMs}) => {
                return new Promise((resolve) => {
                    try {
                        const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                        const ctrl = cc ? cc.GetByName(ctrlName) : (window[ctrlName] || null);
                        
                        if (!ctrl) {
                            const ld = document.querySelector(`#${ctrlName}_LD, .dxgvLoadingDiv_EIS, .dxgvLoadingPanel_EIS, .dxgvLoadingDiv`);
                            if (!ld || ld.offsetParent === null) return resolve({status: 'no_control_idle'});
                        }

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

    def _wait_portal_idle(self, page, timeout=45000):
        try:
            time.sleep(0.3)
            for sel in [".dxgvLoadingDiv", ".dxgvLoadingDiv_EIS", ".dxgvLoadingPanel_EIS", "#gvDSKetQuaGuiHoso_LD", ".dxp-loadingPanel"]:
                try:
                    loaders = page.locator(sel)
                    if loaders.count() > 0:
                        loaders.first.wait_for(state="hidden", timeout=timeout)
                except Exception:
                    pass
            time.sleep(0.5)
        except Exception:
            pass

    def start_flow_b(self):
        import threading
        self.save_config()
        self.btn_flow_b.configure(state=tk.DISABLED)
        self.btn_flow_c.configure(state=tk.DISABLED)
        self.is_running = True
        self.last_status = {"status": "running", "flow": "B", "message": "Đang khởi chạy Luồng B...", "error": None}
        threading.Thread(target=self._run_flow_b_worker, kwargs={"is_from_web": False}, daemon=True).start()

    def _run_flow_b_worker(self, is_from_web: bool = False):
        from playwright.sync_api import sync_playwright
        from_d = self.from_date.get().strip()
        to_d = self.to_date.get().strip()
        srv = self.server_url.get().strip().rstrip("/")

        self.is_running = True
        self.last_status = {"status": "running", "flow": "B", "message": "Đang chạy Luồng B (Tải danh sách đã gửi listbh.xlsx)...", "error": None}
        self.log("=== BẮT ĐẦU LUỒNG B (TẢI DANH SÁCH ĐÃ GỬI LISTBH.XLSX) ===")

        try:
            with sync_playwright() as p:
                storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
                browser = self._launch_native_browser(p)
                context = browser.new_context(storage_state=storage_path, viewport=None, accept_downloads=True)
                page = context.new_page()

                try:
                    self._ensure_login(page)
                    self._wait_portal_idle(page)

                    # Điều hướng trực tiếp vào Danh sách hồ sơ KCB
                    self.log("Đang điều hướng đến: Danh sách đề nghị thanh toán (/DanhSachHSKCB/Index)...")
                    target_url_b = f"{self.portal_url.get().strip().rstrip('/')}/DanhSachHSKCB/Index" if hasattr(self, 'portal_url') else "https://gdbhyt.baohiemxahoi.gov.vn/DanhSachHSKCB/Index"
                    try:
                        page.goto(target_url_b, timeout=45000)
                        page.wait_for_load_state("domcontentloaded")
                    except Exception: pass

                    # Chờ các control chính hoặc fallback menu
                    try:
                        page.wait_for_selector("#gvDanhSachHoSo, #bt_TimKiem, #btnExport, #cb_TrangThaiTT", timeout=20000)
                    except Exception:
                        try:
                            top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                            if top_menu.is_visible(timeout=3000): top_menu.click()
                            time.sleep(0.5)
                            xml_menu = page.locator("#HeaderMenu_DXME2_ div, #HeaderMenu div, .dxm-item").filter(has_text="Hồ sơ XML").first
                            if xml_menu.is_visible(timeout=3000): xml_menu.click(force=True)
                            time.sleep(0.5)
                            page.locator("a, span, .dxm-item").filter(has_text=re.compile(r"Danh sách", re.IGNORECASE)).first.click(force=True)
                            page.wait_for_load_state("domcontentloaded")
                        except Exception: pass

                    self._wait_portal_idle(page)

                    # 3. Chọn Trạng thái: "Đã đề nghị thanh toán" qua DevExpress Client API
                    self.log("Đang chọn trạng thái: 'Đã đề nghị thanh toán'...")
                    status_selected = False
                    try:
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
                        if status_selected:
                            self.log("Đã chọn trạng thái: 'Đã đề nghị thanh toán' qua DevExpress API ✅")
                    except Exception as js_err:
                        self.log(f"Lưu ý JS API trạng thái: {js_err}")

                    # Fallback nếu cần
                    if not status_selected:
                        try:
                            btn_cb = page.locator("#cb_TrangThaiTT_B-1, #cb_TrangThaiTT_B-1Img, td[id*='cb_TrangThaiTT_B-1']").first
                            if btn_cb.is_visible(timeout=2000):
                                btn_cb.click(force=True)
                                time.sleep(0.4)
                                item = page.locator("#cb_TrangThaiTT_DDD_L_LBT td, tr.dxeListBoxItemRow_EIS td, .dxeListBoxItem").filter(has_text=re.compile(r"Đã đề nghị thanh toán", re.IGNORECASE)).first
                                if item.is_visible(timeout=2000):
                                    item.click(force=True)
                                    self.log("Đã chọn trạng thái qua giao diện DOM fallback ✅")
                        except Exception: pass

                    self._wait_portal_idle(page)

                    # 4. Bấm Tìm kiếm & Chờ nạp dữ liệu xong
                    self.log("Bấm Tìm kiếm dữ liệu...")
                    searched = False
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
                            self.log("Đã kích hoạt nút Tìm kiếm qua DevExpress DoClick API ✅")
                    except Exception:
                        pass

                    if not searched:
                        for s_sel in ["#bt_TimKiem_CD", "#bt_TimKiem_B", "#bt_TimKiem", "#btnTimKiem_CD", "#btnTimKiem", ".dxbButton:has-text('Tìm kiếm')", "span:has-text('Tìm kiếm')"]:
                            try:
                                s_el = page.locator(s_sel).first
                                if s_el.is_visible(timeout=1500):
                                    s_el.click(force=True)
                                    searched = True
                                    break
                            except Exception: pass

                    # 5. Xuất Excel và tải file listbh.xlsx
                    self.log("Đang kích hoạt Xuất Excel danh sách đã gửi...")
                    
                    # Bước 5.1: Click nút "Xuất Excel" (btnExport) để mở Popup Export
                    self.log("Click nút 'Xuất Excel' (btnExport)...")
                    opened_popup = page.evaluate("""() => {
                        try {
                            const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                            const btn = window.btnExport || (cc ? cc.GetByName('btnExport') : null);
                            if (btn && typeof btn.DoClick === 'function') {
                                btn.DoClick();
                                return true;
                            }
                        } catch(e) {}
                        return false;
                    }""")

                    if not opened_popup:
                        btn_exp = page.locator("#btnExport_CD, #btnExport, #bt_XuatExcel_CD, #bt_XuatExcel, .dxbButton:has-text('Xuất Excel')").first
                        if btn_exp.is_visible(timeout=3000):
                            btn_exp.click(force=True)

                    time.sleep(1.2)

                    # Bước 5.2: Bấm nút "Xuất excel" (btnExportExcel) trong Popup kèm theo expect_download
                    self.log("Đang bấm nút 'Xuất excel' (btnExportExcel) để tải file listbh.xlsx...")
                    with page.expect_download(timeout=300000) as dl_info:
                        clicked_excel = page.evaluate("""() => {
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

                        if not clicked_excel:
                            btn_down = page.locator("#btnExportExcel_CD, #btnExportExcel, .dxbButton:has-text('Xuất excel'), [id*='btnExportExcel']").first
                            if btn_down.is_visible(timeout=5000):
                                btn_down.click(force=True)
                            else:
                                page.evaluate("""() => {
                                    const btns = Array.from(document.querySelectorAll('.dxbButton, button, a, tr, td, span'));
                                    const target = btns.find(b => b.textContent && b.textContent.trim().toLowerCase() === 'xuất excel');
                                    if (target) target.click();
                                }""")

                    self.log("Cổng BHYT đã tạo tệp Excel xong! Đang tải về máy...")
                    download = dl_info.value
                    dest_path = os.path.join(TEMP_DIR, "listbh.xlsx")
                    download.save_as(dest_path)
                    self.log(f"Tải tệp danh sách đã gửi thành công: {dest_path} ✅")

                    context.storage_state(path=SESSION_FILE)

                    df = pd.read_excel(dest_path)
                    row_count = len(df)
                    self.log(f"Đã nạp file listbh.xlsx với {row_count} dòng dữ liệu.")

                    if is_from_web:
                        self.log("Đang gửi kết quả về WebApp Server...")
                        try:
                            with open(dest_path, "rb") as f:
                                resp = requests.post(
                                    f"{srv}/api/reconcile/upload_listbh",
                                    files={"file": ("listbh.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                                    timeout=60
                                )
                                self.log(f"Kết quả gửi WebApp: {resp.status_code}")
                        except Exception as ue:
                            self.log(f"Lỗi gửi file lên server: {ue}")

                    self.last_status = {
                        "status": "success",
                        "flow": "B",
                        "message": f"Tải thành công {row_count} bản ghi danh sách đã gửi.",
                        "error": None
                    }
                    self.log(f"=== HOÀN THÀNH LUỒNG B: {row_count} BẢN GHI ===")

                except Exception as e:
                    self.last_status = {"status": "error", "flow": "B", "message": str(e), "error": str(e)}
                    self.log(f"LỖI LUỒNG B: {str(e)}")
                finally:
                    context.close()
                    browser.close()

        except Exception as e:
            self.last_status = {"status": "error", "flow": "B", "message": str(e), "error": str(e)}
            self.log(f"LỖI KHỞI CHẠY TRÌNH DUYỆT B: {str(e)}")
        finally:
            self.is_running = False
            self.btn_flow_b.configure(state=tk.NORMAL)
            self.btn_flow_c.configure(state=tk.NORMAL)

    def _launch_native_browser(self, p):
        try:
            return p.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--start-maximized", "--disable-infobars", "--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            return p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--disable-infobars", "--disable-blink-features=AutomationControlled"]
            )

    def _extract_records_from_grid(self, page):
        return page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'], #gvDSKetQuaGuiHoso tr.dxgvDataRow_EIS, #gvDSKetQuaGuiHoso tr.dxgvDataRow"));
            return rows.map((r, idx) => {
                let maGD = '';
                const onclickAttr = r.getAttribute('onclick') || '';
                const match = onclickAttr.match(/['"]([^'"]+)['"]/);
                if (match) maGD = match[1];
                
                const link = r.querySelector('a, span[onclick], td[onclick], input[type="checkbox"]');
                if (!maGD && link) {
                    const lClick = link.getAttribute('onclick') || '';
                    const m2 = lClick.match(/['"]([^'"]+)['"]/);
                    if (m2) maGD = m2[1];
                    else maGD = link.value || link.textContent.trim();
                }
                
                if (!maGD) {
                    const rowId = r.getAttribute('id') || '';
                    maGD = rowId;
                }
                
                return {
                    stt: idx + 1,
                    maGD: maGD
                };
            });
        }""")

    def _download_direct_record(self, page, ma_gd, stt, temp_dir):
        try:
            portal_base = self.portal_url.get().strip().rstrip('/') if hasattr(self, 'portal_url') else "https://gdbhyt.baohiemxahoi.gov.vn"
            url = f"{portal_base}/DanhSachKetQuaGuiHosoQD130/ExportChiTietLoi?maGD={ma_gd}"
            with page.expect_download(timeout=45000) as dl_info:
                page.evaluate(f"""() => {{
                    const a = document.createElement('a');
                    a.href = '{url}';
                    a.download = '';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                }}""")
            download = dl_info.value
            dest_path = os.path.join(temp_dir, f"err_{stt}_{int(time.time()*1000)}.xlsx")
            download.save_as(dest_path)
            self.log(f"  -> Tải trực tiếp thành công bản ghi #{stt} ✅")
            return dest_path
        except Exception as e:
            try:
                with page.expect_download(timeout=30000) as dl_info:
                    page.evaluate(f"""() => {{
                        const rows = Array.from(document.querySelectorAll("#gvDSKetQuaGuiHoso tr[id*='DXDataRow'], #gvDSKetQuaGuiHoso tr.dxgvDataRow"));
                        if (rows[{stt-1}]) {{
                            const link = rows[{stt-1}].querySelector('a, span[onclick], td[onclick]');
                            if (link) link.click();
                        }}
                    }}""")
                download = dl_info.value
                dest_path = os.path.join(temp_dir, f"err_{stt}_{int(time.time()*1000)}.xlsx")
                download.save_as(dest_path)
                return dest_path
            except Exception as e2:
                self.log(f"  -> Không thể tải bản ghi #{stt}: {e2}")
        return None

    def start_flow_c(self):
        import threading
        self.save_config()
        self.btn_flow_b.configure(state=tk.DISABLED)
        self.btn_flow_c.configure(state=tk.DISABLED)
        self.is_running = True
        self.last_status = {"status": "running", "flow": "C", "message": "Đang khởi chạy Luồng C...", "error": None}
        threading.Thread(target=self._run_flow_c_worker, kwargs={"is_from_web": False}, daemon=True).start()

    def _run_flow_c_worker(self, is_from_web: bool = False):
        from playwright.sync_api import sync_playwright
        from_d = self.from_date.get().strip()
        to_d = self.to_date.get().strip()
        srv = self.server_url.get().strip().rstrip("/")

        self.is_running = True
        self.last_status = {"status": "running", "flow": "C", "message": "Đang chạy Luồng C (Tải danh sách lỗi chi tiết)...", "error": None}
        self.log("=== BẮT ĐẦU LUỒNG C (TẢI DANH SÁCH LỖI CHI TIẾT) ===")

        # Xóa file cũ
        for old_f in glob.glob(os.path.join(TEMP_DIR, "*.*")):
            try: os.remove(old_f)
            except Exception: pass

        try:
            with sync_playwright() as p:
                storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
                browser = self._launch_native_browser(p)
                context = browser.new_context(storage_state=storage_path, viewport=None, accept_downloads=True)
                page = context.new_page()
                page.set_default_timeout(600000)
                page.set_default_navigation_timeout(600000)

                try:
                    self._ensure_login(page)
                    self._wait_portal_idle(page)

                    # 1. Điều hướng QĐ 3176
                    self.log("Đang điều hướng đến: Kết quả gửi hồ sơ XML (/DanhSachKetQuaGuiHoSoQD130/Index)...")
                    portal_base = self.portal_url.get().strip().rstrip('/') if hasattr(self, 'portal_url') else "https://gdbhyt.baohiemxahoi.gov.vn"
                    target_url_c = f"{portal_base}/DanhSachKetQuaGuiHoSoQD130/Index"
                    try:
                        page.goto(target_url_c, timeout=90000, wait_until="load")
                    except Exception:
                        pass

                    page.wait_for_selector("#roundPanel, #gvDSKetQuaGuiHoso", timeout=90000)
                    self._wait_portal_idle(page)

                    # 2. Đặt ngày = Today
                    self.log("Thiết lập ngày 'Today'...")
                    try:
                        page.evaluate("""() => {
                            const now = new Date();
                            if (window.dt_TuNgay && typeof window.dt_TuNgay.SetValue === 'function') window.dt_TuNgay.SetValue(now);
                            if (window.dt_DenNgay && typeof window.dt_DenNgay.SetValue === 'function') window.dt_DenNgay.SetValue(now);
                        }""")
                    except Exception: pass

                    # 3. Bấm Tìm kiếm
                    self.log("Bấm nút Tìm kiếm (chờ tối đa 10 phút)...")
                    search_btn = page.locator("span").filter(has_text=re.compile(r"^Tìm kiếm$")).first
                    if search_btn.is_visible(timeout=3000):
                        search_btn.click(force=True)
                    else:
                        page.evaluate("if (window.btnTimKiem && typeof window.btnTimKiem.DoClick === 'function') window.btnTimKiem.DoClick();")

                    time.sleep(1.0)
                    self._wait_portal_idle(page)

                    # 4. Lọc Cột 5 = 1 (Lỗi)
                    self.log("Áp dụng bộ lọc Cột 5 = 1 (Lỗi)...")
                    col5_inp = page.locator("#gvDSKetQuaGuiHoso_DXFREditorcol5_I")
                    if col5_inp.is_visible(timeout=5000):
                        col5_inp.click()
                        col5_inp.fill("1")
                        col5_inp.press("Enter")
                    else:
                        page.evaluate("if (window.gvDSKetQuaGuiHoso) window.gvDSKetQuaGuiHoso.AutoFilterByColumn(5, '1');")
                    time.sleep(1.0)
                    self._wait_portal_idle(page)

                    # 5. Chọn Page size = 100
                    try:
                        page_size_inp = page.get_by_role("textbox", name="Page size:")
                        if page_size_inp.is_visible(timeout=2000):
                            page_size_inp.click()
                            time.sleep(0.4)
                            page.get_by_text("100", exact=True).first.click()
                            time.sleep(1.0)
                            self._wait_portal_idle(page)
                    except Exception: pass

                    # 6. Sắp xếp giảm dần theo Thời gian
                    try:
                        thoi_gian_hdr = page.get_by_role("cell", name="Thời gian", exact=True).or_(page.get_by_text("Thời gian", exact=True)).first
                        if thoi_gian_hdr.is_visible(timeout=3000):
                            thoi_gian_hdr.click(force=True)
                            time.sleep(1.0)
                            self._wait_portal_idle(page)
                            thoi_gian_hdr.click(force=True)
                            time.sleep(1.0)
                            self._wait_portal_idle(page)
                    except Exception: pass

                    # 7. Quét dữ liệu và Direct URL download
                    self.log("BẮT ĐẦU TẢI DANH SÁCH LỖI (DIRECT URL DOWNLOAD)...")
                    downloaded_count = 0
                    p_num = 1
                    max_records_to_dl = 100

                    while downloaded_count < max_records_to_dl:
                        self.log(f"Quét dữ liệu Trang {p_num}...")
                        self._wait_portal_idle(page)
                        records = self._extract_records_from_grid(page)
                        if not records:
                            self.log("Không tìm thấy bản ghi lỗi nào trên trang này.")
                            break

                        self.log(f"Tìm thấy {len(records)} bản ghi lỗi trên trang {p_num}...")
                        for rec in records:
                            fp = self._download_direct_record(page, rec['maGD'], rec['stt'], TEMP_DIR)
                            if fp: downloaded_count += 1
                            time.sleep(0.2)
                            if downloaded_count >= max_records_to_dl:
                                break

                        if downloaded_count >= max_records_to_dl:
                            break

                        p_num += 1
                        pager = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom")
                        next_btn = pager.get_by_text(str(p_num), exact=True)
                        if next_btn.count() > 0:
                            next_btn.first.click(force=True)
                            time.sleep(1.0)
                            self._wait_portal_idle(page)
                        else:
                            break

                    self.log(f"Đã tải thành công tổng cộng {downloaded_count} gói hồ sơ lỗi.")
                    context.storage_state(path=SESSION_FILE)

                finally:
                    context.close()
                    browser.close()

            # Gom file
            merged_file = os.path.join(TEMP_DIR, "HoSoLoiChiTiet.xlsx")
            files = glob.glob(os.path.join(TEMP_DIR, "err_*.xlsx")) + glob.glob(os.path.join(TEMP_DIR, "err_*.xls"))
            all_dfs = []
            for f in files:
                try:
                    if os.path.getsize(f) > 0:
                        df_item = pd.read_excel(f)
                        if not df_item.empty:
                            col_map = {}
                            for c in df_item.columns:
                                c_str = str(c).strip().upper()
                                if "MA_LK" in c_str or "MÃ LIÊN KẾT" in c_str or "MÃ LK" in c_str:
                                    col_map[c] = "MA_LK"
                                elif "MALOI" in c_str or "MÃ LỖI" in c_str:
                                    col_map[c] = "MALOI"
                                elif "MOTALOI" in c_str or "MÔ TẢ" in c_str or "NỘI DUNG LỖI" in c_str or "CHI TIẾT LỖI" in c_str:
                                    col_map[c] = "MOTALOI"
                                elif "NGAY_RA" in c_str or "NGÀY RA" in c_str:
                                    col_map[c] = "Ngày ra"
                            df_item = df_item.rename(columns=col_map)
                            all_dfs.append(df_item)
                except Exception as ef:
                    self.log(f"Lỗi đọc file con {os.path.basename(f)}: {ef}")

            if all_dfs:
                comb = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
                comb.to_excel(merged_file, index=False)
                self.log(f"Tổng hợp thành công {len(comb)} dòng lỗi chi tiết vào {merged_file} ✅")
            else:
                self.log("Không có gói lỗi nào được tải về trong khoảng ngày này.")
                pd.DataFrame(columns=["MA_LK", "MALOI", "MOTALOI", "Ngày ra", "Tên bệnh nhân", "Mã thẻ"]).to_excel(merged_file, index=False)

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
                self.last_status = {"status": "success", "flow": "C", "message": res_data.get('message', 'Thành công'), "error": None}
                self.log("=== ĐỐI SOÁT C HOÀN TẤT THÀNH CÔNG! ✅ ===")
                self.log(f"Kết quả: {res_data.get('message', 'Thành công')}")
                if not is_from_web:
                    messagebox.showinfo("Thành công", f"Đã hoàn thành Đối soát C trên máy chủ!\n{res_data.get('message', '')}")
            else:
                err_text = r_sync.text
                self.last_status = {"status": "error", "flow": "C", "message": f"Máy chủ trả về lỗi: {err_text}", "error": err_text}
                self.log(f"Lỗi đối soát: {err_text}")
                if not is_from_web:
                    messagebox.showerror("Lỗi đối soát", f"Máy chủ trả về lỗi: {err_text}")

        except Exception as e:
            self.last_status = {"status": "error", "flow": "C", "message": str(e), "error": str(e)}
            self.log(f"LỖI THỰC THI: {e}")
            if not is_from_web:
                messagebox.showerror("Lỗi", f"Lỗi Luồng C: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_flow_b.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_flow_c.configure(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientRPAGui(root)
    root.mainloop()
