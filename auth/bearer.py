"""
CorvusTunnel Bearer Token Authentication.

Timing-safe comparison to prevent timing attacks.
"""

from __future__ import annotations

import hmac

from config.settings import get_settings


def verify_bearer_token(authorization: str) -> bool:
    """
    Verify a bearer token from the Authorization header.
    
    Uses constant-time comparison (hmac.compare_digest) to prevent
    timing attacks that could leak token information.
    
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

    provided_token = parts[1]
    expected_token = get_settings().agent_token

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(provided_token, expected_token)
