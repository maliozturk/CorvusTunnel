# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/audit/logger.py
# Description: Hashed, tamper-evident audit trail safe to retain.
# \*---------------------------------------------------------------------*/



import hashlib
import json
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, log_dir: str = "./logs"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._log_dir / f"audit_{today}.jsonl"

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    def log(
        self,
        action: str,
        job_id: str | None = None,
        target: str | None = None,
        prompt: str | None = None,
        client_ip: str | None = None,
        result_code: int | None = None,
        detail: str | None = None,
        **extra: Any,
    ) -> None:
        event: dict[str, Any] = {
            "ts": time.time(),
            "iso": datetime.now(timezone.utc).isoformat(),
            "action": action,
        }

        if job_id is not None:
            event["job_id"] = job_id
        if target is not None:
            event["target"] = target
        if prompt is not None:
            event["prompt_hash"] = self._hash_prompt(prompt)
        if client_ip is not None:
            event["client_ip"] = client_ip
        if result_code is not None:
            event["result_code"] = result_code
        if detail is not None:
            event["detail"] = detail
        if extra:
            event.update(extra)

        log_path = self._get_log_path()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            import sys

            print(f"[AUDIT FALLBACK] {json.dumps(event)}", file=sys.stderr)

    def read_recent(self, limit: int = 50) -> list[dict]:
        log_path = self._get_log_path()
        if not log_path.exists():
            return []

        entries = []
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


@lru_cache(maxsize=1)
def get_audit_logger() -> AuditLogger:
    from corvustunnel.config.settings import get_settings

    settings = get_settings()
    return AuditLogger(log_dir=settings.audit_log_dir)
