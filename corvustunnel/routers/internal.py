"""
CorvusTunnel Internal API Router.

Runs on port 8001, bound to 127.0.0.1 only.
Provides admin views for audit logs and system status.

NOTE: Job approval/rejection endpoints were removed in v0.2.0
(terminal-only mode). This router is kept for future admin features.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from corvustunnel.auth.dependencies import require_local_only
from corvustunnel.audit.logger import get_audit_logger

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Recent audit logs ───────────────────────────────────────────────
@router.get(
    "/audit",
    dependencies=[Depends(require_local_only)],
)
async def recent_audit(limit: int = 50):
    """View recent audit log entries."""
    audit = get_audit_logger()
    entries = audit.read_recent(limit=limit)
    return {"entries": entries, "total": len(entries)}


# ── Deep log viewer (full forensic trail) ───────────────────────────
@router.get(
    "/deeplog",
    dependencies=[Depends(require_local_only)],
)
async def view_deep_log(limit: int = 100, date: str | None = None):
    """View the deep log — full plaintext forensic trail.

    Only accessible from localhost.  Shows terminal I/O, browse
    activity, auth events, and security blocks.
    """
    from corvustunnel.audit.deep_logger import get_deep_logger
    dl = get_deep_logger()
    entries = dl.read_recent(limit=limit, date=date)
    dates = dl.list_dates()
    return {"entries": entries, "total": len(entries), "available_dates": dates}


# ── Terminal session status ─────────────────────────────────────────
@router.get(
    "/terminal/status",
    dependencies=[Depends(require_local_only)],
)
async def terminal_status():
    """View the current terminal session status."""
    from corvustunnel.executor.term_session import get_terminal_session
    session = get_terminal_session()
    return session.status()
