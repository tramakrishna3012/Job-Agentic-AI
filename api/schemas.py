"""
Pydantic data schemas and validation models for Phase 1 REST API.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_STATUSES = {"Applied", "Interview", "Rejected", "Offer"}


class StatusUpdateRequest(BaseModel):
    """Payload for PATCH /api/applications/{id}."""
    status: str = Field(..., description="Target status: Applied, Interview, Rejected, or Offer")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        trimmed = value.strip()
        # Case-insensitive normalization against allowed statuses
        for allowed in ALLOWED_STATUSES:
            if trimmed.lower() == allowed.lower():
                return allowed
        raise ValueError(
            f"Invalid status '{value}'. Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}"
        )


class ApplicationSummary(BaseModel):
    """Summary schema for list view."""
    id: int
    company: str
    role: str
    date_applied: str
    status: str
    match_score: Optional[int] = None
    drive_link: Optional[str] = None
    days_since_update: int

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetail(BaseModel):
    """Detailed schema for single application view."""
    id: int
    company: str
    role: str
    date_applied: str
    status: str
    match_score: Optional[int] = None
    drive_link: Optional[str] = None
    jd_hash: Optional[str] = None
    fit_summary: Optional[str] = None
    days_since_update: int

    model_config = ConfigDict(from_attributes=True)


class StatsResponse(BaseModel):
    """Aggregated application status statistics."""
    applied: int = 0
    interview: int = 0
    rejected: int = 0
    offer: int = 0
    total: int = 0
