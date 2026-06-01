"""
CorvusTunnel Bearer Token Authentication.

Two-token system:
  - Boot token:    one-time-use, from AGENT_TOKEN env, delivered via QR code
  - Session token: issued after boot token is claimed, used for all API calls

Timing-safe comparison to prevent timing attacks.
"""

from __future__ import annotations

import hmac
import secrets
import threading

from config.settings import get_settings


class TokenManager:
    """Manages boot token (one-time) and session token (persistent).

    Boot token is consumed after first successful claim.
    Session token is returned to the client and used for all subsequent auth.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._boot_token: str = get_settings().agent_token
        self._boot_consumed: bool = False
        self._session_token: str | None = None

    def claim_boot_token(self, token: str) -> str | None:
        """Exchange the boot token for a session token.

        Returns the session token on success, None if invalid or already consumed.
        """
        with self._lock:
            if self._boot_consumed:
                return None
            if not hmac.compare_digest(token, self._boot_token):
                return None

            # Consume boot token and generate session token
            self._boot_consumed = True
            self._session_token = secrets.token_urlsafe(48)
            return self._session_token

    def verify(self, token: str) -> bool:
        """Verify a token (session token only, boot token is dead after claim)."""
        with self._lock:
            if self._session_token and hmac.compare_digest(token, self._session_token):
                return True
            # Allow boot token ONLY if not yet claimed (for backward compat / API calls before claim)
            if not self._boot_consumed and hmac.compare_digest(token, self._boot_token):
                return True
            return False

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


def verify_bearer_token(authorization: str) -> bool:
    """
    Verify a bearer token from the Authorization header.

    Uses the TokenManager which accepts session tokens (or unclaimed boot tokens).

    Args:
        authorization: The full Authorization header value,
                       expected format: "Bearer <token>"

    Returns:
        True if the token is valid, False otherwise.
    """
    if not authorization:
        return False

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer":
        return False

    return get_token_manager().verify(parts[1])
