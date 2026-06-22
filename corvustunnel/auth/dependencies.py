# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/auth/dependencies.py
# Description: FastAPI dependencies enforcing bearer auth and
#              localhost-only access.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

from fastapi import HTTPException, Request

from corvustunnel.audit.logger import get_audit_logger
from corvustunnel.auth.bearer import verify_bearer_token


async def require_public_auth(request: Request) -> None:
    from corvustunnel.audit.deep_logger import get_deep_logger
    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    authorization = request.headers.get("Authorization", "")

    client_ip = get_trusted_client_ip(request)

    if not verify_bearer_token(authorization, client_ip=client_ip):
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
