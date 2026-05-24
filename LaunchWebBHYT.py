import os
import sys
import json
import socket
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Cấu hình lưu trữ
CONFIG_FILE = "launcher_config.json"

class BHYTLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("CheckBHYT LAN WebApp Launcher")
        self.root.geometry("620x520")
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
        self.status_text = tk.StringVar(value="Đang quét...")
        self.status_color = self.accent_orange
        
        # Load cấu hình cũ nếu có
        self.load_config()
        
        # Tạo giao diện
        self.create_widgets()
        
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
        
        # Nếu chưa cấu hình, tự động nhận dạng thư mục hiện tại của Launcher làm mặc định
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

    def create_widgets(self):
        # 1. Header Title
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=30, pady=25)
        
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
            text="Công cụ quản trị, build và khởi chạy ngầm máy chủ đối soát mạng nội bộ", 
            font=("Segoe UI", 10), 
            bg=self.bg_color, 
            fg=self.text_sec
        )
        lbl_sub.pack(anchor=tk.W, pady=3)

        # 2. Main Config Card
        card_frame = tk.Frame(self.root, bg=self.card_bg, bd=1, relief=tk.FLAT)
        card_frame.pack(fill=tk.BOTH, padx=30, expand=True)
        
        # Thư mục Git
        lbl_folder = tk.Label(
            card_frame, 
            text="THƯ MỤC DỰ ÁN (GIT CLONED FOLDER)", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_folder.pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        folder_select_frame = tk.Frame(card_frame, bg=self.card_bg)
        folder_select_frame.pack(fill=tk.X, padx=20, pady=5)
        
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
            bg=self.accent_blue, 
            fg=self.text_main, 
            activebackground="#2563eb", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        btn_browse.pack(side=tk.RIGHT, padx=(10, 0), ipady=5, ipadx=10)

        # Port selection
        lbl_port = tk.Label(
            card_frame, 
            text="CỔNG DỊCH VỤ DÀNH CHO LAN (PORT)", 
            font=("Segoe UI", 9, "bold"), 
            bg=self.card_bg, 
            fg=self.text_sec
        )
        lbl_port.pack(anchor=tk.W, padx=20, pady=(15, 5))
        
        ent_port = tk.Entry(
            card_frame, 
            textvariable=self.port_val, 
            font=("Segoe UI", 11, "bold"), 
            bg="#0f172a", 
            fg="#60a5fa", 
            insertbackground=self.text_main, 
            bd=1, 
            relief=tk.SOLID, 
            width=10
        )
        ent_port.pack(anchor=tk.W, padx=20, pady=5, ipady=6)

        # Trạng thái máy chủ
        status_frame = tk.Frame(card_frame, bg=self.card_bg)
        status_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        lbl_status_title = tk.Label(
            status_frame, 
            text="TRẠNG THÁI SERVER DỰA TRÊN PORT:", 
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

        # 3. Action Buttons Section
        btn_frame = tk.Frame(self.root, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=30, pady=25)
        
        # Hàng 1: Build Cài đặt & Bắt đầu chạy ngầm
        self.btn_setup = tk.Button(
            btn_frame, 
            text="Cài đặt thư viện (pip setup)", 
            command=self.run_setup_thread, 
            font=("Segoe UI", 10, "bold"), 
            bg="#334155", 
            fg=self.text_main, 
            activebackground="#475569", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_setup.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10), ipady=10)
        
        self.btn_start = tk.Button(
            btn_frame, 
            text="Khởi chạy Server chạy ngầm", 
            command=self.start_server_background, 
            font=("Segoe UI", 10, "bold"), 
            bg=self.accent_green, 
            fg=self.text_main, 
            activebackground="#059669", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_start.grid(row=0, column=1, sticky="ew", pady=(0, 10), ipady=10)
        
        # Hàng 2: Kiểm tra IP & Dừng chạy ngầm
        self.btn_check_ip = tk.Button(
            btn_frame, 
            text="Lấy Link truy cập LAN", 
            command=self.get_lan_access_link, 
            font=("Segoe UI", 10, "bold"), 
            bg="#334155", 
            fg=self.text_main, 
            activebackground="#475569", 
            activeforeground="white", 
            bd=0, 
            cursor="hand2"
        )
        self.btn_check_ip.grid(row=1, column=0, sticky="ew", padx=(0, 10), ipady=10)
        
        self.btn_stop = tk.Button(
            btn_frame, 
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
        self.btn_stop.grid(row=1, column=1, sticky="ew", ipady=10)
        
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn Thư mục Git đã Clone")
        if folder:
            self.folder_path.set(folder)
            self.save_config()

    def validate_setup(self):
        folder = self.folder_path.get().strip()
        port = self.port_val.get().strip()
        
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục dự án (Git cloned folder) hợp lệ!")
            return False
            
        if not os.path.exists(os.path.join(folder, "web_app", "run.py")):
            messagebox.showerror("Lỗi", "Không tìm thấy cấu trúc thư mục 'web_app/run.py' tại thư mục đã chọn!")
            return False
            
        if not port.isdigit() or not (1024 <= int(port) <= 65535):
            messagebox.showerror("Lỗi", "Vui lòng nhập cổng dịch vụ hợp lệ (từ 1024 đến 65535)!")
            return False
            
        return True

    def run_setup_thread(self):
        if not self.validate_setup():
            return
            
        self.btn_setup.configure(state=tk.DISABLED, text="Đang cài đặt thư viện...")
        threading.Thread(target=self.run_setup, daemon=True).start()

    def run_setup(self):
        folder = self.folder_path.get().strip()
        req_path = os.path.join(folder, "requirements.txt")
        
        try:
            # Khởi chạy pip install trong tiến trình con
            cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            process = subprocess.Popen(
                cmd,
                cwd=folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            
            # Đọc logs nếu có (tùy chọn)
            process.wait()
            
            if process.returncode == 0:
                messagebox.showinfo("Thành công", "Đã cài đặt các thư viện dependencies thành công! Sẵn sàng khởi chạy máy chủ LAN.")
            else:
                messagebox.showerror("Thất bại", f"Lỗi trong quá trình cài đặt thư viện! Mã lỗi: {process.returncode}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kích hoạt trình cài đặt: {e}")
        finally:
            self.root.after(0, lambda: self.btn_setup.configure(state=tk.NORMAL, text="Cài đặt thư viện (pip setup)"))

    def start_server_background(self):
        if not self.validate_setup():
            return
            
        folder = self.folder_path.get().strip()
        port = self.port_val.get().strip()
        
        # 1. Lưu cấu hình
        self.save_config()
        
        # 2. Kiểm tra xem port có đang bị chiếm dụng không
        if self.is_port_active(int(port)):
            res = messagebox.askyesno(
                "Cảnh báo cổng dịch vụ", 
                f"Cổng {port} hiện đang hoạt động. Bạn có muốn DỪNG dịch vụ cũ để khởi chạy máy chủ mới hay không?"
            )
            if res:
                self.stop_server_background_sync(int(port))
            else:
                return

        # 3. Chạy Server dưới dạng DETACHED BACKGROUND PROCESS
        try:
            run_script_path = os.path.join(folder, "web_app", "run.py")
            
            # Chuẩn bị biến môi trường
            env = os.environ.copy()
            env["BHYT_PORT"] = str(port)
            env["BHYT_NO_RELOAD"] = "1"  # Tắt reload để chạy ngầm tối ưu nhất
            
            # Khởi chạy uvicorn nền
            cmd = [sys.executable, run_script_path, "--port", str(port)]
            
            # Windows creationflags: DETACHED_PROCESS = 0x00000008, CREATE_NO_WINDOW = 0x08000000
            # Giúp tiến trình chạy ngầm hoàn toàn độc lập và không tắt kể cả khi tắt Launcher GUI
            subprocess.Popen(
                cmd,
                cwd=folder,
                env=env,
                close_fds=True,
                creationflags=0x00000008 | 0x08000000
            )
            
            messagebox.showinfo(
                "Khởi chạy thành công",
                f"CheckBHYT WebApp đã được khởi chạy thành công trong nền hệ thống Windows!\n"
                f"Dịch vụ chạy ngầm trên cổng: {port}\n\n"
                f"Bạn có thể đóng Launcher này, máy chủ LAN vẫn sẽ tiếp tục hoạt động."
            )
            
        except Exception as e:
            messagebox.showerror("Lỗi khởi chạy", f"Không thể chạy tiến trình ngầm: {e}")

    def stop_server_background(self):
        port = self.port_val.get().strip()
        if not port.isdigit():
            messagebox.showerror("Lỗi", "Vui lòng nhập cổng dịch vụ hợp lệ!")
            return
            
        count = self.stop_server_background_sync(int(port))
        if count > 0:
            messagebox.showinfo("Thành công", f"Đã giải phóng cổng {port} và dừng thành công {count} tiến trình máy chủ chạy ngầm! ✅")
        else:
            messagebox.showinfo("Thông báo", f"Không tìm thấy tiến trình nào đang chiếm dụng cổng {port}.")

    def stop_server_background_sync(self, port: int) -> int:
        """
        Tìm kiếm tất cả PID chiếm dụng cổng port trên Windows bằng netstat và giải phóng chúng triệt để
        """
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

    def get_lan_access_link(self):
        port = self.port_val.get().strip()
        if not port.isdigit():
            port = "8000"
            
        # Quét IP LAN
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
            
        link = f"http://{ip}:{port}"
        
        # Sao chép vào clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(link)
        
        messagebox.showinfo(
            "Liên kết truy cập LAN BHYT",
            f"Địa chỉ IP máy chủ LAN của bạn:\n{link}\n\n"
            f"-> [ĐÃ SAO CHÉP LIÊN KẾT VÀO CLIPBOARD]\n\n"
            f"Bạn hãy gửi địa chỉ này cho các khoa lâm sàng để truy cập nhập ghi chú đối soát."
        )

    def is_port_active(self, port: int) -> bool:
        """
        Kiểm tra nhanh xem cổng có đang mở/hoạt động không
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            return False

    def status_checking_loop(self):
        """
        Quét trạng thái cổng định kỳ mỗi 1.5 giây để cập nhật trực quan trên GUI
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
                
            self.stop_check_event.wait(1.5)

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
