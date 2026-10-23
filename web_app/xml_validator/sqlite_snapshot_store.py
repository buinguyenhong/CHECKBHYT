"""SQLite persistence for read-only XML rows fetched from the existing HIS XML tables.

This module intentionally does not call XML generation/export stored procedures.
It stores per-run snapshots rather than replacing prior snapshots.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable


def default_db_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get(
        "BHYT_XML_ARCHIVE_DB",
        os.path.join(base_dir, "xml_archive.db"),
    )


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    initialize(conn)
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS xml_validation_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        date_from TEXT,
        date_to TEXT,
        source TEXT NOT NULL DEFAULT 'eHospital_ThienHanh_XML',
        status TEXT NOT NULL DEFAULT 'running',
        cases_seen INTEGER NOT NULL DEFAULT 0,
        cases_snapshotted INTEGER NOT NULL DEFAULT 0,
        error_message TEXT
    );

    CREATE TABLE IF NOT EXISTS xml_case_snapshots (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES xml_validation_runs(run_id),
        ma_lk TEXT NOT NULL,
        loai_ca TEXT,
        benh_an_id TEXT,
        tiep_nhan_id TEXT,
        xac_nhan_chi_phi_id TEXT,
        xml_type TEXT NOT NULL,
        source_schema TEXT,
        source_table TEXT NOT NULL,
        row_ordinal INTEGER NOT NULL DEFAULT 0,
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL,
        captured_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS ix_xml_snapshots_ma_lk
        ON xml_case_snapshots(ma_lk);
    CREATE INDEX IF NOT EXISTS ix_xml_snapshots_run
        ON xml_case_snapshots(run_id);
    CREATE INDEX IF NOT EXISTS ix_xml_snapshots_type
        ON xml_case_snapshots(run_id, ma_lk, xml_type);
    """)
    conn.commit()


def create_run(conn: sqlite3.Connection, date_from: str = "", date_to: str = "") -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO xml_validation_runs
           (started_at, date_from, date_to, status)
           VALUES (?, ?, ?, 'running')""",
        (now, date_from, date_to),
    )
    conn.commit()
    return int(cur.lastrowid)


def save_rows(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    ma_lk: str,
    loai_ca: str = "",
    benh_an_id: Any = None,
    tiep_nhan_id: Any = None,
    xac_nhan_chi_phi_id: Any = None,
    xml_type: str,
    source_schema: str = "",
    source_table: str,
    rows: Iterable[dict[str, Any]],
) -> int:
    """Append rows to this run. Repeated cases/runs are retained as history."""
    captured_at = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for ordinal, row in enumerate(rows):
        payload = json.dumps(row, ensure_ascii=False, default=str, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        conn.execute(
            """INSERT INTO xml_case_snapshots
               (run_id, ma_lk, loai_ca, benh_an_id, tiep_nhan_id,
                xac_nhan_chi_phi_id, xml_type, source_schema, source_table,
                row_ordinal, payload_json, payload_sha256, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, str(ma_lk).strip(), loai_ca or "",
                None if benh_an_id is None else str(benh_an_id),
                None if tiep_nhan_id is None else str(tiep_nhan_id),
                None if xac_nhan_chi_phi_id is None else str(xac_nhan_chi_phi_id),
                xml_type.upper(), source_schema or "", source_table, ordinal,
                payload, digest, captured_at,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    status: str,
    cases_seen: int = 0,
    cases_snapshotted: int = 0,
    error_message: str | None = None,
) -> None:
    conn.execute(
        """UPDATE xml_validation_runs
           SET finished_at=?, status=?, cases_seen=?, cases_snapshotted=?,
               error_message=?
           WHERE run_id=?""",
        (
            datetime.now(timezone.utc).isoformat(), status, cases_seen,
            cases_snapshotted, error_message, run_id,
        ),
    )
    conn.commit()


def load_run_rows(conn: sqlite3.Connection, run_id: int) -> dict[str, dict[str, list[dict]]]:
    """Load the newest snapshot rows for a run into an XMLRuleEngine-compatible shape.

    Returns {MA_LK: {XML1: [{tree, filename, xml_type}], ...}}. Payloads are
    parsed as XML elements when possible. Key/value and wide table normalization
    belongs in the SQL adapter, after its real schema has been inspected.
    """
    from lxml import etree

    grouped: dict[str, dict[str, list[dict]]] = {}
    rows = conn.execute(
        """SELECT ma_lk, xml_type, source_table, row_ordinal, payload_json
           FROM xml_case_snapshots
           WHERE run_id=?
           ORDER BY ma_lk, xml_type, source_table, row_ordinal""",
        (run_id,),
    ).fetchall()

    for row in rows:
        # The payload must contain an XML string under one of these explicit keys.
        payload = json.loads(row["payload_json"])
        xml_text = payload.get("_xml_text") or payload.get("xml_text")
        if not xml_text:
            continue
        try:
            parser = etree.XMLParser(remove_blank_text=True, recover=False)
            root = etree.fromstring(str(xml_text).encode("utf-8"), parser=parser)
            tree = etree.ElementTree(root)
        except Exception:
            continue
        ma_lk = row["ma_lk"]
        xml_type = row["xml_type"]
        grouped.setdefault(ma_lk, {}).setdefault(xml_type, []).append({
            "filename": f"{row['source_table']}:{row['row_ordinal']}",
            "filepath": "",
            "tree": tree,
            "xml_type": xml_type,
        })
    return grouped
