"""
CorvusTunnel License Key Generator.

Run this script on YOUR machine (never shipped in the container).
Generates RSA key pairs and signs license keys as JWTs.

Usage:
    # First time: generate RSA key pair
    python keygen.py --init

    # Generate a license key for a customer
    python keygen.py --generate --customer "John Doe" --plan pro --days 365

    # Verify a license key
    python keygen.py --verify KEY_STRING
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path

# ── Key storage ──────────────────────────────────────────────────────
KEYS_DIR = Path(__file__).parent / ".keys"
PRIVATE_KEY_FILE = KEYS_DIR / "private.key"
PUBLIC_KEY_FILE = KEYS_DIR / "public.key"

# We use HMAC-SHA256 for simplicity (no RSA dependency).
# The "private key" is a 64-byte secret used for signing.
# The "public key" is NOT truly public — it's embedded in the container
# in obfuscated form (PyArmor protects it).
# For a truly asymmetric system, swap to RSA with `cryptography` package.


def _generate_keys() -> None:
    """Generate a new signing key pair."""
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    if PRIVATE_KEY_FILE.exists():
        print(f"⚠ Keys already exist at {KEYS_DIR}")
        print("  Delete them first if you want to regenerate.")
        sys.exit(1)

    secret = secrets.token_hex(64)  # 512-bit signing key
    PRIVATE_KEY_FILE.write_text(secret)
    PUBLIC_KEY_FILE.write_text(secret)  # Same key for HMAC (embedded in container)

    print(f"✅ Keys generated at {KEYS_DIR}")
    print(f"   Private key: {PRIVATE_KEY_FILE}")
    print(f"   Public key:  {PUBLIC_KEY_FILE}  (embed this in the container)")
    print()
    print("⚠ KEEP private.key SECRET. Never commit to git.")
    print("  Add '.keys/' to your .gitignore.")


def _load_signing_key() -> str:
    """Load the signing key."""
    if not PRIVATE_KEY_FILE.exists():
        print("❌ No signing key found. Run: python keygen.py --init")
        sys.exit(1)
    return PRIVATE_KEY_FILE.read_text().strip()


def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    """Base64url decode with padding restoration."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _sign_jwt(payload: dict, key: str) -> str:
    """Create a minimal JWT (header.payload.signature)."""
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{h}.{p}".encode()
    sig = hmac.new(key.encode(), message, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


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


def generate_license(
    customer: str,
    plan: str = "pro",
    days: int = 365,
) -> str:
    """Generate a signed license key for a customer.

    Args:
        customer: Customer name or ID.
        plan: License plan (e.g., "pro", "enterprise").
        days: Number of days until expiry.

    Returns:
        A signed JWT license key string.
    """
    key = _load_signing_key()

    now = int(time.time())
    payload = {
        "sub": customer,
        "plan": plan,
        "iat": now,
        "exp": now + (days * 86400),
        "jti": secrets.token_hex(8),  # unique license ID
    }

    token = _sign_jwt(payload, key)
    return token


def verify_license(token: str, key: str | None = None) -> dict | None:
    """Verify a license key and return its payload.

    Args:
        token: The license JWT string.
        key: Signing key (if None, loads from file).

    Returns:
        License payload dict if valid and not expired, None otherwise.
    """
    if key is None:
        key = _load_signing_key()

    payload = _verify_jwt(token, key)
    if payload is None:
        return None

    # Check expiry
    if payload.get("exp", 0) < time.time():
        return None

    return payload


def main():
    parser = argparse.ArgumentParser(description="CorvusTunnel License Key Generator")
    parser.add_argument("--init", action="store_true", help="Generate signing key pair")
    parser.add_argument("--generate", action="store_true", help="Generate a license key")
    parser.add_argument("--verify", type=str, help="Verify a license key")
    parser.add_argument("--customer", type=str, default="customer", help="Customer name")
    parser.add_argument("--plan", type=str, default="pro", help="License plan")
    parser.add_argument("--days", type=int, default=365, help="Days until expiry")

    args = parser.parse_args()

    if args.init:
        _generate_keys()

    elif args.generate:
        token = generate_license(
            customer=args.customer,
            plan=args.plan,
            days=args.days,
        )
        print(f"✅ License key generated for: {args.customer}")
        print(f"   Plan: {args.plan}")
        print(f"   Expires in: {args.days} days")
        print()
        print(f"   Key: {token}")
        print()
        print("   Give this key to the customer for their docker-compose.yml")

    elif args.verify:
        payload = verify_license(args.verify)
        if payload:
            import datetime
            exp = datetime.datetime.fromtimestamp(payload["exp"])
            print(f"✅ Valid license")
            print(f"   Customer: {payload.get('sub', '?')}")
            print(f"   Plan:     {payload.get('plan', '?')}")
            print(f"   Expires:  {exp.isoformat()}")
            print(f"   ID:       {payload.get('jti', '?')}")
        else:
            print("❌ Invalid or expired license key")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
