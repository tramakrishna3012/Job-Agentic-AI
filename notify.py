"""
Notifier module.
Dispatches WhatsApp status notifications using either:
1. CallMeBot (100% free personal WhatsApp API gateway, default)
2. Twilio WhatsApp REST API
using the exact template specified in design.md Section 5.
"""

from __future__ import annotations

import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger("jaa.notify")


class Notifier:
    """WhatsApp notifier supporting CallMeBot and Twilio."""

    def __init__(
        self,
        provider: Optional[str] = None,
        # CallMeBot configs
        callmebot_phone: Optional[str] = None,
        callmebot_api_key: Optional[str] = None,
        # Twilio configs
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_from: Optional[str] = None,
        twilio_to: Optional[str] = None,
        max_retries: int = 3,
    ) -> None:
        self.callmebot_phone = callmebot_phone or os.getenv("CALLMEBOT_PHONE")
        self.callmebot_api_key = callmebot_api_key or os.getenv("CALLMEBOT_API_KEY")

        self.twilio_account_sid = twilio_account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = twilio_auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = twilio_from or os.getenv("TWILIO_WHATSAPP_FROM")
        self.twilio_to = twilio_to or os.getenv("YOUR_WHATSAPP_TO")

        self.max_retries = max_retries
        self._twilio_client = None

        # Auto-detect provider if not explicitly given
        if provider:
            self.provider = provider.lower()
        elif self.callmebot_api_key and self.callmebot_phone:
            self.provider = "callmebot"
        elif self.twilio_account_sid and self.twilio_auth_token:
            self.provider = "twilio"
        else:
            # Default to callmebot
            self.provider = "callmebot"

    @property
    def twilio_client(self):
        """Lazy initializer for Twilio Client."""
        if self._twilio_client is None:
            if not self.twilio_account_sid or not self.twilio_auth_token:
                raise ValueError(
                    "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be configured in environment."
                )
            from twilio.rest import Client  # type: ignore

            self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        return self._twilio_client

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

    def _send_via_callmebot(self, message_text: str) -> str:
        """Send message via CallMeBot free WhatsApp gateway."""
        if not self.callmebot_phone or not self.callmebot_api_key:
            raise ValueError(
                "CALLMEBOT_PHONE and CALLMEBOT_API_KEY must be configured in your .env file."
            )

        # Sanitize phone number (remove spaces, dashes, parentheses)
        phone = "".join(c for c in self.callmebot_phone if c.isdigit() or c == "+")
        params = {
            "phone": phone,
            "text": message_text,
            "apikey": self.callmebot_api_key.strip(),
        }
        query_string = urllib.parse.urlencode(params)
        url = f"https://api.callmebot.com/whatsapp.php?{query_string}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JAA-Agent/1.0"},
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            if status_code != 200 or "error" in body.lower():
                raise RuntimeError(f"CallMeBot API error (HTTP {status_code}): {body}")
            return "callmebot_ok"

    def _send_via_twilio(self, message_text: str) -> str:
        """Send message via Twilio WhatsApp API."""
        if not self.twilio_from or not self.twilio_to:
            raise ValueError(
                "TWILIO_WHATSAPP_FROM and YOUR_WHATSAPP_TO must be configured for Twilio."
            )

        from_number = self.twilio_from
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        to_number = self.twilio_to
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        msg = self.twilio_client.messages.create(
            body=message_text,
            from_=from_number,
            to=to_number,
        )
        return msg.sid

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
        Returns the notification reference ID.
        """
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
                if self.provider == "callmebot":
                    ref_id = self._send_via_callmebot(body)
                    logger.info("WhatsApp notification delivered via CallMeBot")
                    return ref_id
                elif self.provider == "twilio":
                    ref_id = self._send_via_twilio(body)
                    logger.info(f"WhatsApp notification delivered via Twilio (SID: {ref_id})")
                    return ref_id
                else:
                    raise ValueError(f"Unknown notification provider: {self.provider}")
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"{self.provider.capitalize()} notification attempt {attempt}/{self.max_retries} failed: {exc}"
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)

        raise RuntimeError(
            f"Failed to send WhatsApp notification via {self.provider} after {self.max_retries} attempts: {last_exception}"
        ) from last_exception
