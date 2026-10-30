import os
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from services.his_service import get_conn, discard_conn, build_conn_str, SQL_QUERY_TIMEOUT_SECONDS, SQL_CONNECT_TIMEOUT_SECONDS

XML_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_db_config.json")
DEFAULT_XML_TABLES = [
    "XML1_CV130", "XML2_CV130", "XML3_CV130", "XML4_CV130", "XML5_CV130",
    "XML6_CV130", "XML7_CV130", "XML8_CV130", "XML9_CV130", "XML10_CV130",
    "XML11_CV130", "XML12_CV130", "XML13_CV130", "XML14_CV130", "XML15_CV130"
]

# Danh mục các cột cần thiết cho từng bảng XML nhằm tối ưu hiệu năng I/O và RAM (Column Projection)
XML_TABLE_COLUMNS: Dict[str, List[str]] = {
    "XML1": [
        "MA_LK", "MA_BN", "HO_TEN", "SO_CCCD", "NGAY_SINH", "GIOI_TINH", "DIA_CHI",
        "MA_THE", "MA_DKBD", "MA_CSKCB", "GT_THE_TU", "GT_THE_DEN",
        "MA_THE_KHAC", "MA_DKBD_KHAC", "GT_THE_TU_KHAC", "GT_THE_DEN_KHAC",
        "NGAY_VAO", "NGAY_RA", "NGAY_TTOAN", "MA_LYDO_VVIEN", "LY_DO_VV", "MA_DOITUONG_KCB",
        "MA_LOAI_KCB", "MA_BENH_CHINH", "MA_BENH_KT", "MA_BENH_YHCT", "CHAN_DOAN_VAO", "CHAN_DOAN_RV",
        "PP_DIEUTRI", "KET_QUA_DTRI", "TINH_TRANG_RV", "MA_LOAI_RV", "CAN_NANG", "NAM_QT", "THANG_QT",
        "MUC_HUONG", "MA_KHU_VUC", "NGAY_MIEN_CCT", "NAM_NAM_LIEN_TUC",
        "T_TONGCHI", "T_TONGCHI_BV", "TONG_CHI", "T_BNTT", "T_BNCCT", "T_BHTT",
        "T_NGUONKHAC", "T_NGOAIDM", "T_NGOAIDS", "TIEN_NGOAI_DS",
        "TIEN_GIUONG", "T_GIUONG", "T_VANCHUYEN", "T_VAN_CHUYEN",
        "MA_TAI_NAN", "MA_THE_TAM"
    ],
    "XML2": [
        "MA_LK", "STT", "MA_THUOC", "MA_NHOM", "TEN_THUOC", "DON_VI_TINH", "HAM_LUONG", "DUONG_DUNG",
        "PHAM_VI", "SO_LUONG", "DON_GIA", "TYLE_TT", "TYLE_TT_BH", "TYLE", "MUC_HUONG",
        "THANH_TIEN", "THANH_TIEN_BV", "THANH_TIEN_BH",
        "T_BHTT", "T_BNTT", "T_BNCCT", "T_NGUONKHAC",
        "T_NGUONKHAC_NSNN", "T_NGUONKHAC_VTNN", "T_NGUONKHAC_VTTN", "T_NGUONKHAC_CL",
        "T_NGOAIDM", "T_NGOAIDS",
        "MA_KHOA", "MA_BAC_SI", "MA_DICH_VU", "NGAY_YL", "NGAY_TH_YL", "TT_THAU"
    ],
    "XML3": [
        "MA_LK", "STT", "MA_DICH_VU", "MA_VAT_TU", "MA_NHOM", "GOI_VTYT", "TEN_DICH_VU", "DON_VI_TINH",
        "PHAM_VI", "SO_LUONG", "DON_GIA", "DON_GIA_BV", "DON_GIA_BH", "DON_GIA_DV",
        "TYLE_TT", "TYLE_TT_DV", "TYLE_TT_BH", "TYLE", "MUC_HUONG",
        "THANH_TIEN", "THANH_TIEN_BV", "THANH_TIEN_BH",
        "T_BHTT", "T_BNTT", "T_BNCCT", "T_NGUONKHAC",
        "T_NGUONKHAC_NSNN", "T_NGUONKHAC_VTNN", "T_NGUONKHAC_VTTN", "T_NGUONKHAC_CL",
        "T_NGOAIDM", "T_NGOAIDS",
        "MA_KHOA", "MA_GIUONG", "MA_BAC_SI", "NGUOI_THUC_HIEN", "NGAY_YL", "NGAY_TH_YL", "NGAY_KQ", "MA_PTTT", "TT_THAU"
    ],
    "XML4": [
        "MA_LK", "STT", "MA_DICH_VU", "MA_CHI_SO", "TEN_CHI_SO", "GIA_TRI", "MA_MAY", "MO_TA", "KET_LUAN", "NGAY_KQ", "MA_BS_DOC_KQ"
    ],
    "XML5": [
        "MA_LK", "STT", "DIEN_BIEN_LS", "GIAI_DOAN_BENH", "HOI_CHAN", "PHAU_THUAT", "NGAY_YL", "NGUOI_THUC_HIEN"
    ],
    "XML6": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "MA_THE", "MA_DKBD", "MA_CSKCB", "MA_NOI_DEN", "NGAY_VAO", "NGAY_RA", "LY_DO_CT"
    ],
    "XML7": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "MA_THE", "CHAN_DOAN_RV", "PP_DIEUTRI", "NGAY_VAO", "NGAY_RA", "NGOAITRU_TUNGAY", "MA_BS"
    ],
    "XML8": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "MA_THE", "MA_TTDV", "TOMTAT_KQ", "PP_DIEUTRI", "CHAN_DOAN_RV", "NGAY_VAO", "NGAY_RA"
    ],
    "XML9": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "MA_TTDV", "MA_THE_NND", "SO_CCCD_NND"
    ],
    "XML10": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "NGAY_TU_VONG"
    ],
    "XML11": [
        "MA_LK", "HO_TEN", "MA_THE", "TU_NGAY", "DEN_NGAY"
    ],
    "XML12": [
        "MA_LK", "HO_TEN", "NGAY_SINH"
    ],
    "XML13": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "SO_CCCD", "NGAY_GD"
    ],
    "XML14": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "MA_THE", "NGAY_HEN_KL", "MA_CSKCB"
    ],
    "XML15": [
        "MA_LK", "HO_TEN", "NGAY_SINH", "GIOI_TINH", "PHAN_LOAI_LAO"
    ]
}

def load_xml_db_config() -> dict:
    default_cfg = {
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "thsrvsql01",
        "database": "eHospital_ThienHanh_XML",
        "auth": "Windows Auth",
        "user": "",
        "password": "",
        "use_nolock": True,
        "tables": DEFAULT_XML_TABLES
    }
    if os.path.exists(XML_CONFIG_FILE):
        try:
            with open(XML_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
                if not default_cfg.get("tables"):
                    default_cfg["tables"] = DEFAULT_XML_TABLES
                if "use_nolock" not in default_cfg:
                    default_cfg["use_nolock"] = True
        except Exception:
            pass
    return default_cfg

def save_xml_db_config(cfg: dict):
    with open(XML_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

class XmlSourceAdapter:
    """
    Adapter chuyên trách đọc dữ liệu XML từ SQL Server eHospital_ThienHanh_XML.
    CAM KẾT AN TOÀN: CHỈ DÙNG TRUY VẤN SELECT, TUYỆT ĐỐI KHÔNG GHI HOẶC GỌI STORE TẠO LẠI XML.
    """
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or load_xml_db_config()

    def get_connection(self):
        try:
            import pyodbc
        except ImportError:
            raise RuntimeError("pyodbc chưa được cài đặt trên môi trường.")

        auth = self.cfg.get("auth", "Windows Auth")
        conn_str = build_conn_str(
            self.cfg.get("driver", "ODBC Driver 17 for SQL Server"),
            self.cfg.get("server", "thsrvsql01"),
            self.cfg.get("database", "eHospital_ThienHanh_XML"),
            auth,
            self.cfg.get("user", ""),
            self.cfg.get("password", "")
        )
        conn = pyodbc.connect(conn_str, timeout=SQL_CONNECT_TIMEOUT_SECONDS)
        try:
            conn.timeout = SQL_QUERY_TIMEOUT_SECONDS
        except Exception:
            pass
        return conn

    def test_connection(self) -> Tuple[bool, str]:
        """Kiểm tra kết nối Read-Only tới SQL Server XML và đếm số bảng XML tồn tại."""
        conn = None
        cur = None
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME LIKE 'XML%'")
            found_tables = [str(r[0]) for r in cur.fetchall()]
            srv = self.cfg.get("server", "thsrvsql01")
            db_name = self.cfg.get("database", "eHospital_ThienHanh_XML")
            return True, f"Kết nối thành công tới {srv} / {db_name}! Phát hiện {len(found_tables)} bảng XML."
        except Exception as e:
            return False, f"Lỗi kết nối CSDL XML: {str(e)}"
        finally:
            if cur:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def fetch_xml_batch(
        self,
        ma_lk_list: List[str],
        chunk_size: int = 50
    ) -> Tuple[Dict[str, Dict[str, List[Dict[str, Any]]]], Dict[str, Dict[str, str]], Dict[str, Dict[str, Any]]]:
        """
        Truy vấn dữ liệu XML của tập MA_LK theo lô (batch) bằng Parameterized Query an toàn.
        Trả về tuple: (results, case_table_status, batch_table_status)
        - results: { ma_lk: { 'XML1': [rows], 'XML2': [rows], ... } }
        - case_table_status: { ma_lk: { 'XML1': 'SUCCESS'|'EMPTY'|'ERROR', ... } } (Riêng cho từng hồ sơ)
        - batch_table_status: { 'XML1': {'status': 'SUCCESS'|'EMPTY'|'ERROR', 'rows_count': int, 'error': str}, ... }
        """
        clean_keys = [str(k).strip() for k in ma_lk_list if str(k).strip()]
        if not clean_keys:
            return {}, {}, {}

        results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {k: {} for k in clean_keys}
        case_table_status: Dict[str, Dict[str, str]] = {k: {} for k in clean_keys}
        batch_table_status: Dict[str, Dict[str, Any]] = {}
        conn = None
        try:
            conn = self.get_connection()
        except Exception as e:
            print(f"[!] [XmlSourceAdapter] Không thể kết nối SQL Server XML: {e}")
            raise ConnectionError(f"Không thể kết nối CSDL XML (SQL Server): {e}")

        try:
            raw_tables = self.cfg.get("tables", DEFAULT_XML_TABLES)
            import re
            valid_tbl_re = re.compile(r"^XML(1[0-5]?|[1-9])(_CV130|_4210|_4750)?$", re.IGNORECASE)
            tables_to_query = [t for t in raw_tables if valid_tbl_re.match(str(t).strip())]
            if not tables_to_query:
                tables_to_query = DEFAULT_XML_TABLES

            use_nolock = self.cfg.get("use_nolock", True)
            lock_hint = "WITH (NOLOCK)" if use_nolock else ""

            # Khởi tạo trạng thái mặc định
            for tbl in tables_to_query:
                tbl_short = tbl.split("_")[0].upper()
                batch_table_status[tbl_short] = {"status": "EMPTY", "rows_count": 0, "error": ""}
                for k in clean_keys:
                    case_table_status[k][tbl_short] = "EMPTY"

            for i in range(0, len(clean_keys), chunk_size):
                chunk = clean_keys[i:i + chunk_size]
                placeholders = ", ".join(["?"] * len(chunk))

                for tbl in tables_to_query:
                    tbl_short = tbl.split("_")[0].upper()
                    
                    # Áp dụng Column Projection để tối ưu I/O và RAM bộ nhớ
                    proj_cols = XML_TABLE_COLUMNS.get(tbl_short)
                    cols_str = ", ".join(proj_cols) if proj_cols else "*"
                    sql = f"SELECT {cols_str} FROM dbo.{tbl} {lock_hint} WHERE MA_LK IN ({placeholders})".strip()

                    cur = None
                    try:
                        cur = conn.cursor()
                        try:
                            cur.execute(sql, tuple(chunk))
                        except Exception as proj_err:
                            # Nếu một cột không tồn tại trên schema thực tế, fallback an toàn về SELECT *
                            sql_fallback = f"SELECT * FROM dbo.{tbl} {lock_hint} WHERE MA_LK IN ({placeholders})".strip()
                            cur.execute(sql_fallback, tuple(chunk))

                        cols = [c[0] for c in cur.description] if cur.description else []
                        rows = cur.fetchall()

                        # Đếm số dòng xuất hiện của từng MA_LK trong chunk cho bảng này
                        chunk_case_rows: Dict[str, int] = {k: 0 for k in chunk}

                        if rows:
                            # Cập nhật batch_table_status: chỉ chuyển sang SUCCESS nếu chưa bị ERROR ở chunk trước
                            if batch_table_status[tbl_short]["status"] != "ERROR":
                                batch_table_status[tbl_short]["status"] = "SUCCESS"
                            batch_table_status[tbl_short]["rows_count"] += len(rows)

                            for row in rows:
                                row_dict = {}
                                for idx, col in enumerate(cols):
                                    val = row[idx]
                                    if isinstance(val, (pd.Timestamp, pd.Period)):
                                        val = str(val)
                                    elif hasattr(val, 'isoformat'):
                                        val = val.isoformat()
                                    row_dict[col] = val
                                
                                row_lk = str(row_dict.get("MA_LK", "")).strip()
                                if row_lk in results:
                                    if tbl_short not in results[row_lk]:
                                        results[row_lk][tbl_short] = []
                                    results[row_lk][tbl_short].append(row_dict)
                                    chunk_case_rows[row_lk] = chunk_case_rows.get(row_lk, 0) + 1

                        # Cập nhật trạng thái cụ thể cho từng MA_LK trong chunk:
                        for lk in chunk:
                            if chunk_case_rows.get(lk, 0) > 0:
                                case_table_status[lk][tbl_short] = "SUCCESS"
                            else:
                                case_table_status[lk][tbl_short] = "EMPTY"

                    except Exception as q_err:
                        err_msg = str(q_err)
                        print(f"[-] [XmlSourceAdapter] Lỗi truy vấn bảng {tbl} ở chunk {i//chunk_size + 1}: {err_msg}")
                        # Không bao giờ ghi đè trạng thái ERROR bằng SUCCESS
                        batch_table_status[tbl_short]["status"] = "ERROR"
                        batch_table_status[tbl_short]["error"] = err_msg

                        # Đánh dấu lỗi cho toàn bộ hồ sơ trong chunk gặp sự cố
                        for lk in chunk:
                            case_table_status[lk][tbl_short] = "ERROR"

                    finally:
                        if cur:
                            try:
                                cur.close()
                            except Exception:
                                pass

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        return results, case_table_status, batch_table_status
