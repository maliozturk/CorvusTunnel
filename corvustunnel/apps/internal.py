# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/apps/internal.py
# Description: Internal FastAPI app (port 8001, localhost only): admin
#              and status views.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import logging

from fastapi import FastAPI

from corvustunnel.routers.internal import router as internal_router
from corvustunnel.version import __version__

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CorvusTunnel Internal",
    description="Local-only admin API",
    version=__version__,
    docs_url="/docs",
)

app.include_router(internal_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "CorvusTunnel Internal API",
        "version": __version__,
        "endpoints": [
            "GET  /audit",
            "GET  /deeplog",
            "GET  /terminal/status",
            "GET  /docs",
        ],
    }
