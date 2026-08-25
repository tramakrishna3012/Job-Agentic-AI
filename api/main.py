"""
FastAPI application for Phase 1 Tracking Dashboard.
Serves both REST API endpoints and static Next.js frontend from a single process.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.auth import get_dashboard_token, verify_dashboard_token
from api.db import get_application_by_id, get_stats, list_applications, update_status
from api.schemas import ApplicationDetail, ApplicationSummary, StatsResponse, StatusUpdateRequest

app = FastAPI(
    title="Job Application Assistant (JAA) - Phase 1 Dashboard API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Enable CORS for local Next.js development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Auth Token Endpoint (Optional Cookie Helper)
# ------------------------------------------------------------------------------
@app.post("/api/auth/login")
def login_dashboard(token_input: str = Query(..., description="DASHBOARD_TOKEN to verify"), response: Response = None):
    """Verify DASHBOARD_TOKEN and set httpOnly cookie."""
    expected = get_dashboard_token()
    if token_input.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard token.",
        )
    if response:
        response.set_cookie(
            key="dashboard_token",
            value=expected,
            httponly=True,
            samesite="lax",
            secure=False,  # Set to False for local localhost usage
        )
    return {"status": "authenticated"}


# ------------------------------------------------------------------------------
# Phase 1 REST API Endpoints (All protected by DASHBOARD_TOKEN)
# ------------------------------------------------------------------------------
@app.get(
    "/api/applications",
    response_model=List[ApplicationSummary],
    dependencies=[Depends(verify_dashboard_token)],
    summary="List all tracked applications (filterable by status)",
)
def get_applications(status: Optional[str] = None):
    """Retrieve all tailored applications, optionally filtered by status (Applied/Interview/Rejected/Offer)."""
    return list_applications(status_filter=status)


@app.get(
    "/api/applications/{id}",
    response_model=ApplicationDetail,
    dependencies=[Depends(verify_dashboard_token)],
    summary="Retrieve single application detail",
)
def get_application(id: int):
    """Retrieve detailed view for an application by ID."""
    record = get_application_by_id(id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found.",
        )
    return record


@app.patch(
    "/api/applications/{id}",
    response_model=ApplicationDetail,
    dependencies=[Depends(verify_dashboard_token)],
    summary="Update application status",
)
def patch_application_status(id: int, payload: StatusUpdateRequest):
    """
    Update strictly the status field of an application.
    Validates that status is one of: Applied, Interview, Rejected, Offer.
    """
    updated = update_status(id, payload.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {id} not found.",
        )
    return updated


@app.get(
    "/api/stats",
    response_model=StatsResponse,
    dependencies=[Depends(verify_dashboard_token)],
    summary="Application counts by status",
)
def get_application_stats():
    """Retrieve total counts grouped by application status."""
    return get_stats()


# ------------------------------------------------------------------------------
# Static Frontend Serving (Single Process)
# ------------------------------------------------------------------------------
DASHBOARD_OUT_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "out"

if DASHBOARD_OUT_DIR.exists():
    app.mount("/_next", StaticFiles(directory=str(DASHBOARD_OUT_DIR / "_next")), name="next_assets")
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_OUT_DIR)), name="static_dashboard")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend_or_fallback(full_path: str):
    """Serve built Next.js export or fallback landing page."""
    # Prevent intercepting API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API route not found.")

    if DASHBOARD_OUT_DIR.exists():
        target_file = DASHBOARD_OUT_DIR / full_path
        if target_file.is_file():
            return FileResponse(target_file)

        # Look for index.html or target/index.html (Next.js static export format)
        index_file = DASHBOARD_OUT_DIR / full_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        root_index = DASHBOARD_OUT_DIR / "index.html"
        if root_index.is_file():
            return FileResponse(root_index)

    # Fallback if dashboard is not built yet
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
        <head>
            <title>JAA Tracking Dashboard</title>
            <style>
                body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .card { background: #1e293b; padding: 2rem; border-radius: 12px; border: 1px solid #334155; max-width: 500px; text-align: center; }
                h1 { color: #38bdf8; margin-bottom: 0.5rem; }
                code { background: #0f172a; padding: 0.2rem 0.4rem; border-radius: 4px; color: #fbbf24; }
                a { color: #38bdf8; text-decoration: none; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🚀 JAA Dashboard API is Running</h1>
                <p>FastAPI backend is active on this port.</p>
                <p>To view the full React Dashboard, build the Next.js frontend with:<br><br><code>npm --prefix dashboard run build</code></p>
                <p>View Swagger API Documentation: <a href="/api/docs">/api/docs</a></p>
            </div>
        </body>
        </html>
        """
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
