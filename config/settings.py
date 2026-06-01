"""
CorvusTunnel Settings — Pydantic-based configuration loaded from environment.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    In Docker, all settings are passed via `-e` flags or set by
    the boot orchestrator (boot.py).
    """

    model_config = {"env_file_encoding": "utf-8"}

    # ── Auth ──────────────────────────────────────────────────────────
    agent_token: str = Field(
        ...,
        description="Bearer token for API authentication",
    )

    # ── Server ────────────────────────────────────────────────────────
    public_port: int = Field(default=8000, ge=1024, le=65535)
    internal_port: int = Field(default=8001, ge=1024, le=65535)

    # ── Audit ─────────────────────────────────────────────────────────
    audit_log_dir: str = Field(
        default="./logs",
        description="Directory for audit log files (hashed, safe)",
    )
    deep_log_dir: str = Field(
        default="",
        description="Directory for deep (plaintext) logs. "
                    "Defaults to /app/logs/deep inside container.",
    )

    @property
    def resolved_deep_log_dir(self) -> str:
        """Return the deep log directory, defaulting to a secure location."""
        if self.deep_log_dir:
            return self.deep_log_dir
        return os.path.join(os.path.expanduser("~"), ".corvustunnel", "logs")

    # ── Workspace ─────────────────────────────────────────────────────
    allowed_dirs: str = Field(
        default="/workspace",
        description="Comma-separated directories visible in folder browser",
    )

    @property
    def allowed_dir_list(self) -> list[str]:
        """Parse comma-separated allowed directories."""
        if not self.allowed_dirs:
            return []
        return [d.strip() for d in self.allowed_dirs.split(',') if d.strip()]

    # ── Validators ────────────────────────────────────────────────────

    @field_validator("audit_log_dir")
    @classmethod
    def ensure_directory_exists(cls, v: str) -> str:
        """Create the directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @field_validator("public_port", "internal_port")
    @classmethod
    def ports_must_differ(cls, v: int, info) -> int:
        """Ensure public and internal ports are different."""
        if info.field_name == "internal_port":
            data = info.data
            if "public_port" in data and data["public_port"] == v:
                raise ValueError("public_port and internal_port must be different")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    return Settings()


def generate_token(length: int = 64) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)
