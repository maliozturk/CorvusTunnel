"""
CorvusTunnel Public Application — Port 8000.

Serves:
- /api/* — Public REST API (authenticated)
- /       — Terminal UI (static HTML)
- /health — Health check (no auth)

Security middleware chain (order matters):
1. IP Ban check (cheapest — rejects banned IPs immediately)
2. Body size limits (reject oversized payloads before parsing)
3. Security headers (added to every response)
4. CORS (restricted — no credentials)
5. Rate limiting (slowapi)
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from _version import __version__
from routers.public import router as public_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel",
    description="Remote Agent Control System",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)


# ── 1. Security Headers ─────────────────────────────────────────────
from middleware.security_headers import add_security_headers
add_security_headers(app)


# ── 2. CORS (no credentials — Bearer tokens don't need them) ────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,     # Fixed: was True (dangerous with *)
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── 3. Rate Limiting ────────────────────────────────────────────────
from middleware.rate_limit import setup_rate_limiting
setup_rate_limiting(app)


# ── 4. IP Ban Middleware ─────────────────────────────────────────────
from middleware.ip_ban import add_ip_ban_middleware
add_ip_ban_middleware(app)


# ── 5. Request Body Size Limits ──────────────────────────────────────
MAX_BODY_SIZES = {
    "/api/claim": 1024,          # 1 KB
    "/api/browse/mkdir": 1024,   # 1 KB
    "/api/ws-ticket": 512,       # 512 B
}
DEFAULT_MAX_BODY = 4096          # 4 KB


@app.middleware("http")
async def body_size_limiter(request: Request, call_next):
    """Reject oversized request bodies before parsing."""
    content_length = request.headers.get("content-length")
    if content_length:
        size = int(content_length)
        max_size = MAX_BODY_SIZES.get(request.url.path, DEFAULT_MAX_BODY)
        if size > max_size:
            return Response(
                content='{"detail":"Payload too large"}',
                status_code=413,
                media_type="application/json",
            )
    return await call_next(request)


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
async def root_health(request: Request):
    """Root-level health check (redirects to API health)."""
    from routers.public import health
    return await health(request)


# ── Mount static assets (vendor JS/CSS) ──────────────────────────────
# Must come AFTER explicit routes so / still serves index.html
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
