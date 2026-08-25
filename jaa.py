#!/usr/bin/env python3
"""
Job Application Assistant (JAA) - Phase 0 CLI Orchestrator.
Automates the resume tailoring, PDF generation, Google Drive filing,
SQLite tracking, and notification pipeline.

Usage:
  python jaa.py --company "Acme Corp" --role "Backend Engineer" --jd jd.txt
  python jaa.py --company "Acme Corp" --role "Backend Engineer" --jd - < jd.txt
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import pipeline modules
from drive_client import DriveClient
from notify import Notifier
from render import ResumeRenderer
from tailor import TailorEngine
from tracker import Tracker

# Configure clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jaa")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Job Application Assistant (JAA) - Automated Resume Tailoring & Notification Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--company",
        "-c",
        required=True,
        help="Target company name (e.g. 'Acme Corp')",
    )
    parser.add_argument(
        "--role",
        "-r",
        required=True,
        help="Target role title (e.g. 'Senior Backend Engineer')",
    )
    parser.add_argument(
        "--jd",
        "-j",
        required=True,
        help="Path to job description text file, or '-' to read from stdin",
    )
    parser.add_argument(
        "--resume",
        default=os.getenv("MASTER_RESUME_PATH", "resume.yaml"),
        help="Path to structured master resume file (YAML or JSON)",
    )
    parser.add_argument(
        "--output-pdf",
        "-o",
        default=None,
        help="Optional local output path to save the generated PDF",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("DB_PATH", "jaa.db"),
        help="Path to local SQLite tracking database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run tailoring and PDF generation locally without uploading to Drive or sending WhatsApp",
    )
    return parser.parse_args()


def read_job_description(jd_source: str) -> str:
    """Read job description from a file or standard input."""
    if jd_source == "-":
        if sys.stdin.isatty():
            print("Reading Job Description from stdin. Press Ctrl+Z (Windows) or Ctrl+D (Unix) then Enter to finish:")
        jd_text = sys.stdin.read().strip()
    else:
        path = Path(jd_source)
        if not path.exists():
            raise FileNotFoundError(f"Job description file not found at: {jd_source}")
        jd_text = path.read_text(encoding="utf-8").strip()

    if not jd_text:
        raise ValueError("Job description is empty. Please provide valid text.")
    return jd_text


def run_pipeline(
    company: str,
    role: str,
    jd_source: str,
    resume_path: str = "resume.yaml",
    output_pdf_path: Optional[str] = None,
    db_path: str = "jaa.db",
    dry_run: bool = False,
) -> None:
    """Execute the Phase 0 end-to-end tailoring and notification pipeline."""
    pipeline_start = time.time()
    company = company.strip()
    role = role.strip()

    print(f"\n🚀 [JAA] Starting pipeline for {role} @ {company}")
    print("=" * 60)

    # 1. Read Inputs
    jd_text = read_job_description(jd_source)
    tailor_engine = TailorEngine()
    jd_hash = tailor_engine.compute_jd_hash(jd_text)

    # Load master resume
    master_resume = tailor_engine.load_master_resume(resume_path)
    candidate_name = master_resume.get("name", "Resume")

    # 2. Stage 1: Tailoring via OpenAI
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    print(f"\n[1/5] 🤖 Tailoring resume with OpenAI ({model_name}, strict truthfulness contract)...")
    tailor_start = time.time()
    try:
        tailored_resume, fit_summary, match_score = tailor_engine.tailor_resume(
            master_resume=master_resume,
            jd_text=jd_text,
            company=company,
            role=role,
        )
        print(f"      ✓ Completed in {time.time() - tailor_start:.2f}s")
        print(f"      ✓ Match Score: {match_score}/100")
        print(f"      ✓ Fit Summary: {fit_summary}")
    except Exception as exc:
        print(f"      ❌ Stage 1 (Tailoring) failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # 3. Stage 2: Render ATS-safe PDF
    print(f"\n[2/5] 📄 Rendering ATS-safe PDF with Jinja2...")
    render_start = time.time()
    temp_pdf_file = None
    try:
        renderer = ResumeRenderer()
        if output_pdf_path:
            pdf_dest = output_pdf_path
        else:
            temp_dir = tempfile.gettempdir()
            safe_comp = "".join(c for c in company if c.isalnum() or c in (" ", "_", "-")).strip()
            pdf_dest = os.path.join(temp_dir, f"{safe_comp}_{candidate_name.replace(' ', '_')}.pdf")
            temp_pdf_file = pdf_dest

        renderer.render_pdf(tailored_resume, pdf_dest)
        print(f"      ✓ PDF generated at: {pdf_dest} in {time.time() - render_start:.2f}s")
    except Exception as exc:
        print(f"      ❌ Stage 2 (Rendering) failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # 4. Stage 3: Google Drive Upload / In-Place Update
    drive_file_id: Optional[str] = None
    drive_link: str = f"local://{pdf_dest}"

    # Initialize tracker early to query existing file IDs
    tracker = Tracker(db_path=db_path)
    existing_app = tracker.get_application(company, role)
    existing_drive_id = existing_app.get("drive_file_id") if existing_app else None

    if dry_run:
        print(f"\n[3/5] ☁️ [DRY-RUN] Skipping Google Drive upload.")
    else:
        print(f"\n[3/5] ☁️ Syncing with Google Drive (/JobApplications/{company}/{candidate_name}.pdf)...")
        drive_start = time.time()
        try:
            drive_client = DriveClient()
            drive_file_id, drive_link = drive_client.upload_or_update_resume(
                local_pdf_path=pdf_dest,
                company=company,
                candidate_name=candidate_name,
                existing_file_id=existing_drive_id,
            )
            print(f"      ✓ Drive File ID: {drive_file_id}")
            print(f"      ✓ Drive Link: {drive_link} ({time.time() - drive_start:.2f}s)")
        except Exception as exc:
            print(f"      ❌ Stage 3 (Google Drive) failed: {exc}", file=sys.stderr)
            print("      (Halting pipeline. No false notification will be sent.)", file=sys.stderr)
            sys.exit(1)

    # 5. Stage 4: Local SQLite Tracking Log
    print(f"\n[4/5] 🗄️ Recording application in SQLite ({db_path})...")
    try:
        app_record = tracker.log_application(
            company=company,
            role=role,
            jd_hash=jd_hash,
            drive_link=drive_link,
            drive_file_id=drive_file_id,
            match_score=match_score,
            fit_summary=fit_summary,
            status="Tailored",
        )
        print(f"      ✓ Application record ID #{app_record.get('id')} saved/updated successfully.")
    except Exception as exc:
        print(f"      ❌ Stage 4 (SQLite Tracking) failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # 6. Stage 5: Push Notification
    if dry_run:
        print(f"\n[5/5] 📱 [DRY-RUN] Skipping push notification.")
    else:
        print(f"\n[5/5] 📱 Sending notification via {os.getenv('NTFY_TOPIC', 'ntfy')}...")
        notify_start = time.time()
        try:
            notifier = Notifier()
            ref_id = notifier.send_notification(
                role=role,
                company=company,
                match_score=match_score,
                fit_summary=fit_summary,
                drive_link=drive_link,
            )
            print(f"      ✓ Notification sent! (Ref: {ref_id}) in {time.time() - notify_start:.2f}s")
        except Exception as exc:
            print(f"      ❌ Stage 5 (Notification) failed: {exc}", file=sys.stderr)
            sys.exit(1)

    # Pipeline Completion
    total_duration = time.time() - pipeline_start
    print("\n" + "=" * 60)
    print(f"🎉 All pipeline stages completed successfully in {total_duration:.2f}s!")
    print(f"   Target: {role} @ {company}")
    print(f"   Match Score: {match_score}/100")
    print(f"   Link: {drive_link}")
    print("=" * 60 + "\n")


def main() -> None:
    args = parse_args()
    try:
        run_pipeline(
            company=args.company,
            role=args.role,
            jd_source=args.jd,
            resume_path=args.resume,
            output_pdf_path=args.output_pdf,
            db_path=args.db_path,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"\n❌ Unhandled error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
