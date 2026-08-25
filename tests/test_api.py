"""
Comprehensive test suite for Phase 1 FastAPI REST endpoints.
Tests Bearer authentication, GET /api/applications with filtering,
GET /api/applications/{id}, PATCH /api/applications/{id} status updates,
GET /api/stats, and SQLite read-only / write isolation.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

VALID_TOKEN = "test_secret_token_123"


@pytest.fixture
def test_db():
    """Create a temporary SQLite database populated with sample applications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_api.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE applications (
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
        # Seed 3 records
        conn.execute(
            """
            INSERT INTO applications (
                company, role, jd_hash, timestamp, drive_file_id,
                drive_link, match_score, fit_summary, status, created_at, updated_at
            ) VALUES
            ('Google', 'AI Engineer', 'hash_google', '2026-08-20T10:00:00+00:00', 'drive_1', 'https://drive/1', 95, 'Great fit for AI role', 'Applied', '2026-08-20T10:00:00+00:00', '2026-08-20T10:00:00+00:00'),
            ('Microsoft', 'Cloud Architect', 'hash_msft', '2026-08-22T10:00:00+00:00', 'drive_2', 'https://drive/2', 88, 'Strong Azure background', 'Interview', '2026-08-22T10:00:00+00:00', '2026-08-22T10:00:00+00:00'),
            ('Amazon', 'SRE', 'hash_amzn', '2026-08-24T10:00:00+00:00', 'drive_3', 'https://drive/3', 82, 'Solid Linux/K8s', 'Rejected', '2026-08-24T10:00:00+00:00', '2026-08-24T10:00:00+00:00')
            """
        )
        conn.commit()
        conn.close()

        with patch.dict(os.environ, {"DB_PATH": str(db_path), "DASHBOARD_TOKEN": VALID_TOKEN}):
            yield str(db_path)


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_middleware_missing_token(client, test_db):
    """Test accessing API without token returns 401."""
    resp = client.get("/api/applications")
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_auth_middleware_invalid_token(client, test_db):
    """Test accessing API with wrong token returns 401."""
    resp = client.get("/api/applications", headers={"Authorization": "Bearer wrong_token"})
    assert resp.status_code == 401


def test_get_applications_list(client, test_db):
    """Test listing all applications with valid token."""
    resp = client.get("/api/applications", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    # Check computed field and structure
    first = data[0]
    assert "days_since_update" in first
    assert "company" in first
    assert "role" in first
    assert "status" in first


def test_get_applications_filtered_by_status(client, test_db):
    """Test filtering applications by status query parameter."""
    resp = client.get(
        "/api/applications?status=Interview",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["company"] == "Microsoft"
    assert data[0]["status"] == "Interview"


def test_get_application_detail(client, test_db):
    """Test retrieving single application details."""
    resp = client.get("/api/applications/1", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["company"] == "Google"
    assert data["jd_hash"] == "hash_google"
    assert data["fit_summary"] == "Great fit for AI role"
    assert "days_since_update" in data


def test_get_application_not_found(client, test_db):
    """Test 404 for nonexistent application ID."""
    resp = client.get("/api/applications/9999", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert resp.status_code == 404


def test_patch_application_status_valid(client, test_db):
    """Test updating application status to Interview and verifying write isolation."""
    resp = client.patch(
        "/api/applications/1",
        json={"status": "Interview"},
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Interview"

    # Verify directly in SQLite DB that other fields were untouched
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM applications WHERE id = 1").fetchone()
    conn.close()

    assert row["status"] == "Interview"
    assert row["company"] == "Google"
    assert row["role"] == "AI Engineer"
    assert row["drive_file_id"] == "drive_1"
    assert row["jd_hash"] == "hash_google"


def test_patch_application_status_invalid_rejected_400(client, test_db):
    """Test updating status with invalid value returns 422/400 validation error."""
    resp = client.patch(
        "/api/applications/1",
        json={"status": "InvalidStatusXYZ"},
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )
    assert resp.status_code == 422 or resp.status_code == 400


def test_patch_application_not_found(client, test_db):
    """Test patching nonexistent application returns 404."""
    resp = client.patch(
        "/api/applications/9999",
        json={"status": "Offer"},
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )
    assert resp.status_code == 404


def test_get_stats(client, test_db):
    """Test GET /api/stats returns correct counts."""
    resp = client.get("/api/stats", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["applied"] == 1
    assert stats["interview"] == 1
    assert stats["rejected"] == 1
    assert stats["offer"] == 0
    assert stats["total"] == 3
