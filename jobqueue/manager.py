"""
CorvusTunnel Job Queue Manager.

Thread-safe in-memory job queue with support for manual approval workflow.
Jobs go through: pending → approved → running → done/failed/timeout
                  pending → rejected
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from typing import Any, Callable, Coroutine

from models.responses import JobResponse, JobStatus


class Job:
    """Internal job representation."""

    def __init__(
        self,
        target: str,
        prompt: str,
        require_approval: bool = True,
        work_dir: str | None = None,
    ):
        self.job_id: str = uuid.uuid4().hex[:8]
        self.target: str = target
        self.prompt: str = prompt
        self.work_dir: str | None = work_dir
        self.status: JobStatus = "pending" if require_approval else "approved"
        self.result: dict[str, Any] | None = None
        self.created_at: float = time.time()
        self.updated_at: float = self.created_at
        self._output_lines: list[str] = []
        self._sse_queues: list[asyncio.Queue] = []

    def to_response(self) -> JobResponse:
        """Convert to API response model."""
        return JobResponse(
            job_id=self.job_id,
            target=self.target,
            prompt=self.prompt,
            status=self.status,
            result=self.result,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update_status(self, status: JobStatus) -> None:
        """Update job status and timestamp."""
        self.status = status
        self.updated_at = time.time()

    def set_result(self, result: dict[str, Any]) -> None:
        """Set the execution result."""
        self.result = result
        self.updated_at = time.time()

    def add_output_line(self, line: str) -> None:
        """Add a line of output and notify SSE subscribers."""
        self._output_lines.append(line)
        for q in self._sse_queues:
            try:
                q.put_nowait(("output", line))
            except asyncio.QueueFull:
                pass

    def notify_status_change(self) -> None:
        """Notify SSE subscribers of a status change."""
        for q in self._sse_queues:
            try:
                q.put_nowait(("status", self.status))
            except asyncio.QueueFull:
                pass

    def notify_done(self) -> None:
        """Notify SSE subscribers that the job is complete."""
        for q in self._sse_queues:
            try:
                q.put_nowait(("done", self.status))
            except asyncio.QueueFull:
                pass

    def subscribe_sse(self) -> asyncio.Queue:
        """Create and return a new SSE subscription queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._sse_queues.append(q)
        return q

    def unsubscribe_sse(self, q: asyncio.Queue) -> None:
        """Remove an SSE subscription queue."""
        if q in self._sse_queues:
            self._sse_queues.remove(q)

    @property
    def output_text(self) -> str:
        """Get all output lines as a single string."""
        return "\n".join(self._output_lines)


class JobManager:
    """
    Thread-safe in-memory job queue manager.
    
    Manages the lifecycle of jobs from submission through execution.
    """

    def __init__(self, max_history: int = 200):
        self._lock = asyncio.Lock()
        self._pending: dict[str, Job] = {}
        self._active: dict[str, Job] = {}
        self._history: deque[Job] = deque(maxlen=max_history)
        self._executor_callback: Callable[
            [Job], Coroutine[Any, Any, dict[str, Any]]
        ] | None = None

    def set_executor(
        self,
        callback: Callable[[Job], Coroutine[Any, Any, dict[str, Any]]],
    ) -> None:
        """Set the executor callback for running jobs."""
        self._executor_callback = callback

    async def submit(self, target: str, prompt: str, require_approval: bool = True, work_dir: str | None = None) -> Job:
        """
        Submit a new job.
        
        If require_approval is True, the job goes to pending state.
        Otherwise, it's immediately queued for execution.
        """
        job = Job(target=target, prompt=prompt, require_approval=require_approval, work_dir=work_dir)

        async with self._lock:
            if require_approval:
                self._pending[job.job_id] = job
            else:
                self._active[job.job_id] = job

        if not require_approval:
            # Fire-and-forget execution
            asyncio.create_task(self._execute_job(job))

        return job

    async def approve(self, job_id: str) -> Job | None:
        """
        Approve a pending job and start execution.
        
        Returns the job if found, None otherwise.
        """
        async with self._lock:
            job = self._pending.pop(job_id, None)
            if job is None:
                return None
            job.update_status("approved")
            job.notify_status_change()
            self._active[job.job_id] = job

        # Start execution
        asyncio.create_task(self._execute_job(job))
        return job

    async def reject(self, job_id: str) -> Job | None:
        """
        Reject a pending job.
        
        Returns the job if found, None otherwise.
        """
        async with self._lock:
            job = self._pending.pop(job_id, None)
            if job is None:
                return None
            job.update_status("rejected")
            job.notify_done()
            self._history.appendleft(job)

        return job

    async def get_job(self, job_id: str) -> Job | None:
        """Look up a job by ID across all states."""
        # Check pending
        if job_id in self._pending:
            return self._pending[job_id]
        # Check active
        if job_id in self._active:
            return self._active[job_id]
        # Check history
        for job in self._history:
            if job.job_id == job_id:
                return job
        return None

    async def get_pending(self) -> list[Job]:
        """Get all pending (awaiting approval) jobs."""
        return list(self._pending.values())

    async def get_all_jobs(self, limit: int = 50) -> list[Job]:
        """Get all jobs across all states, most recent first."""
        jobs: list[Job] = []
        jobs.extend(self._pending.values())
        jobs.extend(self._active.values())
        jobs.extend(self._history)
        # Sort by created_at, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    async def _execute_job(self, job: Job) -> None:
        """Execute a job using the registered executor callback."""
        if self._executor_callback is None:
            job.update_status("failed")
            job.set_result({"error": "No executor configured"})
            job.notify_done()
            async with self._lock:
                self._active.pop(job.job_id, None)
                self._history.appendleft(job)
            return

        job.update_status("running")
        job.notify_status_change()

        try:
            result = await self._executor_callback(job)
            if result.get("error"):
                job.update_status("failed")
            elif result.get("timed_out"):
                job.update_status("timeout")
            else:
                job.update_status("done")
            job.set_result(result)
        except Exception as e:
            job.update_status("failed")
            job.set_result({"error": str(e)})

        job.notify_done()

        async with self._lock:
            self._active.pop(job.job_id, None)
            self._history.appendleft(job)


# ── Singleton ────────────────────────────────────────────────────────

_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    """Return the singleton JobManager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
