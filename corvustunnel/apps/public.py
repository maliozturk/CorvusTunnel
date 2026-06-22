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
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from corvustunnel.middleware.rate_limit import setup_rate_limiting
from corvustunnel.middleware.security_headers import add_security_headers
from corvustunnel.routers.channel import router as channel_router
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

MAX_BODY_BYTES = 4096


@app.middleware("http")
async def body_size_limiter(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > MAX_BODY_BYTES:
            return Response(
                content='{"detail":"Payload too large"}',
                status_code=413,
                media_type="application/json",
            )
    return await call_next(request)


app.include_router(public_router)
app.include_router(channel_router)

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/", include_in_schema=False)
async def serve_root():
    return RedirectResponse(url="/app/")


@app.get("/health", include_in_schema=False)
async def root_health(request: Request):
    from corvustunnel.routers.public import health

    return await health(request)


app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="app")
