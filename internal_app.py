"""
CorvusTunnel Internal Application — Port 8001.

Runs ONLY on 127.0.0.1. Handles job approval/rejection.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from routers.internal import router as internal_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel Internal",
    description="Local-only admin API for job approval",
    version="0.1.0",
    docs_url="/docs",
)

# ── Mount internal router ────────────────────────────────────────────
app.include_router(internal_router)


@app.get("/", include_in_schema=False)
async def root():
    """Internal API root."""
    from jobqueue.manager import get_job_manager
    manager = get_job_manager()
    pending = await manager.get_pending()
    return {
        "service": "CorvusTunnel Internal API",
        "pending_jobs": len(pending),
        "endpoints": [
            "POST /approve/{job_id}",
            "POST /reject/{job_id}",
            "GET  /pending",
            "GET  /audit",
            "GET  /docs",
        ],
    }
