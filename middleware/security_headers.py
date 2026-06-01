"""
CorvusTunnel Security Headers Middleware.

Adds security headers to every HTTP response to harden the application
against common web vulnerabilities (clickjacking, MIME-sniffing, XSS, etc.).
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint


def add_security_headers(app: FastAPI) -> None:
    """Register the security-headers middleware on *app*.

    Appends the following headers to every response:

    - X-Frame-Options
    - X-Content-Type-Options
    - Strict-Transport-Security
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy
    - X-XSS-Protection
    """

    @app.middleware("http")
    async def _security_headers_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' wss:; "
            "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com; "
            "img-src 'self' data:"
        )
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
