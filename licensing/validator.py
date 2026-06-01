"""
CorvusTunnel License Validator.

Validates license keys at container startup and periodically (24h heartbeat).
Uses HMAC-SHA256 signed JWTs — no network required.

The signing key is embedded in this file and protected by PyArmor obfuscation
in production builds.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import threading
import time

logger = logging.getLogger("corvustunnel.licensing")

# ── Embedded signing key ─────────────────────────────────────────────
# This is loaded from the .keys/public.key file during development.
# In production (PyArmor-obfuscated), this module is encrypted,
# so the key is not trivially extractable.
#
# Set CORVUS_SIGNING_KEY env var to override (for development only).
# In production, call embed_key() during build to hardcode it.

_EMBEDDED_KEY: str = ""  # Will be set by _load_key()


def _load_key() -> str:
    """Load the signing key from env or embedded .keys file."""
    global _EMBEDDED_KEY

    # Already loaded
    if _EMBEDDED_KEY:
        return _EMBEDDED_KEY

    # 1. Environment override (dev only)
    env_key = os.environ.get("CORVUS_SIGNING_KEY", "")
    if env_key:
        _EMBEDDED_KEY = env_key
        return _EMBEDDED_KEY

    # 2. Load from .keys/public.key file (dev mode)
    key_file = os.path.join(os.path.dirname(__file__), ".keys", "public.key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            _EMBEDDED_KEY = f.read().strip()
        return _EMBEDDED_KEY

    logger.error("No signing key found. Set CORVUS_SIGNING_KEY or run keygen.py --init")
    return ""


# ── JWT Helpers ──────────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    """Base64url decode with padding restoration."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _verify_jwt(token: str, key: str) -> dict | None:
    """Verify and decode a JWT. Returns payload or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        message = f"{parts[0]}.{parts[1]}".encode()
        expected_sig = hmac.new(key.encode(), message, hashlib.sha256).digest()
        actual_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(parts[1]))
        return payload
    except Exception:
        return None


# ── License Result ───────────────────────────────────────────────────

class LicenseResult:
    """Result of a license validation check."""

    def __init__(
        self,
        valid: bool,
        customer: str = "",
        plan: str = "",
        expires_at: int = 0,
        reason: str = "",
    ):
        self.valid = valid
        self.customer = customer
        self.plan = plan
        self.expires_at = expires_at
        self.reason = reason

    def __repr__(self) -> str:
        if self.valid:
            return f"LicenseResult(valid=True, customer={self.customer!r}, plan={self.plan!r})"
        return f"LicenseResult(valid=False, reason={self.reason!r})"


# ── Core Validation ──────────────────────────────────────────────────

def validate_license(license_key: str) -> LicenseResult:
    """Validate a license key string.

    Args:
        license_key: The JWT license key from CORVUS_LICENSE_KEY env var.

    Returns:
        LicenseResult with validation outcome.
    """
    if not license_key or not license_key.strip():
        return LicenseResult(valid=False, reason="No license key provided")

    key = _load_key()
    if not key:
        return LicenseResult(valid=False, reason="Signing key not configured")

    payload = _verify_jwt(license_key.strip(), key)
    if payload is None:
        return LicenseResult(valid=False, reason="Invalid license key signature")

    # Check expiry
    exp = payload.get("exp", 0)
    if exp < time.time():
        return LicenseResult(valid=False, reason="License key has expired")

    return LicenseResult(
        valid=True,
        customer=payload.get("sub", "unknown"),
        plan=payload.get("plan", "unknown"),
        expires_at=exp,
    )


# ── Heartbeat (background thread) ───────────────────────────────────

_heartbeat_thread: threading.Thread | None = None
_heartbeat_stop = threading.Event()

HEARTBEAT_INTERVAL = 86400  # 24 hours
GRACE_PERIOD = 3600         # 1 hour after first failure


def _heartbeat_loop(license_key: str) -> None:
    """Background loop that re-validates the license every 24h."""
    failure_start: float | None = None

    while not _heartbeat_stop.wait(timeout=HEARTBEAT_INTERVAL):
        result = validate_license(license_key)

        if result.valid:
            failure_start = None
            logger.debug("License heartbeat OK: %s", result.customer)
            continue

        # License invalid/expired
        if failure_start is None:
            failure_start = time.time()
            logger.warning(
                "License validation failed: %s. "
                "Grace period: %d minutes remaining.",
                result.reason,
                GRACE_PERIOD // 60,
            )
            continue

        # Check if grace period exceeded
        elapsed = time.time() - failure_start
        if elapsed >= GRACE_PERIOD:
            _shutdown_gracefully(result.reason)
            return


def start_heartbeat(license_key: str) -> None:
    """Start the 24h license heartbeat in a background daemon thread."""
    global _heartbeat_thread

    if _heartbeat_thread and _heartbeat_thread.is_alive():
        return

    _heartbeat_stop.clear()
    _heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(license_key,),
        daemon=True,
        name="license-heartbeat",
    )
    _heartbeat_thread.start()
    logger.info("License heartbeat started (interval: %dh)", HEARTBEAT_INTERVAL // 3600)


def stop_heartbeat() -> None:
    """Stop the heartbeat thread."""
    _heartbeat_stop.set()


# ── Graceful Shutdown ────────────────────────────────────────────────

_SHUTDOWN_BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ⚠  CorvusTunnel License Expired                       ║
║                                                          ║
║   Your license is no longer valid.                       ║
║   Renew at: https://corvustunnel.com/renew               ║
║                                                          ║
║   CorvusTunnel will shut down now.                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

_STARTUP_FAIL_BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ❌  CorvusTunnel License Invalid                       ║
║                                                          ║
║   {reason:<52s}║
║                                                          ║
║   Get a license at: https://corvustunnel.com             ║
║                                                          ║
║   Set CORVUS_LICENSE_KEY in your docker-compose.yml      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


def _shutdown_gracefully(reason: str) -> None:
    """Print shutdown banner and exit."""
    print(_SHUTDOWN_BANNER, file=sys.stderr, flush=True)
    logger.critical("Shutting down: %s", reason)
    os._exit(1)


# ── Entrypoint Functions ─────────────────────────────────────────────

def validate_or_exit() -> None:
    """Validate license at startup. Exit if invalid.

    Called from entrypoint.sh:
        python -c "from licensing.validator import validate_or_exit; validate_or_exit()"
    """
    license_key = os.environ.get("CORVUS_LICENSE_KEY", "")

    # No license key = free/dev mode (skip validation)
    if not license_key:
        logger.info("No license key set — running in development mode")
        return

    result = validate_license(license_key)

    if not result.valid:
        banner = _STARTUP_FAIL_BANNER.format(reason=result.reason)
        print(banner, file=sys.stderr, flush=True)
        sys.exit(1)

    import datetime
    exp_date = datetime.datetime.fromtimestamp(result.expires_at).strftime("%Y-%m-%d")
    logger.info(
        "License valid — customer: %s, plan: %s, expires: %s",
        result.customer,
        result.plan,
        exp_date,
    )

    # Start background heartbeat
    start_heartbeat(license_key)
