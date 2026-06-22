# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/auth/bearer.py
# Description: Boot/session token management, IP binding, and one-time
#              WebSocket tickets.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import hmac
import logging
import secrets
import threading
import time

from corvustunnel.config.settings import get_settings

logger = logging.getLogger("corvustunnel.auth.bearer")

_WS_TICKET_TTL_SECONDS: float = 30.0


class TokenManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._boot_token: str = get_settings().agent_token
        self._boot_consumed: bool = False
        self._session_token: str | None = None

        self._bound_ip: str | None = None

        self._ws_tickets: dict[str, dict] = {}
        self._ws_lock = threading.Lock()

    def claim_boot_token(self, token: str, client_ip: str | None = None) -> str | None:
        with self._lock:
            if self._boot_consumed:
                return None
            if not hmac.compare_digest(token, self._boot_token):
                return None

            self._boot_consumed = True
            self._session_token = secrets.token_urlsafe(48)

            if client_ip:
                self._bound_ip = client_ip
                logger.info("Session bound to IP %s", client_ip)

            return self._session_token

    def verify(self, token: str, client_ip: str | None = None) -> bool:
        with self._lock:
            if self._session_token and hmac.compare_digest(token, self._session_token):
                if self._bound_ip and client_ip:
                    if self._bound_ip != client_ip:
                        logger.warning(
                            "IP mismatch: bound=%s, request=%s",
                            self._bound_ip,
                            client_ip,
                        )
                        return False
                return True
            if not self._boot_consumed and hmac.compare_digest(token, self._boot_token):
                return True
            return False

    def create_ws_ticket(self, client_ip: str) -> str:
        ticket = secrets.token_urlsafe(32)
        now = time.monotonic()

        with self._ws_lock:
            self._cleanup_expired_tickets(now)
            self._ws_tickets[ticket] = {"created_at": now, "ip": client_ip}

        logger.debug("WS ticket created for IP %s", client_ip)
        return ticket

    def consume_ws_ticket(self, ticket: str, client_ip: str) -> bool:
        now = time.monotonic()

        with self._ws_lock:
            self._cleanup_expired_tickets(now)
            data = self._ws_tickets.pop(ticket, None)

        if data is None:
            logger.debug("WS ticket not found or already consumed")
            return False

        if now - data["created_at"] > _WS_TICKET_TTL_SECONDS:
            logger.debug("WS ticket expired")
            return False

        if data["ip"] != client_ip:
            logger.warning(
                "WS ticket IP mismatch: expected=%s, got=%s",
                data["ip"],
                client_ip,
            )
            return False

        logger.debug("WS ticket consumed for IP %s", client_ip)
        return True

    def _cleanup_expired_tickets(self, now: float) -> None:
        expired = [
            t for t, d in self._ws_tickets.items() if now - d["created_at"] > _WS_TICKET_TTL_SECONDS
        ]
        for t in expired:
            del self._ws_tickets[t]

    @property
    def is_claimed(self) -> bool:
        with self._lock:
            return self._boot_consumed


_manager: TokenManager | None = None
_manager_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = TokenManager()
    return _manager


def verify_bearer_token(authorization: str, client_ip: str | None = None) -> bool:
    if not authorization:
        return False

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        return False

    return get_token_manager().verify(parts[1], client_ip=client_ip)
