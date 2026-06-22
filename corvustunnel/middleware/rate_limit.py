# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/middleware/rate_limit.py
# Description: Per-IP request rate limiting via slowapi.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    ip = get_trusted_client_ip(request)
    return ip if ip != "unknown" else get_remote_address(request)


limiter = Limiter(key_func=get_real_ip)
"""Module-level ``Limiter`` instance used to decorate individual routes."""


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
