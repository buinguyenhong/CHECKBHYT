import os
import math
import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session
from models import Record

DEFAULT_WEBHOOK_URL = "https://tool.thienhanhhospital.com/webhook/bvth-bhyt-baocao"

def get_daily_error_summary_data(db: Session) -> Dict[str, Any]:
    """
    Tính toán báo cáo lỗi theo ngày (Phương án A: Toàn bộ lỗi tồn đọng sau đối soát).
    Thống kê theo từng khoa: Số ca lỗi (distinct ma_lk), Số lỗi (dòng lỗi), Số ca quá hạn > 7 ngày.
    """
    today = datetime.date.today()
    
    # Lấy toàn bộ hồ sơ nhóm LOI đang cần xử lý
    records = db.query(
        Record.ma_lk,
        Record.ten_khoa,
        Record.ngay_ra_vien,
        Record.ngay_doi_soat,
        Record.ngay_ra
    ).filter(
        Record.type_group == "LOI",
        Record.status != "RESOLVED"
    ).all()
    
    dept_map: Dict[str, Dict[str, Any]] = {}
    all_lks = set()
    all_overdue_lks = set()
    total_errors = len(records)
    
    for r_ma_lk, r_dept, r_nrv, r_nds, r_nr in records:
        dept = (r_dept or "").strip() or "Chưa phân khoa"
        if dept not in dept_map:
            dept_map[dept] = {
                "lks": set(),
                "total_errors": 0,
                "overdue_lks": set()
            }
        
        dept_map[dept]["total_errors"] += 1
        dept_map[dept]["lks"].add(r_ma_lk)
        all_lks.add(r_ma_lk)
        
        # Kiểm tra quá hạn: so sánh ngày ra viện với ngày hiện tại (> 7 ngày)
        d_val = r_nrv or r_nr or r_nds
        if d_val:
            if isinstance(d_val, datetime.datetime):
                d_val = d_val.date()
            if isinstance(d_val, datetime.date):
                if (today - d_val).days > 7:
                    dept_map[dept]["overdue_lks"].add(r_ma_lk)
                    all_overdue_lks.add(r_ma_lk)
                    
    dept_list = []
    max_cases = 1
    for dept, data in dept_map.items():
        c_count = len(data["lks"])
        if c_count > max_cases:
            max_cases = c_count
            
    for dept, data in dept_map.items():
        c_count = len(data["lks"])
        e_count = data["total_errors"]
        od_count = len(data["overdue_lks"])
        od_rate = round((od_count / c_count * 100), 1) if c_count > 0 else 0.0
        bar_pct = round((c_count / max_cases * 100), 1) if max_cases > 0 else 0.0
        
        dept_list.append({
            "ten_khoa": dept,
            "so_ca_loi": c_count,
            "so_loi": e_count,
            "so_ca_qua_han": od_count,
            "ty_le_qua_han": od_rate,
            "bar_pct": bar_pct
        })
        
    # Sắp xếp các khoa: Ưu tiên số ca quá hạn giảm dần (từ nhiều đến ít), tiếp theo là số ca lỗi, rồi số lỗi
    dept_list.sort(key=lambda x: (x["so_ca_qua_han"], x["so_ca_loi"], x["so_loi"]), reverse=True)
    
    total_cases = len(all_lks)
    total_overdue = len(all_overdue_lks)
    overdue_rate = round((total_overdue / total_cases * 100), 1) if total_cases > 0 else 0.0
    
    total_depts = len(dept_list)
    if total_depts <= 8:
        total_pages = 1
    else:
        total_pages = 1 + math.ceil((total_depts - 8) / 14)
    
    return {
        "report_date": today.strftime("%d/%m/%Y"),
        "report_time": datetime.datetime.now().strftime("%H:%M - %d/%m/%Y"),
        "total_cases": total_cases,
        "total_errors": total_errors,
        "total_overdue": total_overdue,
        "overdue_rate": overdue_rate,
        "total_pages": total_pages,
        "departments": dept_list
    }

def generate_daily_error_html(summary_data: Dict[str, Any], page: int = 1) -> str:
    """
    Sinh 1 file HTML hoàn chỉnh thiết kế cố định chuẩn iPhone 14 (rộng 390px, cao tối đa 844px).
    Không dùng JS, không file/font ngoài, CSS inline, không tràn, không bị cắt.
    Hỗ trợ phân trang:
    - Trang 1: 8 khoa đầu tiên (có nhiều ca quá hạn nhất) + 3 KPI Cards.
    - Trang 2 trở đi: tối đa 14 khoa/trang, mở rộng bảng hiển thị, không lặp lại 3 KPI Cards.
    """
    report_date = summary_data.get("report_date", "")
    report_time = summary_data.get("report_time", "")
    total_cases = summary_data.get("total_cases", 0)
    total_errors = summary_data.get("total_errors", 0)
    total_overdue = summary_data.get("total_overdue", 0)
    overdue_rate = summary_data.get("overdue_rate", 0.0)
    departments = summary_data.get("departments", [])
    total_depts = len(departments)
    
    if total_depts <= 8:
        total_pages = 1
    else:
        total_pages = 1 + math.ceil((total_depts - 8) / 14)
        
    page = max(1, min(page, total_pages))
    
    if page == 1:
        page_depts = departments[:8]
        start_idx = 1 if page_depts else 0
        end_idx = len(page_depts)
        is_first_page = True
    else:
        start_offset = 8 + (page - 2) * 14
        end_offset = start_offset + 14
        page_depts = departments[start_offset:end_offset]
        start_idx = start_offset + 1
        end_idx = start_offset + len(page_depts)
        is_first_page = False

    # Xây dựng các hàng HTML cho bảng khoa của trang này
    dept_rows_html = []
    for d in page_depts:
        dept_name = d["ten_khoa"]
        # Cắt ngắn tên khoa nếu quá dài để không bị rớt dòng
        short_name = dept_name if len(dept_name) <= 18 else dept_name[:17] + "…"
        bar_w = max(5, min(100, d["bar_pct"]))
        
        od_badge = f'<span class="badge-od">{d["so_ca_qua_han"]}</span>' if d["so_ca_qua_han"] > 0 else '<span class="text-muted">0</span>'
        
        row = f"""
        <tr>
            <td class="col-dept">
                <div class="dept-title" title="{dept_name}">{short_name}</div>
                <div class="progress-track"><div class="progress-fill" style="width:{bar_w}%;"></div></div>
            </td>
            <td class="col-num text-bold">{d["so_ca_loi"]}</td>
            <td class="col-num">{d["so_loi"]}</td>
            <td class="col-num">{od_badge}</td>
        </tr>
        """
        dept_rows_html.append(row)
        
    rows_joined = "".join(dept_rows_html) if dept_rows_html else """
        <tr><td colspan="4" style="text-align:center; padding:16px; color:#64748b; font-style:italic;">Không có hồ sơ lỗi tồn đọng. Xuất sắc! ✓</td></tr>
    """

    if is_first_page:
        top_section = f"""
        <div>
            <div class="header">
                <div class="org-name">Bệnh viện Đa khoa Thiện Hạnh</div>
                <div class="report-title">Phòng Công nghệ Thông tin</div>
                <div class="header-meta">
                    <span>Báo Cáo Giám Sát Hồ Sơ Lỗi BHYT</span>
                    <span class="date-pill">{report_date}</span>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-val">{total_cases}</div>
                    <div class="kpi-label">Ca Lỗi</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-val">{total_errors}</div>
                    <div class="kpi-label">Tổng Lỗi</div>
                </div>
                <div class="kpi-card alert">
                    <div class="kpi-val">{total_overdue}</div>
                    <div class="kpi-label">Quá Hạn &gt;7d</div>
                    <div class="kpi-sub">{overdue_rate}% ca</div>
                </div>
            </div>
        </div>
        """
        table_title_html = f"""
            <span>Chi tiết Lỗi theo Khoa (Top ca quá hạn)</span>
            <span style="font-size:10.5px; color:#64748b; font-weight:normal;">({end_idx}/{total_depts} khoa)</span>
        """
        table_card_class = "table-card"
    else:
        top_section = f"""
        <div>
            <div class="header" style="padding: 10px 14px; margin-bottom: 8px;">
                <div class="org-name">Bệnh viện Đa khoa Thiện Hạnh • Phòng CNTT</div>
                <div class="report-title" style="font-size: 14px;">Báo Cáo Giám Sát Lỗi BHYT (Tiếp theo)</div>
                <div class="header-meta" style="margin-top: 4px;">
                    <span>Danh sách khoa phòng lâm sàng</span>
                    <span class="date-pill">{report_date}</span>
                </div>
            </div>
        </div>
        """
        table_title_html = f"""
            <span>Chi tiết Lỗi theo Khoa (Khoa {start_idx} - {end_idx})</span>
            <span style="font-size:10.5px; color:#64748b; font-weight:normal;">({end_idx}/{total_depts} khoa)</span>
        """
        table_card_class = "table-card table-card-expanded"

    footer_page_info = f"Trang {page}/{total_pages}"

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=390, height=844, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Báo cáo BHYT - {report_date} - Trang {page}/{total_pages}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
    width: 390px;
    height: 844px;
    max-height: 844px;
    overflow: hidden;
    background: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.4;
    color: #0f172a;
    -webkit-font-smoothing: antialiased;
}}
.phone-container {{
    width: 390px;
    height: 844px;
    max-height: 844px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 14px 14px 12px 14px;
    overflow: hidden;
}}
.header {{
    background: linear-gradient(135deg, #1e3a8a 0%, #0284c7 100%);
    border-radius: 12px;
    padding: 11px 14px;
    color: #ffffff;
    box-shadow: 0 4px 10px rgba(2, 132, 199, 0.25);
    margin-bottom: 10px;
}}
.org-name {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #bae6fd;
    margin-bottom: 2px;
}}
.report-title {{
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -0.3px;
    color: #ffffff;
    line-height: 1.25;
}}
.header-meta {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
    font-size: 11px;
    color: #e0f2fe;
}}
.date-pill {{
    background: rgba(255, 255, 255, 0.2);
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
}}
.kpi-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1.15fr;
    gap: 8px;
    margin-bottom: 10px;
}}
.kpi-card {{
    background: #ffffff;
    border-radius: 10px;
    padding: 9px 8px;
    border: 1px solid #e2e8f0;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.kpi-card.alert {{
    background: #fff1f2;
    border-color: #fecdd3;
}}
.kpi-val {{
    font-size: 20px;
    font-weight: 800;
    color: #0284c7;
    line-height: 1.1;
    margin-bottom: 2px;
}}
.kpi-card.alert .kpi-val {{
    color: #e11d48;
}}
.kpi-label {{
    font-size: 10.5px;
    color: #64748b;
    font-weight: 600;
    text-transform: uppercase;
}}
.kpi-sub {{
    font-size: 9.5px;
    color: #e11d48;
    font-weight: 700;
    margin-top: 1px;
}}
.table-card {{
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    padding: 10px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    margin-bottom: 9px;
}}
.table-card-expanded {{
    margin-bottom: 9px;
}}
.table-title {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12.5px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #f1f5f9;
}}
.dept-table {{
    width: 100%;
    border-collapse: collapse;
}}
.dept-table th {{
    font-size: 10.5px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    padding: 3px 4px 6px 4px;
    border-bottom: 1px solid #cbd5e1;
}}
.dept-table td {{
    padding: 5px 4px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: middle;
}}
.col-dept {{
    text-align: left;
    width: 44%;
}}
.col-num {{
    text-align: right;
    width: 18%;
    font-size: 12px;
}}
.dept-title {{
    font-size: 12px;
    font-weight: 600;
    color: #1e293b;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.progress-track {{
    height: 3px;
    background: #e2e8f0;
    border-radius: 2px;
    margin-top: 2px;
    overflow: hidden;
}}
.progress-fill {{
    height: 3px;
    background: #0284c7;
    border-radius: 2px;
}}
.text-bold {{
    font-weight: 700;
    color: #0f172a;
}}
.text-muted {{
    color: #94a3b8;
    font-size: 11px;
}}
.badge-od {{
    display: inline-block;
    background: #ffe4e6;
    color: #e11d48;
    font-weight: 700;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 8px;
}}
.footer {{
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    padding: 8px 10px;
    font-size: 10px;
    color: #64748b;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.footer-note {{
    font-weight: 600;
    color: #b91c1c;
}}
.page-badge {{
    background: #e2e8f0;
    color: #334155;
    padding: 2px 7px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 9.5px;
}}
</style>
</head>
<body>
<div class="phone-container">
    {top_section}

    <div class="{table_card_class}">
        <div class="table-title">
            {table_title_html}
        </div>
        <table class="dept-table">
            <thead>
                <tr>
                    <th style="text-align:left;">Khoa / Phòng</th>
                    <th style="text-align:right;">Ca lỗi</th>
                    <th style="text-align:right;">Số lỗi</th>
                    <th style="text-align:right;">Quá hạn</th>
                </tr>
            </thead>
            <tbody>
                {rows_joined}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <span class="footer-note">⚠️ Đề nghị các khoa xử lý dứt điểm ca quá hạn</span>
        <span class="page-badge">{footer_page_info}</span>
    </div>
</div>
</body>
</html>"""
    return html.strip()

def generate_daily_error_excel(db: Session, upload_dir: str) -> str:
    """
    Xuất file Excel báo cáo lỗi theo ngày:
    Khoa - Số ca lỗi - Số lỗi - Số ca lỗi quá hạn (quá 7 ngày).
    """
    summary_data = get_daily_error_summary_data(db)
    today_str = datetime.date.today().strftime("%Y%m%d")
    filename = f"BAO_CAO_LOI_THEO_NGAY_{today_str}.xlsx"
    out_path = os.path.join(upload_dir, filename)
    
    departments = summary_data.get("departments", [])
    
    rows = []
    for idx, d in enumerate(departments, 1):
        rows.append({
            "STT": idx,
            "Khoa/Phòng": d["ten_khoa"],
            "Số ca lỗi": d["so_ca_loi"],
            "Tổng số lỗi": d["so_loi"],
            "Số ca quá hạn (> 7 ngày)": d["so_ca_qua_han"],
            "Tỷ lệ quá hạn (%)": f"{d['ty_le_qua_han']}%"
        })
        
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["STT", "Khoa/Phòng", "Số ca lỗi", "Tổng số lỗi", "Số ca quá hạn (> 7 ngày)", "Tỷ lệ quá hạn (%)"])
    else:
        # Dòng tổng cộng
        t_cases = summary_data.get("total_cases", 0)
        t_errors = summary_data.get("total_errors", 0)
        t_overdue = summary_data.get("total_overdue", 0)
        t_rate = summary_data.get("overdue_rate", 0.0)
        
        total_row = {
            "STT": "-",
            "Khoa/Phòng": "Tổng cộng toàn viện",
            "Số ca lỗi": t_cases,
            "Tổng số lỗi": t_errors,
            "Số ca quá hạn (> 7 ngày)": t_overdue,
            "Tỷ lệ quá hạn (%)": f"{t_rate}%"
        }
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Báo Cáo Lỗi Theo Ngày"
    
    # Header title
    rep_date = summary_data.get("report_date", "")
    ws.merge_cells("A1:F1")
    ws["A1"] = f"BÁO CÁO TỔNG HỢP LỖI BHYT THEO KHOA PHÒNG - NGÀY {rep_date}"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32
    
    # Metadata
    ws.merge_cells("A2:F2")
    ws["A2"] = f"Phòng Công nghệ Thông tin | Thời điểm xuất: {summary_data.get('report_time', '')}"
    ws["A2"].font = Font(name="Arial", size=10, italic=True, color="475569")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20
    
    # Table headers
    headers = ["STT", "Khoa/Phòng", "Số ca lỗi", "Tổng số lỗi", "Số ca quá hạn (> 7 ngày)", "Tỷ lệ quá hạn (%)"]
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    
    ws.row_dimensions[4].height = 26
    for c_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    # Write rows
    start_row = 5
    for r_idx, r_data in enumerate(df.to_dict(orient="records"), start_row):
        ws.row_dimensions[r_idx].height = 22
        is_total = (r_data["Khoa/Phòng"] == "Tổng cộng toàn viện")
        row_font = Font(name="Arial", size=10, bold=is_total, color="000000")
        row_fill = PatternFill(start_color="F1F5F9" if is_total else ("FFFFFF" if r_idx % 2 == 1 else "F8FAFC"), fill_type="solid")
        
        c1 = ws.cell(row=r_idx, column=1, value=r_data["STT"])
        c2 = ws.cell(row=r_idx, column=2, value=r_data["Khoa/Phòng"])
        c3 = ws.cell(row=r_idx, column=3, value=r_data["Số ca lỗi"])
        c4 = ws.cell(row=r_idx, column=4, value=r_data["Tổng số lỗi"])
        c5 = ws.cell(row=r_idx, column=5, value=r_data["Số ca quá hạn (> 7 ngày)"])
        c6 = ws.cell(row=r_idx, column=6, value=r_data["Tỷ lệ quá hạn (%)"])
        
        for c in (c1, c2, c3, c4, c5, c6):
            c.font = row_font
            c.fill = row_fill
            c.border = thin_border
            
        c1.alignment = Alignment(horizontal="center", vertical="center")
        c2.alignment = Alignment(horizontal="left", vertical="center")
        c3.alignment = Alignment(horizontal="right", vertical="center")
        c4.alignment = Alignment(horizontal="right", vertical="center")
        c5.alignment = Alignment(horizontal="right", vertical="center")
        c6.alignment = Alignment(horizontal="right", vertical="center")
        
        # Highlight ca quá hạn
        if not is_total and isinstance(r_data["Số ca quá hạn (> 7 ngày)"], (int, float)) and r_data["Số ca quá hạn (> 7 ngày)"] > 0:
            c5.font = Font(name="Arial", size=10, bold=True, color="B91C1C")
            c5.fill = PatternFill(start_color="FEE2E2", fill_type="solid")
            
    # Set column widths
    col_widths = {'A': 8, 'B': 30, 'C': 16, 'D': 16, 'E': 26, 'F': 20}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width
        
    wb.save(out_path)
    return out_path

def send_daily_error_webhook(
    html_content: Optional[str] = None,
    summary_data: Optional[Dict[str, Any]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL
) -> Dict[str, Any]:
    """
    Gửi Webhook POST tới n8n với body JSON chứa:
    - 'output': HTML trang 1
    - 'output_page_1': HTML trang 1 (top các khoa có ca quá hạn nhiều nhất)
    - 'output_page_2': HTML trang 2 (các khoa tiếp theo, nếu có)
    - 'total_pages': Tổng số trang (1 hoặc 2)
    - 'pages': Danh sách HTML từng trang
    Tự động ưu tiên httpx nếu có, hoặc fallback về urllib.request (thư viện chuẩn của Python)
    để đảm bảo không bao giờ bị lỗi ModuleNotFoundError khi khởi động hệ thống.
    """
    if summary_data is None:
        summary_data = {}
        
    total_pages = summary_data.get("total_pages", 1)
    
    page1_html = html_content or generate_daily_error_html(summary_data, page=1)
    page2_html = generate_daily_error_html(summary_data, page=2) if total_pages >= 2 else ""
    pages = [generate_daily_error_html(summary_data, page=p) for p in range(1, total_pages + 1)]

    payload = {
        "output": page1_html,
        "output_page_1": page1_html,
        "output_page_2": page2_html,
        "total_pages": total_pages,
        "pages": pages,
        "report_date": summary_data.get("report_date", ""),
        "total_cases": summary_data.get("total_cases", 0),
        "total_errors": summary_data.get("total_errors", 0),
        "overdue_cases": summary_data.get("total_overdue", 0),
        "overdue_rate": summary_data.get("overdue_rate", 0.0),
        "departments_count": len(summary_data.get("departments", []))
    }
    
    # Cách 1: Thử sử dụng httpx nếu môi trường đã cài
    try:
        import httpx
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(webhook_url, json=payload)
            return {
                "success": resp.status_code in [200, 201, 202, 204],
                "status_code": resp.status_code,
                "response_text": resp.text[:500]
            }
    except ImportError:
        pass
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error": str(e)
        }

    # Cách 2: Fallback urllib.request chuẩn tích hợp sẵn trong Python (không cần pip install)
    try:
        import urllib.request
        import urllib.error
        import json
        req_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=req_data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "CheckBHYT-Reporter/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15.0) as response:
            status_code = response.getcode()
            resp_body = response.read().decode("utf-8", errors="ignore")
            return {
                "success": status_code in [200, 201, 202, 204],
                "status_code": status_code,
                "response_text": resp_body[:500]
            }
    except urllib.error.HTTPError as he:
        err_body = ""
        try:
            err_body = he.read().decode("utf-8", errors="ignore")[:500]
        except Exception:
            pass
        return {
            "success": False,
            "status_code": he.code,
            "error": f"HTTP {he.code}: {he.reason} - {err_body}"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error": str(e)
        }

def export_department_performance_multi_sheet(db: Session, upload_dir: str) -> str:
    """
    Xuất file Excel báo cáo phân tích thực hiện sửa lỗi theo khoa phòng ban
    chia theo từng sheet theo tháng (giống Báo cáo tổng hợp), loại trừ ca FAIL ảo.
    """
    records = db.query(
        Record.ma_lk,
        Record.type_group,
        Record.status,
        Record.ten_khoa,
        Record.ngay_ra_vien,
        Record.ngay_doi_soat,
        Record.ngay_ra
    ).all()

    filename = "BAO_CAO_KHOA_PHONG_THEO_THANG.xlsx"
    out_path = os.path.join(upload_dir, filename)

    if not records:
        df_empty = pd.DataFrame(columns=[
            "STT", "Khoa/Phòng", 
            "Tổng số lỗi phát sinh", "Số lỗi đã xử lý", "Số lỗi chưa xử lý", "Tỷ lệ sửa lỗi (%)",
            "Tổng số ca FAIL", "Số ca FAIL đã xử lý", "Số ca FAIL chưa xử lý", "Tỷ lệ giải quyết FAIL (%)"
        ])
        df_empty.to_excel(out_path, index=False)
        return out_path

    data = []
    for r in records:
        date_val = r[4] or r[5] or r[6]
        month_str = date_val.strftime("%Y-%m") if date_val else "Không rõ"
        data.append({
            "ma_lk": r[0],
            "type_group": r[1],
            "status": r[2],
            "ten_khoa": r[3] or "Chưa phân khoa",
            "month": month_str
        })
    df_rec = pd.DataFrame(data)

    all_months = set(df_rec["month"].unique())
    all_months.discard("Không rõ")
    sorted_months = sorted(list(all_months), reverse=True)
    if not sorted_months:
        sorted_months = [datetime.date.today().strftime("%Y-%m")]

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for m in sorted_months:
            parts = m.split("-")
            sheet_name = f"Tháng {parts[1]}-{parts[0]}" if len(parts) == 2 else f"Tháng {m}"

            df_rec_m = df_rec[df_rec["month"] == m] if not df_rec.empty else pd.DataFrame()
            if df_rec_m.empty:
                continue

            # Tập hợp các ca lỗi trong tháng để loại trừ khỏi ca FAIL
            loi_lks_m = set(df_rec_m[df_rec_m["type_group"] == "LOI"]["ma_lk"].unique())

            grouped = df_rec_m.groupby("ten_khoa")

            report_data = []
            stt = 1
            for dept, group in grouped:
                # 1. Nhóm LỖI (LOI)
                df_err = group[group["type_group"] == "LOI"]
                tot_err = len(df_err)
                res_err = len(df_err[df_err["status"] == "RESOLVED"])
                unres_err = tot_err - res_err
                err_rate = f"{(res_err / tot_err * 100):.1f}%" if tot_err > 0 else "0.0%"

                # 2. Nhóm FAIL (chỉ lấy ca FAIL thực sự, loại trừ các ca có lỗi)
                df_fail = group[(group["type_group"] == "FAIL") & (~group["ma_lk"].isin(loi_lks_m))]
                fail_lks_dept = set(df_fail["ma_lk"].unique())
                tot_fail = len(fail_lks_dept)
                res_fail_lks_dept = set(df_fail[df_fail["status"] == "RESOLVED"]["ma_lk"].unique())
                res_fail = len(res_fail_lks_dept)
                unres_fail = tot_fail - res_fail
                fail_rate = f"{(res_fail / tot_fail * 100):.1f}%" if tot_fail > 0 else "0.0%"

                report_data.append({
                    "STT": stt,
                    "Khoa/Phòng": dept,
                    "Tổng số lỗi phát sinh": tot_err,
                    "Số lỗi đã xử lý": res_err,
                    "Số lỗi chưa xử lý": unres_err,
                    "Tỷ lệ sửa lỗi (%)": err_rate,
                    "Tổng số ca FAIL": tot_fail,
                    "Số ca FAIL đã xử lý": res_fail,
                    "Số ca FAIL chưa xử lý": unres_fail,
                    "Tỷ lệ giải quyết FAIL (%)": fail_rate,
                    "_tot_err": tot_err,
                    "_res_err": res_err,
                    "_unres_err": unres_err,
                    "_tot_fail": tot_fail,
                    "_res_fail": res_fail,
                    "_unres_fail": unres_fail
                })
                stt += 1

            df_sheet = pd.DataFrame(report_data)
            if not df_sheet.empty:
                df_sheet = df_sheet.sort_values(by="_tot_err", ascending=False)
                df_sheet["STT"] = range(1, len(df_sheet) + 1)

                t_err = int(df_sheet["_tot_err"].sum())
                t_res_err = int(df_sheet["_res_err"].sum())
                t_unres_err = int(df_sheet["_unres_err"].sum())
                t_err_rate = f"{(t_res_err / t_err * 100):.1f}%" if t_err > 0 else "0.0%"

                t_fail = int(df_sheet["_tot_fail"].sum())
                t_res_fail = int(df_sheet["_res_fail"].sum())
                t_unres_fail = int(df_sheet["_unres_fail"].sum())
                t_fail_rate = f"{(t_res_fail / t_fail * 100):.1f}%" if t_fail > 0 else "0.0%"

                cols_to_drop = ["_tot_err", "_res_err", "_unres_err", "_tot_fail", "_res_fail", "_unres_fail"]
                df_sheet = df_sheet.drop(columns=cols_to_drop)

                total_row = {
                    "STT": "-",
                    "Khoa/Phòng": "Tổng cộng toàn viện",
                    "Tổng số lỗi phát sinh": t_err,
                    "Số lỗi đã xử lý": t_res_err,
                    "Số lỗi chưa xử lý": t_unres_err,
                    "Tỷ lệ sửa lỗi (%)": t_err_rate,
                    "Tổng số ca FAIL": t_fail,
                    "Số ca FAIL đã xử lý": t_res_fail,
                    "Số ca FAIL chưa xử lý": t_unres_fail,
                    "Tỷ lệ giải quyết FAIL (%)": t_fail_rate
                }
                df_sheet = pd.concat([df_sheet, pd.DataFrame([total_row])], ignore_index=True)
            else:
                df_sheet = pd.DataFrame(columns=[
                    "STT", "Khoa/Phòng", 
                    "Tổng số lỗi phát sinh", "Số lỗi đã xử lý", "Số lỗi chưa xử lý", "Tỷ lệ sửa lỗi (%)",
                    "Tổng số ca FAIL", "Số ca FAIL đã xử lý", "Số ca FAIL chưa xử lý", "Tỷ lệ giải quyết FAIL (%)"
                ])

            # Ghi tiêu đề vào sheet
            title_df = pd.DataFrame([[f"BÁO CÁO HIỆU SUẤT XỬ LÝ LỖI THEO KHOA - THÁNG {parts[1]}/{parts[0]}"]], columns=["TITLE"])
            title_df.to_excel(writer, sheet_name=sheet_name, startrow=0, startcol=0, header=False, index=False)
            df_sheet.to_excel(writer, sheet_name=sheet_name, startrow=2, startcol=0, index=False)

            # Căn chỉnh độ rộng cột
            ws = writer.sheets[sheet_name]
            col_widths = {'A': 6, 'B': 26, 'C': 22, 'D': 18, 'E': 18, 'F': 16, 'G': 18, 'H': 18, 'I': 18, 'J': 22}
            for col, w in col_widths.items():
                ws.column_dimensions[col].width = w

    return out_path
