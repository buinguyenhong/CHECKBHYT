import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add web_app to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from services.portal_automation import portal_service

def main():
    print("=" * 60)
    print("CHƯƠNG TRÌNH CHẠY THỬ TỰ ĐỘNG HÓA CỔNG BHYT (PLAYWRIGHT RPA)")
    print("=" * 60)
    print("1. Chạy thử Luồng B (Tự động tải danh sách đã gửi listbh.xlsx)")
    print("2. Chạy thử Luồng C (Tự động tải danh sách lỗi & gom HoSoLoiChiTiet.xlsx)")
    print("=" * 60)
    
    choice = input("Vui lòng chọn luồng muốn test (1 hoặc 2) [Mặc định: 1]: ").strip() or "1"
    from_date = input("Nhập Từ ngày (dd/mm/yyyy hoặc yyyy-mm-dd) [Mặc định: 01/08/2026]: ").strip() or "01/08/2026"
    to_date = input("Nhập Đến ngày (dd/mm/yyyy hoặc yyyy-mm-dd) [Mặc định: 16/08/2026]: ").strip() or "16/08/2026"

    if choice == "1":
        print(f"\n[+] Đang khởi chạy Luồng B với khoảng ngày: {from_date} -> {to_date}...")
        try:
            res = portal_service.run_flow_b(from_date, to_date)
            print("\n[✓] KẾT QUẢ LUỒNG B:")
            print(f"  - Trạng thái: {res.get('status')}")
            print(f"  - File đã tải: {res.get('file_path')}")
            print(f"  - Số dòng dữ liệu: {res.get('rows')}")
            print(f"  - Thông báo: {res.get('message')}")
        except Exception as e:
            print(f"\n[X] LỖI THỰC THI LUỒNG B: {e}")

    elif choice == "2":
        print(f"\n[+] Đang khởi chạy Luồng C với khoảng ngày: {from_date} -> {to_date}...")
        try:
            res = portal_service.run_flow_c(from_date, to_date)
            print("\n[✓] KẾT QUẢ LUỒNG C:")
            print(f"  - Trạng thái: {res.get('status')}")
            print(f"  - File đã tổng hợp: {res.get('file_path')}")
            print(f"  - Số gói lỗi đã tải: {res.get('downloaded_files')}")
            print(f"  - Tổng số dòng lỗi chi tiết: {res.get('total_errors')}")
            print(f"  - Thông báo: {res.get('message')}")
        except Exception as e:
            print(f"\n[X] LỖI THỰC THI LUỒNG C: {e}")
    else:
        print("[!] Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
