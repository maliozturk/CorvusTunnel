# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/audit/deep_logger.py
# Description: Verbose plaintext forensic log (localhost-only, admin).
# \*---------------------------------------------------------------------*/



import json
import os
import platform
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


class DeepLogger:
    _BOOT_LOGGED = False

    def __init__(self, log_dir: str = "./logs"):
        self._log_dir = Path(log_dir) / "deep"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq = 0

        if not DeepLogger._BOOT_LOGGED:
            DeepLogger._BOOT_LOGGED = True
            self._log_boot()

    def log(
        self,
        action: str,
        *,
        category: str = "general",
        **kwargs: Any,
    ) -> None:
        with self._lock:
            self._seq += 1
            seq = self._seq

        event: dict[str, Any] = {
            "seq": seq,
            "ts": time.time(),
            "iso": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "action": action,
        }
        for k, v in kwargs.items():
            if v is not None:
                event[k] = v

        self._write(event)

    def auth_success(self, client_ip: str) -> None:
        self.log("auth_success", category="auth", client_ip=client_ip)

    def auth_fail(self, client_ip: str, reason: str = "") -> None:
        self.log("auth_fail", category="auth", client_ip=client_ip, reason=reason)

    def prompt_submitted(
        self,
        job_id: str,
        prompt: str,
        target: str,
        client_ip: str,
        work_dir: str | None = None,
        require_approval: bool = True,
        is_shell: bool = False,
    ) -> None:
        self.log(
            "prompt_submitted",
            category="job",
            job_id=job_id,
            prompt=prompt,
            target=target,
            client_ip=client_ip,
            work_dir=work_dir,
            require_approval=require_approval,
            is_shell=is_shell,
        )

    def job_approved(self, job_id: str) -> None:
        self.log("job_approved", category="job", job_id=job_id)

    def job_rejected(self, job_id: str) -> None:
        self.log("job_rejected", category="job", job_id=job_id)

    def exec_start(self, job_id: str, command: str, work_dir: str, mode: str = "agy") -> None:
        self.log(
            "exec_start",
            category="exec",
            job_id=job_id,
            command=command,
            work_dir=work_dir,
            mode=mode,
        )

    def exec_done(
        self,
        job_id: str,
        return_code: int | None,
        duration_s: float,
        stdout: str | None = None,
        stderr: str | None = None,
        error: str | None = None,
        timed_out: bool = False,
    ) -> None:
        self.log(
            "exec_done",
            category="exec",
            job_id=job_id,
            return_code=return_code,
            duration_s=round(duration_s, 3),
            stdout=stdout,
            stderr=stderr,
            error=error,
            timed_out=timed_out,
        )

    def browse(self, client_ip: str, path: str | None, result_count: int) -> None:
        self.log(
            "browse",
            category="browse",
            client_ip=client_ip,
            path=path,
            result_count=result_count,
        )

    def browse_blocked(self, client_ip: str, path: str, reason: str) -> None:
        self.log(
            "browse_blocked",
            category="browse",
            client_ip=client_ip,
            path=path,
            reason=reason,
        )

    def error(self, action: str, error: str, **ctx: Any) -> None:
        self.log(
            action,
            category="error",
            error=error,
            traceback=traceback.format_exc() if sys.exc_info()[0] else None,
            **ctx,
        )

    def read_recent(self, limit: int = 100, date: str | None = None) -> list[dict]:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_path = self._log_dir / f"deep_{date}.jsonl"
        if not log_path.exists():
            return []

        entries: list[dict] = []
        try:
            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            return []

        return entries[-limit:]

    def list_dates(self) -> list[str]:
        dates = []
        for p in sorted(self._log_dir.glob("deep_*.jsonl"), reverse=True):
            dates.append(p.stem.replace("deep_", ""))
        return dates

    def _log_boot(self) -> None:
        self.log(
            "server_boot",
            category="system",
            python=sys.version,
            platform=platform.platform(),
            pid=os.getpid(),
            cwd=os.getcwd(),
        )

    def _get_log_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._log_dir / f"deep_{today}.jsonl"

    def _write(self, event: dict[str, Any]) -> None:
        log_path = self._get_log_path()
        try:
            with self._lock:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except OSError:
            print(
                f"[DEEP LOG FALLBACK] {json.dumps(event, default=str)}",
                file=sys.stderr,
            )


@lru_cache(maxsize=1)
def get_deep_logger() -> DeepLogger:
    from corvustunnel.config.settings import get_settings

    settings = get_settings()
    return DeepLogger(log_dir=settings.resolved_deep_log_dir)


def deep_log(action: str, *, category: str = "general", **kwargs: Any) -> None:
    get_deep_logger().log(action, category=category, **kwargs)
