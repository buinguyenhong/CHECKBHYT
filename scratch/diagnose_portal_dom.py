import os
import sys
import time
import json
import datetime
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SESSION_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app", "data", "portal_session.json"))
BASE_URL = "https://gdbhyt.baohiemxahoi.gov.vn"

def safe_print(msg):
    try:
        print(msg)
    except Exception:
        pass

def run_diagnosis():
    safe_print("=" * 70)
    safe_print("🔍 BẮT ĐẦU CHẨN ĐOÁN & QUÉT TOÀN BỘ CẤU TRÚC DOM TRỰC TIẾP TRÊN TRÌNH DUYỆT")
    safe_print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        context = browser.new_context(storage_state=storage_path, viewport={'width': 1400, 'height': 850})
        page = context.new_page()

        try:
            safe_print("[1] Đang truy cập Cổng BHYT...")
            page.goto(f"{BASE_URL}/", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Kiểm tra đăng nhập
            if "Login" in page.url or page.locator("#txtUserName, #txtMaCSKCB").count() > 0:
                safe_print("[!] Cần đăng nhập. Vui lòng đăng nhập trên cửa sổ trình duyệt đang mở...")
                # Chờ người dùng đăng nhập xong
                page.wait_for_selector("#HeaderMenu, #HeaderPane", timeout=120000)
                context.storage_state(path=SESSION_FILE)
                safe_print("[+] Đăng nhập thành công, đã lưu phiên!")

            safe_print("\n[2] QUÉT TOÀN BỘ MENU TRÊN HEADER (#HeaderMenu)...")
            menu_info = page.evaluate("""() => {
                const items = Array.from(document.querySelectorAll('#HeaderMenu .dxm-item, #HeaderMenu a, #HeaderMenu span, .dxm-popup .dxm-item'));
                return items.map(el => ({
                    id: el.id,
                    tag: el.tagName,
                    text: (el.textContent || '').trim().replace(/\\s+/g, ' '),
                    className: el.className
                })).filter(x => x.text.length > 0);
            }""")
            for m in menu_info[:15]:
                safe_print(f"  - [{m['tag']}] ID: {m['id']} | Text: '{m['text']}'")

            # ==========================================
            # KHẢO SÁT LUỒNG B (Danh sách đề nghị thanh toán)
            # ==========================================
            safe_print("\n" + "=" * 60)
            safe_print("🔍 KHẢO SÁT LUỒNG B: Điều hướng vào 'Danh sách đề nghị thanh toán'...")
            safe_print("=" * 60)
            
            # Click Top menu
            top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
            if top_menu.is_visible():
                top_menu.click()
                time.sleep(1)

            # Check submenus
            sub_items = page.evaluate("""() => {
                const popups = Array.from(document.querySelectorAll('.dxm-popup, div[id*="_DXME"], .dxm-shadow, .dxm-item'));
                return popups.filter(p => p.offsetParent !== null).map(p => ({
                    id: p.id,
                    text: (p.textContent || '').trim().replace(/\\s+/g, ' ')
                }));
            }""")
            safe_print(f"  -> Các popup menu đang mở: {len(sub_items)}")

            # Click link Danh sách đề nghị thanh toán
            ds_link = page.locator("a, span, .dxm-item").filter(has_text=re.compile(r"Danh sách đề nghị thanh toán", re.IGNORECASE)).first
            if ds_link.is_visible(timeout=5000):
                safe_print("  -> Tìm thấy liên kết 'Danh sách đề nghị thanh toán', đang click...")
                ds_link.click(force=True)
            else:
                safe_print("  -> Thử click qua JS evaluate...")
                page.evaluate("""() => {
                    const all = Array.from(document.querySelectorAll('a, span, td, div'));
                    const target = all.find(e => e.textContent && e.textContent.trim().includes('Danh sách đề nghị thanh toán'));
                    if (target) target.click();
                }""")

            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            safe_print(f"  -> URL hiện tại sau điều hướng Luồng B: {page.url}")

            # Quét các Controls DevExpress trên trang Luồng B
            ctrls_b = page.evaluate("""() => {
                const list = [];
                if (window.ASPxClientControl) {
                    const cc = window.ASPxClientControl.GetControlCollection();
                    if (cc && typeof cc.ForEachControl === 'function') {
                        cc.ForEachControl(c => {
                            if (c && c.name) {
                                list.push({
                                    name: c.name,
                                    type: c.constructor ? c.constructor.name : 'Unknown'
                                });
                            }
                        });
                    }
                }
                // Inputs & Buttons
                const inputs = Array.from(document.querySelectorAll('input, select, button, .dxbButton')).map(el => ({
                    id: el.id,
                    name: el.name,
                    tag: el.tagName,
                    text: (el.textContent || el.value || '').trim()
                }));
                return { devExpress: list, domInputs: inputs };
            }""")

            safe_print(f"  -> Danh sách DevExpress Controls trên trang Luồng B ({len(ctrls_b['devExpress'])} controls):")
            for c in ctrls_b['devExpress']:
                safe_print(f"     * {c['name']} ({c['type']})")

            safe_print(f"  -> Các input / button trên DOM ({len(ctrls_b['domInputs'])} items):")
            for inp in ctrls_b['domInputs'][:20]:
                if inp['id'] or inp['name']:
                    safe_print(f"     * [{inp['tag']}] ID: {inp['id']} | Name: {inp['name']} | Text/Val: {inp['text']}")

            # ==========================================
            # KHẢO SÁT LUỒNG C (Kết quả gửi hồ sơ XML)
            # ==========================================
            safe_print("\n" + "=" * 60)
            safe_print("🔍 KHẢO SÁT LUỒNG C: Điều hướng vào 'Kết quả gửi hồ sơ XML'...")
            safe_print("=" * 60)

            # Click top menu
            top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
            if top_menu.is_visible():
                top_menu.click()
                time.sleep(1)

            # Click Hồ sơ XML
            xml_item = page.locator("#HeaderMenu_DXME2_ div, #HeaderMenu div, .dxm-item, span").filter(has_text="Hồ sơ XML").first
            if xml_item.is_visible(timeout=3000):
                xml_item.click(force=True)
                time.sleep(0.8)

            # Click QĐ 3176
            qd_item = page.locator(".dxm-item, a, span").filter(has_text=re.compile(r"3176")).first
            if qd_item.is_visible(timeout=3000):
                qd_item.click(force=True)
                time.sleep(0.8)

            # Click Kết quả gửi hồ sơ XML
            page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a')).filter(a => a.textContent && a.textContent.includes('Kết quả gửi hồ sơ XML'));
                if (links.length > 1) links[1].click();
                else if (links.length === 1) links[0].click();
            }""")
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            safe_print(f"  -> URL hiện tại sau điều hướng Luồng C: {page.url}")

            # Quét toàn bộ DevExpress Controls & Date Controls trên Luồng C
            ctrls_c = page.evaluate("""() => {
                const devList = [];
                if (window.ASPxClientControl) {
                    const cc = window.ASPxClientControl.GetControlCollection();
                    if (cc && typeof cc.ForEachControl === 'function') {
                        cc.ForEachControl(c => {
                            if (c && c.name) {
                                devList.push({
                                    name: c.name,
                                    type: c.constructor ? c.constructor.name : 'Unknown',
                                    isDate: typeof c.GetDate === 'function',
                                    dateVal: typeof c.GetDate === 'function' ? String(c.GetDate()) : null
                                });
                            }
                        });
                    }
                }
                const inputs = Array.from(document.querySelectorAll('input')).map(el => ({
                    id: el.id,
                    name: el.name,
                    value: el.value,
                    className: el.className
                }));
                const buttons = Array.from(document.querySelectorAll('.dxbButton, button, td.dxb, a[id*="btn"], span[id*="btn"], input[type="submit"]')).map(el => ({
                    id: el.id,
                    text: (el.textContent || el.value || '').trim()
                }));
                return { devExpress: devList, inputs: inputs, buttons: buttons };
            }""")

            safe_print(f"\n  -> Chi tiết DevExpress Controls trên trang Luồng C ({len(ctrls_c['devExpress'])} controls):")
            for c in ctrls_c['devExpress']:
                if c['isDate'] or 'grid' in c['type'].lower() or 'btn' in c['name'].lower() or 'tu' in c['name'].lower() or 'den' in c['name'].lower():
                    safe_print(f"     * Control: '{c['name']}' | Type: {c['type']} | isDate: {c['isDate']} | CurrentDate: {c['dateVal']}")

            safe_print(f"\n  -> Các Input elements có trên trang Luồng C:")
            for inp in ctrls_c['inputs']:
                if 'tu' in inp['id'].lower() or 'den' in inp['id'].lower() or 'date' in inp['id'].lower() or 'ngay' in inp['id'].lower() or inp['value']:
                    safe_print(f"     * Input ID: '{inp['id']}' | Name: '{inp['name']}' | Value: '{inp['value']}'")

            safe_print(f"\n  -> Các Nút Bấm (Buttons) có trên trang Luồng C:")
            for btn in ctrls_c['buttons']:
                if btn['text'] or btn['id']:
                    safe_print(f"     * Button ID: '{btn['id']}' | Text: '{btn['text']}'")

            safe_print("\n[+] Đang giữ trình duyệt trong 15 giây để bạn quan sát trực tiếp...")
            time.sleep(15)

        except Exception as e:
            safe_print(f"[!] Lỗi trong quá trình chẩn đoán: {e}")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    import re
    run_diagnosis()
