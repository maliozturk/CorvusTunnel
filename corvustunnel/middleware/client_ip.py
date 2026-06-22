# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/middleware/client_ip.py
# Description: Spoof-resistant client-IP resolution; trusts
#              X-Forwarded-For only from a trusted proxy.
# \*---------------------------------------------------------------------*/



from typing import Any

_LOOPBACK = {"127.0.0.1", "::1"}


def _trusted_proxies() -> set[str]:
    from corvustunnel.config.settings import get_settings

    return _LOOPBACK | set(get_settings().trusted_proxy_list)


def get_trusted_client_ip(conn: Any) -> str:
    peer = None
    client = getattr(conn, "client", None)
    if client is not None:
        peer = client.host

    headers = getattr(conn, "headers", None)
    forwarded = headers.get("x-forwarded-for") if headers else None

    if forwarded and peer in _trusted_proxies():
        return forwarded.split(",")[0].strip()

    return peer or "unknown"
