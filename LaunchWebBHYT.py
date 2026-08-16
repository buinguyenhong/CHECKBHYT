import os
import sys
import json
import socket
import threading
import datetime
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

# Cấu hình lưu trữ
CONFIG_FILE = "launcher_config.json"

class BHYTLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("CheckBHYT LAN WebApp Launcher")
        self.root.geometry("620x720")
        self.root.resizable(False, False)
        
        # Thiết lập chủ đề màu sắc Glassmorphic Dark-Theme
        self.bg_color = "#0b1329"        # Deep Space Dark
        self.card_bg = "#1e293b"         # Sleek Slate Card
        self.text_main = "#f8fafc"       # White-blue
        self.text_sec = "#94a3b8"        # Slate text
        self.accent_blue = "#3b82f6"     # Vibrant blue
        self.accent_green = "#10b981"    # Premium Emerald
        self.accent_orange = "#f59e0b"   # Alert Orange
        self.accent_red = "#ef4444"      # Danger Red
        
        self.root.configure(bg=self.bg_color)
        
        # Biến điều khiển
        self.folder_path = tk.StringVar()
        self.port_val = tk.StringVar(value="8000")
        self.status_text = tk.StringVar(value="Đang kiểm tra...")
        self.status_color = self.accent_orange
        self.active_tab = "install"      # 'install' | 'sys'
        
        # Load cấu hình cũ
        self.load_config()
        
        # Tạo giao diện chính
        self.create_layouts()
        
        # Bắt đầu luồng kiểm tra trạng thái định kỳ
        self.stop_check_event = threading.Event()
        self.check_thread = threading.Thread(target=self.status_checking_loop, daemon=True)
        self.check_thread.start()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.folder_path.set(cfg.get("folder_path", ""))
                    self.port_val.set(cfg.get("port", "8000"))
            except Exception:
                pass
        
        if not self.folder_path.get():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(os.path.join(current_dir, "web_app")):
                self.folder_path.set(current_dir)

    def save_config(self):
        cfg = {
            "folder_path": self.folder_path.get(),
            "port": self.port_val.get()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def create_layouts(self):
        # 1. Header Title
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=30, pady=(20, 15))
        
        lbl_title = tk.Label(
            header_frame, 
            text="CheckBHYT LAN WebApp Launcher", 
            font=("Segoe UI", 18, "bold"), 
            bg=self.bg_color, 
            fg=self.accent_blue
        )
        lbl_title.pack(anchor=tk.W)
        
        lbl_sub = tk.Label(
            header_frame, 
            text="Công cụ cấu hình, cài đặt dependencies và quản lý server LAN chạy ngầm", 
            font=("Segoe UI", 9), 
            bg=self.bg_color, 
            fg=self.text_sec
        )
        lbl_sub.pack(anchor=tk.W, pady=3)

        # 2. Navigation Tabs Buttons
        tab_nav_frame = tk.Frame(self.root, bg=self.bg_color)
        tab_nav_frame.pack(fill=tk.X, padx=30, pady=(0, 15))
        
        self.btn_tab_install = tk.Button(
            tab_nav_frame, 
            text="1. Cài đặt lần đầu", 
            font=("Segoe UI", 9, "bold"),
            command=lambda: self.switch_tab("install"),
            bd=0,
            cursor="hand2"
        )
        self.btn_tab_install.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 4))
        
        self.btn_tab_sys = tk.Button(
            tab_nav_frame, 
            text="2. Thông tin hệ thống", 
            font=("Segoe UI", 9, "bold"),
            command=lambda: self.switch_tab("sys"),
            bd=0,
            cursor="hand2"
        )
        self.btn_tab_sys.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=4)

        self.btn_tab_autostart = tk.Button(
            tab_nav_frame, 
            text="3. Tự khởi động", 
            font=("Segoe UI", 9, "bold"),
            command=lambda: self.switch_tab("autostart"),
            bd=0,
            cursor="hand2"
        )
        self.btn_tab_autostart.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(4, 0))

        # 3. Tab Container (Card)
        self.card_container = tk.Frame(self.root, bg=self.card_bg, bd=1, relief=tk.FLAT)
        self.card_container.pack(fill=tk.BOTH, padx=30, expand=True, pady=(0, 20))

        # --- TAB 1 FRAME: INSTALLATION ---
        self.frame_install = tk.Frame(self.card_container, bg=self.card_bg)
        self.setup_install_tab()
        
        # --- TAB 2 FRAME: SYSTEM INFO & CONTROL ---
        self.frame_sys = tk.Frame(self.card_container, bg=self.card_bg)
        self.setup_sys_tab()

        # --- TAB 3 FRAME: AUTOSTART ---
        self.frame_autostart = tk.Frame(self.card_container, bg=self.card_bg)
        self.setup_autostart_tab()
        
        # Mặc định mở Tab 1
        self.switch_tab("install")

    def switch_tab(self, tab_name):
        self.active_tab = tab_name
        
        if tab_name == "install":
            self.btn_tab_install.configure(bg=self.accent_blue, fg=self.text_main, activebackground=self.accent_blue, activeforeground=self.text_main)
            self.btn_tab_sys.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.btn_tab_autostart.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.frame_install.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
            self.frame_sys.pack_forget()
            self.frame_autostart.pack_forget()
        elif tab_name == "sys":
            self.btn_tab_install.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.btn_tab_sys.configure(bg=self.accent_blue, fg=self.text_main, activebackground=self.accent_blue, activeforeground=self.text_main)
            self.btn_tab_autostart.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.frame_sys.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
            self.frame_install.pack_forget()
            self.frame_autostart.pack_forget()
        else: # autostart
            self.btn_tab_install.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.btn_tab_sys.configure(bg="#334155", fg=self.text_sec, activebackground="#334155", activeforeground=self.text_sec)
            self.btn_tab_autostart.configure(bg=self.accent_blue, fg=self.text_main, activebackground=self.accent_blue, activeforeground=self.text_main)
            self.frame_autostart.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
            self.frame_install.pack_forget()
            self.frame_sys.pack_forget()
            self.update_autostart_status()

    # ========================================================
    # TAB 1: CÀI ĐẶT LẦN ĐẦU (INSTALLATION)
    # ========================================================
    def setup_install_tab(self):
        # Description
        lbl_desc = tk.Label(
            self.frame_install, 
            text="💡 Các bước cài đặt cơ bản khi khởi động dự án lần đầu tiên:", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.card_bg, 
            fg=self.accent_orange
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 15))
        
        # Step 1: Select folder
        lbl_step1 = tk.Label(
            self.frame_install, 
            text="BƯỚC 1: CHỌN THƯ MỤC CHỨA WEBAPP (GIT CLONED FOLDER)", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_step1.pack(anchor=tk.W, pady=(0, 5))
        
        folder_select_frame = tk.Frame(self.frame_install, bg=self.card_bg)
        folder_select_frame.pack(fill=tk.X, pady=(0, 20))
        
        ent_folder = tk.Entry(
            folder_select_frame, 
            textvariable=self.folder_path, 
            font=("Segoe UI", 10), 
            bg="#0f172a", 
            fg=self.text_main, 
            insertbackground=self.text_main, 
            bd=1, 
            relief=tk.SOLID
        )
        ent_folder.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        
        btn_browse = tk.Button(
            folder_select_frame, 
            text="Chọn Folder", 
            command=self.browse_folder, 
            font=("Segoe UI", 9, "bold"), 
            bg="#334155", 
            fg=self.text_main, 
            activebackground="#475569", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        btn_browse.pack(side=tk.RIGHT, padx=(10, 0), ipady=5, ipadx=10)

        # Port selection
        lbl_port = tk.Label(
            self.frame_install, 
            text="CỔNG DỊCH VỤ DÀNH CHO MẠNG LAN BỆNH VIỆN (PORT)", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_port.pack(anchor=tk.W, pady=(0, 5))
        
        ent_port = tk.Entry(
            self.frame_install, 
            textvariable=self.port_val, 
            font=("Segoe UI", 11, "bold"), 
            bg="#0f172a", 
            fg="#60a5fa", 
            insertbackground=self.text_main, 
            bd=1, 
            relief=tk.SOLID, 
            width=12
        )
        ent_port.pack(anchor=tk.W, pady=(0, 20), ipady=6)
        
        # Step 2: Install requirements & Playwright
        lbl_step2 = tk.Label(
            self.frame_install, 
            text="BƯỚC 2: TỰ ĐỘNG CÀI ĐẶT THƯ VIỆN & TRÌNH DUYỆT RPA (DEPENDENCIES)", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_step2.pack(anchor=tk.W, pady=(0, 5))
        
        lbl_step2_sub = tk.Label(
            self.frame_install, 
            text="Hệ thống sẽ chạy ngầm lệnh 'pip install -r requirements.txt' và 'playwright install chromium' để tải tất cả thư viện backend và trình duyệt tự động hóa Cổng BHYT.", 
            font=("Segoe UI", 9), 
            bg=self.card_bg, 
            fg=self.text_sec,
            justify=tk.LEFT,
            wraplength=500
        )
        lbl_step2_sub.pack(anchor=tk.W, pady=(0, 12))
        
        btn_setup_frame = tk.Frame(self.frame_install, bg=self.card_bg)
        btn_setup_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_setup = tk.Button(
            btn_setup_frame, 
            text="Kích hoạt cài đặt thư viện & Chromium RPA", 
            command=self.run_setup_thread, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_blue, 
            fg=self.text_main, 
            activebackground="#2563eb", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_setup.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 6))

        self.btn_chromium = tk.Button(
            btn_setup_frame, 
            text="Cài riêng Chromium", 
            command=self.run_install_chromium_thread, 
            font=("Segoe UI", 9, "bold"), 
            bg="#334155", 
            fg=self.text_main, 
            activebackground="#475569", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_chromium.pack(side=tk.RIGHT, ipady=10, ipadx=8)

        # Khung chứa cửa sổ Log cài đặt
        log_frame = tk.Frame(self.frame_install, bg=self.card_bg)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(
            log_frame, 
            height=6, 
            bg="#0f172a", 
            fg=self.accent_green, 
            bd=1, 
            relief=tk.SOLID, 
            font=("Consolas", 9), 
            wrap=tk.WORD
        )
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.txt_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.configure(yscrollcommand=scrollbar.set)
        
        self.txt_log.insert(tk.END, ">>> Tiến trình cài đặt thư viện sẽ hiển thị trực tiếp tại đây...\n")
        self.txt_log.configure(state=tk.DISABLED)

    # ========================================================
    # TAB 2: THÔNG TIN HỆ THỐNG & ĐIỀU KHIỂN (SYSTEM INFO)
    # ========================================================
    def setup_sys_tab(self):
        # 1. Server Status Badge (Glow status)
        status_frame = tk.Frame(self.frame_sys, bg=self.card_bg)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        lbl_status_title = tk.Label(
            status_frame, 
            text="TRẠNG THÁI SERVER ONLINE:", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_status_title.pack(side=tk.LEFT)
        
        self.lbl_status_badge = tk.Label(
            status_frame, 
            textvariable=self.status_text, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.status_color
        )
        self.lbl_status_badge.pack(side=tk.LEFT, padx=10)
        
        # 3. Access Link Row
        link_frame = tk.Frame(self.frame_sys, bg=self.card_bg)
        link_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.btn_copy_link = tk.Button(
            link_frame, 
            text="Lấy Link & Copy địa chỉ LAN", 
            command=self.copy_lan_link, 
            font=("Segoe UI", 9, "bold"), 
            bg="#334155", 
            fg=self.text_main, 
            activebackground="#475569", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_copy_link.pack(side=tk.LEFT, ipady=6, ipadx=10)
        
        self.lbl_lan_address = tk.Label(
            link_frame, 
            text="Nhấp nút để lấy liên kết truy cập", 
            font=("Segoe UI", 10, "italic"), 
            bg=self.card_bg, 
            fg=self.accent_green
        )
        self.lbl_lan_address.pack(side=tk.LEFT, padx=15)
        
        # 4. Action buttons: Start & Stop Server
        btn_action_frame = tk.Frame(self.frame_sys, bg=self.card_bg)
        btn_action_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.btn_start = tk.Button(
            btn_action_frame, 
            text="Khởi động Server chạy ngầm", 
            command=self.start_server_background, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_green, 
            fg=self.text_main, 
            activebackground="#059669", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 5))
        
        self.btn_stop = tk.Button(
            btn_action_frame, 
            text="Dừng Server chạy ngầm", 
            command=self.stop_server_background, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_red, 
            fg=self.text_main, 
            activebackground="#dc2626", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(5, 0))

    # ========================================================
    # LOGIC XỬ LÝ (LOGIC OPERATIONS)
    # ========================================================
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn Thư mục chứa WebApp")
        if folder:
            self.folder_path.set(folder)
            self.save_config()

    def validate_inputs(self):
        folder = self.folder_path.get().strip()
        port = self.port_val.get().strip()
        
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Cảnh báo thư mục", "Vui lòng chọn thư mục dự án (Git cloned folder) hợp lệ!")
            return False
            
        if not os.path.exists(os.path.join(folder, "web_app", "run.py")):
            messagebox.showerror("Cảnh báo cấu trúc", "Không tìm thấy cấu trúc thư mục 'web_app/run.py' tại thư mục đã chọn!")
            return False
            
        if not port.isdigit() or not (1024 <= int(port) <= 65535):
            messagebox.showerror("Cảnh báo cổng", "Vui lòng nhập cổng dịch vụ hợp lệ (từ 1024 đến 65535)!")
            return False
            
        return True

    def run_setup_thread(self):
        if not self.validate_inputs():
            return
        self.btn_setup.configure(state=tk.DISABLED, text="Đang tải các thư viện & Chromium...")
        if hasattr(self, 'btn_chromium'):
            self.btn_chromium.configure(state=tk.DISABLED)
        threading.Thread(target=self.run_setup, daemon=True).start()

    def run_install_chromium_thread(self):
        if not self.validate_inputs():
            return
        self.btn_setup.configure(state=tk.DISABLED)
        if hasattr(self, 'btn_chromium'):
            self.btn_chromium.configure(state=tk.DISABLED, text="Đang tải Chromium...")
        threading.Thread(target=self.run_install_chromium, daemon=True).start()

    def append_log(self, text):
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.insert(tk.END, text)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)

    def run_setup(self):
        folder = self.folder_path.get().strip()
        try:
            self.root.after(0, lambda: self.txt_log.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.txt_log.delete("1.0", tk.END))
            self.root.after(0, lambda: self.txt_log.insert(tk.END, ">>> [1/2] Đang cài đặt thư viện phụ thuộc (pip install -r requirements.txt)...\n"))
            self.root.after(0, lambda: self.txt_log.configure(state=tk.DISABLED))

            # Bước 1: pip install -r requirements.txt
            cmd_pip = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            process_pip = subprocess.Popen(
                cmd_pip,
                cwd=folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            
            while True:
                line = process_pip.stdout.readline()
                if not line:
                    break
                self.root.after(0, lambda l=line: self.append_log(l))
                
            process_pip.wait()
            
            if process_pip.returncode != 0:
                self.root.after(0, lambda: self.append_log(f"\n>>> CÀI ĐẶT THƯ VIỆN THẤT BẠI! Mã lỗi: {process_pip.returncode} ❌\n"))
                messagebox.showerror("Lỗi cài đặt", f"Cài đặt thư viện thất bại, vui lòng kiểm tra kết nối mạng máy tính. Mã lỗi: {process_pip.returncode}")
                return

            # Bước 2: playwright install chromium
            self.root.after(0, lambda: self.append_log("\n>>> [2/2] Đang cài đặt trình duyệt tự động hóa Chromium (Playwright RPA)...\n"))
            cmd_pw = [sys.executable, "-m", "playwright", "install", "chromium"]
            process_pw = subprocess.Popen(
                cmd_pw,
                cwd=folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=0x08000000
            )

            while True:
                line = process_pw.stdout.readline()
                if not line:
                    break
                self.root.after(0, lambda l=line: self.append_log(l))

            process_pw.wait()

            if process_pw.returncode == 0:
                self.root.after(0, lambda: self.append_log("\n>>> CÀI ĐẶT THÀNH CÔNG TOÀN BỘ HỆ THỐNG & CHROMIUM RPA! ✅\n"))
                messagebox.showinfo("Thành công", "Cài đặt thành công toàn bộ thư viện dependencies & Chromium Playwright RPA!\nChuyển sang Tab 2 để khởi chạy Server.")
                self.root.after(0, lambda: self.switch_tab("sys"))
            else:
                self.root.after(0, lambda: self.append_log(f"\n>>> CÀI ĐẶT CHROMIUM CÓ CẢNH BÁO! Mã lỗi: {process_pw.returncode}\n"))
                messagebox.showwarning("Cảnh báo Chromium", "Đã cài xong thư viện Python nhưng cài đặt Chromium có cảnh báo. Bạn có thể bấm nút 'Cài riêng Chromium' để thử lại.")
                self.root.after(0, lambda: self.switch_tab("sys"))

        except Exception as e:
            self.root.after(0, lambda: self.append_log(f"\n>>> LỖI HỆ THỐNG: {e}\n"))
            messagebox.showerror("Lỗi hệ thống", f"Không thể kích hoạt bộ cài: {e}")
        finally:
            self.root.after(0, lambda: self.btn_setup.configure(state=tk.NORMAL, text="Kích hoạt cài đặt thư viện & Chromium RPA"))
            if hasattr(self, 'btn_chromium'):
                self.root.after(0, lambda: self.btn_chromium.configure(state=tk.NORMAL, text="Cài riêng Chromium"))

    def run_install_chromium(self):
        folder = self.folder_path.get().strip()
        try:
            self.root.after(0, lambda: self.txt_log.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.txt_log.delete("1.0", tk.END))
            self.root.after(0, lambda: self.txt_log.insert(tk.END, ">>> Đang tải và cài đặt trình duyệt Chromium cho Playwright RPA...\n"))
            self.root.after(0, lambda: self.txt_log.configure(state=tk.DISABLED))

            cmd_pw = [sys.executable, "-m", "playwright", "install", "chromium"]
            process_pw = subprocess.Popen(
                cmd_pw,
                cwd=folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=0x08000000
            )

            while True:
                line = process_pw.stdout.readline()
                if not line:
                    break
                self.root.after(0, lambda l=line: self.append_log(l))

            process_pw.wait()

            if process_pw.returncode == 0:
                self.root.after(0, lambda: self.append_log("\n>>> CÀI ĐẶT CHROMIUM THÀNH CÔNG! ✅\n"))
                messagebox.showinfo("Thành công", "Đã cài đặt thành công trình duyệt Chromium Playwright!")
            else:
                self.root.after(0, lambda: self.append_log(f"\n>>> CÀI ĐẶT CHROMIUM THẤT BẠI! Mã lỗi: {process_pw.returncode} ❌\n"))
                messagebox.showerror("Lỗi cài đặt", f"Không thể cài đặt Chromium. Mã lỗi: {process_pw.returncode}")
        except Exception as e:
            self.root.after(0, lambda: self.append_log(f"\n>>> LỖI HỆ THỐNG: {e}\n"))
            messagebox.showerror("Lỗi hệ thống", f"Lỗi thực thi: {e}")
        finally:
            self.root.after(0, lambda: self.btn_setup.configure(state=tk.NORMAL, text="Kích hoạt cài đặt thư viện & Chromium RPA"))
            if hasattr(self, 'btn_chromium'):
                self.root.after(0, lambda: self.btn_chromium.configure(state=tk.NORMAL, text="Cài riêng Chromium"))


    def start_server_background(self):
        if not self.validate_inputs():
            return
            
        folder = self.folder_path.get().strip()
        port = self.port_val.get().strip()
        
        self.save_config()
        
        # Kiểm tra trùng port
        if self.is_port_active(int(port)):
            res = messagebox.askyesno(
                "Cảnh báo trùng cổng", 
                f"Cổng {port} hiện đang bận (hoặc máy chủ cũ đang chạy).\nBạn có muốn dừng dịch vụ trên cổng {port} để khởi động máy chủ mới hay không?"
            )
            if res:
                self.stop_server_on_port_sync(int(port))
            else:
                return

        # Chạy máy chủ ngầm decoupled hoàn toàn
        try:
            run_script_path = os.path.join(folder, "web_app", "run.py")
            env = os.environ.copy()
            env["BHYT_PORT"] = str(port)
            env["BHYT_NO_RELOAD"] = "1"  # Khóa reload tối ưu hóa RAM chạy ngầm
            
            cmd = [sys.executable, run_script_path, "--port", str(port)]
            
            log_file_path = os.path.join(folder, "web_app_server.log")
            log_file = open(log_file_path, "a", encoding="utf-8")
            log_file.write(f"\n--- KHỞI ĐỘNG HỆ THỐNG: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            log_file.flush()

            # DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                cmd,
                cwd=folder,
                env=env,
                stdout=log_file,
                stderr=log_file,
                close_fds=False,  # Cần thiết khi redirect stdout/stderr trên Windows
                creationflags=0x00000008 | 0x08000000
            )
            
            messagebox.showinfo(
                "Khởi chạy thành công",
                f"CheckBHYT WebApp đã được khởi chạy thành công trong nền hệ thống Windows!\n"
                f"Dịch vụ chạy ngầm trên cổng: {port}\n\n"
                f"Bạn có thể đóng bảng điều khiển này, máy chủ LAN vẫn hoạt động ổn định."
            )
            
        except Exception as e:
            messagebox.showerror("Lỗi khởi chạy", f"Không thể khởi chạy dịch vụ ngầm: {e}")

    def stop_server_background(self):
        port = self.port_val.get().strip()
        if not port.isdigit():
            messagebox.showerror("Lỗi", "Vui lòng nhập cổng dịch vụ hợp lệ!")
            return
            
        count = self.stop_server_on_port_sync(int(port))
        if count > 0:
            messagebox.showinfo("Thành công", f"Đã giải phóng cổng {port} và dừng thành công {count} tiến trình chạy ngầm! ✅")
        else:
            messagebox.showinfo("Thông báo", f"Không có tiến trình nào đang chiếm dụng cổng {port}.")

    def stop_server_on_port_sync(self, port: int) -> int:
        try:
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            pids = set()
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
            
            killed = 0
            for pid in pids:
                if pid != '0' and pid.isdigit():
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, creationflags=0x08000000)
                    killed += 1
            return killed
        except Exception:
            return 0

    def copy_lan_link(self):
        port = self.port_val.get().strip()
        if not port.isdigit():
            port = "8000"
            
        # Tìm IP LAN thực tế
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
            
        link = f"http://{ip}:{port}"
        
        # Hiển thị lên giao diện
        self.lbl_lan_address.configure(text=link, font=("Segoe UI", 11, "bold"))
        
        # Copy vào clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        
        messagebox.showinfo(
            "Đã sao chép liên kết",
            f"Đã sao chép liên kết mạng nội bộ bệnh viện vào Clipboard:\n{link}\n\n"
            f"Bạn hãy gửi địa chỉ này cho các khoa lâm sàng lâm sàng để tiến hành nhập giải trình lỗi BHYT."
        )

    def is_port_active(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            return False

    def status_checking_loop(self):
        """
        Quét trạng thái cổng định kỳ mỗi 1.2 giây để cập nhật trực quan trên GUI
        """
        while not self.stop_check_event.is_set():
            port_str = self.port_val.get().strip()
            if port_str.isdigit():
                port = int(port_str)
                is_active = self.is_port_active(port)
                
                if is_active:
                    self.status_text.set("ĐANG HOẠT ĐỘNG (ACTIVE) ✅")
                    self.lbl_status_badge.configure(fg=self.accent_green)
                else:
                    self.status_text.set("ĐÃ DỪNG HOẠT ĐỘNG (STOPPED) ❌")
                    self.lbl_status_badge.configure(fg=self.accent_red)
            else:
                self.status_text.set("CỔNG KHÔNG HỢP LỆ")
                self.lbl_status_badge.configure(fg=self.accent_red)
                
            self.stop_check_event.wait(1.2)

    def setup_autostart_tab(self):
        lbl_desc = tk.Label(
            self.frame_autostart, 
            text="💡 Cấu hình tự động khởi động WebApp khi bật máy:", 
            font=("Segoe UI", 10, "bold"), 
            bg=self.card_bg, 
            fg=self.accent_orange
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 15))

        self.autostart_mode = tk.StringVar(value="boot")
        
        mode_frame = tk.LabelFrame(
            self.frame_autostart, 
            text="CHỌN CHẾ ĐỘ TỰ ĐỘNG CHẠY", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec,
            bd=1,
            relief=tk.GROOVE,
            padx=10,
            pady=10
        )
        mode_frame.pack(fill=tk.X, pady=(0, 20))

        r_boot = tk.Radiobutton(
            mode_frame, 
            text="Khởi động cùng Windows (Chạy ngầm ở background - Khuyên dùng cho Server)", 
            variable=self.autostart_mode, 
            value="boot",
            bg=self.card_bg, 
            fg=self.text_main,
            selectcolor=self.card_bg,
            activebackground=self.card_bg,
            activeforeground=self.text_main,
            font=("Segoe UI", 9)
        )
        r_boot.pack(anchor=tk.W, pady=5)

        r_logon = tk.Radiobutton(
            mode_frame, 
            text="Khởi động khi User đăng nhập (Phù hợp cho máy trạm/PC thường)", 
            variable=self.autostart_mode, 
            value="logon",
            bg=self.card_bg, 
            fg=self.text_main,
            selectcolor=self.card_bg,
            activebackground=self.card_bg,
            activeforeground=self.text_main,
            font=("Segoe UI", 9)
        )
        r_logon.pack(anchor=tk.W, pady=5)

        # Status Label
        status_row = tk.Frame(self.frame_autostart, bg=self.card_bg)
        status_row.pack(fill=tk.X, pady=(0, 20))

        lbl_status_title = tk.Label(
            status_row, 
            text="TRẠNG THÁI NHIỆM VỤ:", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_status_title.pack(side=tk.LEFT)

        self.autostart_status_text = tk.StringVar(value="Đang kiểm tra...")
        self.lbl_autostart_status = tk.Label(
            status_row, 
            textvariable=self.autostart_status_text, 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.accent_orange
        )
        self.lbl_autostart_status.pack(side=tk.LEFT, padx=10)

        # Buttons to register/unregister
        btn_action_frame = tk.Frame(self.frame_autostart, bg=self.card_bg)
        btn_action_frame.pack(fill=tk.X, pady=10)

        self.btn_reg_autostart = tk.Button(
            btn_action_frame, 
            text="Kích hoạt tự động chạy", 
            command=self.register_autostart, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_green, 
            fg=self.text_main, 
            activebackground="#059669", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_reg_autostart.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 5))

        self.btn_unreg_autostart = tk.Button(
            btn_action_frame, 
            text="Hủy tự động chạy", 
            command=self.unregister_autostart, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_red, 
            fg=self.text_main, 
            activebackground="#dc2626", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_unreg_autostart.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(5, 0))

    def update_autostart_status(self):
        try:
            cmd = ["schtasks", "/query", "/tn", "CheckBHYT_LAN_WebApp"]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode == 0:
                self.autostart_status_text.set("ĐÃ KÍCH HOẠT (ACTIVE) ✅")
                self.lbl_autostart_status.configure(fg=self.accent_green)
            else:
                self.autostart_status_text.set("CHƯA KÍCH HOẠT (INACTIVE) ❌")
                self.lbl_autostart_status.configure(fg=self.accent_red)
        except Exception:
            self.autostart_status_text.set("LỖI KIỂM TRA")
            self.lbl_autostart_status.configure(fg=self.accent_red)

    def register_autostart(self):
        if not self.validate_inputs():
            return
            
        folder = self.folder_path.get().strip()
        port = self.port_val.get().strip()
        
        # Locate pythonw.exe in the same folder as current python interpreter
        python_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(python_dir, "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = sys.executable
            
        run_script_path = os.path.join(folder, "web_app", "run.py")
        mode = self.autostart_mode.get()
        
        tr_command = f'"{pythonw_path}" "{run_script_path}" --port {port}'
        
        if mode == "boot":
            cmd = [
                "schtasks", "/create", 
                "/tn", "CheckBHYT_LAN_WebApp", 
                "/tr", tr_command, 
                "/sc", "onstart", 
                "/ru", "SYSTEM", 
                "/f"
            ]
        else:
            cmd = [
                "schtasks", "/create", 
                "/tn", "CheckBHYT_LAN_WebApp", 
                "/tr", tr_command, 
                "/sc", "onlogon", 
                "/f"
            ]
            
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode == 0:
                messagebox.showinfo("Thành công", "Đăng ký tác vụ tự khởi động cùng Windows thành công! ✅")
                self.update_autostart_status()
            else:
                error_msg = res.stderr or res.stdout or "Không rõ lỗi."
                if "Access is denied" in error_msg or "Từ chối truy cập" in error_msg or res.returncode == 5:
                    messagebox.showerror(
                        "Lỗi phân quyền", 
                        "Đăng ký khởi động cùng hệ thống cần quyền Administrator.\n\n"
                        "Vui lòng tắt ứng dụng này, sau đó click chuột phải vào file Launcher và chọn 'Run as administrator' để thực hiện lại!"
                    )
                else:
                    messagebox.showerror("Thất bại", f"Đăng ký thất bại: {error_msg}")
        except Exception as e:
            messagebox.showerror("Lỗi hệ thống", f"Không thể kích hoạt Task Scheduler: {e}")

    def unregister_autostart(self):
        cmd = ["schtasks", "/delete", "/tn", "CheckBHYT_LAN_WebApp", "/f"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode == 0:
                messagebox.showinfo("Thành công", "Đã xóa tác vụ tự khởi động cùng Windows thành công! ❌")
                self.update_autostart_status()
            else:
                error_msg = res.stderr or res.stdout or "Nhiệm vụ chưa đăng ký."
                messagebox.showinfo("Thông tin", f"Hủy đăng ký: {error_msg}")
                self.update_autostart_status()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa nhiệm vụ: {e}")

    def on_closing(self):
        self.stop_check_event.set()
        self.root.destroy()

if __name__ == "__main__":
    # Nâng cao độ sắc nét của Font chữ Tkinter trên màn hình Windows High-DPI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    root = tk.Tk()
    app = BHYTLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
