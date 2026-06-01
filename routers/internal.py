"""
CorvusTunnel Internal API Router.

Runs on port 8001, bound to 127.0.0.1 only.
Handles job approval, rejection, and admin views.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import require_local_only
from audit.logger import get_audit_logger
from models.responses import JobResponse, JobListResponse
from jobqueue.manager import get_job_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Approve job ──────────────────────────────────────────────────────
@router.post(
    "/approve/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_local_only)],
)
async def approve_job(job_id: str):
    """
    Approve a pending job and start execution.
    
    Only accessible from localhost (127.0.0.1 / ::1).
    """
    audit = get_audit_logger()
    manager = get_job_manager()

    job = await manager.approve(job_id)
    if job is None:
        raise HTTPException(404, f"Job '{job_id}' not found in pending queue")

    audit.log(action="approve", job_id=job_id, target=job.target)

    from audit.deep_logger import get_deep_logger
    get_deep_logger().job_approved(job_id)

    logger.info(f"Job {job_id} approved, execution started")

    return job.to_response()


# ── Reject job ───────────────────────────────────────────────────────
@router.post(
    "/reject/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_local_only)],
)
async def reject_job(job_id: str):
    """
    Reject a pending job.
    
    Only accessible from localhost (127.0.0.1 / ::1).
    """
    audit = get_audit_logger()
    manager = get_job_manager()

    job = await manager.reject(job_id)
    if job is None:
        raise HTTPException(404, f"Job '{job_id}' not found in pending queue")

    audit.log(action="reject", job_id=job_id, target=job.target)

    from audit.deep_logger import get_deep_logger
    get_deep_logger().job_rejected(job_id)

    logger.info(f"Job {job_id} rejected")

    return job.to_response()


# ── Pending jobs ─────────────────────────────────────────────────────
@router.get(
    "/pending",
    response_model=JobListResponse,
    dependencies=[Depends(require_local_only)],
)
async def list_pending():
    """List all jobs awaiting approval."""
    manager = get_job_manager()
    jobs = await manager.get_pending()

    return JobListResponse(
        jobs=[j.to_response() for j in jobs],
        total=len(jobs),
    )


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

    Only accessible from localhost.  Shows prompts, outputs, browse
    activity, auth events, and security blocks.
    """
    from audit.deep_logger import get_deep_logger
    dl = get_deep_logger()
    entries = dl.read_recent(limit=limit, date=date)
    dates = dl.list_dates()
    return {"entries": entries, "total": len(entries), "available_dates": dates}
