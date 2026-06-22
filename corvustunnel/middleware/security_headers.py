# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/middleware/security_headers.py
# Description: Adds security headers (CSP, HSTS, frame options, etc.) to
#              every response.
# \*---------------------------------------------------------------------*/



from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint


def add_security_headers(app: FastAPI) -> None:

    @app.middleware("http")
    async def _security_headers_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
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
