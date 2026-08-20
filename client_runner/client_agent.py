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
    HTTP Server cục bộ lắng nghe tại 127.0.0.1:8765 cho phép WebApp trên trình duyệt
    tự động phát hiện và kích hoạt Chromium trực tiếp trên màn hình Máy trạm.
    """
    def log_message(self, format, *args):
        pass  # Tắt log stdout mặc định

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
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
            try:
                server = ThreadingHTTPServer(('127.0.0.1', 8765), ClientAgentHTTPHandler)
                server.serve_forever()
            except Exception as e:
                self.log(f"Lưu ý Local Bridge (Port 8765): {e}")

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
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(storage_state=storage_path, viewport={'width': 1366, 'height': 768}, accept_downloads=True)
                page = context.new_page()

                try:
                    self._ensure_login(page)
                    self._wait_portal_idle(page)

                    # Điều hướng trực tiếp
                    self.log("Đang mở Danh sách đề nghị thanh toán...")
                    try:
                        top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                        if top_menu.is_visible(timeout=3000):
                            top_menu.click()
                            time.sleep(0.5)
                    except Exception:
                        pass
                    page.get_by_role("link", name="Danh sách đề nghị thanh toán").click(timeout=15000)
                    page.wait_for_load_state("domcontentloaded")
                    self._wait_portal_idle(page)

                    # 3. Chọn Trạng thái: "Đã đề nghị thanh toán" qua DevExpress Client API
                    self.log("Đang chọn trạng thái: 'Đã đề nghị thanh toán' qua DevExpress API...")
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

                    # 4. Bấm Tìm kiếm qua DevExpress DoClick API & Đợi Callback
                    self.log("Bấm Tìm kiếm dữ liệu qua DevExpress API...")
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

                    # Chờ máy chủ Cổng BHYT phản hồi tìm kiếm xong qua DevExpress EndCallback
                    self.log("Đang chờ máy chủ Cổng BHYT nạp dữ liệu danh sách đề nghị thanh toán...")
                    self._wait_devexpress_callback(page, "bt_TimKiem", 45)
                    self._wait_portal_idle(page, timeout=45000)

                    # 5. Xuất Excel và tải file listbh.xlsx
                    self.log("Đang kích hoạt Xuất Excel danh sách đã gửi (hỗ trợ tối đa 5 phút)...")
                    
                    # Bước 5.1: Click nút cha "Xuất Excel" để mở menu
                    self.log("Click nút 'Xuất Excel' để mở menu lựa chọn...")
                    export_opened = False
                    try:
                        export_opened = page.evaluate("""() => {
                            try {
                                const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                                const btnXuat = window.bt_XuatExcel || (cc ? (cc.GetByName('bt_XuatExcel') || cc.GetByName('btnXuatExcel')) : null);
                                if (btnXuat && typeof btnXuat.DoClick === 'function') {
                                    btnXuat.DoClick();
                                    return true;
                                }
                            } catch(e) {}
                            return false;
                        }""")
                    except Exception: pass

                    if not export_opened:
                        for x_sel in ["#HeaderMenu span:has-text('Xuất Excel')", "#bt_XuatExcel_CD", "#bt_XuatExcel", ".dxbButton:has-text('Xuất Excel')", "td.dxb:has-text('Xuất Excel')", "span:has-text('Xuất Excel')"]:
                            try:
                                x_el = page.locator(x_sel).first
                                if x_el.is_visible(timeout=2000):
                                    x_el.click(force=True)
                                    export_opened = True
                                    break
                            except Exception: pass

                    time.sleep(0.8)

                    # Bước 5.2: Click vào mục con TRONG POPUP MENU để tải file listbh.xlsx
                    self.log("Đang click vào mục con 'Xuất excel' trong popup menu...")
                    with page.expect_download(timeout=300000) as dl_info:
                        clicked_sub = False
                        
                        # Cách 1: JavaScript tìm đúng phần tử trong popup container đang hiển thị
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

                        if not clicked_sub:
                            for p_sel in [".dxm-popup .dxm-item", ".dxm-popup table.dxm-item", "div[id*='_DXME'] span", ".dxm-shadow span"]:
                                try:
                                    p_items = page.locator(p_sel).filter(has_text=re.compile(r"Xuất excel", re.IGNORECASE))
                                    if p_items.count() > 0:
                                        p_items.first.click(force=True)
                                        clicked_sub = True
                                        break
                                except Exception: pass
                    self.log("Cổng BHYT đã tạo tệp Excel xong! Đang tải file về máy trạm...")
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
                self.last_status = {"status": "success", "flow": "B", "message": res_data.get('message', 'Thành công'), "error": None}
                self.log("=== ĐỐI SOÁT B HOÀN TẤT THÀNH CÔNG! ✅ ===")
                self.log(f"Kết quả: {res_data.get('message', 'Thành công')}")
                if not is_from_web:
                    messagebox.showinfo("Thành công", f"Đã hoàn thành Đối soát B trên máy chủ!\n{res_data.get('message', '')}")
            else:
                err_text = r_sync.text
                self.last_status = {"status": "error", "flow": "B", "message": f"Máy chủ trả về lỗi: {err_text}", "error": err_text}
                self.log(f"Lỗi đối soát: {err_text}")
                if not is_from_web:
                    messagebox.showerror("Lỗi đối soát", f"Máy chủ trả về lỗi: {err_text}")

        except Exception as e:
            self.last_status = {"status": "error", "flow": "B", "message": str(e), "error": str(e)}
            self.log(f"LỖI THỰC THI: {e}")
            if not is_from_web:
                messagebox.showerror("Lỗi", f"Lỗi Luồng B: {e}")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_flow_b.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_flow_c.configure(state=tk.NORMAL))

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
        self.last_status = {"status": "running", "flow": "C", "message": f"Đang chạy Luồng C (Từ {from_d} đến {to_d})...", "error": None}
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
                    self._wait_portal_idle(page)

                    # 4 bước điều hướng trực tiếp (Không hover)
                    self.log("Điều hướng: Hồ sơ ĐNTT > Hồ sơ XML > QĐ 3176 > Kết quả gửi XML...")
                    try:
                        top = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
                        if top.is_visible(timeout=3000): top.click()
                    except Exception: pass
                    time.sleep(0.6)

                    try:
                        xml_item = page.locator("span.dx-vam, a, div, span").filter(has_text="Hồ sơ XML").first
                        xml_item.click(force=True)
                    except Exception: pass
                    time.sleep(0.6)

                    try:
                        qd = page.locator("span.dx-vam, a, div, span").filter(has_text=re.compile(r"3176")).first
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
                    self._wait_portal_idle(page)

                    # 3. BƯỚC 1: ĐẶT NGÀY TODAY & TÌM KIẾM BẰNG DEVEXPRESS CLIENT API
                    self.log("Đang đặt khoảng ngày tìm kiếm = TODAY qua DevExpress API...")
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
                            self.log("Đã đặt Từ ngày và Đến ngày = Hôm nay qua DevExpress SetDate() API tức thì ✅")
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
                    self.log("Bấm Tìm kiếm dữ liệu qua DevExpress API...")
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
                    self.log("Đang chờ máy chủ Cổng BHYT phản hồi dữ liệu tìm kiếm (DevExpress EndCallback)...")
                    self._wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                    self._wait_portal_idle(page)

                    # 4. BƯỚC 2: CHỌN HIỂN THỊ 100 DÒNG / TRANG & CHỜ ENDCALLBACK
                    self.log("Thiết lập hiển thị 100 bản ghi/trang...")
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
                        
                        p_img = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom_DDBImg, #gvDSKetQuaGuiHoso_DXPagerBottom .dxp-dropDownButton").first
                        if p_img.is_visible(timeout=2000):
                            p_img.click()
                            time.sleep(0.3)
                            page.get_by_text("100", exact=True).click(timeout=2000)
                        
                        self._wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                        self._wait_portal_idle(page)
                        self.log("Đã nạp xong hiển thị 100 bản ghi/trang ✅")
                    except Exception as e:
                        self.log(f"Lưu ý chọn 100 dòng: {e}")

                    # 5. BƯỚC 3: NHẬN DIỆN CỘT LỖI & ÁP DỤNG BỘ LỌC 1 TRỰC TIẾP QUA DEVEXPRESS API
                    self.log("Đang áp dụng bộ lọc cột Lỗi = 1 qua DevExpress Client API...")
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
                    self.log(f"Kết quả kích hoạt lọc cột lỗi = 1: {filter_res.get('method', 'DOM fallback')} (Cột #{filter_res.get('colIdx', 5)}) ✅")

                    # Chờ bộ lọc áp dụng tức thì
                    self._wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 45)
                    self._wait_portal_idle(page)

                    # 6. BƯỚC 4: LẶP QUA CÁC TRANG VÀ TẢI TỪNG FILE CHI TIẾT
                    total_dl = 0
                    p_idx = 1
                    while True:
                        self.log(f"Đang quét danh sách hồ sơ lỗi tại Trang {p_idx}...")
                        self._wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 30)
                        self._wait_portal_idle(page)

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

                        self.log(f"Trang {p_idx}: Tìm thấy {len(rows_summary)} ca lỗi cần tải chi tiết.")

                        if len(rows_summary) == 0:
                            self.log("Không tìm thấy ca lỗi nào trên trang này.")
                            break

                        for idx, row_item in enumerate(rows_summary):
                            try:
                                self.log(f"[{total_dl + 1}/{total_dl + len(rows_summary) - idx}] Đang mở chi tiết ca lỗi dòng #{idx + 1}...")

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
                                exp_btn = page.locator("span, a, td, button").filter(has_text=re.compile(r"^Xuất Excel$", re.IGNORECASE)).first
                                if exp_btn.is_visible(timeout=6000):
                                    with page.expect_download(timeout=60000) as d_info:
                                        exp_btn.click(force=True)
                                    d = d_info.value
                                    t_path = os.path.join(TEMP_DIR, f"err_p{p_idx}_{idx+1}_{int(time.time()*1000)}.xlsx")
                                    d.save_as(t_path)
                                    total_dl += 1
                                    self.log(f"  -> Đã tải thành công tệp lỗi #{total_dl} ✅")
                                else:
                                    self.log(f"  -> Lưu ý: Không thấy nút 'Xuất Excel' trong popup dòng #{idx + 1}.")

                                # Đóng popup chi tiết lỗi tức thì qua DevExpress Hide() API
                                page.evaluate("""() => {
                                    try {
                                        const cc = window.ASPxClientControl ? window.ASPxClientControl.GetControlCollection() : null;
                                        const pop = window.PopupNhanChiTietLoiHS || (cc ? cc.GetByName('PopupNhanChiTietLoiHS') : null);
                                        if (pop && typeof pop.Hide === 'function') pop.Hide();
                                    } catch(e) {}
                                }""")
                                
                                for c_s in [".dxpc-closeBtn", "img[alt*='Close']", "img[title*='Close']", ".dxWeb_pcCloseButton_Youthful"]:
                                    ce = page.locator(c_s).first
                                    if ce.is_visible(timeout=500):
                                        ce.click(force=True)
                                        break
                                
                                time.sleep(0.4)

                            except Exception as re:
                                self.log(f"  Lỗi tải dòng #{idx+1}: {re}")
                                try:
                                    page.evaluate("""() => {
                                        if (window.PopupNhanChiTietLoiHS && typeof window.PopupNhanChiTietLoiHS.Hide === 'function') {
                                            window.PopupNhanChiTietLoiHS.Hide();
                                        }
                                    }""")
                                except Exception:
                                    pass

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
                                next_btn = page.locator("#gvDSKetQuaGuiHoso_DXPagerBottom .dxp-button:has-text('>')").first
                                if next_btn.is_visible(timeout=2000) and "dxp-disabled" not in (next_btn.get_attribute("class") or ""):
                                    next_btn.click()
                                    moved_next = True

                            if moved_next:
                                self.log(f"Chuyển sang trang tiếp theo (Trang {p_idx + 1})...")
                                p_idx += 1
                                self._wait_devexpress_callback(page, "gvDSKetQuaGuiHoso", 30)
                                self._wait_portal_idle(page)
                            else:
                                self.log("Đã duyệt hết tất cả các trang.")
                                break

                        except Exception:
                            self.log("Hoàn thành duyệt các trang.")
                            break

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
