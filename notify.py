"""
Notifier module.
Dispatches WhatsApp status notifications via Twilio REST API
using the exact template specified in design.md Section 5.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from twilio.rest import Client

logger = logging.getLogger("jaa.notify")


class Notifier:
    """Twilio WhatsApp notifier."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        whatsapp_from: Optional[str] = None,
        whatsapp_to: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_from = whatsapp_from or os.getenv("TWILIO_WHATSAPP_FROM")
        self.whatsapp_to = whatsapp_to or os.getenv("YOUR_WHATSAPP_TO")
        self.max_retries = max_retries
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initializer for Twilio Client."""
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                raise ValueError(
                    "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be configured in environment."
                )
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def format_message(
        self,
        role: str,
        company: str,
        match_score: int,
        fit_summary: str,
        drive_link: str,
    ) -> str:
        """
        Format WhatsApp message following design.md Section 5:
        ✅ Resume tailored: {Role} @ {Company}
        Match score: {score}/100
        {fit_summary}
        📄 {drive_link}
        """
        return (
            f"✅ Resume tailored: {role} @ {company}\n"
            f"Match score: {match_score}/100\n"
            f"{fit_summary}\n"
            f"📄 {drive_link}"
        )

    def send_notification(
        self,
        role: str,
        company: str,
        match_score: int,
        fit_summary: str,
        drive_link: str,
    ) -> str:
        """
        Send WhatsApp notification with retry backoff.
        Returns the Twilio Message SID.
        """
        if not self.whatsapp_from or not self.whatsapp_to:
            raise ValueError(
                "TWILIO_WHATSAPP_FROM and YOUR_WHATSAPP_TO must be configured."
            )

        # Ensure whatsapp: prefix is present
        from_number = self.whatsapp_from
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        to_number = self.whatsapp_to
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        body = self.format_message(
            role=role,
            company=company,
            match_score=match_score,
            fit_summary=fit_summary,
            drive_link=drive_link,
        )

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                message = self.client.messages.create(
                    body=body,
                    from_=from_number,
                    to=to_number,
                )
                logger.info(
                    f"WhatsApp notification sent successfully (SID: {message.sid})"
                )
                return message.sid
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"Twilio WhatsApp attempt {attempt}/{self.max_retries} failed: {exc}"
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise RuntimeError(
            f"Failed to send WhatsApp notification after {self.max_retries} attempts: {last_exception}"
        ) from last_exception
