"""
CorvusTunnel E2E Encryption — PyNaCl (libsodium).

Implements end-to-end encryption between the client (phone/browser)
and the server using X25519 Diffie-Hellman key exchange + NaCl Box
(crypto_box: X25519 + XSalsa20-Poly1305).

Flow (per session — full forward secrecy):
    1. Client generates an *ephemeral* X25519 keypair on connect.
    2. Client POSTs its public key to /api/e2e/exchange (over the relay).
    3. Server generates a fresh *ephemeral* X25519 keypair for that session,
       derives the shared Box, stores it, and returns its ephemeral public key.
    4. Both sides hold an identical Box and encrypt every WebSocket frame.
    5. When the session ends the Box is dropped — the keys never touch disk.

Wire format for an encrypted frame (matches tweetnacl on the client):
    base64url( nonce[24] || ciphertext )   — ciphertext includes the Poly1305 tag.

Security properties:
    - Forward secrecy: both endpoints use ephemeral keys, nothing persisted.
    - Authenticated encryption (Poly1305 MAC).
    - 24-byte random nonce per message (prepended to ciphertext).
    - The relay only ever sees opaque ciphertext.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
from typing import Any

logger = logging.getLogger("corvustunnel.crypto")

# Lazy import nacl to allow graceful fallback
_nacl_available = False
try:
    import nacl.encoding
    import nacl.public
    _nacl_available = True
except ImportError:
    logger.warning(
        "PyNaCl not installed — E2E encryption disabled. "
        "Install with: pip install PyNaCl"
    )


def _b64url_encode(data: bytes) -> str:
    """Base64url-encode bytes (no padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64url-decode a string (with padding restoration)."""
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


class E2ECrypto:
    """End-to-end encryption manager.

    Holds one ephemeral shared :class:`Box` per session. There is no
    long-lived server keypair: every session derives fresh keys, giving
    forward secrecy, and nothing is written to disk.

    Thread-safe for concurrent WebSocket connections.
    """

    def __init__(self) -> None:
        # Per-session shared secrets: session_id → Box
        self._session_boxes: dict[str, nacl.public.Box] = {}
        self._session_lock = threading.Lock()

    @property
    def available(self) -> bool:
        """Whether E2E encryption is available (PyNaCl installed)."""
        return _nacl_available

    @property
    def server_public_key_b64(self) -> str:
        """Deprecated: there is no global server key in the ephemeral model.

        Kept so older callers (e.g. QR/relay registration) degrade gracefully
        to "no key advertised" — the client performs a live key exchange
        instead. Always returns an empty string.
        """
        return ""

    # ── Key Exchange ─────────────────────────────────────────────────

    def exchange(self, session_id: str, client_public_key_b64: str) -> str:
        """Perform an ephemeral key exchange with a client.

        Generates a fresh server keypair for *session_id*, derives the shared
        Box from it and the client's public key, stores the Box, and returns
        the server's ephemeral public key.

        Args:
            session_id: Unique identifier for this session.
            client_public_key_b64: Client's ephemeral public key (base64url).

        Returns:
            Server's ephemeral public key as a base64url string.

        Raises:
            ValueError: If E2E is not available or the key is invalid.
        """
        if not self.available:
            raise ValueError("E2E encryption not available (PyNaCl not installed)")

        try:
            client_public_bytes = _b64url_decode(client_public_key_b64)
            client_public_key = nacl.public.PublicKey(client_public_bytes)
        except Exception as e:
            raise ValueError(f"Invalid client public key: {e}")

        # Fresh ephemeral server keypair → forward secrecy, no disk persistence.
        server_private_key = nacl.public.PrivateKey.generate()
        box = nacl.public.Box(server_private_key, client_public_key)

        with self._session_lock:
            self._session_boxes[session_id] = box

        server_public_b64 = _b64url_encode(
            server_private_key.public_key.encode(encoder=nacl.encoding.RawEncoder)
        )
        logger.info("E2E key exchange completed for session %s", session_id)
        return server_public_b64

    def has_session(self, session_id: str) -> bool:
        """Check if a session has completed key exchange."""
        with self._session_lock:
            return session_id in self._session_boxes

    def remove_session(self, session_id: str) -> None:
        """Drop a session's encryption state (called on disconnect)."""
        with self._session_lock:
            self._session_boxes.pop(session_id, None)

    # ── Encrypt / Decrypt ────────────────────────────────────────────

    def encrypt(self, session_id: str, plaintext: str) -> str:
        """Encrypt a message for a session.

        Args:
            session_id: The session to encrypt for.
            plaintext: The message to encrypt (UTF-8 string).

        Returns:
            Base64url-encoded ciphertext (nonce prepended).

        Raises:
            KeyError: If session has no encryption state.
        """
        with self._session_lock:
            box = self._session_boxes.get(session_id)

        if box is None:
            raise KeyError(f"No E2E session: {session_id}")

        encrypted = box.encrypt(plaintext.encode("utf-8"))  # nonce prepended
        return _b64url_encode(encrypted)

    def decrypt(self, session_id: str, ciphertext_b64: str) -> str:
        """Decrypt a message from a session.

        Args:
            session_id: The session to decrypt for.
            ciphertext_b64: Base64url-encoded ciphertext (nonce prepended).

        Returns:
            Decrypted plaintext (UTF-8 string).

        Raises:
            KeyError: If session has no encryption state.
            nacl.exceptions.CryptoError: If decryption/authentication fails.
        """
        with self._session_lock:
            box = self._session_boxes.get(session_id)

        if box is None:
            raise KeyError(f"No E2E session: {session_id}")

        plaintext_bytes = box.decrypt(_b64url_decode(ciphertext_b64))
        return plaintext_bytes.decode("utf-8")

    def encrypt_json(self, session_id: str, data: dict[str, Any]) -> str:
        """Encrypt a JSON-serializable dict."""
        return self.encrypt(session_id, json.dumps(data, separators=(",", ":")))

    def decrypt_json(self, session_id: str, ciphertext_b64: str) -> dict[str, Any]:
        """Decrypt a JSON message."""
        return json.loads(self.decrypt(session_id, ciphertext_b64))


# ── Singleton ────────────────────────────────────────────────────────

_e2e_crypto: E2ECrypto | None = None
_e2e_lock = threading.Lock()


def get_e2e_crypto() -> E2ECrypto:
    """Return the singleton E2ECrypto instance."""
    global _e2e_crypto
    if _e2e_crypto is None:
        with _e2e_lock:
            if _e2e_crypto is None:
                _e2e_crypto = E2ECrypto()
    return _e2e_crypto
