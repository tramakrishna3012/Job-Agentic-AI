"""
Database access layer for Phase 1 FastAPI backend.
Enforces strict read-only connections for GET endpoints, and isolated single-field
updates for the PATCH endpoint. Computes days_since_update in Python memory.
"""

from __future__ import annotations

import datetime
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH_ENV = "DB_PATH"


def get_db_path() -> Path:
    """Resolve database path from environment."""
    return Path(os.getenv(DB_PATH_ENV, "jaa.db")).resolve()


def compute_days_since_update(updated_at_str: Optional[str]) -> int:
    """Compute elapsed days since last status update."""
    if not updated_at_str:
        return 0
    try:
        clean_str = updated_at_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - dt
        return max(0, delta.days)
    except Exception:
        return 0


def get_read_only_connection() -> sqlite3.Connection:
    """Create a strictly read-only SQLite connection."""
    db_path = get_db_path()
    if not db_path.exists():
        # If DB doesn't exist yet, create empty table
        conn_init = sqlite3.connect(str(db_path))
        conn_init.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                jd_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                drive_file_id TEXT,
                drive_link TEXT,
                match_score INTEGER,
                fit_summary TEXT,
                status TEXT DEFAULT 'Applied',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(company, role) ON CONFLICT REPLACE
            )
            """
        )
        conn_init.commit()
        conn_init.close()

    uri_path = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_write_connection() -> sqlite3.Connection:
    """Create a write connection strictly for status updates."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def list_applications(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """List applications with optional status filtering."""
    with get_read_only_connection() as conn:
        if status_filter:
            cursor = conn.execute(
                """
                SELECT id, company, role, created_at, status, match_score, drive_link, updated_at
                FROM applications
                WHERE LOWER(status) = LOWER(?)
                ORDER BY updated_at DESC
                """,
                (status_filter.strip(),),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, company, role, created_at, status, match_score, drive_link, updated_at
                FROM applications
                ORDER BY updated_at DESC
                """
            )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append(
                {
                    "id": d["id"],
                    "company": d["company"],
                    "role": d["role"],
                    "date_applied": d["created_at"],
                    "status": d["status"] or "Applied",
                    "match_score": d["match_score"],
                    "drive_link": d["drive_link"],
                    "days_since_update": compute_days_since_update(d.get("updated_at")),
                }
            )
        return results


def get_application_by_id(app_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve detailed single application record."""
    with get_read_only_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, company, role, created_at, status, match_score, drive_link, jd_hash, fit_summary, updated_at
            FROM applications
            WHERE id = ?
            """,
            (app_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "id": d["id"],
            "company": d["company"],
            "role": d["role"],
            "date_applied": d["created_at"],
            "status": d["status"] or "Applied",
            "match_score": d["match_score"],
            "drive_link": d["drive_link"],
            "jd_hash": d["jd_hash"],
            "fit_summary": d["fit_summary"],
            "days_since_update": compute_days_since_update(d.get("updated_at")),
        }


def update_status(app_id: int, new_status: str) -> Optional[Dict[str, Any]]:
    """
    Update strictly status and updated_at for an application.
    Never modifies drive_file_id, jd_hash, company, role, or other fields.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_write_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE applications
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, now_iso, app_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None

    return get_application_by_id(app_id)


def get_stats() -> Dict[str, int]:
    """Retrieve count breakdown of applications by status."""
    with get_read_only_connection() as conn:
        cursor = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM applications
            GROUP BY status
            """
        )
        rows = cursor.fetchall()
        counts = {"applied": 0, "interview": 0, "rejected": 0, "offer": 0, "total": 0}
        for r in rows:
            status_name = (r["status"] or "applied").lower().strip()
            count = r["count"]
            if status_name in counts:
                counts[status_name] += count
            elif status_name == "tailored":
                # Tailored status maps to applied count
                counts["applied"] += count
            counts["total"] += count
        return counts
