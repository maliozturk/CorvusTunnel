# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/crypto/e2e.py
# Description: Ephemeral X25519 + NaCl Box end-to-end encryption for
#              WebSocket frames.
# \*---------------------------------------------------------------------*/



import base64
import json
import logging
import threading
from typing import Any

logger = logging.getLogger("corvustunnel.crypto")

_nacl_available = False
try:
    import nacl.encoding
    import nacl.public

    _nacl_available = True
except ImportError:
    logger.warning(
        "PyNaCl not installed — E2E encryption disabled. Install with: pip install PyNaCl"
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


class E2ECrypto:
    def __init__(self) -> None:
        self._session_boxes: dict[str, nacl.public.Box] = {}
        self._session_lock = threading.Lock()

    @property
    def available(self) -> bool:
        return _nacl_available

    @property
    def server_public_key_b64(self) -> str:
        return ""

    def exchange(self, session_id: str, client_public_key_b64: str) -> str:
        if not self.available:
            raise ValueError("E2E encryption not available (PyNaCl not installed)")

        try:
            client_public_bytes = _b64url_decode(client_public_key_b64)
            client_public_key = nacl.public.PublicKey(client_public_bytes)
        except Exception as e:
            raise ValueError(f"Invalid client public key: {e}")

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
        with self._session_lock:
            return session_id in self._session_boxes

    def remove_session(self, session_id: str) -> None:
        with self._session_lock:
            self._session_boxes.pop(session_id, None)

    def encrypt(self, session_id: str, plaintext: str) -> str:
        with self._session_lock:
            box = self._session_boxes.get(session_id)

        if box is None:
            raise KeyError(f"No E2E session: {session_id}")

        encrypted = box.encrypt(plaintext.encode("utf-8"))
        return _b64url_encode(encrypted)

    def decrypt(self, session_id: str, ciphertext_b64: str) -> str:
        with self._session_lock:
            box = self._session_boxes.get(session_id)

        if box is None:
            raise KeyError(f"No E2E session: {session_id}")

        plaintext_bytes = box.decrypt(_b64url_decode(ciphertext_b64))
        return plaintext_bytes.decode("utf-8")

    def encrypt_json(self, session_id: str, data: dict[str, Any]) -> str:
        return self.encrypt(session_id, json.dumps(data, separators=(",", ":")))

    def decrypt_json(self, session_id: str, ciphertext_b64: str) -> dict[str, Any]:
        return json.loads(self.decrypt(session_id, ciphertext_b64))


_e2e_crypto: E2ECrypto | None = None
_e2e_lock = threading.Lock()


def get_e2e_crypto() -> E2ECrypto:
    global _e2e_crypto
    if _e2e_crypto is None:
        with _e2e_lock:
            if _e2e_crypto is None:
                _e2e_crypto = E2ECrypto()
    return _e2e_crypto
