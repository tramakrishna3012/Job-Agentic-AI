"""
Authentication module for FastAPI endpoints.
Protects all /api/* routes using a shared secret bearer token (DASHBOARD_TOKEN).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_bearer = HTTPBearer(auto_error=False)


def get_dashboard_token() -> str:
    """Retrieve DASHBOARD_TOKEN from environment."""
    token = os.getenv("DASHBOARD_TOKEN")
    if not token:
        # Fallback default if not explicitly provided in environment
        return "jaa_secret_token_alex_2026"
    return token.strip()


def verify_dashboard_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> str:
    """
    Validate that incoming request has a valid Bearer token matching DASHBOARD_TOKEN.
    Also supports reading from 'dashboard_token' cookie or header for browser requests.
    """
    expected_token = get_dashboard_token()
    token: Optional[str] = None

    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
    elif "Authorization" in request.headers:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    elif "dashboard_token" in request.cookies:
        token = request.cookies.get("dashboard_token", "").strip()

    if not token or token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing dashboard authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
