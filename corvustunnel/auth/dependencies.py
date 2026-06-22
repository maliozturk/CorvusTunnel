"""
CorvusTunnel FastAPI Auth Dependencies.

Provides reusable Depends() functions for route protection.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from corvustunnel.auth.bearer import verify_bearer_token
from corvustunnel.audit.logger import get_audit_logger


async def require_public_auth(request: Request) -> None:
    """
    Dependency: Require valid Bearer token for public endpoints.

    In Quick Tunnel mode (no Cloudflare Access), Bearer token is the
    primary auth layer. When Access is enabled, both JWT and Bearer
    are validated.

    The real client IP is extracted from ``X-Forwarded-For`` (first
    entry) when available, falling back to ``request.client.host``.
    This IP is forwarded to :func:`verify_bearer_token` so that
    IP-binding checks are enforced.
    """
    from corvustunnel.audit.deep_logger import get_deep_logger

    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    authorization = request.headers.get("Authorization", "")

    # Real client IP — X-Forwarded-For is trusted only from a trusted proxy
    client_ip = get_trusted_client_ip(request)

    if not verify_bearer_token(authorization, client_ip=client_ip):
        # Log failed auth attempt
        logger = get_audit_logger()
        logger.log(
            action="auth_fail",
            client_ip=client_ip,
            detail="Invalid or missing bearer token",
        )
        get_deep_logger().auth_fail(client_ip, reason="Invalid or missing bearer token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    get_deep_logger().auth_success(client_ip)


async def require_local_only(request: Request) -> None:
    """
    Dependency: Restrict access to localhost connections only.
    
    Used for internal endpoints (approve, reject, pending) that
    must never be accessible from the tunnel.
    """
    client_host = request.client.host if request.client else None
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}

    if client_host not in allowed_hosts:
        logger = get_audit_logger()
        logger.log(
            action="access_denied",
            client_ip=client_host or "unknown",
            detail="Internal endpoint accessed from non-local IP",
        )
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only accessible from localhost",
        )
