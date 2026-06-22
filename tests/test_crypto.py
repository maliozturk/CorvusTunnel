"""
Tests for crypto/e2e.py — NaCl E2E encryption.

Covers:
  - Module imports without error
  - PyNaCl availability detection
  - Key generation (when PyNaCl is installed)
  - Encrypt/decrypt roundtrip
  - Key exchange between server and client
  - Graceful fallback when PyNaCl is not installed
  - Base64url encoding/decoding helpers
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


def _nacl_available() -> bool:
    """Check if PyNaCl is actually installed."""
    try:
        import nacl.public  # noqa: F401
        return True
    except ImportError:
        return False


class TestCryptoImport:
    """Tests for importing the crypto module."""

    def test_crypto_module_imports(self):
        """crypto.e2e should import without raising an exception."""
        import corvustunnel.crypto.e2e  # noqa: F401

    def test_get_e2e_crypto_returns_instance(self, env_token):
        """get_e2e_crypto should return an E2ECrypto instance."""
        from corvustunnel.crypto.e2e import get_e2e_crypto, E2ECrypto
        instance = get_e2e_crypto()
        assert isinstance(instance, E2ECrypto)

    def test_available_property_reflects_nacl(self, env_token):
        """available property should match whether PyNaCl is installed."""
        from corvustunnel.crypto.e2e import get_e2e_crypto
        instance = get_e2e_crypto()
        assert instance.available == _nacl_available()


class TestBase64Helpers:
    """Tests for base64url encode/decode helpers."""

    def test_b64url_roundtrip(self):
        """Encoding then decoding should return the original bytes."""
        from corvustunnel.crypto.e2e import _b64url_encode, _b64url_decode

        original = b"hello world! this is a test 1234"
        encoded = _b64url_encode(original)
        decoded = _b64url_decode(encoded)
        assert decoded == original

    def test_b64url_no_padding(self):
        """Base64url output should have no '=' padding."""
        from corvustunnel.crypto.e2e import _b64url_encode

        encoded = _b64url_encode(b"test")
        assert "=" not in encoded

    def test_b64url_url_safe_chars(self):
        """Output should use URL-safe characters (- and _ instead of + and /)."""
        from corvustunnel.crypto.e2e import _b64url_encode

        # Use bytes that would produce + or / in standard base64
        data = b"\xfb\xff\xfe"
        encoded = _b64url_encode(data)
        assert "+" not in encoded
        assert "/" not in encoded


def _client_pub_b64() -> str:
    """Generate a fresh client public key as base64url (test helper)."""
    import nacl.public

    from corvustunnel.crypto.e2e import _b64url_encode

    client_key = nacl.public.PrivateKey.generate().public_key
    return _b64url_encode(client_key.encode(encoder=nacl.encoding.RawEncoder))


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestEphemeralExchangeKeys:
    """The server uses fresh ephemeral keys per exchange (forward secrecy)."""

    def test_exchange_returns_ephemeral_public_key(self, env_token):
        """exchange() returns the session's ephemeral server public key."""
        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_decode

        crypto = E2ECrypto()
        key_b64 = crypto.exchange("sess-a", _client_pub_b64())
        assert key_b64  # non-empty
        # X25519 public key is 32 bytes
        assert len(_b64url_decode(key_b64)) == 32

    def test_no_global_server_key(self, env_token):
        """There is no persistent global server key in the ephemeral model."""
        from corvustunnel.crypto.e2e import E2ECrypto

        crypto = E2ECrypto()
        assert crypto.server_public_key_b64 == ""

    def test_each_session_gets_a_different_key(self, env_token):
        """Two exchanges must yield different server keys (forward secrecy)."""
        from corvustunnel.crypto.e2e import E2ECrypto

        crypto = E2ECrypto()
        key1 = crypto.exchange("sess-1", _client_pub_b64())
        key2 = crypto.exchange("sess-2", _client_pub_b64())
        assert key1 != key2


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestEncryptDecrypt:
    """Tests for encrypt/decrypt roundtrip (requires PyNaCl)."""

    def _setup_session(self):
        """Create a server and client, perform key exchange."""
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto

        server = E2ECrypto()

        # Create a client keypair
        client_private = nacl.public.PrivateKey.generate()
        client_public = client_private.public_key

        from corvustunnel.crypto.e2e import _b64url_encode
        client_pub_b64 = _b64url_encode(
            client_public.encode(encoder=nacl.encoding.RawEncoder)
        )

        # Perform key exchange
        session_id = "test-session-001"
        server.exchange(session_id, client_pub_b64)

        return server, client_private, client_public, session_id

    def test_encrypt_decrypt_roundtrip(self, env_token):
        """Encrypting then decrypting should return the original plaintext."""
        server, _, _, session_id = self._setup_session()

        plaintext = "Hello, World! 🦆"
        ciphertext = server.encrypt(session_id, plaintext)
        decrypted = server.decrypt(session_id, ciphertext)
        assert decrypted == plaintext

    def test_encrypt_json_roundtrip(self, env_token):
        """encrypt_json / decrypt_json should round-trip a dict."""
        server, _, _, session_id = self._setup_session()

        data = {"action": "test", "value": 42, "emoji": "🐦"}
        ciphertext = server.encrypt_json(session_id, data)
        decrypted = server.decrypt_json(session_id, ciphertext)
        assert decrypted == data

    def test_encrypt_empty_string(self, env_token):
        """Encrypting an empty string should still round-trip."""
        server, _, _, session_id = self._setup_session()

        ciphertext = server.encrypt(session_id, "")
        decrypted = server.decrypt(session_id, ciphertext)
        assert decrypted == ""

    def test_ciphertext_differs_each_time(self, env_token):
        """Same plaintext should produce different ciphertext (random nonce)."""
        server, _, _, session_id = self._setup_session()

        plaintext = "deterministic?"
        ct1 = server.encrypt(session_id, plaintext)
        ct2 = server.encrypt(session_id, plaintext)
        assert ct1 != ct2  # Random nonce ensures different ciphertext

    def test_decrypt_wrong_session_raises(self, env_token):
        """Decrypting with a non-existent session should raise KeyError."""
        server, _, _, session_id = self._setup_session()

        ciphertext = server.encrypt(session_id, "test")
        with pytest.raises(KeyError):
            server.decrypt("wrong-session", ciphertext)


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestKeyExchange:
    """Tests for the key exchange mechanism."""

    def test_exchange_creates_session(self, env_token):
        """After exchange, the session should exist."""
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_encode

        server = E2ECrypto()
        client_key = nacl.public.PrivateKey.generate().public_key
        client_b64 = _b64url_encode(
            client_key.encode(encoder=nacl.encoding.RawEncoder)
        )

        session_id = "exchange-test"
        result = server.exchange(session_id, client_b64)

        # exchange returns the session's ephemeral server public key (32 bytes)
        from corvustunnel.crypto.e2e import _b64url_decode
        assert len(_b64url_decode(result)) == 32
        assert server.has_session(session_id) is True

    def test_remove_session(self, env_token):
        """remove_session should delete encryption state."""
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_encode

        server = E2ECrypto()
        client_key = nacl.public.PrivateKey.generate().public_key
        client_b64 = _b64url_encode(
            client_key.encode(encoder=nacl.encoding.RawEncoder)
        )

        session_id = "remove-test"
        server.exchange(session_id, client_b64)
        assert server.has_session(session_id) is True

        server.remove_session(session_id)
        assert server.has_session(session_id) is False

    def test_exchange_invalid_key_raises(self, env_token):
        """Invalid client public key should raise ValueError."""
        from corvustunnel.crypto.e2e import E2ECrypto

        server = E2ECrypto()
        with pytest.raises(ValueError, match="Invalid client public key"):
            server.exchange("bad-session", "not-a-valid-key!!!")


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestClientServerInterop:
    """Prove a *separate* client (as the browser would) interoperates.

    The browser uses tweetnacl; this reconstructs the client side with PyNaCl
    using only the server's returned ephemeral public key. tweetnacl and PyNaCl
    implement the identical crypto_box primitive, so this exercises the exact
    wire format the JS client relies on.
    """

    def _handshake(self):
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_decode, _b64url_encode

        server = E2ECrypto()
        client_priv = nacl.public.PrivateKey.generate()
        client_pub_b64 = _b64url_encode(
            client_priv.public_key.encode(encoder=nacl.encoding.RawEncoder)
        )
        sid = "interop"
        server_pub_b64 = server.exchange(sid, client_pub_b64)
        # Client derives the same Box from the server's ephemeral public key
        server_pub = nacl.public.PublicKey(_b64url_decode(server_pub_b64))
        client_box = nacl.public.Box(client_priv, server_pub)
        return server, sid, client_box

    def test_server_to_client(self, env_token):
        """Client decrypts what the server encrypted."""
        from corvustunnel.crypto.e2e import _b64url_decode

        server, sid, client_box = self._handshake()
        ct = server.encrypt(sid, "output from PTY █ 日本語")
        plain = client_box.decrypt(_b64url_decode(ct)).decode("utf-8")
        assert plain == "output from PTY █ 日本語"

    def test_client_to_server(self, env_token):
        """Server decrypts what the client encrypted."""
        from corvustunnel.crypto.e2e import _b64url_encode

        server, sid, client_box = self._handshake()
        encrypted = client_box.encrypt(b"ls -la\r")  # nonce||ct
        ct_b64 = _b64url_encode(bytes(encrypted))
        assert server.decrypt(sid, ct_b64) == "ls -la\r"


class TestCryptoFallback:
    """Tests for graceful fallback when PyNaCl is not installed."""

    def test_unavailable_when_nacl_missing(self, env_token):
        """When _nacl_available is False, E2ECrypto.available should be False."""
        from corvustunnel.crypto.e2e import E2ECrypto

        with patch("corvustunnel.crypto.e2e._nacl_available", False):
            crypto = E2ECrypto()
            assert crypto.available is False
            assert crypto.server_public_key_b64 == ""

    def test_exchange_raises_without_nacl(self, env_token):
        """exchange() should raise ValueError when PyNaCl is unavailable."""
        from corvustunnel.crypto.e2e import E2ECrypto

        with patch("corvustunnel.crypto.e2e._nacl_available", False):
            crypto = E2ECrypto()
            with pytest.raises(ValueError, match="not available"):
                crypto.exchange("session", "some-key")
