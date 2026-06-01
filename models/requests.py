"""
CorvusTunnel Request Models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    """Request body for submitting a prompt to an executor."""

    target: Literal["antigravity"] = Field(
        default="antigravity",
        description="Executor target. Currently only 'antigravity' is supported.",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The prompt or command to send to the executor.",
    )
    require_approval: bool = Field(
        default=True,
        description="If True, the job waits for manual approval before execution.",
    )
    work_dir: str | None = Field(
        default=None,
        description="Working directory for execution. If None, uses server default.",
    )
