# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/apps/public.py
# Description: Public FastAPI app (port 8000): security middleware chain,
#              static UI, and the API router exposed through the relay.
# \*---------------------------------------------------------------------*/



import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from corvustunnel.middleware.ip_ban import add_ip_ban_middleware
from corvustunnel.middleware.rate_limit import setup_rate_limiting
from corvustunnel.middleware.security_headers import add_security_headers
from corvustunnel.routers.public import router as public_router
from corvustunnel.version import __version__

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel",
    description="Remote Agent Control System",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
)

add_security_headers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

setup_rate_limiting(app)

add_ip_ban_middleware(app)

MAX_BODY_SIZES = {
    "/api/claim": 1024,
    "/api/browse/mkdir": 1024,
    "/api/ws-ticket": 512,
}
DEFAULT_MAX_BODY = 4096


@app.middleware("http")
async def body_size_limiter(request: Request, call_next):
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


app.include_router(public_router)

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/", include_in_schema=False)
async def serve_ui():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "CorvusTunnel API is running. Chat UI not found."}


@app.get("/health", include_in_schema=False)
async def root_health(request: Request):
    from corvustunnel.routers.public import health

    return await health(request)


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
