# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/routers/public.py
# Description: Public REST surface. Everything authenticated now runs inside
#              the encrypted channel (routers/channel.py); only the
#              unauthenticated liveness probe remains here.
# \*---------------------------------------------------------------------*/

import logging
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

from corvustunnel.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

_start_time = time.time()


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health(request: Request):
    from corvustunnel.version import __version__

    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_seconds=round(time.time() - _start_time, 1),
    )
