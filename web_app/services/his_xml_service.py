"""Read-only discovery helpers for the existing eHospital XML database.

No XML generation/export stored procedure is called by this module.
The actual MA_LK -> patient-id -> XacNhanChiPhi_Id joins must be configured only
after the live schema has been inspected.
"""
from __future__ import annotations

from typing import Any

from services.his_service import get_conn, discard_conn, SQL_QUERY_TIMEOUT_SECONDS

XML_DATABASE_DEFAULT = "eHospital_ThienHanh_XML"
XML_TABLE_NAMES = tuple(f"XML{i}_CV130" for i in range(1, 16))
RELATIONSHIP_COLUMN_NAMES = {
    "ma_lk", "malk", "malienket", "sophieu_ba", "sotiepnhan",
    "benhan_id", "tiepnhan_id", "xacnhanchiphi_id",
}


def _rows_as_dicts(cursor) -> list[dict[str, Any]]:
    names = [col[0] for col in (cursor.description or [])]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def inspect_xml_schema(cfg: dict) -> dict:
    """Read SQL Server catalog metadata only; return XML table columns and join candidates."""
    conn = get_conn(cfg)
    try:
        cur = conn.cursor()
        try:
            cur.timeout = SQL_QUERY_TIMEOUT_SECONDS
        except Exception:
            pass

        cur.execute(
            """
            SELECT s.name AS schema_name, t.name AS table_name,
                   c.column_id, c.name AS column_name, ty.name AS data_type,
                   c.max_length, c.precision, c.scale, c.is_nullable
            FROM [eHospital_ThienHanh_XML].sys.tables AS t
            JOIN [eHospital_ThienHanh_XML].sys.schemas AS s ON s.schema_id=t.schema_id
            JOIN [eHospital_ThienHanh_XML].sys.columns AS c ON c.object_id=t.object_id
            JOIN [eHospital_ThienHanh_XML].sys.types AS ty ON ty.user_type_id=c.user_type_id
            WHERE t.name IN (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ORDER BY s.name, t.name, c.column_id
            """,
            XML_TABLE_NAMES,
        )
        xml_columns = _rows_as_dicts(cur)

        cur.execute(
            """
            SELECT DB_NAME() AS database_name, s.name AS schema_name,
                   t.name AS table_name, c.name AS column_name, ty.name AS data_type
            FROM sys.tables AS t
            JOIN sys.schemas AS s ON s.schema_id=t.schema_id
            JOIN sys.columns AS c ON c.object_id=t.object_id
            JOIN sys.types AS ty ON ty.user_type_id=c.user_type_id
            WHERE LOWER(c.name) IN (?, ?, ?, ?, ?, ?, ?, ?)
            ORDER BY s.name, t.name, c.name
            """,
            sorted(RELATIONSHIP_COLUMN_NAMES),
        )
        his_candidates = _rows_as_dicts(cur)

        cur.execute(
            """
            SELECT s.name AS schema_name, t.name AS table_name,
                   c.name AS column_name, ty.name AS data_type
            FROM [eHospital_ThienHanh_XML].sys.tables AS t
            JOIN [eHospital_ThienHanh_XML].sys.schemas AS s ON s.schema_id=t.schema_id
            JOIN [eHospital_ThienHanh_XML].sys.columns AS c ON c.object_id=t.object_id
            JOIN [eHospital_ThienHanh_XML].sys.types AS ty ON ty.user_type_id=c.user_type_id
            WHERE LOWER(c.name) IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ORDER BY s.name, t.name, c.name
            """,
            sorted(RELATIONSHIP_COLUMN_NAMES | {"chi_tieu", "gia_tri", "stt"}),
        )
        xml_candidates = _rows_as_dicts(cur)

        found_tables = sorted({str(row["table_name"]) for row in xml_columns})
        return {
            "xml_database": XML_DATABASE_DEFAULT,
            "xml_tables_found": found_tables,
            "xml_tables_missing": sorted(set(XML_TABLE_NAMES) - set(found_tables)),
            "xml_table_columns": xml_columns,
            "his_relationship_candidates": his_candidates,
            "xml_relationship_candidates": xml_candidates,
            "read_only": True,
            "xml_generation_procedures_called": False,
        }
    finally:
        conn.close()
        discard_conn(conn)


def read_sample_rows(cfg: dict, schema_name: str, table_name: str, limit: int = 10) -> list[dict]:
    """Read a small sample from an existing XML table; identifiers are checked against catalog."""
    if table_name not in XML_TABLE_NAMES:
        raise ValueError("Bảng phải thuộc danh sách XML1_CV130 đến XML15_CV130.")
    if not schema_name.replace("_", "").isalnum():
        raise ValueError("Tên schema không hợp lệ.")
    limit = max(1, min(int(limit), 20))

    conn = get_conn(cfg)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP (1) s.name
            FROM [eHospital_ThienHanh_XML].sys.tables t
            JOIN [eHospital_ThienHanh_XML].sys.schemas s ON s.schema_id=t.schema_id
            WHERE s.name=? AND t.name=?
            """,
            (schema_name, table_name),
        )
        if not cur.fetchone():
            raise ValueError("Không tìm thấy bảng trong schema đã chọn.")
        cur.execute(
            f"SELECT TOP ({limit}) * FROM [eHospital_ThienHanh_XML].[{schema_name}].[{table_name}]"
        )
        return _rows_as_dicts(cur)
    finally:
        conn.close()
        discard_conn(conn)
