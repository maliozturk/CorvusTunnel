"""
CorvusTunnel E2E Encryption — PyNaCl (libsodium).

Implements end-to-end encryption between the client (phone/browser)
and the server using X25519 Diffie-Hellman key exchange + NaCl SecretBox.

Flow:
    1. Server generates a long-lived keypair on first boot → stored in ~/.corvustunnel/keys/
    2. QR code includes the server's public key (base64url)
    3. Client scans QR → generates ephemeral keypair → sends its public key to /api/e2e/exchange
    4. Both derive a shared secret via X25519 Diffie-Hellman
    5. All subsequent WebSocket messages are encrypted with NaCl SecretBox (XSalsa20-Poly1305)

Security properties:
    - Forward secrecy per session (client uses ephemeral keys)
    - Authenticated encryption (Poly1305 MAC)
    - 24-byte random nonce per message (prepended to ciphertext)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("corvustunnel.crypto")

# Lazy import nacl to allow graceful fallback
_nacl_available = False
try:
    import nacl.public
    import nacl.utils
    import nacl.encoding
    _nacl_available = True
except ImportError:
    logger.warning(
        "PyNaCl not installed — E2E encryption disabled. "
        "Install with: pip install PyNaCl"
    )


def _get_keys_dir() -> Path:
    """Return the directory for storing server keys."""
    keys_dir = Path.home() / ".corvustunnel" / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    return keys_dir


def _b64url_encode(data: bytes) -> str:
    """Base64url-encode bytes (no padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64url-decode a string (with padding restoration)."""
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


class E2ECrypto:
    """End-to-end encryption manager.

    Manages the server's long-lived keypair and per-session shared secrets.
    Thread-safe for concurrent WebSocket connections.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._server_private_key: nacl.public.PrivateKey | None = None
        self._server_public_key: nacl.public.PublicKey | None = None

        # Per-session shared secrets: session_id → Box
        self._session_boxes: dict[str, nacl.public.Box] = {}
        self._session_lock = threading.Lock()

        if _nacl_available:
            self._load_or_generate_keys()

    @property
    def available(self) -> bool:
        """Whether E2E encryption is available (PyNaCl installed)."""
        return _nacl_available and self._server_public_key is not None

    @property
    def server_public_key_b64(self) -> str:
        """Server's public key as base64url string (for QR code)."""
        if not self.available:
            return ""
        return _b64url_encode(
            self._server_public_key.encode(encoder=nacl.encoding.RawEncoder)
        )

    # ── Key Management ───────────────────────────────────────────────

    def _load_or_generate_keys(self) -> None:
        """Load existing server keypair or generate a new one."""
        keys_dir = _get_keys_dir()
        private_key_file = keys_dir / "server_private.key"
        public_key_file = keys_dir / "server_public.key"

        if private_key_file.exists():
            # Load existing keys
            try:
                private_bytes = private_key_file.read_bytes()
                self._server_private_key = nacl.public.PrivateKey(private_bytes)
                self._server_public_key = self._server_private_key.public_key
                logger.info("Loaded E2E server keys from %s", keys_dir)
                return
            except Exception as e:
                logger.warning("Failed to load E2E keys, regenerating: %s", e)

        # Generate new keypair
        self._server_private_key = nacl.public.PrivateKey.generate()
        self._server_public_key = self._server_private_key.public_key

        # Save keys (private key file readable only by owner)
        private_key_file.write_bytes(
            self._server_private_key.encode(encoder=nacl.encoding.RawEncoder)
        )
        os.chmod(str(private_key_file), 0o600)

        public_key_file.write_bytes(
            self._server_public_key.encode(encoder=nacl.encoding.RawEncoder)
        )

        logger.info("Generated new E2E server keys in %s", keys_dir)

    # ── Key Exchange ─────────────────────────────────────────────────

    def exchange(self, session_id: str, client_public_key_b64: str) -> str:
        """Perform key exchange with a client.

        Args:
            session_id: Unique identifier for this session.
            client_public_key_b64: Client's public key as base64url string.

        Returns:
            Server's public key as base64url string.

        Raises:
            ValueError: If E2E is not available or key is invalid.
        """
        if not self.available:
            raise ValueError("E2E encryption not available (PyNaCl not installed)")

        try:
            client_public_bytes = _b64url_decode(client_public_key_b64)
            client_public_key = nacl.public.PublicKey(client_public_bytes)
        except Exception as e:
            raise ValueError(f"Invalid client public key: {e}")

        # Create a Box (shared secret derived via X25519 DH)
        box = nacl.public.Box(self._server_private_key, client_public_key)

        with self._session_lock:
            self._session_boxes[session_id] = box

        logger.info("E2E key exchange completed for session %s", session_id)
        return self.server_public_key_b64

    def has_session(self, session_id: str) -> bool:
        """Check if a session has completed key exchange."""
        with self._session_lock:
            return session_id in self._session_boxes

    def remove_session(self, session_id: str) -> None:
        """Remove a session's encryption state."""
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

        plaintext_bytes = plaintext.encode("utf-8")
        encrypted = box.encrypt(plaintext_bytes)  # nonce prepended automatically

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
            nacl.exceptions.CryptoError: If decryption fails.
        """
        with self._session_lock:
            box = self._session_boxes.get(session_id)

        if box is None:
            raise KeyError(f"No E2E session: {session_id}")

        ciphertext_bytes = _b64url_decode(ciphertext_b64)
        plaintext_bytes = box.decrypt(ciphertext_bytes)

        return plaintext_bytes.decode("utf-8")

    def encrypt_json(self, session_id: str, data: dict[str, Any]) -> str:
        """Encrypt a JSON-serializable dict."""
        return self.encrypt(session_id, json.dumps(data, separators=(",", ":")))

    def decrypt_json(self, session_id: str, ciphertext_b64: str) -> dict[str, Any]:
        """Decrypt a JSON message."""
        plaintext = self.decrypt(session_id, ciphertext_b64)
        return json.loads(plaintext)


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
