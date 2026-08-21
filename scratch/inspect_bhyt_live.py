import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SESSION_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web_app", "browser_session", "portal_storage_state.json"))
OUTPUT_INSPECTION = os.path.abspath(os.path.join(os.path.dirname(__file__), "portal_dom_inspection.json"))
BASE_URL = "https://gdbhyt.baohiemxahoi.gov.vn"

def log(msg):
    print(f"[*] {msg}", flush=True)

def inspect_page_structure(page, page_name):
    log(f"\n--- ĐANG QUÉT CẤU TRÚC DOM TRANG: {page_name} ---")
    log(f"URL: {page.url}")
    
    info = page.evaluate("""() => {
        const res = {
            url: window.location.href,
            title: document.title,
            devExpressControls: [],
            inputs: [],
            buttons: [],
            tables: [],
            popups: []
        };

        // 1. DevExpress Client-Side Controls
        if (window.ASPxClientControl) {
            const cc = window.ASPxClientControl.GetControlCollection();
            if (cc && typeof cc.ForEachControl === 'function') {
                cc.ForEachControl(c => {
                    if (c && c.name) {
                        res.devExpressControls.push({
                            name: c.name,
                            type: c.constructor ? c.constructor.name : 'Unknown',
                            isDate: typeof c.GetDate === 'function',
                            currentDate: typeof c.GetDate === 'function' ? String(c.GetDate()) : null,
                            hasDoClick: typeof c.DoClick === 'function',
                            hasPerformCallback: typeof c.PerformCallback === 'function',
                            hasAutoFilterByColumn: typeof c.AutoFilterByColumn === 'function'
                        });
                    }
                });
            }
        }

        // 2. All Inputs
        const inps = Array.from(document.querySelectorAll('input, select, textarea'));
        res.inputs = inps.map(el => ({
            id: el.id,
            name: el.name,
            type: el.type || el.tagName.toLowerCase(),
            value: el.value,
            placeholder: el.placeholder,
            className: el.className,
            visible: el.offsetParent !== null
        })).filter(x => x.visible || x.id || x.name);

        // 3. All Buttons & Clickable DevExpress Items
        const btns = Array.from(document.querySelectorAll('.dxbButton, button, a.dxbButton, td.dxb, [id*="btn"], [id*="bt_"], input[type="submit"], input[type="button"]'));
        res.buttons = btns.map(el => ({
            id: el.id,
            tag: el.tagName,
            text: (el.textContent || el.value || '').trim().replace(/\\s+/g, ' '),
            className: el.className,
            visible: el.offsetParent !== null
        })).filter(x => x.text.length > 0 || x.id);

        // 4. Tables & GridViews
        const tbls = Array.from(document.querySelectorAll('table[id*="gv"], table.dxgvTable, table[id*="Grid"]'));
        res.tables = tbls.map(t => ({
            id: t.id,
            className: t.className,
            rowCount: t.querySelectorAll('tr').length
        }));

        // 5. Popups & Menus
        const pops = Array.from(document.querySelectorAll('.dxpc-mainDiv, .dxm-popup, div[id*="_PW-"], div[id*="_DXME"]'));
        res.popups = pops.map(p => ({
            id: p.id,
            className: p.className,
            visible: p.offsetParent !== null
        }));

        return res;
    }""")

    log(f"  + DevExpress Controls tìm thấy ({len(info['devExpressControls'])} controls):")
    for c in info['devExpressControls']:
        extra = []
        if c['isDate']: extra.append(f"DateEdit(val={c['currentDate']})")
        if c['hasDoClick']: extra.append("DoClick()")
        if c['hasPerformCallback']: extra.append("PerformCallback()")
        if c['hasAutoFilterByColumn']: extra.append("AutoFilterByColumn()")
        extra_str = f" [{', '.join(extra)}]" if extra else ""
        log(f"     * Control Name: '{c['name']}' | Type: {c['type']}{extra_str}")

    log(f"\n  + Inputs / Ô nhập liệu ({len(info['inputs'])} inputs):")
    for inp in info['inputs']:
        if inp['id'] or inp['name'] or inp['value']:
            log(f"     * Input ID: '{inp['id']}' | Name: '{inp['name']}' | Value: '{inp['value']}' | Visible: {inp['visible']}")

    log(f"\n  + Nút bấm / Actions ({len(info['buttons'])} buttons):")
    for b in info['buttons']:
        if b['visible'] and b['text']:
            log(f"     * Button ID: '{b['id']}' | Text: '{b['text']}'")

    log(f"\n  + Tables / GridViews ({len(info['tables'])} tables):")
    for t in info['tables']:
        log(f"     * Table ID: '{t['id']}' | Rows: {t['rowCount']}")

    return info

def main():
    log("=" * 70)
    log("🚀 KHỞI CHẠY TRÌNH DUYỆT CHROMIUM TRỰC TIẾP ĐỂ ĐỌC CẤU TRÚC TRANG BHYT")
    log("=" * 70)

    with sync_playwright() as p:
        storage_path = SESSION_FILE if os.path.exists(SESSION_FILE) else None
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=storage_path,
            viewport={'width': 1440, 'height': 900},
            accept_downloads=True
        )
        page = context.new_page()

        all_inspections = {}

        try:
            log("1. Đang truy cập Cổng BHYT...")
            page.goto(BASE_URL, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Kiểm tra đăng nhập
            is_login_needed = False
            try:
                has_logout = page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát')").is_visible(timeout=2000)
                has_login_btn = page.locator("a:has-text('Đăng nhập'), input[value='Đăng nhập'], input[name*='UserName']").is_visible(timeout=2000)
                if not has_logout or has_login_btn:
                    is_login_needed = True
            except Exception:
                is_login_needed = True

            if is_login_needed:
                log("👉 CẦN ĐĂNG NHẬP: Đang tự động điền tài khoản...")
                # Điền thông tin
                try:
                    ma_inp = page.locator("input[name*='MaCSKCB'], input[id*='txtMaCSKCB']").first
                    if ma_inp.is_visible(timeout=3000): ma_inp.fill("66232")
                    u_inp = page.locator("input[name*='UserName'], input[id*='txtUserName']").first
                    if u_inp.is_visible(timeout=3000): u_inp.fill("066091019320")
                    p_inp = page.locator("input[type='password'], input[name*='Password']").first
                    if p_inp.is_visible(timeout=3000): p_inp.fill("Nguyenhong123@")
                except Exception: pass

                log("⚠️ VUI LÒNG NHÌN MÀN HÌNH TRÌNH DUYỆT, NHẬP MÃ CAPTCHA VÀ BẤM ĐĂNG NHẬP (Chờ tối đa 10 phút)...")
                start_w = time.time()
                logged_in = False
                while time.time() - start_w < 600:
                    try:
                        if page.locator("a:has-text('Đăng xuất'), a:has-text('Thoát'), #btnLogout").is_visible():
                            logged_in = True
                            break
                        if page.locator("#HeaderMenu").is_visible() and not page.locator("input[name*='UserName']").is_visible():
                            logged_in = True
                            break
                    except Exception: pass
                    time.sleep(1)

                if logged_in:
                    log("✅ Đã đăng nhập thành công! Đang lưu phiên...")
                    context.storage_state(path=SESSION_FILE)
                    time.sleep(2)
                else:
                    raise Exception("Hết thời gian chờ đăng nhập.")

            # ========================================================
            # 2. KHẢO SÁT MENU & ĐIỀU HƯỚNG VÀO LUỒNG B
            # ========================================================
            log("\n" + "=" * 60)
            log("2. KHẢO SÁT LUỒNG B (Danh sách đề nghị thanh toán)")
            log("=" * 60)
            
            top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
            if top_menu.is_visible(timeout=3000):
                top_menu.click()
                time.sleep(0.6)

            xml_menu = page.locator("#HeaderMenu_DXME2_ div, #HeaderMenu div, .dxm-popup div, .dxm-item").filter(has_text="Hồ sơ XML").first
            if xml_menu.is_visible(timeout=3000):
                xml_menu.click()
                time.sleep(0.6)

            ds_link = page.locator("a, span, .dxm-item").filter(has_text="Danh sách đề nghị thanh toán").first
            if ds_link.is_visible(timeout=5000):
                ds_link.click(force=True)
            else:
                page.evaluate("""() => {
                    const all = Array.from(document.querySelectorAll('a, span, td, div, .dxm-item'));
                    const target = all.find(e => e.textContent && e.textContent.trim().includes('Danh sách đề nghị thanh toán'));
                    if (target) target.click();
                }""")

            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            all_inspections["Flow_B"] = inspect_page_structure(page, "Luồng B (Danh sách đề nghị thanh toán)")

            # ========================================================
            # 3. KHẢO SÁT MENU & ĐIỀU HƯỚNG VÀO LUỒNG C
            # ========================================================
            log("\n" + "=" * 60)
            log("3. KHẢO SÁT LUỒNG C (Kết quả gửi hồ sơ XML - QĐ 3176)")
            log("=" * 60)

            top_menu = page.locator("#HeaderMenu").get_by_text("Hồ sơ đề nghị thanh toán", exact=True)
            if top_menu.is_visible(timeout=3000):
                top_menu.click()
                time.sleep(0.6)

            xml_menu = page.locator("#HeaderMenu_DXME2_ div, #HeaderMenu div, .dxm-popup div, .dxm-item").filter(has_text="Hồ sơ XML").first
            if xml_menu.is_visible(timeout=3000):
                xml_menu.click()
                time.sleep(0.6)

            qd3176 = page.locator(".dxm-item, a, span").filter(has_text="3176").first
            if qd3176.is_visible(timeout=3000):
                qd3176.click(force=True)
                time.sleep(0.6)

            page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a')).filter(a => a.textContent && a.textContent.includes('Kết quả gửi hồ sơ XML'));
                if (links.length > 1) links[1].click();
                else if (links.length === 1) links[0].click();
            }""")

            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            all_inspections["Flow_C"] = inspect_page_structure(page, "Luồng C (Kết quả gửi hồ sơ XML)")

            # ========================================================
            # Lưu file kết quả chẩn đoán
            # ========================================================
            with open(OUTPUT_INSPECTION, "w", encoding="utf-8") as f:
                json.dump(all_inspections, f, ensure_ascii=False, indent=2)

            log("\n" + "=" * 70)
            log(f"🎉 ĐÃ HOÀN TẤT ĐỌC TOÀN BỘ CẤU TRÚC TRANG! Dữ liệu đã lưu vào: {OUTPUT_INSPECTION}")
            log("=" * 70)
            log("Trình duyệt sẽ mở trong 20 giây để bạn quan sát...")
            time.sleep(20)

        except Exception as e:
            log(f"❌ Lỗi khi đọc cấu trúc trang: {e}")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    main()
