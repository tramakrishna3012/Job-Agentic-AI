"""
DriveClient module.
Interacts with Google Drive API using the restricted 'drive.file' OAuth scope
to organize, upload, and update tailored resumes under /JobApplications/{Company}/{CandidateName}.pdf.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("jaa.drive")

# Restricted OAuth scope - strictly files created/opened by this app
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveClient:
    """Client for Google Drive API operations with restricted scope."""

    def __init__(
        self,
        client_secret_path: Optional[str] = None,
        token_path: str = "token.json",
    ) -> None:
        self.client_secret_path = client_secret_path or os.getenv(
            "GOOGLE_OAUTH_CLIENT_SECRET_PATH", "credentials.json"
        )
        self.token_path = Path(token_path)
        self._service = None

    def authenticate(self) -> None:
        """Authenticate with Google OAuth 2.0 and cache token locally."""
        creds: Optional[Credentials] = None

        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), DRIVE_SCOPES
                )
            except Exception as exc:
                logger.warning(f"Existing token.json could not be loaded: {exc}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    logger.warning(f"Token refresh failed: {exc}. Starting new OAuth flow.")
                    creds = None

            if not creds:
                if not Path(self.client_secret_path).exists():
                    raise FileNotFoundError(
                        f"Google OAuth client secrets file not found at: '{self.client_secret_path}'. "
                        "Please download OAuth 2.0 Client ID credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_path, DRIVE_SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future runs
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            try:
                # Set restrictive file permissions where supported
                os.chmod(self.token_path, 0o600)
            except Exception:
                pass

        self._service = build("drive", "v3", credentials=creds)

    @property
    def service(self):
        """Get or initialize Google Drive service."""
        if self._service is None:
            self.authenticate()
        return self._service

    def _find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """Find an existing folder or create a new one under parent_id."""
        query_parts = [
            f"name = '{folder_name}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")
        else:
            query_parts.append("'root' in parents")

        query = " and ".join(query_parts)
        response = (
            self.service.files()
            .list(q=query, spaces="drive", fields="files(id, name)")
            .execute()
        )
        files = response.get("files", [])
        if files:
            return files[0]["id"]

        # Create folder
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            folder_metadata["parents"] = [parent_id]

        folder = (
            self.service.files()
            .create(body=folder_metadata, fields="id")
            .execute()
        )
        return folder["id"]

    def upload_or_update_resume(
        self,
        local_pdf_path: str,
        company: str,
        candidate_name: str,
        existing_file_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Upload or update a resume PDF under /JobApplications/{Company}/{CandidateName}.pdf.
        Returns: (file_id, web_view_link)
        """
        pdf_path = Path(local_pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Local resume PDF not found: {local_pdf_path}")

        # Sanitize filename
        safe_candidate_name = "".join(c for c in candidate_name if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"{safe_candidate_name}.pdf" if safe_candidate_name else "Resume.pdf"

        media = MediaFileUpload(str(pdf_path), mimetype="application/pdf", resumable=True)

        # If existing_file_id is provided, try updating directly
        if existing_file_id:
            try:
                updated_file = (
                    self.service.files()
                    .update(
                        fileId=existing_file_id,
                        media_body=media,
                        fields="id, name, webViewLink",
                    )
                    .execute()
                )
                file_id = updated_file["id"]
                link = updated_file.get(
                    "webViewLink", f"https://drive.google.com/file/d/{file_id}/view"
                )
                logger.info(f"Updated existing Drive file {file_id} for {company}")
                return file_id, link
            except Exception as exc:
                logger.warning(
                    f"Could not update file by ID {existing_file_id}: {exc}. Checking folder."
                )

        # Ensure folder hierarchy: /JobApplications/{Company}
        root_app_folder_id = self._find_or_create_folder("JobApplications")
        company_folder_id = self._find_or_create_folder(company, parent_id=root_app_folder_id)

        # Check if file with same name exists in company folder
        file_query = (
            f"name = '{filename}' and '{company_folder_id}' in parents and trashed = false"
        )
        file_response = (
            self.service.files()
            .list(q=file_query, spaces="drive", fields="files(id, name, webViewLink)")
            .execute()
        )
        existing_files = file_response.get("files", [])

        if existing_files:
            target_id = existing_files[0]["id"]
            updated_file = (
                self.service.files()
                .update(
                    fileId=target_id,
                    media_body=media,
                    fields="id, name, webViewLink",
                )
                .execute()
            )
            file_id = updated_file["id"]
            link = updated_file.get(
                "webViewLink", f"https://drive.google.com/file/d/{file_id}/view"
            )
            logger.info(f"Updated existing file in folder {company}: {file_id}")
            return file_id, link

        # Create new file in company folder
        file_metadata = {
            "name": filename,
            "parents": [company_folder_id],
        }
        created_file = (
            self.service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink",
            )
            .execute()
        )
        file_id = created_file["id"]
        link = created_file.get(
            "webViewLink", f"https://drive.google.com/file/d/{file_id}/view"
        )
        logger.info(f"Created new Drive file for {company}: {file_id}")
        return file_id, link
