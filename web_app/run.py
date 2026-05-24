import sys
import os
import socket

# Hướng dẫn IT cài đặt nếu thiếu thư viện
try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import jinja2
    import pandas
except ImportError as e:
    print("❌ THIẾU THƯ VIỆN HOẶC PHỤ THUỘC!")
    print(f"Chi tiết lỗi: {e}")
    print("\nVui lòng thực hiện cài đặt các thư viện bằng lệnh dưới đây:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

def get_lan_ip():
    """
    Tự động quét và lấy địa chỉ IP LAN hiện tại của máy chủ host
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Không cần kết nối thật, chỉ lấy IP interface hoạt động
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        # Fallback về localhost nếu không có mạng
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    sys.path.insert(0, app_dir)
    
    lan_ip = get_lan_ip()
    port = 8000
    
    print("==================================================================")
    print("   HE THONG DOI SOAT BHYT MANG NOI BO (LAN WEBAPP) - BNH          ")
    print("==================================================================")
    print(f"[*] May chu dang khoi chay tai IP LAN: {lan_ip}")
    print(f"[*] Cac khoa lam sang truy cap qua dia chi:")
    print(f"    http://{lan_ip}:{port}")
    print("------------------------------------------------------------------")
    print("[*] Tai khoan admin mac dinh:")
    print("   - Username: admin")
    print("   - Password: adminBHYT2026")
    print("   (Vui long dang nhap bang quyen IT de cau hinh SQL HIS va tao tk)")
    print("==================================================================")
    print("Khoi dong may chu uvicorn...")
    
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
