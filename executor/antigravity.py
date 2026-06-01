"""
CorvusTunnel Antigravity Executor.

Uses pywinpty PTY for agy commands (agy writes directly to Windows
Console API, so piped stdout cannot capture its output).
Uses standard subprocess for shell commands (prefixed with $).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
from typing import Any, TYPE_CHECKING

from executor.base import BaseExecutor, ExecutionResult

if TYPE_CHECKING:
    from jobqueue.manager import Job

logger = logging.getLogger(__name__)

# ANSI escape sequence pattern for cleaning PTY output
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[[\?]?[0-9;]*[a-zA-Z]")

AGY_EXE = r"C:\Users\alini\AppData\Local\agy\bin\agy.exe"


class AntigravityExecutor(BaseExecutor):
    """
    Executor for Antigravity AI coding assistant.

    agy CLI writes output directly to the Windows Console API,
    bypassing stdout/stderr file descriptors. We use pywinpty
    to create a pseudo-terminal that captures this output.
    """

    @property
    def name(self) -> str:
        return "antigravity"

    async def execute(
        self,
        job: Job,
        work_dir: str,
        timeout: int = 300,
        max_output: int = 10000,
    ) -> dict[str, Any]:
        """Execute a prompt — routes to PTY (agy) or subprocess (shell)."""
        prompt = job.prompt
        effective_dir = job.work_dir or work_dir

        # Route: $ prefix → shell command, otherwise → agy
        if prompt.startswith("$"):
            return await self._execute_shell(job, prompt[1:].strip(), effective_dir, timeout, max_output)
        else:
            return await self._execute_agy(job, prompt, effective_dir, timeout, max_output)

    async def _execute_agy(
        self, job: Job, prompt: str, work_dir: str, timeout: int, max_output: int
    ) -> dict[str, Any]:
        """Execute via agy CLI using pywinpty PTY."""
        from audit.deep_logger import get_deep_logger

        deep = get_deep_logger()
        cmd = (
            f'"{AGY_EXE}" --prompt-interactive "{prompt}" '
            f"--dangerously-skip-permissions "
            f'--add-dir "{work_dir}"'
        )

        logger.info(f"[{job.job_id}] agy PTY in {work_dir}: {prompt[:80]}...")
        deep.exec_start(job.job_id, prompt, work_dir, mode="agy")
        t0 = time.time()

        try:
            # Run PTY in a thread to avoid blocking the event loop
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._run_pty, cmd, work_dir, timeout, max_output, job
                ),
                timeout=timeout + 10,
            )
            deep.exec_done(
                job.job_id,
                return_code=result.get("return_code"),
                duration_s=time.time() - t0,
                stdout=result.get("stdout"),
                stderr=result.get("stderr"),
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"[{job.job_id}] agy timed out after {timeout}s")
            deep.exec_done(job.job_id, return_code=None, duration_s=time.time() - t0, timed_out=True)
            return ExecutionResult(
                error=f"Timed out after {timeout}s", timed_out=True
            ).to_dict()
        except Exception as e:
            error_msg = f"agy execution error: {type(e).__name__}: {e}"
            logger.error(f"[{job.job_id}] {error_msg}")
            deep.exec_done(job.job_id, return_code=None, duration_s=time.time() - t0, error=error_msg)
            return ExecutionResult(error=error_msg).to_dict()

    def _run_pty(
        self, cmd: str, work_dir: str, timeout: int, max_output: int, job: Job
    ) -> dict[str, Any]:
        """Run agy in a PTY (called in a thread)."""
        import winpty

        pty = winpty.PTY(500, 50)
        pty.spawn(cmd, cwd=work_dir)

        output = ""
        start = time.time()
        trust_confirmed = False

        while time.time() - start < timeout:
            if not pty.isalive():
                # Drain remaining output
                try:
                    data = pty.read()
                    if data:
                        output += data
                except Exception:
                    pass
                break
            try:
                data = pty.read()
                if data:
                    output += data

                    # Auto-confirm "Do you trust this project?" prompt.
                    # Default selection is "Yes, I trust this folder" so
                    # a single Enter keypress accepts it.
                    if not trust_confirmed and "trust" in data.lower():
                        time.sleep(0.5)  # let the TUI render fully
                        pty.write("\r\n")
                        trust_confirmed = True

                    # Stream lines to SSE as they come
                    lines = data.split("\n")
                    for line in lines:
                        clean = _ANSI_RE.sub("", line).strip()
                        if clean and len(output) <= max_output:
                            job.add_output_line(clean)
            except Exception:
                pass
            time.sleep(0.3)

        # Clean final output
        clean_output = _ANSI_RE.sub("", output).strip()

        if len(clean_output) > max_output:
            clean_output = clean_output[:max_output] + "\n... (truncated)"

        return ExecutionResult(
            stdout=clean_output,
            return_code=0 if not pty.isalive() else -1,
        ).to_dict()

    async def _execute_shell(
        self, job: Job, shell_cmd: str, work_dir: str, timeout: int, max_output: int
    ) -> dict[str, Any]:
        """Execute a direct shell command via subprocess."""
        from config.protection import is_path_in_corvus, CORVUS_ROOT
        from audit.deep_logger import get_deep_logger

        deep = get_deep_logger()

        # ── Protection: block commands targeting CorvusTunnel ─────────
        corvus_lower = str(CORVUS_ROOT).lower().replace("\\", "/")
        cmd_lower = shell_cmd.lower().replace("\\", "/")
        if corvus_lower in cmd_lower:
            reason = "Shell command references CorvusTunnel directory — blocked"
            logger.warning(f"[{job.job_id}] BLOCKED: {reason}")
            deep.log(
                "exec_blocked", category="security",
                job_id=job.job_id, command=shell_cmd, reason=reason,
            )
            return ExecutionResult(error=reason).to_dict()

        # Block if work_dir IS the CorvusTunnel directory
        if is_path_in_corvus(work_dir):
            reason = "Cannot execute shell commands inside CorvusTunnel directory"
            logger.warning(f"[{job.job_id}] BLOCKED: {reason}")
            deep.log(
                "exec_blocked", category="security",
                job_id=job.job_id, command=shell_cmd,
                work_dir=work_dir, reason=reason,
            )
            return ExecutionResult(error=reason).to_dict()

        if sys.platform == "win32":
            cmd = ["powershell", "-NoProfile", "-Command", shell_cmd]
        else:
            cmd = ["bash", "-c", shell_cmd]

        logger.info(f"[{job.job_id}] Shell in {work_dir}: {shell_cmd[:80]}...")
        deep.exec_start(job.job_id, shell_cmd, work_dir, mode="shell")
        t0 = time.time()

        env = self._build_env()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env=env,
            )

            stdout_lines: list[str] = []
            stderr_lines: list[str] = []
            total_size = 0

            async def read_stream(stream, lines):
                nonlocal total_size
                if stream is None:
                    return
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode("utf-8", errors="replace").rstrip("\n\r")
                    total_size += len(line)
                    if total_size <= max_output:
                        lines.append(line)
                        job.add_output_line(line)

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, stdout_lines),
                        read_stream(proc.stderr, stderr_lines),
                    ),
                    timeout=timeout,
                )
                await proc.wait()
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                out = "\n".join(stdout_lines)[-max_output:]
                err = "\n".join(stderr_lines)[-max_output:]
                deep.exec_done(job.job_id, proc.returncode, time.time() - t0, out, err, timed_out=True)
                return ExecutionResult(
                    stdout=out, stderr=err,
                    return_code=proc.returncode, timed_out=True,
                ).to_dict()

            out = "\n".join(stdout_lines)[-max_output:]
            err = "\n".join(stderr_lines)[-max_output:]
            deep.exec_done(job.job_id, proc.returncode, time.time() - t0, out, err)
            return ExecutionResult(
                stdout=out, stderr=err, return_code=proc.returncode,
            ).to_dict()

        except FileNotFoundError:
            deep.exec_done(job.job_id, None, time.time() - t0, error=f"Command not found: {cmd[0]}")
            return ExecutionResult(error=f"Command not found: {cmd[0]}").to_dict()
        except Exception as e:
            deep.exec_done(job.job_id, None, time.time() - t0, error=f"{type(e).__name__}: {e}")
            return ExecutionResult(error=f"{type(e).__name__}: {e}").to_dict()

    def _build_env(self) -> dict[str, str]:
        """Build a sanitized environment for shell subprocesses."""
        env = os.environ.copy()
        sensitive_keys = [
            "AGENT_TOKEN", "CF_ACCESS_AUD", "CF_TEAM_DOMAIN",
            "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN", "GH_TOKEN",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        ]
        for key in sensitive_keys:
            env.pop(key, None)
        return env
