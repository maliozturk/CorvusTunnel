"""
CorvusTunnel IP Ban Middleware.

In-memory IP ban system that tracks failed authentication attempts and
temporarily bans IPs that exceed the failure threshold.

Ban policy:
  - 5 failures within a 10-minute window → 15-minute ban.
  - Expired bans and stale failure records are cleaned up automatically.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("corvustunnel.ip_ban")

# ── Policy constants ─────────────────────────────────────────────────
_FAILURE_THRESHOLD: int = 5
_FAILURE_WINDOW_SECONDS: float = 10 * 60  # 10 minutes
_BAN_DURATION_SECONDS: float = 15 * 60    # 15 minutes


class IPBanTracker:
    """Thread-safe singleton that tracks per-IP auth failures and bans.

    Attributes:
        _failures:  ``{ip: [timestamp, …]}`` – recent failure timestamps.
        _bans:      ``{ip: ban_expiry_timestamp}`` – currently banned IPs.
    """

    _instance: IPBanTracker | None = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> IPBanTracker:
        """Ensure only one instance exists (singleton)."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._lock = threading.Lock()
                    instance._failures: dict[str, list[float]] = {}
                    instance._bans: dict[str, float] = {}
                    cls._instance = instance
        return cls._instance

    # ── Public API ───────────────────────────────────────────────────

    def record_failure(self, ip: str) -> None:
        """Record a failed authentication attempt for *ip*.

        If the failure count within the rolling window reaches the
        threshold, the IP is banned and failures are cleared.
        """
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)

            timestamps = self._failures.setdefault(ip, [])
            timestamps.append(now)

            # Prune timestamps outside the rolling window
            cutoff = now - _FAILURE_WINDOW_SECONDS
            timestamps[:] = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= _FAILURE_THRESHOLD:
                self._bans[ip] = now + _BAN_DURATION_SECONDS
                self._failures.pop(ip, None)
                logger.warning(
                    "IP %s banned for %d minutes after %d failures",
                    ip,
                    int(_BAN_DURATION_SECONDS // 60),
                    _FAILURE_THRESHOLD,
                )

    def is_banned(self, ip: str) -> bool:
        """Return ``True`` if *ip* is currently banned."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)
            return ip in self._bans

    # ── Helpers ──────────────────────────────────────────────────────

    def _cleanup_expired(self, now: float) -> None:
        """Remove expired bans and stale failure records (caller holds lock)."""
        expired_bans = [ip for ip, expiry in self._bans.items() if now >= expiry]
        for ip in expired_bans:
            del self._bans[ip]
            logger.info("Ban expired for IP %s", ip)

        stale_ips = [
            ip
            for ip, ts_list in self._failures.items()
            if not ts_list or ts_list[-1] < now - _FAILURE_WINDOW_SECONDS
        ]
        for ip in stale_ips:
            del self._failures[ip]


def get_ban_tracker() -> IPBanTracker:
    """Return the singleton IPBanTracker instance."""
    return IPBanTracker()


def get_client_ip(request: Request) -> str:
    """Extract the real client IP, trusting X-Forwarded-For only from a
    trusted proxy (see :mod:`middleware.client_ip`)."""
    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    return get_trusted_client_ip(request)


def add_ip_ban_middleware(app: FastAPI) -> None:
    """Register middleware that rejects requests from banned IPs with 403."""

    @app.middleware("http")
    async def _ip_ban_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = get_client_ip(request)
        tracker = IPBanTracker()

        if tracker.is_banned(client_ip):
            logger.warning("Rejected request from banned IP %s", client_ip)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        return await call_next(request)
