import sys
import os
import json
import shutil
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QTabWidget,
    QGroupBox, QFrame, QDateEdit, QComboBox, QLineEdit,
    QScrollArea
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QGuiApplication

# Clipboard: ưu tiên pyperclip; nếu thiếu thì fallback Qt clipboard
try:
    import pyperclip  # type: ignore
except Exception:
    pyperclip = None

try:
    import pyodbc
except Exception:
    pyodbc = None


# =========================
# Config
# =========================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "sql": {
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "",
        "database": "",
        "auth": "Windows Auth",   # Windows Auth | SQL Auth
        "user": "",
        "password": ""
    },
    "bh": {
        "listbh_key_col": "Mã liên kết",
        "listbh_date_col": "Ngày ra"
    }
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        out = json.loads(json.dumps(DEFAULT_CONFIG))
        out["sql"].update(cfg.get("sql", {}))
        out["bh"].update(cfg.get("bh", {}))
        return out
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# =========================
# Cache (SQL)
# =========================
CACHE_DIR = "cache_sql"
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, "index.json")


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_cache_index() -> dict:
    ensure_cache_dir()
    if not os.path.exists(CACHE_INDEX_FILE):
        return {}
    try:
        with open(CACHE_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def save_cache_index(index: dict):
    ensure_cache_dir()
    with open(CACHE_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def yyyymmdd_to_date(s: str):
    return datetime.strptime(s, "%Y%m%d").date()


def date_to_yyyymmdd(d) -> str:
    return d.strftime("%Y%m%d")


def next_day_yyyymmdd(s: str) -> str:
    d = yyyymmdd_to_date(s) + timedelta(days=1)
    return date_to_yyyymmdd(d)


def cache_file_for_start(tu: str) -> str:
    return os.path.join(CACHE_DIR, f"sql_list_{tu}.pkl")


def cache_get(tu: str) -> Optional[Tuple[str, pd.DataFrame]]:
    index = load_cache_index()
    if tu not in index:
        return None
    info = index.get(tu, {})
    cached_end = info.get("end")
    path = info.get("file")
    if not cached_end or not path or not os.path.exists(path):
        return None
    try:
        df = pd.read_pickle(path)
        if not isinstance(df, pd.DataFrame):
            return None
        return cached_end, df
    except Exception:
        return None


def cache_put(tu: str, den: str, df: pd.DataFrame):
    ensure_cache_dir()
    index = load_cache_index()
    path = cache_file_for_start(tu)
    df.to_pickle(path)
    index[tu] = {"end": den, "file": path}
    save_cache_index(index)


def cache_clear_all():
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR, ignore_errors=True)


# =========================
# UI Style (đồng nhất dark: menu/scrollbar/popup)
# =========================
APP_QSS = """
/* Base */
QMainWindow { background: #0b1220; }
QWidget { color: #e2e8f0; font-size: 15px; font-family: Segoe UI; }
QScrollArea { background: #0b1220; border: none; }
QScrollArea > QWidget > QWidget { background: #0b1220; }

/* GroupBox */
QGroupBox {
  border: 1px solid #334155;
  border-radius: 12px;
  margin-top: 12px;
  padding: 12px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 12px;
  padding: 0 8px;
  color: #cbd5e1;
  font-weight: 900;
  font-size: 16px;
}

/* Buttons */
QPushButton {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 11px 14px;
  font-weight: 900;
  font-size: 15px;
}
QPushButton:hover { background: #273449; }
QPushButton:pressed { background: #0b1220; }
QPushButton:disabled { color: #64748b; background: #0f172a; border-color: #1f2937; }

/* Inputs */
QLineEdit, QComboBox, QDateEdit {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 15px;
}

/* Combo dropdown popup */
QComboBox QAbstractItemView {
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  selection-background-color: #1e293b;
  selection-color: #e2e8f0;
  outline: 0;
}

/* Tabs */
QTabWidget::pane {
  border: 1px solid #334155;
  border-radius: 12px;
  top: -1px;
  background: #0f172a;
}
QTabBar::tab {
  background: #111827;
  border: 1px solid #334155;
  padding: 12px 16px;
  margin-right: 4px;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  font-weight: 900;
  font-size: 15px;
  color: #e2e8f0;
}
QTabBar::tab:selected {
  background: #0f172a;
  border-bottom-color: #0f172a;
}
QTabBar::tab:disabled { color: #64748b; }

/* Tables */
QTableWidget {
  background: #0f172a;
  gridline-color: #1f2937;
  border: 1px solid #334155;
  border-radius: 12px;
  font-size: 14px;
}
QHeaderView::section {
  background: #111827;
  border: 1px solid #334155;
  padding: 10px;
  font-weight: 900;
  font-size: 14px;
}

/* Labels */
QLabel#titleBig { font-size: 20px; font-weight: 900; color: #e2e8f0; }
QLabel#hint { color:#94a3b8; font-size: 14px; }
QLabel#kpiTitle { color: #94a3b8; font-weight: 900; font-size: 14px; }
QLabel#kpiValue { color: #e2e8f0; font-size: 22px; font-weight: 900; }
QFrame#divider { background: #1f2937; max-height: 1px; min-height: 1px; }

/* MenuBar + Menu */
QMenuBar {
  background: #0f172a;
  color: #e2e8f0;
  border-bottom: 1px solid #334155;
  padding: 6px;
}
QMenuBar::item {
  background: transparent;
  padding: 6px 12px;
  border-radius: 8px;
}
QMenuBar::item:selected { background: #1e293b; }
QMenu {
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 6px;
}
QMenu::item {
  padding: 8px 14px;
  border-radius: 8px;
}
QMenu::item:selected { background: #1e293b; }
QMenu::separator {
  height: 1px;
  background: #1f2937;
  margin: 6px 8px;
}

/* Scrollbars */
QScrollBar:vertical {
  background: #0b1220;
  width: 12px;
  margin: 0px;
}
QScrollBar::handle:vertical {
  background: #334155;
  min-height: 30px;
  border-radius: 6px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
  background: #0b1220;
  height: 12px;
  margin: 0px;
}
QScrollBar::handle:horizontal {
  background: #334155;
  min-width: 30px;
  border-radius: 6px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

/* Tooltip */
QToolTip {
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  padding: 6px;
}
"""


# =========================
# Helpers UI
# =========================
def thong_bao(parent, title: str, msg: str):
    QMessageBox.information(parent, title, msg)


def canh_bao(parent, title: str, msg: str):
    QMessageBox.warning(parent, title, msg)


def loi(parent, title: str, msg: str):
    QMessageBox.critical(parent, title, msg)


def xac_nhan(parent, title: str, msg: str) -> bool:
    return QMessageBox.question(
        parent, title, msg,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    ) == QMessageBox.Yes


def df_to_table(table: QTableWidget, df: pd.DataFrame):
    table.setSortingEnabled(False)
    table.clear()
    table.setRowCount(len(df))
    table.setColumnCount(len(df.columns))
    table.setHorizontalHeaderLabels(list(df.columns))

    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = "" if pd.isna(df.iloc[r, c]) else str(df.iloc[r, c])
            item = QTableWidgetItem(val)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, c, item)

    table.setSortingEnabled(True)
    table.resizeColumnsToContents()


# =========================
# Business rules
# =========================
def chuan_hoa_ma_lk(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return ""
    s = str(value).strip()
    s = s.replace("_CC", "/CC")
    return s


def remove_leading_A(value) -> str:
    s = chuan_hoa_ma_lk(value)
    if s.startswith("A"):
        return s[1:].strip()
    return s


def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def parse_datetime_to_date(series: pd.Series) -> pd.Series:
    import datetime as dt_module
    def parse_single(val):
        if pd.isna(val) or val is None:
            return None
        if isinstance(val, (dt_module.date, dt_module.datetime)):
            if isinstance(val, dt_module.datetime):
                return val.date()
            return val
        val_str = str(val).strip()
        if not val_str:
            return None
        try:
            # Nếu bắt đầu bằng 4 chữ số năm (ví dụ: 202606050823 hoặc 2026-06-01)
            if len(val_str) >= 4 and val_str[:4].isdigit():
                ts = pd.to_datetime(val_str, errors="coerce", dayfirst=False)
            else:
                ts = pd.to_datetime(val_str, errors="coerce", dayfirst=True)
            if pd.isna(ts):
                return None
            return ts.date()
        except Exception:
            return None
    return series.apply(parse_single)


# =========================
# listbh processing
# =========================
def load_listbh(path: str, key_col: str, date_col: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    if key_col not in df.columns:
        raise ValueError(f"listbh thiếu cột '{key_col}'")
    df[key_col] = df[key_col].apply(chuan_hoa_ma_lk)

    if date_col not in df.columns and "Ngày ra" in df.columns:
        date_col = "Ngày ra"

    if date_col in df.columns:
        df["_ngay"] = parse_datetime_to_date(df[date_col])
    else:
        df["_ngay"] = pd.NaT

    out = df[[key_col, "_ngay"]].copy()
    out = out.rename(columns={key_col: "MA_LK"})
    return out


def filter_listbh_by_date(df: pd.DataFrame, tu_ngay, den_ngay) -> pd.DataFrame:
    if df.empty:
        return df
    if "_ngay" not in df.columns:
        return df
    mask = (df["_ngay"] >= tu_ngay) & (df["_ngay"] <= den_ngay)
    return df.loc[mask].copy()


# =========================
# SQL helpers
# =========================
def build_conn_str(driver: str, server: str, db: str, auth: str, user: str, pw: str) -> str:
    if auth == "Windows Auth":
        return f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};Trusted_Connection=yes;"
    return f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};UID={user};PWD={pw};"


def get_conn(cfg: dict):
    if pyodbc is None:
        raise RuntimeError("Chưa cài pyodbc. Cài: pip install pyodbc")
    sql = cfg["sql"]
    if not sql["server"] or not sql["database"]:
        raise RuntimeError("Thiếu Server hoặc Database.")
    if sql["auth"] == "SQL Auth" and not sql["user"]:
        raise RuntimeError("SQL Auth cần User.")
    conn_str = build_conn_str(sql["driver"], sql["server"], sql["database"], sql["auth"], sql["user"], sql["password"])
    return pyodbc.connect(conn_str, timeout=25)


def sql_exec_sp(conn, sp_name: str, tu: str, den: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(f"SET NOCOUNT ON; EXEC {sp_name} @TuNgay=?, @DenNgay=?", (tu, den))

    while cur.description is None:
        has_next = cur.nextset()
        if not has_next:
            return pd.DataFrame()

    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return pd.DataFrame.from_records(rows, columns=cols)


def run_update_sql(conn, sql_text: str) -> int:
    cur = conn.cursor()
    cur.execute("SET NOCOUNT ON;")
    cur.execute(sql_text)
    try:
        rc = cur.rowcount
    except Exception:
        rc = -1
    conn.commit()
    return rc


# =========================
# Normalize sql_list (✅ có Ngày ra viện từ cột NgayRa)
# =========================
def normalize_sql_list(df_op: pd.DataFrame, df_ip: pd.DataFrame) -> pd.DataFrame:
    req_op = ["TenBenhNhan", "SoBHYT", "Column4", "SoPhieuThanhToanNgoaiTru", "NgayRa"]
    req_ip = ["TenBenhNhan", "SoBHYT", "SoPhieu_BA", "khoadieutri", "NgayRa"]

    for c in req_op:
        if c not in df_op.columns:
            raise ValueError(f"SP Ngoại trú thiếu cột '{c}'. Hiện có: {list(df_op.columns)}")
    for c in req_ip:
        if c not in df_ip.columns:
            raise ValueError(f"SP Nội trú thiếu cột '{c}'. Hiện có: {list(df_ip.columns)}")

    op = pd.DataFrame()
    op["Loại ca"] = "Ngoại trú"
    op["MA_LK"] = df_op["Column4"].apply(chuan_hoa_ma_lk)
    op["Họ tên"] = df_op["TenBenhNhan"].fillna("")
    op["Mã thẻ"] = df_op["SoBHYT"].fillna("")
    op["Tên khoa"] = "Khám bệnh"
    op["Mã y tế"] = df_op["SoPhieuThanhToanNgoaiTru"].fillna("")
    op["Ngày ra viện"] = parse_datetime_to_date(df_op["NgayRa"])

    ip = pd.DataFrame()
    ip["Loại ca"] = "Nội trú"
    ip["MA_LK"] = df_ip["SoPhieu_BA"].apply(remove_leading_A)
    ip["Họ tên"] = df_ip["TenBenhNhan"].fillna("")
    ip["Mã thẻ"] = df_ip["SoBHYT"].fillna("")
    ip["Tên khoa"] = df_ip["khoadieutri"].fillna("")
    ip["Mã y tế"] = ""
    ip["Ngày ra viện"] = parse_datetime_to_date(df_ip["NgayRa"])

    out = pd.concat([op, ip], ignore_index=True)
    out = out[out["MA_LK"].astype(str).str.len() > 0]
    out["MA_LK"] = out["MA_LK"].apply(chuan_hoa_ma_lk)
    out = out.drop_duplicates(subset=["MA_LK"], keep="first")

    return out[["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện"]].copy()


# =========================
# Reset SQL generator
# =========================
def build_reset_sql(keys: List[str], loai: str) -> str:
    keys = [chuan_hoa_ma_lk(k) for k in keys if chuan_hoa_ma_lk(k)]
    keys = unique_keep_order(keys)
    if not keys:
        return "-- Không có mã nào để reset."

    quoted = ",\n    ".join([f"'{k}'" for k in keys])

    if loai == "Ngoại trú":
        return f"""UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM TiepNhan tn
JOIN XacNhanChiPhi xn ON xn.TiepNhan_Id = tn.TiepNhan_Id
WHERE tn.SoTiepNhan IN (
    {quoted}
);
"""
    return f"""UPDATE xn
SET Export=0, Export1=0, Export_CV130=0
FROM BenhAn ba
JOIN XacNhanChiPhi xn ON xn.BenhAn_Id = ba.BenhAn_Id
WHERE ba.SoBenhAn IN (
    {quoted}
);
"""


# =========================
# Error file processing
# =========================
def load_hosoloichitiet(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    if "MA_LK" not in df.columns:
        raise ValueError("HoSoLoiChiTiet.xlsx phải có cột 'MA_LK'")
    if "MALOI" not in df.columns:
        df["MALOI"] = ""
    if "MOTALOI" not in df.columns:
        df["MOTALOI"] = ""

    df["MA_LK"] = df["MA_LK"].apply(chuan_hoa_ma_lk)

    if "Ngày ra" in df.columns:
        df["Ngày ra"] = parse_datetime_to_date(df["Ngày ra"])

    out_cols = ["MA_LK", "MALOI", "MOTALOI"]
    if "Ngày ra" in df.columns:
        out_cols.append("Ngày ra")

    return df[out_cols].copy()


def merge_error_with_sql(hsloi: pd.DataFrame, sql_list: pd.DataFrame) -> pd.DataFrame:
    base = sql_list[["MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện"]].copy()
    merged = hsloi.merge(base, on="MA_LK", how="left")
    merged["MA_LK"] = merged["MA_LK"].astype(str).apply(chuan_hoa_ma_lk)

    merged = merged.drop_duplicates(keep="first")

    cols = ["MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện", "MALOI", "MOTALOI"]
    if "Ngày ra" in merged.columns:
        cols.insert(cols.index("MALOI"), "Ngày ra")
    cols = [c for c in cols if c in merged.columns]
    return merged[cols].copy()


# =========================
# KPI
# =========================
@dataclass
class KPI:
    tong_sql: int = 0
    tong_bh: int = 0
    da_gui: int = 0
    fail: int = 0


# =========================
# Main Window
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiểm tra gửi BHYT (SQL + File) — BNH")

        # Fit theo màn hình (tránh mất phần dưới ở 1366x768)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1600, screen.width()), min(950, screen.height()))

        self.cfg = load_config()

        # Data
        self.df_listbh_all = pd.DataFrame()
        self.df_listbh_filtered = pd.DataFrame()
        self.df_sql_list = pd.DataFrame()
        self.df_compare = pd.DataFrame()
        self.df_fail = pd.DataFrame()

        self.df_hsloi = pd.DataFrame()
        self.df_loi_merged = pd.DataFrame()

        # ===== Scrollable container
        container = QWidget()
        main = QVBoxLayout(container)
        main.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(container)
        self.setCentralWidget(scroll)

        # ===== Header
        header = QHBoxLayout()
        title = QLabel("KIỂM TRA GỬI BHYT — SQL (LAN) + FILE (listbh / lỗi)")
        title.setObjectName("titleBig")
        header.addWidget(title)
        header.addStretch()
        main.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.HLine)
        main.addWidget(div)

        # ===== Top panels
        top = QGridLayout()
        top.setColumnStretch(0, 2)
        top.setColumnStretch(1, 1)
        main.addLayout(top)

        # ===== Workflow panel
        self.gb_flow = QGroupBox("Quy trình thao tác")
        flow = QVBoxLayout(self.gb_flow)
        flow.setSpacing(10)

        row1 = QHBoxLayout()
        self.btn_add_listbh = QPushButton("1) Thêm file danh sách đã gửi BHYT")
        self.btn_add_listbh.clicked.connect(self.on_add_listbh)
        row1.addWidget(self.btn_add_listbh)
        flow.addLayout(row1)

        row2 = QHBoxLayout()
        self.de_from = QDateEdit()
        self.de_to = QDateEdit()
        self.de_from.setCalendarPopup(True)
        self.de_to.setCalendarPopup(True)
        today = QDate.currentDate()
        self.de_from.setDate(today)
        self.de_to.setDate(today)
        self.btn_filter_bh = QPushButton("2) Lọc list bh theo ngày")
        self.btn_filter_bh.clicked.connect(self.on_filter_bh)
        row2.addWidget(QLabel("Từ ngày"))
        row2.addWidget(self.de_from)
        row2.addWidget(QLabel("Đến ngày"))
        row2.addWidget(self.de_to)
        row2.addWidget(self.btn_filter_bh)
        flow.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_compare = QPushButton("3) So sánh dữ liệu database và BHYT")
        self.btn_compare.clicked.connect(self.on_compare)
        self.cmb_view = QComboBox()
        self.cmb_view.addItems(["Chỉ hiện FAIL", "Hiện tất cả"])
        self.cmb_view.currentIndexChanged.connect(self.refresh_compare_table)
        row3.addWidget(self.btn_compare)
        row3.addWidget(self.cmb_view)
        flow.addLayout(row3)

        row4 = QHBoxLayout()
        self.btn_copy_op = QPushButton("4) Copy SQL reset Ngoại trú")
        self.btn_copy_ip = QPushButton("4) Copy SQL reset Nội trú")
        self.btn_run_op = QPushButton("4b) CHẠY reset Ngoại trú")
        self.btn_run_ip = QPushButton("4b) CHẠY reset Nội trú")
        self.btn_copy_op.clicked.connect(lambda: self.copy_reset("Ngoại trú"))
        self.btn_copy_ip.clicked.connect(lambda: self.copy_reset("Nội trú"))
        self.btn_run_op.clicked.connect(lambda: self.run_reset("Ngoại trú"))
        self.btn_run_ip.clicked.connect(lambda: self.run_reset("Nội trú"))
        row4.addWidget(self.btn_copy_op)
        row4.addWidget(self.btn_copy_ip)
        row4.addWidget(self.btn_run_op)
        row4.addWidget(self.btn_run_ip)
        flow.addLayout(row4)

        row5 = QHBoxLayout()
        self.btn_add_loi = QPushButton("5) Thêm HoSoLoiChiTiet.xlsx (file lỗi)")
        self.btn_add_loi.clicked.connect(self.on_add_loi)
        self.btn_merge_loi = QPushButton("6) Ghép lỗi + bỏ trùng hoàn toàn")
        self.btn_merge_loi.clicked.connect(self.on_merge_loi)
        row5.addWidget(self.btn_add_loi)
        row5.addWidget(self.btn_merge_loi)
        flow.addLayout(row5)

        row6 = QHBoxLayout()
        self.btn_export_sql = QPushButton("Xuất Excel dữ liệu database")
        self.btn_export_fail = QPushButton("Xuất Excel: DANH_SACH_FAIL.xlsx")
        self.btn_export_loi = QPushButton("Xuất Excel: DANH_SACH_KEM_LOI.xlsx")
        self.btn_export_sql.clicked.connect(self.export_sql_list)
        self.btn_export_fail.clicked.connect(self.export_fail)
        self.btn_export_loi.clicked.connect(self.export_loi)
        row6.addWidget(self.btn_export_sql)
        row6.addWidget(self.btn_export_fail)
        row6.addWidget(self.btn_export_loi)
        flow.addLayout(row6)

        self.lb_status = QLabel("Sẵn sàng.")
        self.lb_status.setObjectName("hint")
        flow.addWidget(self.lb_status)

        top.addWidget(self.gb_flow, 0, 0)

        # ===== KPI panel
        self.gb_kpi = QGroupBox("Tổng quan")
        k = QGridLayout(self.gb_kpi)

        def kpi_card(title_text: str):
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(12, 10, 12, 10)
            t = QLabel(title_text)
            t.setObjectName("kpiTitle")
            val = QLabel("0")
            val.setObjectName("kpiValue")
            v.addWidget(t)
            v.addWidget(val)
            w.setStyleSheet("background:#0f172a; border:1px solid #334155; border-radius:12px;")
            return w, val

        c1, self.k_sql = kpi_card("Tổng ca SQL")
        c2, self.k_bh = kpi_card("Tổng ca BH (lọc)")
        c3, self.k_sent = kpi_card("Đã gửi BH")
        c4, self.k_fail = kpi_card("FAIL")

        k.addWidget(c1, 0, 0)
        k.addWidget(c2, 0, 1)
        k.addWidget(c3, 1, 0)
        k.addWidget(c4, 1, 1)

        top.addWidget(self.gb_kpi, 0, 1)

        # ===== Tabs
        self.tabs = QTabWidget()
        main.addWidget(self.tabs)

        self.tab_sql = QWidget()
        self.tabs.addTab(self.tab_sql, "SQL (LAN) — Kết nối & xuất sql_list")
        self.build_tab_sql()

        self.tbl_sql = QTableWidget()
        self.tbl_bh = QTableWidget()
        self.tbl_compare = QTableWidget()
        self.tbl_loi = QTableWidget()

        self.tabs.addTab(self.tbl_sql, "sql_list")
        self.tabs.addTab(self.tbl_bh, "listbh (lọc)")
        self.tabs.addTab(self.tbl_compare, "So sánh")
        self.tabs.addTab(self.tbl_loi, "Ghép lỗi")

        self.update_buttons()
        self.set_kpi(KPI())

    # ---------------- SQL TAB ----------------
    def build_tab_sql(self):
        layout = QVBoxLayout(self.tab_sql)
        layout.setSpacing(12)

        if pyodbc is None:
            warn = QLabel("Thiếu pyodbc. Cài: pip install pyodbc")
            warn.setStyleSheet("color:#fca5a5; font-weight:900;")
            layout.addWidget(warn)

        gb = QGroupBox("Kết nối SQL Server (LAN)")
        g = QGridLayout(gb)

        self.cmb_driver = QComboBox()
        self.cmb_driver.addItems(["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"])
        self.ed_server = QLineEdit()
        self.ed_db = QLineEdit()
        self.cmb_auth = QComboBox()
        self.cmb_auth.addItems(["Windows Auth", "SQL Auth"])
        self.ed_user = QLineEdit()
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.Password)

        self.sql_from = QDateEdit()
        self.sql_to = QDateEdit()
        self.sql_from.setCalendarPopup(True)
        self.sql_to.setCalendarPopup(True)
        today = QDate.currentDate()
        self.sql_from.setDate(today)
        self.sql_to.setDate(today)

        self.ed_sp_op = QLineEdit("dbo.sp_BCVP_095_DsDeNghiThanhToanBHYT_NgoaiTru_25a_CV5937")
        self.ed_sp_ip = QLineEdit("dbo.sp_BCVP_096_DsDeNghiThanhToanBHYT_NoiTru_26A_CV5937")

        self.btn_save_cfg = QPushButton("Lưu cấu hình")
        self.btn_save_cfg.clicked.connect(self.on_save_config)
        self.btn_test_conn = QPushButton("Test kết nối")
        self.btn_test_conn.clicked.connect(self.on_test_connection)
        self.btn_run_sp = QPushButton("Chạy SP → Tạo sql_list (có cache)")
        self.btn_run_sp.clicked.connect(self.on_run_sp)

        self.btn_clear_cache = QPushButton("Clear cache SQL")
        self.btn_clear_cache.clicked.connect(self.on_clear_cache)

        r = 0
        g.addWidget(QLabel("Driver"), r, 0)
        g.addWidget(self.cmb_driver, r, 1)
        g.addWidget(QLabel("Server"), r, 2)
        g.addWidget(self.ed_server, r, 3)
        r += 1

        g.addWidget(QLabel("Database"), r, 0)
        g.addWidget(self.ed_db, r, 1)
        g.addWidget(QLabel("Xác thực"), r, 2)
        g.addWidget(self.cmb_auth, r, 3)
        r += 1

        g.addWidget(QLabel("User (SQL Auth)"), r, 0)
        g.addWidget(self.ed_user, r, 1)
        g.addWidget(QLabel("Password"), r, 2)
        g.addWidget(self.ed_pass, r, 3)
        r += 1

        g.addWidget(QLabel("Từ ngày"), r, 0)
        g.addWidget(self.sql_from, r, 1)
        g.addWidget(QLabel("Đến ngày"), r, 2)
        g.addWidget(self.sql_to, r, 3)
        r += 1

        g.addWidget(QLabel("SP Ngoại trú"), r, 0)
        g.addWidget(self.ed_sp_op, r, 1, 1, 3)
        r += 1

        g.addWidget(QLabel("SP Nội trú"), r, 0)
        g.addWidget(self.ed_sp_ip, r, 1, 1, 3)
        r += 1

        g.addWidget(self.btn_save_cfg, r, 0)
        g.addWidget(self.btn_test_conn, r, 1)
        g.addWidget(self.btn_run_sp, r, 2)
        g.addWidget(self.btn_clear_cache, r, 3)

        layout.addWidget(gb)

        hint = QLabel(
            "Cache logic:\n"
            "- Cache theo 'Từ ngày' (TuNgay). Nếu chạy lần 2 cùng TuNgay và DenNgay lớn hơn → chỉ chạy phần thiếu rồi ghép.\n"
            "- Nếu DenNgay nhỏ hơn cache → chạy full để đảm bảo đúng.\n"
            "- Nút Clear cache SQL để xoá cache.\n"
        )
        hint.setObjectName("hint")
        layout.addWidget(hint)
        layout.addStretch()

        self.apply_config_to_ui()
        self.cmb_auth.currentIndexChanged.connect(self.toggle_auth)
        self.toggle_auth()

    def apply_config_to_ui(self):
        sql = self.cfg["sql"]
        self.cmb_driver.setCurrentText(sql.get("driver", "ODBC Driver 17 for SQL Server"))
        self.ed_server.setText(sql.get("server", ""))
        self.ed_db.setText(sql.get("database", ""))
        self.cmb_auth.setCurrentText(sql.get("auth", "Windows Auth"))
        self.ed_user.setText(sql.get("user", ""))
        self.ed_pass.setText(sql.get("password", ""))

    def read_ui_to_config(self):
        self.cfg["sql"]["driver"] = self.cmb_driver.currentText()
        self.cfg["sql"]["server"] = self.ed_server.text().strip()
        self.cfg["sql"]["database"] = self.ed_db.text().strip()
        self.cfg["sql"]["auth"] = self.cmb_auth.currentText()
        self.cfg["sql"]["user"] = self.ed_user.text().strip()
        self.cfg["sql"]["password"] = self.ed_pass.text()

    def toggle_auth(self):
        is_sql = (self.cmb_auth.currentText() == "SQL Auth")
        self.ed_user.setEnabled(is_sql)
        self.ed_pass.setEnabled(is_sql)

    # ---------------- KPI/Status ----------------
    def set_status(self, msg: str):
        self.lb_status.setText(msg)

    def set_kpi(self, kpi: KPI):
        self.k_sql.setText(str(kpi.tong_sql))
        self.k_bh.setText(str(kpi.tong_bh))
        self.k_sent.setText(str(kpi.da_gui))
        self.k_fail.setText(str(kpi.fail))

    def update_buttons(self):
        has_listbh = not self.df_listbh_all.empty
        has_bh_filtered = not self.df_listbh_filtered.empty
        has_sql = not self.df_sql_list.empty
        has_fail = not self.df_fail.empty
        has_hsloi = not self.df_hsloi.empty
        has_loi_merged = not self.df_loi_merged.empty

        self.btn_filter_bh.setEnabled(has_listbh)
        self.btn_compare.setEnabled(has_sql and has_bh_filtered)

        self.btn_copy_op.setEnabled(has_fail)
        self.btn_copy_ip.setEnabled(has_fail)
        self.btn_run_op.setEnabled(has_fail)
        self.btn_run_ip.setEnabled(has_fail)

        self.btn_merge_loi.setEnabled(has_hsloi and has_sql)
        self.btn_export_sql.setEnabled(has_sql)
        self.btn_export_fail.setEnabled(has_fail)
        self.btn_export_loi.setEnabled(has_loi_merged)

    # ---------------- SQL Actions ----------------
    def on_save_config(self):
        self.read_ui_to_config()
        save_config(self.cfg)
        thong_bao(self, "Đã lưu", f"Đã lưu cấu hình vào {CONFIG_FILE}")

    def on_test_connection(self):
        try:
            self.read_ui_to_config()
            with get_conn(self.cfg) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                _ = cur.fetchone()
            thong_bao(self, "Kết nối OK", "Kết nối SQL Server thành công ✅")
        except Exception as e:
            loi(self, "Kết nối FAIL", str(e))

    def _run_sp_range(self, tu: str, den: str) -> pd.DataFrame:
        self.read_ui_to_config()
        sp_op = self.ed_sp_op.text().strip()
        sp_ip = self.ed_sp_ip.text().strip()

        with get_conn(self.cfg) as conn:
            df_op = sql_exec_sp(conn, sp_op, tu, den)
            df_ip = sql_exec_sp(conn, sp_ip, tu, den)

        if df_op.empty and df_ip.empty:
            return pd.DataFrame()
            
        df = normalize_sql_list(df_op, df_ip)
        if df.empty:
            return df
            
        # Strict dynamic date filter to prevent HIS SP returning records outside the requested range
        try:
            dt_tu = datetime.strptime(tu, "%Y%m%d").date()
            dt_den = datetime.strptime(den, "%Y%m%d").date()
            df = df[(df["Ngày ra viện"] >= dt_tu) & (df["Ngày ra viện"] <= dt_den)]
        except Exception:
            pass
        return df

    def on_run_sp(self):
        try:
            tu = self.sql_from.date().toString("yyyyMMdd")
            den = self.sql_to.date().toString("yyyyMMdd")
            if tu > den:
                canh_bao(self, "Sai ngày", "Từ ngày phải <= Đến ngày.")
                return

            cached = cache_get(tu)

            if cached is not None:
                cached_end, cached_df = cached

                if cached_end == den:
                    self.df_sql_list = cached_df.copy()
                    self.set_status(f"Dùng cache sql_list: {tu} → {den} | {len(self.df_sql_list)} ca")
                elif cached_end < den:
                    tu2 = next_day_yyyymmdd(cached_end)
                    if tu2 <= den:
                        self.set_status(f"Cache hit. Chỉ chạy phần thiếu: {tu2} → {den} ...")
                        new_df = self._run_sp_range(tu2, den)
                    else:
                        new_df = pd.DataFrame()

                    merged = pd.concat([cached_df, new_df], ignore_index=True)
                    merged = merged.drop_duplicates(subset=["MA_LK"], keep="first")
                    self.df_sql_list = merged
                    cache_put(tu, den, self.df_sql_list)
                    self.set_status(f"Đã ghép cache + phần mới: {tu} → {den} | {len(self.df_sql_list)} ca")
                else:
                    self.set_status("Cache tồn tại nhưng DenNgày nhỏ hơn cache. Chạy full để đúng range.")
                    self.df_sql_list = self._run_sp_range(tu, den)
                    cache_put(tu, den, self.df_sql_list)
            else:
                self.set_status(f"Chưa có cache. Đang chạy SP: {tu} → {den} ...")
                self.df_sql_list = self._run_sp_range(tu, den)
                cache_put(tu, den, self.df_sql_list)

            if self.df_sql_list.empty:
                canh_bao(self, "Không có dữ liệu", "2 Stored Procedure không trả về dòng nào (hoặc không có SELECT).")
                df_to_table(self.tbl_sql, pd.DataFrame())
                self.update_buttons()
                return

            df_to_table(self.tbl_sql, self.df_sql_list)
            self.set_kpi(KPI(tong_sql=len(self.df_sql_list), tong_bh=len(self.df_listbh_filtered)))
            self.update_buttons()
            self.tabs.setCurrentWidget(self.tbl_sql)
            thong_bao(self, "OK", "Đã tạo sql_list.")
        except Exception as e:
            loi(self, "Lỗi tải SQL", str(e))

    def on_clear_cache(self):
        if not xac_nhan(self, "Clear cache", "Bạn có chắc muốn xoá toàn bộ cache SQL không?"):
            return
        try:
            cache_clear_all()
            thong_bao(self, "Đã xoá", "Đã xoá toàn bộ cache SQL.")
            self.set_status("Đã clear cache SQL.")
        except Exception as e:
            loi(self, "Lỗi", str(e))

    # ---------------- listbh Actions ----------------
    def on_add_listbh(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn listbh.xlsx", "", "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            key_col = self.cfg["bh"]["listbh_key_col"]
            date_col = self.cfg["bh"]["listbh_date_col"]
            self.df_listbh_all = load_listbh(path, key_col, date_col)
            self.df_listbh_filtered = pd.DataFrame()
            df_to_table(self.tbl_bh, pd.DataFrame())
            self.set_status(f"Đã tải listbh: {len(self.df_listbh_all)} dòng")
            self.set_kpi(KPI(tong_sql=len(self.df_sql_list), tong_bh=0))
            self.update_buttons()
            self.tabs.setCurrentWidget(self.tbl_bh)
        except Exception as e:
            loi(self, "Lỗi listbh", str(e))

    def on_filter_bh(self):
        if self.df_listbh_all.empty:
            canh_bao(self, "Thiếu dữ liệu", "Bạn cần thêm listbh.xlsx trước.")
            return
        tu = self.de_from.date().toPython()
        den = self.de_to.date().toPython()
        self.df_listbh_filtered = filter_listbh_by_date(self.df_listbh_all, tu, den)
        df_to_table(self.tbl_bh, self.df_listbh_filtered)
        self.set_status(f"Đã lọc listbh: {len(self.df_listbh_filtered)} dòng ({tu} → {den})")
        self.set_kpi(KPI(tong_sql=len(self.df_sql_list), tong_bh=len(self.df_listbh_filtered)))
        self.update_buttons()
        self.tabs.setCurrentWidget(self.tbl_bh)

    # ---------------- Compare ----------------
    def on_compare(self):
        if self.df_sql_list.empty:
            canh_bao(self, "Thiếu sql_list", "Chưa có sql_list. Vào tab SQL để chạy SP.")
            return
        if self.df_listbh_filtered.empty:
            canh_bao(self, "Thiếu listbh", "Chưa lọc listbh theo ngày.")
            return

        bh_keys = set(self.df_listbh_filtered["MA_LK"].dropna().astype(str).map(chuan_hoa_ma_lk))
        df = self.df_sql_list.copy()
        df["MA_LK"] = df["MA_LK"].apply(chuan_hoa_ma_lk)

        df["Trạng thái"] = df["MA_LK"].apply(lambda x: "Đã gửi BH" if x in bh_keys else "FAIL")
        self.df_compare = df
        self.df_fail = df[df["Trạng thái"].astype(str).str.strip() != "Đã gửi BH"].copy()

        self.refresh_compare_table()

        da_gui = int((self.df_compare["Trạng thái"] == "Đã gửi BH").sum())
        fail = int((self.df_compare["Trạng thái"] != "Đã gửi BH").sum())
        self.set_kpi(KPI(tong_sql=len(self.df_sql_list), tong_bh=len(self.df_listbh_filtered), da_gui=da_gui, fail=fail))
        self.set_status(f"So sánh xong. FAIL: {fail} | Đã gửi: {da_gui}")
        self.update_buttons()
        self.tabs.setCurrentWidget(self.tbl_compare)

    def refresh_compare_table(self):
        if self.df_compare.empty:
            df_to_table(self.tbl_compare, pd.DataFrame())
            return
        chi_fail = (self.cmb_view.currentIndex() == 0)
        show = self.df_fail.copy() if chi_fail else self.df_compare.copy()
        cols = ["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện", "Trạng thái"]
        cols = [c for c in cols if c in show.columns]
        df_to_table(self.tbl_compare, show[cols].copy())

    # ---------------- Reset keys ----------------
    def get_reset_keys(self, loai: str) -> List[str]:
        if self.df_compare is None or self.df_compare.empty:
            return []

        df = self.df_compare.copy()
        df["MA_LK"] = df["MA_LK"].astype(str).map(chuan_hoa_ma_lk)
        df["Trạng thái"] = df["Trạng thái"].astype(str).str.strip()

        df_fail = df[df["Trạng thái"] != "Đã gửi BH"].copy()
        if df_fail.empty:
            return []

        # Fallback cho Loại ca nếu bị nan hoặc trống
        def resolve_desktop_loai_ca(row):
            val = row.get("Loại ca")
            if pd.isna(val) or str(val).strip().lower() in ("nan", "none", ""):
                ma = str(row.get("MA_LK", ""))
                return "Ngoại trú" if ma.startswith("TN.") else "Nội trú"
            return str(val).strip()

        df_fail["Loại ca"] = df_fail.apply(resolve_desktop_loai_ca, axis=1)
        df_fail = df_fail[df_fail["Loại ca"] == loai]

        keys = df_fail["MA_LK"].astype(str).tolist()
        keys = [chuan_hoa_ma_lk(k) for k in keys if chuan_hoa_ma_lk(k)]
        return unique_keep_order(keys)

    def copy_reset(self, loai: str):
        keys = self.get_reset_keys(loai)
        if not keys:
            canh_bao(self, "Không có dữ liệu", f"Không có ca FAIL để reset ({loai}).")
            return
        sql = build_reset_sql(keys, loai)

        if pyperclip is not None:
            pyperclip.copy(sql)
        else:
            QApplication.clipboard().setText(sql)

        thong_bao(self, "Đã copy", f"Đã copy SQL reset {loai} ({len(keys)} ca) vào clipboard.")

    def run_reset(self, loai: str):
        keys = self.get_reset_keys(loai)
        if not keys:
            canh_bao(self, "Không có dữ liệu", f"Không có ca FAIL để reset ({loai}).")
            return

        sql = build_reset_sql(keys, loai)
        msg = (
            f"Bạn sắp CHẠY UPDATE reset Export=0 trên DB.\n\n"
            f"Loại: {loai}\n"
            f"Số ca: {len(keys)}\n\n"
            f"Bạn có chắc chắn không?"
        )
        if not xac_nhan(self, "Xác nhận chạy SQL", msg):
            return

        try:
            self.read_ui_to_config()
            with get_conn(self.cfg) as conn:
                rc = run_update_sql(conn, sql)
            thong_bao(self, "Đã chạy SQL", f"Reset {loai} thành công. Rowcount: {rc} (có thể -1 vẫn OK).")
        except Exception as e:
            loi(self, "Lỗi chạy SQL", str(e))

    # ---------------- Error file ----------------
    def on_add_loi(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn HoSoLoiChiTiet.xlsx", "", "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            self.df_hsloi = load_hosoloichitiet(path)
            self.set_status(f"Đã tải file lỗi: {len(self.df_hsloi)} dòng")
            self.update_buttons()
        except Exception as e:
            loi(self, "Lỗi file lỗi", str(e))

    def on_merge_loi(self):
        if self.df_hsloi.empty:
            canh_bao(self, "Thiếu dữ liệu", "Chưa thêm HoSoLoiChiTiet.xlsx")
            return
        if self.df_sql_list.empty:
            canh_bao(self, "Thiếu dữ liệu", "Chưa có sql_list.")
            return
        self.df_loi_merged = merge_error_with_sql(self.df_hsloi, self.df_sql_list)
        df_to_table(self.tbl_loi, self.df_loi_merged)
        self.set_status(f"Đã ghép lỗi: {len(self.df_loi_merged)} dòng (đã bỏ trùng hoàn toàn)")
        self.update_buttons()
        self.tabs.setCurrentWidget(self.tbl_loi)

    # ---------------- Export ----------------
    def export_sql_list(self):
        if self.df_sql_list.empty:
            canh_bao(self, "Không có dữ liệu", "Chưa có sql_list để xuất.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu sql_list", "sql_list.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.df_sql_list.to_excel(path, index=False)
        thong_bao(self, "Đã lưu", f"Đã lưu sql_list:\n{path}")

    def export_fail(self):
        if self.df_fail.empty:
            canh_bao(self, "Không có dữ liệu", "Chưa có danh sách FAIL.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu danh sách FAIL", "DANH_SACH_FAIL.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        cols = ["Loại ca", "MA_LK", "Họ tên", "Mã thẻ", "Tên khoa", "Mã y tế", "Ngày ra viện", "Trạng thái"]
        cols = [c for c in cols if c in self.df_fail.columns]
        self.df_fail[cols].copy().to_excel(path, index=False)
        thong_bao(self, "Đã lưu", f"Đã lưu:\n{path}")

    def export_loi(self):
        if self.df_loi_merged.empty:
            canh_bao(self, "Không có dữ liệu", "Chưa có danh sách ghép lỗi.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Lưu danh sách kèm lỗi", "DANH_SACH_KEM_LOI.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.df_loi_merged.to_excel(path, index=False)
        thong_bao(self, "Đã lưu", f"Đã lưu:\n{path}")


# =========================
# Run
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # ✅ đồng nhất UI, tránh Windows native "lạc tông"
    app.setStyleSheet(APP_QSS)      # ✅ set sớm để mọi widget đều ăn QSS
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
