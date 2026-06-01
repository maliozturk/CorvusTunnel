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
    """Application settings loaded from environment variables / .env file.

    The .env lives at ``~/.corvustunnel/.env`` — deliberately outside any
    project tree so it is unreachable from the tunnel, folder browser,
    or any remote command.
    """

    model_config = {
        "env_file": str(Path.home() / ".corvustunnel" / ".env"),
        "env_file_encoding": "utf-8",
    }

    # ── Auth ──────────────────────────────────────────────────────────
    agent_token: str = Field(
        ...,
        min_length=32,
        description="Bearer token for API authentication",
    )

    # Cloudflare Access (optional — not used with Quick Tunnel)
    cf_team_domain: str | None = Field(
        default=None,
        description="Cloudflare Access team domain, e.g. https://team.cloudflareaccess.com",
    )
    cf_access_aud: str | None = Field(
        default=None,
        description="Cloudflare Access application audience tag",
    )

    # ── Server ────────────────────────────────────────────────────────
    public_port: int = Field(default=8000, ge=1024, le=65535)
    internal_port: int = Field(default=8001, ge=1024, le=65535)

    # ── Executor ──────────────────────────────────────────────────────
    work_dir: str = Field(
        default="./workspace",
        description="Isolated working directory for agent execution",
    )
    max_exec_timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum execution timeout in seconds",
    )
    max_output_size: int = Field(
        default=5000,
        ge=500,
        le=50000,
        description="Maximum output size in characters",
    )

    # ── Audit ─────────────────────────────────────────────────────────
    audit_log_dir: str = Field(
        default="./logs",
        description="Directory for audit log files (hashed, safe)",
    )
    deep_log_dir: str = Field(
        default="",
        description="Directory for deep (plaintext) logs. "
                    "Defaults to ~/.corvustunnel/logs — MUST be outside ALLOWED_DIRS",
    )

    @property
    def resolved_deep_log_dir(self) -> str:
        """Return the deep log directory, defaulting to a secure location."""
        import os
        if self.deep_log_dir:
            return self.deep_log_dir
        return os.path.join(os.path.expanduser("~"), ".corvustunnel", "logs")
    allowed_dirs: str = Field(
        default="",
        description="Comma-separated directories visible in folder browser",
    )

    @property
    def allowed_dir_list(self) -> list[str]:
        """Parse comma-separated allowed directories."""
        if not self.allowed_dirs:
            return []
        return [d.strip() for d in self.allowed_dirs.split(',') if d.strip()]

    @field_validator("work_dir", "audit_log_dir")
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

    @property
    def cf_access_enabled(self) -> bool:
        """Check if Cloudflare Access authentication is configured."""
        return bool(self.cf_team_domain and self.cf_access_aud)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    return Settings()


def generate_token(length: int = 64) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)
