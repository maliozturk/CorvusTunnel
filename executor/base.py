"""
CorvusTunnel Base Executor — Abstract interface for all executors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from jobqueue.manager import Job


class ExecutionResult:
    """Result of an executor run."""

    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        return_code: int | None = None,
        timed_out: bool = False,
        error: str | None = None,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.timed_out = timed_out
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d: dict[str, Any] = {}
        if self.stdout:
            d["stdout"] = self.stdout
        if self.stderr:
            d["stderr"] = self.stderr
        if self.return_code is not None:
            d["return_code"] = self.return_code
        if self.timed_out:
            d["timed_out"] = True
        if self.error:
            d["error"] = self.error
        return d


class BaseExecutor(ABC):
    """Abstract base class for all executors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Executor name (e.g., 'antigravity', 'codex', 'shell')."""
        ...

    @abstractmethod
    async def execute(
        self,
        job: Job,
        work_dir: str,
        timeout: int = 300,
        max_output: int = 5000,
    ) -> dict[str, Any]:
        """
        Execute a prompt/command.
        
        Args:
            job: The Job object (for streaming output via add_output_line)
            work_dir: Working directory for execution
            timeout: Maximum execution time in seconds
            max_output: Maximum output size in characters
            
        Returns:
            Result dictionary with stdout, stderr, return_code, etc.
        """
        ...
