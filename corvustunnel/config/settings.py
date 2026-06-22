# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/config/settings.py
# Description: Environment-driven settings: ports, allowed dirs, trusted
#              proxies, log paths.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file_encoding": "utf-8"}

    agent_token: str = Field(
        ...,
        description="Bearer token for API authentication",
    )

    public_port: int = Field(default=8000, ge=1024, le=65535)
    internal_port: int = Field(default=8001, ge=1024, le=65535)

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
        if self.deep_log_dir:
            return self.deep_log_dir
        return os.path.join(os.path.expanduser("~"), ".corvustunnel", "logs")

    trusted_proxies: str = Field(
        default="",
        description="Comma-separated extra IPs (besides loopback) whose "
        "X-Forwarded-For header is trusted. Set this only if you "
        "front CorvusTunnel with your own reverse proxy.",
    )

    @property
    def trusted_proxy_list(self) -> list[str]:
        if not self.trusted_proxies:
            return []
        return [ip.strip() for ip in self.trusted_proxies.split(",") if ip.strip()]

    allowed_dirs: str = Field(
        default="",
        description="Comma-separated directories visible in folder browser. "
        "Defaults to current working directory if not set.",
    )

    @property
    def allowed_dir_list(self) -> list[str]:
        if not self.allowed_dirs:
            import os

            return [os.getcwd()]
        return [d.strip() for d in self.allowed_dirs.split(",") if d.strip()]

    chat_history_dirs: str = Field(
        default="",
        description="Override paths to agent data dirs. Format: "
        "'antigravity=/path,claude=/path,codex=/path'. "
        "If empty, auto-discovers from home directory "
        "(~/.gemini, ~/.claude, ~/.codex).",
    )

    @field_validator("audit_log_dir")
    @classmethod
    def ensure_directory_exists(cls, v: str) -> str:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())

    @field_validator("public_port", "internal_port")
    @classmethod
    def ports_must_differ(cls, v: int, info) -> int:
        if info.field_name == "internal_port":
            data = info.data
            if "public_port" in data and data["public_port"] == v:
                raise ValueError("public_port and internal_port must be different")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
