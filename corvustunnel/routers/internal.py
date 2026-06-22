# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/routers/internal.py
# Description: Localhost-only admin routes: audit log, deep log, and
#              terminal status.
# \*---------------------------------------------------------------------*/



import logging

from fastapi import APIRouter, Depends

from corvustunnel.audit.logger import get_audit_logger
from corvustunnel.auth.dependencies import require_local_only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/audit",
    dependencies=[Depends(require_local_only)],
)
async def recent_audit(limit: int = 50):
    audit = get_audit_logger()
    entries = audit.read_recent(limit=limit)
    return {"entries": entries, "total": len(entries)}


@router.get(
    "/deeplog",
    dependencies=[Depends(require_local_only)],
)
async def view_deep_log(limit: int = 100, date: str | None = None):
    from corvustunnel.audit.deep_logger import get_deep_logger

    dl = get_deep_logger()
    entries = dl.read_recent(limit=limit, date=date)
    dates = dl.list_dates()
    return {"entries": entries, "total": len(entries), "available_dates": dates}


@router.get(
    "/terminal/status",
    dependencies=[Depends(require_local_only)],
)
async def terminal_status():
    from corvustunnel.executor.term_session import get_terminal_session

    session = get_terminal_session()
    return session.status()
