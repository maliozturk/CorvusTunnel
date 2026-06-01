"""
CorvusTunnel Rate Limiting Middleware.

Uses slowapi to enforce per-IP rate limits on API endpoints.
The custom key function prefers ``X-Forwarded-For`` so that rate limits
apply to the real client IP behind a reverse proxy.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_real_ip(request: Request) -> str:
    """Return the real client IP, checking ``X-Forwarded-For`` first.

    Falls back to :func:`slowapi.util.get_remote_address` when the
    proxy header is absent.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_real_ip)
"""Module-level ``Limiter`` instance used to decorate individual routes."""


def setup_rate_limiting(app: FastAPI) -> None:
    """Attach slowapi rate-limiting middleware and exception handler to *app*.

    After calling this function, routes can use ``@limiter.limit(...)`` to
    enforce per-endpoint rate limits.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
