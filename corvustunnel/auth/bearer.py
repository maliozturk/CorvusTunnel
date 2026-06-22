"""
CorvusTunnel Bearer Token Authentication.

Two-token system:
  - Boot token:    one-time-use, from AGENT_TOKEN env, delivered via QR code
  - Session token: issued after boot token is claimed, used for all API calls

Timing-safe comparison to prevent timing attacks.

Additional features:
  - WebSocket ticket system: one-time, IP-bound, 30-second tickets for WS auth.
  - IP binding: after boot-token claim, all requests must originate from the
    same client IP.
"""

from __future__ import annotations

import hmac
import logging
import secrets
import threading
import time

from corvustunnel.config.settings import get_settings

logger = logging.getLogger("corvustunnel.auth.bearer")

# ── Constants ────────────────────────────────────────────────────────
_WS_TICKET_TTL_SECONDS: float = 30.0


class TokenManager:
    """Manages boot token (one-time) and session token (persistent).

    Boot token is consumed after first successful claim.
    Session token is returned to the client and used for all subsequent auth.

    Extended capabilities:
      - **WS tickets**: short-lived, one-time, IP-bound tickets that can be
        exchanged for a WebSocket connection.
      - **IP binding**: once the boot token is claimed from a specific IP,
        all subsequent session-token verifications enforce the same IP.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._boot_token: str = get_settings().agent_token
        self._boot_consumed: bool = False
        self._session_token: str | None = None

        # IP binding
        self._bound_ip: str | None = None

        # WebSocket ticket store: ticket -> {"created_at": float, "ip": str}
        self._ws_tickets: dict[str, dict] = {}
        self._ws_lock = threading.Lock()

    # ── Boot / session token management ──────────────────────────────

    def claim_boot_token(self, token: str, client_ip: str | None = None) -> str | None:
        """Exchange the boot token for a session token.

        Args:
            token: The boot token value presented by the client.
            client_ip: If provided, binds all future session verification
                       to this IP address.

        Returns:
            The session token on success, ``None`` if invalid or already consumed.
        """
        with self._lock:
            if self._boot_consumed:
                return None
            if not hmac.compare_digest(token, self._boot_token):
                return None

            # Consume boot token and generate session token
            self._boot_consumed = True
            self._session_token = secrets.token_urlsafe(48)

            # Bind to the claiming IP
            if client_ip:
                self._bound_ip = client_ip
                logger.info("Session bound to IP %s", client_ip)

            return self._session_token

    def verify(self, token: str, client_ip: str | None = None) -> bool:
        """Verify a token (session token only, boot token is dead after claim).

        Args:
            token: The token value to verify.
            client_ip: Optional client IP for IP-binding enforcement.
        """
        with self._lock:
            if self._session_token and hmac.compare_digest(token, self._session_token):
                # Enforce IP binding
                if self._bound_ip and client_ip:
                    if self._bound_ip != client_ip:
                        logger.warning(
                            "IP mismatch: bound=%s, request=%s",
                            self._bound_ip,
                            client_ip,
                        )
                        return False
                return True
            # Allow boot token ONLY if not yet claimed (for backward compat / API calls before claim)
            if not self._boot_consumed and hmac.compare_digest(token, self._boot_token):
                return True
            return False

    # ── WebSocket ticket system ──────────────────────────────────────

    def create_ws_ticket(self, client_ip: str) -> str:
        """Generate a one-time WebSocket ticket bound to *client_ip*.

        The ticket expires after 30 seconds and can only be consumed
        from the same IP that requested it.

        Args:
            client_ip: The IP address to bind the ticket to.

        Returns:
            A URL-safe ticket string.
        """
        ticket = secrets.token_urlsafe(32)
        now = time.monotonic()

        with self._ws_lock:
            self._cleanup_expired_tickets(now)
            self._ws_tickets[ticket] = {"created_at": now, "ip": client_ip}

        logger.debug("WS ticket created for IP %s", client_ip)
        return ticket

    def consume_ws_ticket(self, ticket: str, client_ip: str) -> bool:
        """Validate and consume a one-time WebSocket ticket.

        Checks:
          1. Ticket exists.
          2. Ticket has not expired (30 s TTL).
          3. Requesting IP matches the IP the ticket was issued to.

        The ticket is removed regardless of validation outcome to
        prevent replay attacks.

        Args:
            ticket: The ticket string to consume.
            client_ip: The IP address of the consumer.

        Returns:
            ``True`` if the ticket is valid and consumed successfully.
        """
        now = time.monotonic()

        with self._ws_lock:
            self._cleanup_expired_tickets(now)
            data = self._ws_tickets.pop(ticket, None)

        if data is None:
            logger.debug("WS ticket not found or already consumed")
            return False

        # Check expiry
        if now - data["created_at"] > _WS_TICKET_TTL_SECONDS:
            logger.debug("WS ticket expired")
            return False

        # Check IP binding
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
        """Remove expired WS tickets (caller must hold ``_ws_lock``)."""
        expired = [
            t
            for t, d in self._ws_tickets.items()
            if now - d["created_at"] > _WS_TICKET_TTL_SECONDS
        ]
        for t in expired:
            del self._ws_tickets[t]

    # ── Properties ───────────────────────────────────────────────────

    @property
    def is_claimed(self) -> bool:
        with self._lock:
            return self._boot_consumed


# ── Singleton ────────────────────────────────────────────────────────
_manager: TokenManager | None = None
_manager_lock = threading.Lock()


def get_token_manager() -> TokenManager:
    """Return the singleton TokenManager."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = TokenManager()
    return _manager


def verify_bearer_token(
    authorization: str, client_ip: str | None = None
) -> bool:
    """
    Verify a bearer token from the Authorization header.

    Uses the TokenManager which accepts session tokens (or unclaimed boot tokens).

    Args:
        authorization: The full Authorization header value,
                       expected format: "Bearer <token>"
        client_ip: Optional client IP for IP-binding enforcement.

    Returns:
        True if the token is valid, False otherwise.
    """
    if not authorization:
        return False

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        return False

    return get_token_manager().verify(parts[1], client_ip=client_ip)
