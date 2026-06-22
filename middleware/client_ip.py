"""
Canonical client-IP resolution.

Every IP-based control (rate limiting, IP bans, session IP-binding) must use
the *same* notion of "client IP", and that notion must not be spoofable.

``X-Forwarded-For`` is attacker-controlled on any request that reaches the
server directly. We therefore trust it **only** when the immediate peer is a
trusted proxy — by default the loopback address, since the relay bridge and
cloudflared both run on localhost and connect to the public port over
127.0.0.1. For a direct connection from any other address the header is
ignored and the real socket address is used instead.
"""

from __future__ import annotations

from typing import Any

_LOOPBACK = {"127.0.0.1", "::1"}


def _trusted_proxies() -> set[str]:
    from config.settings import get_settings

    return _LOOPBACK | set(get_settings().trusted_proxy_list)


def get_trusted_client_ip(conn: Any) -> str:
    """Resolve the real client IP for a Starlette ``Request`` or ``WebSocket``.

    Trusts the first ``X-Forwarded-For`` hop only when the direct peer is a
    trusted proxy; otherwise returns the direct socket address so the header
    cannot be used to spoof bans, rate limits, or IP binding.
    """
    peer = None
    client = getattr(conn, "client", None)
    if client is not None:
        peer = client.host

    headers = getattr(conn, "headers", None)
    forwarded = headers.get("x-forwarded-for") if headers else None

    if forwarded and peer in _trusted_proxies():
        return forwarded.split(",")[0].strip()

    return peer or "unknown"
