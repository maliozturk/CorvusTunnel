"""
CorvusTunnel Internal Application — Port 8001.

Runs ONLY on 127.0.0.1. Provides admin views and system status.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from routers.internal import router as internal_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel Internal",
    description="Local-only admin API",
    version="0.2.0",
    docs_url="/docs",
)

# ── Mount internal router ────────────────────────────────────────────
app.include_router(internal_router)


@app.get("/", include_in_schema=False)
async def root():
    """Internal API root."""
    return {
        "service": "CorvusTunnel Internal API",
        "version": "0.2.0",
        "endpoints": [
            "GET  /audit",
            "GET  /deeplog",
            "GET  /terminal/status",
            "GET  /docs",
        ],
    }
