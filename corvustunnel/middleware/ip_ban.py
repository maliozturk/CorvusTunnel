# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/middleware/ip_ban.py
# Description: In-memory IP auto-ban after repeated authentication
#              failures.
# \*---------------------------------------------------------------------*/



import logging
import threading
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("corvustunnel.ip_ban")

_FAILURE_THRESHOLD: int = 5
_FAILURE_WINDOW_SECONDS: float = 10 * 60
_BAN_DURATION_SECONDS: float = 15 * 60


class IPBanTracker:
    _instance: "IPBanTracker | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "IPBanTracker":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._lock = threading.Lock()
                    instance._failures: dict[str, list[float]] = {}
                    instance._bans: dict[str, float] = {}
                    cls._instance = instance
        return cls._instance

    def record_failure(self, ip: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)

            timestamps = self._failures.setdefault(ip, [])
            timestamps.append(now)

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
        now = time.monotonic()
        with self._lock:
            self._cleanup_expired(now)
            return ip in self._bans

    def _cleanup_expired(self, now: float) -> None:
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
    return IPBanTracker()


def get_client_ip(request: Request) -> str:
    from corvustunnel.middleware.client_ip import get_trusted_client_ip

    return get_trusted_client_ip(request)


def add_ip_ban_middleware(app: FastAPI) -> None:

    @app.middleware("http")
    async def _ip_ban_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = get_client_ip(request)
        tracker = IPBanTracker()

        if tracker.is_banned(client_ip):
            logger.warning("Rejected request from banned IP %s", client_ip)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        return await call_next(request)
