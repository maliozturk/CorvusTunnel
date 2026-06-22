# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/auth/dependencies.py
# Description: FastAPI dependency restricting the internal admin app to
#              localhost-only access.
# \*---------------------------------------------------------------------*/

from fastapi import HTTPException, Request

from corvustunnel.audit.logger import get_audit_logger


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
