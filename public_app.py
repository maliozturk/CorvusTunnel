"""
CorvusTunnel Public Application — Port 8000.

Serves:
- /api/* — Public REST API (authenticated)
- /       — Terminal UI (static HTML)
- /health — Health check (no auth)
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers.public import router as public_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel",
    description="Remote Agent Control System",
    version="0.2.0",
    docs_url="/docs",
    redoc_url=None,
)

# ── CORS (allow all for Cloudflare Quick Tunnel random domains) ──────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API router ─────────────────────────────────────────────────
app.include_router(public_router)

# ── Serve Chat UI ────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def serve_ui():
    """Serve the terminal UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "CorvusTunnel API is running. Chat UI not found."}


# Health check at root level too (for Cloudflare health checks)
@app.get("/health", include_in_schema=False)
async def root_health():
    """Root-level health check (redirects to API health)."""
    from routers.public import health
    return await health()


# ── Mount static assets (vendor JS/CSS) ──────────────────────────────
# Must come AFTER explicit routes so / still serves index.html
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
