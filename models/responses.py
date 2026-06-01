"""
CorvusTunnel Response Models.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal[
    "pending",      # Waiting for manual approval
    "approved",     # Approved, about to execute
    "running",      # Currently executing
    "done",         # Completed successfully
    "failed",       # Completed with error
    "rejected",     # Manually rejected
    "timeout",      # Execution timed out
]


class JobResponse(BaseModel):
    """Response model for a single job."""

    job_id: str
    target: str
    prompt: str
    status: JobStatus
    result: dict[str, Any] | None = None
    created_at: float
    updated_at: float | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4",
                "target": "antigravity",
                "prompt": "Kodun hangi aşamada?",
                "status": "running",
                "result": None,
                "created_at": 1717012800.0,
                "updated_at": 1717012810.0,
            }
        }


class JobListResponse(BaseModel):
    """Response model for listing jobs."""

    jobs: list[JobResponse]
    total: int


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = "ok"
    version: str = "0.1.0"
    uptime_seconds: float = 0.0


class SSEEvent(BaseModel):
    """Model for Server-Sent Events data."""

    type: Literal["status", "output", "done", "error"] = "output"
    content: str = ""
    job_id: str = ""
