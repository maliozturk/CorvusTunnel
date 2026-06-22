# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_crypto.py
# Description: Tests for the end-to-end encryption module.
# \*---------------------------------------------------------------------*/



from unittest.mock import patch

import pytest


def _nacl_available() -> bool:
    try:
        import nacl.public  # noqa: F401

        return True
    except ImportError:
        return False


class TestCryptoImport:
    def test_crypto_module_imports(self):
        import corvustunnel.crypto.e2e  # noqa: F401

    def test_get_e2e_crypto_returns_instance(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto, get_e2e_crypto

        instance = get_e2e_crypto()
        assert isinstance(instance, E2ECrypto)

    def test_available_property_reflects_nacl(self, env_token):
        from corvustunnel.crypto.e2e import get_e2e_crypto

        instance = get_e2e_crypto()
        assert instance.available == _nacl_available()


class TestBase64Helpers:
    def test_b64url_roundtrip(self):
        from corvustunnel.crypto.e2e import _b64url_decode, _b64url_encode

        original = b"hello world! this is a test 1234"
        encoded = _b64url_encode(original)
        decoded = _b64url_decode(encoded)
        assert decoded == original

    def test_b64url_no_padding(self):
        from corvustunnel.crypto.e2e import _b64url_encode

        encoded = _b64url_encode(b"test")
        assert "=" not in encoded

    def test_b64url_url_safe_chars(self):
        from corvustunnel.crypto.e2e import _b64url_encode

        data = b"\xfb\xff\xfe"
        encoded = _b64url_encode(data)
        assert "+" not in encoded
        assert "/" not in encoded


def _client_pub_b64() -> str:
    import nacl.public

    from corvustunnel.crypto.e2e import _b64url_encode

    client_key = nacl.public.PrivateKey.generate().public_key
    return _b64url_encode(client_key.encode(encoder=nacl.encoding.RawEncoder))


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestEphemeralExchangeKeys:
    def test_exchange_returns_ephemeral_public_key(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_decode

        crypto = E2ECrypto()
        key_b64 = crypto.exchange("sess-a", _client_pub_b64())
        assert key_b64
        assert len(_b64url_decode(key_b64)) == 32

    def test_no_global_server_key(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto

        crypto = E2ECrypto()
        assert crypto.server_public_key_b64 == ""

    def test_each_session_gets_a_different_key(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto

        crypto = E2ECrypto()
        key1 = crypto.exchange("sess-1", _client_pub_b64())
        key2 = crypto.exchange("sess-2", _client_pub_b64())
        assert key1 != key2


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestEncryptDecrypt:
    def _setup_session(self):
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto

        server = E2ECrypto()

        client_private = nacl.public.PrivateKey.generate()
        client_public = client_private.public_key

        from corvustunnel.crypto.e2e import _b64url_encode

        client_pub_b64 = _b64url_encode(client_public.encode(encoder=nacl.encoding.RawEncoder))

        session_id = "test-session-001"
        server.exchange(session_id, client_pub_b64)

        return server, client_private, client_public, session_id

    def test_encrypt_decrypt_roundtrip(self, env_token):
        server, _, _, session_id = self._setup_session()

        plaintext = "Hello, World! 🦆"
        ciphertext = server.encrypt(session_id, plaintext)
        decrypted = server.decrypt(session_id, ciphertext)
        assert decrypted == plaintext

    def test_encrypt_json_roundtrip(self, env_token):
        server, _, _, session_id = self._setup_session()

        data = {"action": "test", "value": 42, "emoji": "🐦"}
        ciphertext = server.encrypt_json(session_id, data)
        decrypted = server.decrypt_json(session_id, ciphertext)
        assert decrypted == data

    def test_encrypt_empty_string(self, env_token):
        server, _, _, session_id = self._setup_session()

        ciphertext = server.encrypt(session_id, "")
        decrypted = server.decrypt(session_id, ciphertext)
        assert decrypted == ""

    def test_ciphertext_differs_each_time(self, env_token):
        server, _, _, session_id = self._setup_session()

        plaintext = "deterministic?"
        ct1 = server.encrypt(session_id, plaintext)
        ct2 = server.encrypt(session_id, plaintext)
        assert ct1 != ct2

    def test_decrypt_wrong_session_raises(self, env_token):
        server, _, _, session_id = self._setup_session()

        ciphertext = server.encrypt(session_id, "test")
        with pytest.raises(KeyError):
            server.decrypt("wrong-session", ciphertext)


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestKeyExchange:
    def test_exchange_creates_session(self, env_token):
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_encode

        server = E2ECrypto()
        client_key = nacl.public.PrivateKey.generate().public_key
        client_b64 = _b64url_encode(client_key.encode(encoder=nacl.encoding.RawEncoder))

        session_id = "exchange-test"
        result = server.exchange(session_id, client_b64)

        from corvustunnel.crypto.e2e import _b64url_decode

        assert len(_b64url_decode(result)) == 32
        assert server.has_session(session_id) is True

    def test_remove_session(self, env_token):
        import nacl.public

        from corvustunnel.crypto.e2e import E2ECrypto, _b64url_encode

        server = E2ECrypto()
        client_key = nacl.public.PrivateKey.generate().public_key
        client_b64 = _b64url_encode(client_key.encode(encoder=nacl.encoding.RawEncoder))

        session_id = "remove-test"
        server.exchange(session_id, client_b64)
        assert server.has_session(session_id) is True

        server.remove_session(session_id)
        assert server.has_session(session_id) is False

    def test_exchange_invalid_key_raises(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto

        server = E2ECrypto()
        with pytest.raises(ValueError, match="Invalid client public key"):
            server.exchange("bad-session", "not-a-valid-key!!!")


@pytest.mark.skipif(not _nacl_available(), reason="PyNaCl not installed")
class TestClientServerInterop:
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
        server_pub = nacl.public.PublicKey(_b64url_decode(server_pub_b64))
        client_box = nacl.public.Box(client_priv, server_pub)
        return server, sid, client_box

    def test_server_to_client(self, env_token):
        from corvustunnel.crypto.e2e import _b64url_decode

        server, sid, client_box = self._handshake()
        ct = server.encrypt(sid, "output from PTY █ 日本語")
        plain = client_box.decrypt(_b64url_decode(ct)).decode("utf-8")
        assert plain == "output from PTY █ 日本語"

    def test_client_to_server(self, env_token):
        from corvustunnel.crypto.e2e import _b64url_encode

        server, sid, client_box = self._handshake()
        encrypted = client_box.encrypt(b"ls -la\r")
        ct_b64 = _b64url_encode(bytes(encrypted))
        assert server.decrypt(sid, ct_b64) == "ls -la\r"


class TestCryptoFallback:
    def test_unavailable_when_nacl_missing(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto

        with patch("corvustunnel.crypto.e2e._nacl_available", False):
            crypto = E2ECrypto()
            assert crypto.available is False
            assert crypto.server_public_key_b64 == ""

    def test_exchange_raises_without_nacl(self, env_token):
        from corvustunnel.crypto.e2e import E2ECrypto

        with patch("corvustunnel.crypto.e2e._nacl_available", False):
            crypto = E2ECrypto()
            with pytest.raises(ValueError, match="not available"):
                crypto.exchange("session", "some-key")
