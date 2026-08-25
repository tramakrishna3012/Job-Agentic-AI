"""
Comprehensive test suite for Phase 0 JAA Pipeline.
Tests SQLite tracker, Jinja2 template rendering, PDF generation,
master resume schema validation, Notifier (ntfy + CallMeBot + Twilio),
TailorEngine (OpenAI + Gemini providers), DriveClient, and CLI flow.
"""

from __future__ import annotations

import json
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
from tailor import GEMINI_OPENAI_BASE_URL, TailorEngine
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


def test_tailor_engine_openai_provider_mock(sample_resume_data):
    """Test TailorEngine with OpenAI provider produces expected return shape."""
    with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4o-mini"}):
        engine = TailorEngine(provider="openai", api_key="sk-test-mock-key")
        assert engine.provider == "openai"
        assert engine.active_model == "gpt-4o-mini"

        mock_llm_response = sample_resume_data.copy()
        mock_llm_response["fit_summary"] = "Strong alignment with backend role."
        mock_llm_response["match_score"] = 91

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_llm_response)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        with patch.object(engine, "_client", MagicMock()) as mock_client:
            mock_client.chat.completions.create.return_value = mock_resp
            tailored, fit_summary, score = engine.tailor_resume(
                master_resume=sample_resume_data,
                jd_text="Need senior Python engineer.",
                company="Acme Corp",
                role="Senior Engineer",
            )
            assert tailored["name"] == "Jane Doe"
            assert fit_summary == "Strong alignment with backend role."
            assert score == 91
            mock_client.chat.completions.create.assert_called_once()


def test_tailor_engine_gemini_provider_mock(sample_resume_data):
    """Test TailorEngine with Gemini provider produces identical return shape."""
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.7-flash"}):
        engine = TailorEngine(provider="gemini", api_key="AIzaSyTestMockKey")
        assert engine.provider == "gemini"
        assert engine.active_model == "gemini-3.7-flash"

        mock_llm_response = sample_resume_data.copy()
        mock_llm_response["fit_summary"] = "Exceptional fit with distributed systems skills."
        mock_llm_response["match_score"] = 96

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_llm_response)
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        with patch.object(engine, "_client", MagicMock()) as mock_client:
            mock_client.chat.completions.create.return_value = mock_resp
            tailored, fit_summary, score = engine.tailor_resume(
                master_resume=sample_resume_data,
                jd_text="Need distributed systems engineer.",
                company="Globex Inc",
                role="Staff Engineer",
            )
            assert tailored["name"] == "Jane Doe"
            assert fit_summary == "Exceptional fit with distributed systems skills."
            assert score == 96
            mock_client.chat.completions.create.assert_called_once()


def test_tailor_engine_provider_selection():
    """Test provider selection and error on missing keys."""
    # Test unsupported provider
    engine_bad = TailorEngine(provider="unsupported_provider", api_key="test")
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        _ = engine_bad.client

    # Test missing Gemini key
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}, clear=True):
        engine_gemini_nokey = TailorEngine()
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            _ = engine_gemini_nokey.client

    # Test missing OpenAI key
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
        engine_openai_nokey = TailorEngine()
        with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
            _ = engine_openai_nokey.client


def test_notifier_message_formatting():
    """Test message format matches design.md Section 5 template."""
    notifier = Notifier(ntfy_topic="jaa_test_topic")
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


def test_ntfy_notifier_send_with_mock():
    """Test ntfy push notification dispatch with mocked HTTP request."""
    notifier = Notifier(
        provider="ntfy",
        ntfy_topic="jaa_alerts_test",
    )
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = b'{"id":"123","event":"message"}'
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        ref_id = notifier.send_notification(
            role="Backend Engineer",
            company="Acme Corp",
            match_score=95,
            fit_summary="ntfy fit summary.",
            drive_link="https://drive.google.com/file/d/123/view",
        )
        assert ref_id == "ntfy_ok"


def test_callmebot_notifier_send_with_mock():
    """Test CallMeBot WhatsApp dispatch with mocked HTTP request."""
    notifier = Notifier(
        provider="callmebot",
        callmebot_phone="+919876543210",
        callmebot_api_key="test_callmebot_key",
    )
    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = b"Message queued"
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        ref_id = notifier.send_notification(
            role="Backend Engineer",
            company="Acme Corp",
            match_score=95,
            fit_summary="CallMeBot fit summary.",
            drive_link="https://drive.link",
        )
        assert ref_id == "callmebot_ok"


def test_twilio_notifier_send_with_mock():
    """Test Twilio WhatsApp dispatch with mocked client."""
    notifier = Notifier(
        provider="twilio",
        twilio_account_sid="ACmock",
        twilio_auth_token="authmock",
        twilio_from="+14155238886",
        twilio_to="+1234567890",
    )
    mock_msg = MagicMock()
    mock_msg.sid = "SM123456789"

    with patch.object(notifier, "_twilio_client", MagicMock()) as mock_client:
        mock_client.messages.create.return_value = mock_msg
        sid = notifier.send_notification(
            role="Backend Engineer",
            company="Acme Corp",
            match_score=90,
            fit_summary="Fit summary line.",
            drive_link="https://drive.link",
        )
        assert sid == "SM123456789"


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
            local_pdf_path="resume.yaml",
            company="Globex Corp",
            candidate_name="Jane Doe",
        )
        assert file_id == "file_abc_123"
        assert "file_abc_123" in link


def test_pipeline_dry_run(sample_resume_data):
    """Test running the full pipeline in dry-run mode with mocked LLM engine."""
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
