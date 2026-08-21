import os
import sys
import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app")))

from services.portal_automation import portal_service

def test_flow_b():
    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU TEST TRỰC TIẾP LUỒNG B (TẢI DS ĐÃ GỬI BHYT)")
    print("=" * 60)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    first_day_str = datetime.date.today().replace(day=1).strftime("%Y-%m-%d")
    try:
        res = portal_service.run_flow_b(first_day_str, today_str, log_func=lambda msg: print(f"  -> {msg}"))
        print("\n✅ KẾT QUẢ TEST LUỒNG B:")
        print(f"  - File đã tải: {res.get('file_path')}")
        print(f"  - Số dòng dữ liệu: {res.get('rows')}")
        print(f"  - Thông báo: {res.get('message')}")
        return True
    except Exception as e:
        print(f"\n❌ LỖI LUỒNG B: {e}")
        return False

def test_flow_c():
    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU TEST TRỰC TIẾP LUỒNG C (TẢI DS LỖI 3176)")
    print("=" * 60)
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    try:
        res = portal_service.run_flow_c(today_str, today_str, log_func=lambda msg: print(f"  -> {msg}"))
        print("\n✅ KẾT QUẢ TEST LUỒNG C:")
        print(f"  - File đã tổng hợp: {res.get('file_path')}")
        print(f"  - Số gói lỗi tải về: {res.get('downloaded_files')}")
        print(f"  - Tổng số lỗi: {res.get('total_errors')}")
        print(f"  - Thông báo: {res.get('message')}")
        return True
    except Exception as e:
        print(f"\n❌ LỖI LUỒNG C: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("\n" + "=" * 50)
        print("TÙY CHỌN CHẠY TEST TỰ ĐỘNG HÓA PLAYWRIGHT")
        print("  - B: Chạy Luồng B (Tải DS đã gửi listbh.xlsx)")
        print("  - C: Chạy Luồng C (Tải DS lỗi 3176)")
        print("  - ALL: Chạy cả 2 luồng")
        print("=" * 50)
        try:
            mode = input("Nhập luồng muốn chạy (B / C / ALL) [Mặc định: C]: ").strip() or "C"
        except Exception:
            mode = "C"

    if mode.upper() == "B":
        test_flow_b()
    elif mode.upper() == "C":
        test_flow_c()
    elif mode.upper() == "ALL":
        test_flow_b()
        test_flow_c()
    else:
        print(f"[!] Không nhận diện được tùy chọn '{mode}'. Mặc định chạy Luồng C:")
        test_flow_c()
