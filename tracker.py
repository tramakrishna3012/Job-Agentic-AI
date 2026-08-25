"""
Tracker module.
Manages local SQLite database recording tailored job applications,
Drive links, match scores, and status history.
"""

from __future__ import annotations

import datetime
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jaa.tracker")


class Tracker:
    """SQLite tracker for job applications."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or os.getenv("DB_PATH", "jaa.db"))
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a sqlite3 connection with Row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema if not already present."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute(
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
                    status TEXT DEFAULT 'Tailored',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(company, role) ON CONFLICT REPLACE
                )
                """
            )
            conn.commit()

    def get_application(self, company: str, role: str) -> Optional[Dict[str, Any]]:
        """Retrieve existing application by company and role (case-insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM applications
                WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)
                ORDER BY updated_at DESC LIMIT 1
                """,
                (company.strip(), role.strip()),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def log_application(
        self,
        company: str,
        role: str,
        jd_hash: str,
        drive_link: str,
        drive_file_id: Optional[str] = None,
        match_score: Optional[int] = None,
        fit_summary: Optional[str] = None,
        status: str = "Tailored",
    ) -> Dict[str, Any]:
        """
        Record or update a tailored application in the SQLite database.
        Returns the saved record as a dictionary.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        existing = self.get_application(company, role)

        created_at = existing["created_at"] if existing else now_iso
        updated_at = now_iso

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO applications (
                    company, role, jd_hash, timestamp, drive_file_id,
                    drive_link, match_score, fit_summary, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company, role) DO UPDATE SET
                    jd_hash = excluded.jd_hash,
                    timestamp = excluded.timestamp,
                    drive_file_id = COALESCE(excluded.drive_file_id, applications.drive_file_id),
                    drive_link = excluded.drive_link,
                    match_score = excluded.match_score,
                    fit_summary = excluded.fit_summary,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    company.strip(),
                    role.strip(),
                    jd_hash,
                    now_iso,
                    drive_file_id,
                    drive_link,
                    match_score,
                    fit_summary,
                    status,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

        logger.info(f"Recorded application in SQLite for {company} - {role}")
        return self.get_application(company, role) or {}

    def list_applications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List most recent applications."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM applications
                ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
