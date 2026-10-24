import os
import json
from typing import List, Dict, Any, Optional
import pandas as pd
from services.his_service import get_conn, discard_conn, build_conn_str, SQL_QUERY_TIMEOUT_SECONDS, SQL_CONNECT_TIMEOUT_SECONDS

XML_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_db_config.json")

def load_xml_db_config() -> dict:
    default_cfg = {
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "thsrvsql01",
        "database": "eHospital_ThienHanh_XML",
        "auth": "Windows Auth",
        "user": "",
        "password": "",
        "tables": [
            "XML1_CV130", "XML2_CV130", "XML3_CV130", "XML4_CV130", "XML5_CV130",
            "XML7_CV130", "XML8_CV130", "XML9_CV130", "XML11_CV130", "XML13_CV130"
        ]
    }
    if os.path.exists(XML_CONFIG_FILE):
        try:
            with open(XML_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
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

    def fetch_xml_batch(self, ma_lk_list: List[str], chunk_size: int = 50) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Truy vấn dữ liệu XML của tập MA_LK theo lô (batch).
        Trả về dict: { ma_lk: { 'XML1': [rows], 'XML2': [rows], ... } }
        """
        clean_keys = [str(k).strip() for k in ma_lk_list if str(k).strip()]
        if not clean_keys:
            return {}

        results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {k: {} for k in clean_keys}
        conn = None
        try:
            conn = self.get_connection()
        except Exception as e:
            # Nếu không thể kết nối SQL Server (ví dụ ở môi trường dev/offline), trả về rỗng kèm cờ
            print(f"[!] [XmlSourceAdapter] Không thể kết nối SQL Server XML: {e}")
            return results

        try:
            tables_to_query = self.cfg.get("tables", [
                "XML1_CV130", "XML2_CV130", "XML3_CV130", "XML4_CV130", "XML5_CV130",
                "XML7_CV130", "XML8_CV130", "XML9_CV130", "XML11_CV130", "XML13_CV130"
            ])

            for i in range(0, len(clean_keys), chunk_size):
                chunk = clean_keys[i:i + chunk_size]
                quoted_keys = ", ".join([f"'{k.replace('\'', '\'\'')}'" for k in chunk])

                for tbl in tables_to_query:
                    # Chuẩn hóa tên viết tắt: XML1_CV130 -> XML1
                    tbl_short = tbl.split("_")[0].upper()
                    
                    # CHỈ THỰC HIỆN CÂU LỆNH SELECT, WITH (NOLOCK) ĐỂ TRÁNH LOCK BẢNG NGHIỆP VỤ
                    sql = f"SELECT * FROM dbo.{tbl} WITH (NOLOCK) WHERE MA_LK IN ({quoted_keys})"
                    try:
                        cur = conn.cursor()
                        cur.execute(sql)
                        cols = [c[0] for c in cur.description] if cur.description else []
                        rows = cur.fetchall()
                        for row in rows:
                            row_dict = {}
                            for idx, col in enumerate(cols):
                                val = row[idx]
                                # Chuẩn hóa kiểu dữ liệu cho JSON serialization
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
                        cur.close()
                    except Exception as q_err:
                        # Bảng có thể chưa tồn tại hoặc rỗng, tiếp tục bảng khác
                        print(f"[-] [XmlSourceAdapter] Không truy vấn được bảng {tbl}: {q_err}")

        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        return results
