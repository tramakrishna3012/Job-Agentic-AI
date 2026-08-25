"""
Comprehensive test suite for Phase 0 JAA Pipeline.
Tests SQLite tracker, Jinja2 template rendering, PDF generation,
master resume schema validation, Notifier, DriveClient, and CLI flow.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from drive_client import DriveClient
from jaa import run_pipeline
from notify import Notifier
from render import ResumeRenderer, render_resume
from tailor import TailorEngine
from tracker import Tracker


@pytest.fixture
def sample_resume_data():
    """Fixture providing valid structured resume data."""
    return {
        "name": "Jane Doe",
        "contact": {
            "email": "jane.doe@example.com",
            "phone": "+1 (555) 019-2834",
            "location": "New York, NY",
            "linkedin": "https://linkedin.com/in/janedoe",
            "portfolio": "https://janedoe.dev",
        },
        "summary": "Experienced Software Engineer with a focus on scalable systems.",
        "experience": [
            {
                "company": "Tech Corp",
                "title": "Senior Backend Developer",
                "dates": "2020 - Present",
                "location": "New York, NY",
                "bullets": [
                    "Engineered RESTful APIs with Python and FastAPI serving 10M requests daily.",
                    "Optimized PostgreSQL database queries reducing latency by 30%.",
                ],
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "Columbia University",
                "dates": "2016 - 2020",
                "details": "Magna Cum Laude",
            }
        ],
        "skills": [
            {
                "category": "Languages",
                "items": ["Python", "SQL", "Go"],
            },
            {
                "category": "Tools",
                "items": ["Docker", "Git", "Kubernetes"],
            },
        ],
        "projects": [
            {
                "name": "FastCache",
                "link": "https://github.com/janedoe/fastcache",
                "description": "High performance caching system",
                "bullets": ["Implemented distributed LRU cache in Go."],
            }
        ],
    }


def test_tracker_upsert():
    """Test Tracker initializes SQLite table, inserts, and updates records on conflict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tracker.db")
        tracker = Tracker(db_path=db_path)

        # 1. Insert first record
        rec1 = tracker.log_application(
            company="Acme Corp",
            role="Backend Engineer",
            jd_hash="hash123",
            drive_link="https://drive.google.com/file/d/file1/view",
            drive_file_id="file1",
            match_score=88,
            fit_summary="Strong match for backend role.",
            status="Tailored",
        )
        assert rec1["company"] == "Acme Corp"
        assert rec1["role"] == "Backend Engineer"
        assert rec1["match_score"] == 88
        assert rec1["drive_file_id"] == "file1"

        # 2. Query application
        fetched = tracker.get_application("Acme Corp", "Backend Engineer")
        assert fetched is not None
        assert fetched["jd_hash"] == "hash123"

        # 3. Update existing record with new match_score and hash (in-place update)
        rec2 = tracker.log_application(
            company="Acme Corp",
            role="Backend Engineer",
            jd_hash="hash456",
            drive_link="https://drive.google.com/file/d/file1/view",
            drive_file_id="file1",
            match_score=95,
            fit_summary="Updated tailored summary.",
            status="Applied",
        )
        assert rec2["id"] == rec1["id"]
        assert rec2["match_score"] == 95
        assert rec2["jd_hash"] == "hash456"
        assert rec2["status"] == "Applied"

        # Ensure only 1 record exists in table
        all_apps = tracker.list_applications()
        assert len(all_apps) == 1


def test_render_html(sample_resume_data):
    """Test Jinja2 template rendering produces clean HTML with all resume sections."""
    renderer = ResumeRenderer()
    html_out = renderer.render_html(sample_resume_data)

    assert "Jane Doe" in html_out
    assert "jane.doe@example.com" in html_out
    assert "Tech Corp" in html_out
    assert "Senior Backend Developer" in html_out
    assert "Columbia University" in html_out
    assert "FastCache" in html_out
    assert "Python, SQL, Go" in html_out


def test_render_pdf_generation(sample_resume_data):
    """Test generating a physical PDF file from resume data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_resume.pdf")
        result_path = render_resume(sample_resume_data, pdf_path)

        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 1000  # Non-empty valid PDF


def test_load_master_resume():
    """Test loading and validating master resume from YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = os.path.join(tmpdir, "test_resume.yaml")
        sample_yaml = """
name: "Alex Tester"
contact:
  email: "alex@test.com"
  phone: "+123456789"
summary: "Tester summary"
experience: []
education: []
skills: []
projects: []
"""
        Path(yaml_path).write_text(sample_yaml, encoding="utf-8")

        loaded = TailorEngine.load_master_resume(yaml_path)
        assert loaded["name"] == "Alex Tester"
        assert loaded["contact"]["email"] == "alex@test.com"


def test_jd_hash_generation():
    """Test SHA256 hashing of job descriptions."""
    jd1 = "Senior Backend Engineer with Python and Kafka experience."
    jd2 = "Senior Backend Engineer with Python and Kafka experience.  "
    # Should strip whitespace and produce same hash
    h1 = TailorEngine.compute_jd_hash(jd1)
    h2 = TailorEngine.compute_jd_hash(jd2)
    assert h1 == h2
    assert len(h1) == 64


def test_notifier_message_formatting():
    """Test WhatsApp message format matches design.md Section 5 template."""
    notifier = Notifier(
        account_sid="ACtest",
        auth_token="authtest",
        whatsapp_from="whatsapp:+14155238886",
        whatsapp_to="whatsapp:+1234567890",
    )
    msg = notifier.format_message(
        role="Backend Engineer",
        company="Acme Corp",
        match_score=92,
        fit_summary="Strong match with 7+ yrs distributed systems experience.",
        drive_link="https://drive.google.com/file/d/123/view",
    )
    expected = (
        "✅ Resume tailored: Backend Engineer @ Acme Corp\n"
        "Match score: 92/100\n"
        "Strong match with 7+ yrs distributed systems experience.\n"
        "📄 https://drive.google.com/file/d/123/view"
    )
    assert msg == expected


def test_notifier_send_with_mock():
    """Test Notifier dispatch with mocked Twilio client."""
    notifier = Notifier(
        account_sid="ACmock",
        auth_token="authmock",
        whatsapp_from="+14155238886",
        whatsapp_to="+1234567890",
    )
    mock_msg = MagicMock()
    mock_msg.sid = "SM123456789"

    with patch.object(notifier, "_client", MagicMock()) as mock_client:
        mock_client.messages.create.return_value = mock_msg
        sid = notifier.send_notification(
            role="Backend Engineer",
            company="Acme Corp",
            match_score=90,
            fit_summary="Fit summary line.",
            drive_link="https://drive.link",
        )
        assert sid == "SM123456789"
        mock_client.messages.create.assert_called_once()


def test_drive_client_upload_with_mock():
    """Test DriveClient upload and folder hierarchy creation with mocked Drive service."""
    drive = DriveClient(client_secret_path="dummy.json")
    mock_service = MagicMock()

    # Mock list (folder check) -> empty, so creates folder
    mock_service.files().list().execute.return_value = {"files": []}
    mock_service.files().create().execute.return_value = {
        "id": "file_abc_123",
        "name": "Jane Doe.pdf",
        "webViewLink": "https://drive.google.com/file/d/file_abc_123/view",
    }

    with patch("drive_client.MediaFileUpload") as mock_media:
        mock_media.return_value = MagicMock()
        drive._service = mock_service
        file_id, link = drive.upload_or_update_resume(
            local_pdf_path="resume.yaml",  # existing file for existence check
            company="Globex Corp",
            candidate_name="Jane Doe",
        )
        assert file_id == "file_abc_123"
        assert "file_abc_123" in link


def test_pipeline_dry_run(sample_resume_data):
    """Test running the full pipeline in dry-run mode with mocked OpenAI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_pipeline.db")
        resume_yaml_path = os.path.join(tmpdir, "resume.yaml")
        jd_file_path = os.path.join(tmpdir, "jd.txt")
        out_pdf_path = os.path.join(tmpdir, "output.pdf")

        Path(resume_yaml_path).write_text(yaml.dump(sample_resume_data), encoding="utf-8")
        Path(jd_file_path).write_text("We are seeking a Python Backend Developer.", encoding="utf-8")

        mock_tailored = sample_resume_data.copy()
        mock_tailored["summary"] = "Tailored summary for Acme."

        with patch.object(
            TailorEngine,
            "tailor_resume",
            return_value=(mock_tailored, "100% fit for backend role.", 92),
        ):
            run_pipeline(
                company="Beta Corp",
                role="Backend Developer",
                jd_source=jd_file_path,
                resume_path=resume_yaml_path,
                output_pdf_path=out_pdf_path,
                db_path=db_path,
                dry_run=True,
            )

        # Check PDF was rendered
        assert os.path.exists(out_pdf_path)
        assert os.path.getsize(out_pdf_path) > 500

        # Check DB was written
        tracker = Tracker(db_path=db_path)
        app = tracker.get_application("Beta Corp", "Backend Developer")
        assert app is not None
        assert app["match_score"] == 92
        assert app["fit_summary"] == "100% fit for backend role."
