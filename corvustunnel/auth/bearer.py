# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/auth/bearer.py
# Description: Boot/session token manager. The one-time boot token is claimed
#              for a reusable session token, both exchanged only inside the
#              authenticated channel; the session is bound to that channel.
# \*---------------------------------------------------------------------*/

import hmac
import logging
import secrets
import threading

from corvustunnel.config.settings import get_settings

logger = logging.getLogger("corvustunnel.auth.bearer")


class TokenManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._boot_token: str = get_settings().agent_token
        self._boot_consumed: bool = False
        self._session_token: str | None = None

    def claim_boot_token(self, token: str, client_ip: str | None = None) -> str | None:
        with self._lock:
            if self._boot_consumed:
                return None
            if not hmac.compare_digest(token, self._boot_token):
                return None
            self._boot_consumed = True
            self._session_token = secrets.token_urlsafe(48)
            return self._session_token

    def verify(self, token: str, client_ip: str | None = None) -> bool:
        with self._lock:
            if self._session_token and hmac.compare_digest(token, self._session_token):
                return True
            if not self._boot_consumed and hmac.compare_digest(token, self._boot_token):
                return True
            return False

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
