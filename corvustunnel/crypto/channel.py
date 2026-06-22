# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/crypto/channel.py
# Description: Authenticated, forward-secret end-to-end channel. A per-boot
#              Ed25519 identity (public half pinned in the QR) signs an
#              ephemeral X25519 handshake, defeating any relay key-exchange
#              MITM; traffic then flows under per-direction XSalsa20-Poly1305
#              keys with counter nonces (replay/reorder rejected).
# \*---------------------------------------------------------------------*/

import base64
import hashlib
import os

import nacl.bindings
import nacl.exceptions
import nacl.secret
import nacl.signing

_CONTEXT = b"corvustunnel-channel-v1"


def _b64e(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(s):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


def _transcript(client_eph, server_eph, client_nonce, server_nonce):
    return hashlib.sha512(client_eph + server_eph + client_nonce + server_nonce).digest()


def _derive(label, shared, transcript):
    return hashlib.sha512(label + b"|" + _CONTEXT + b"|" + shared + b"|" + transcript).digest()[:32]


class HandshakeError(Exception):
    pass


class ServerIdentity:
    def __init__(self, signing_key=None):
        self._signing_key = signing_key or nacl.signing.SigningKey.generate()

    @property
    def public_key(self):
        return bytes(self._signing_key.verify_key)

    @property
    def public_key_b64(self):
        return _b64e(self.public_key)

    def sign(self, message):
        return self._signing_key.sign(message).signature


class Channel:
    def __init__(self, send_key, recv_key):
        self._send_box = nacl.secret.SecretBox(send_key)
        self._recv_box = nacl.secret.SecretBox(recv_key)
        self._send_counter = 0
        self._recv_counter = 0

    def encrypt(self, plaintext):
        nonce = self._send_counter.to_bytes(nacl.secret.SecretBox.NONCE_SIZE, "big")
        ciphertext = self._send_box.encrypt(plaintext, nonce).ciphertext
        self._send_counter += 1
        return ciphertext

    def decrypt(self, ciphertext):
        nonce = self._recv_counter.to_bytes(nacl.secret.SecretBox.NONCE_SIZE, "big")
        try:
            plaintext = self._recv_box.decrypt(ciphertext, nonce)
        except nacl.exceptions.CryptoError as exc:
            raise HandshakeError("frame authentication failed") from exc
        self._recv_counter += 1
        return plaintext


def server_handshake(identity, client_hello):
    client_eph = _b64d(client_hello["e"])
    client_nonce = _b64d(client_hello["n"])
    if len(client_eph) != 32 or len(client_nonce) != 32:
        raise HandshakeError("malformed client hello")

    server_eph_pub, server_eph_priv = nacl.bindings.crypto_box_keypair()
    server_nonce = os.urandom(32)
    shared = nacl.bindings.crypto_scalarmult(server_eph_priv, client_eph)
    transcript = _transcript(client_eph, server_eph_pub, client_nonce, server_nonce)

    key_c2s = _derive(b"c2s", shared, transcript)
    key_s2c = _derive(b"s2c", shared, transcript)
    channel = Channel(send_key=key_s2c, recv_key=key_c2s)

    server_hello = {
        "e": _b64e(server_eph_pub),
        "n": _b64e(server_nonce),
        "sig": _b64e(identity.sign(transcript)),
    }
    return server_hello, channel


def client_handshake(server_identity_pub, client_eph_priv, client_nonce, server_hello):
    server_eph = _b64d(server_hello["e"])
    server_nonce = _b64d(server_hello["n"])
    signature = _b64d(server_hello["sig"])

    client_eph_pub = nacl.bindings.crypto_scalarmult_base(client_eph_priv)
    transcript = _transcript(client_eph_pub, server_eph, client_nonce, server_nonce)

    try:
        nacl.signing.VerifyKey(server_identity_pub).verify(transcript, signature)
    except nacl.exceptions.BadSignatureError as exc:
        raise HandshakeError("server identity signature invalid") from exc

    shared = nacl.bindings.crypto_scalarmult(client_eph_priv, server_eph)
    key_c2s = _derive(b"c2s", shared, transcript)
    key_s2c = _derive(b"s2c", shared, transcript)
    return Channel(send_key=key_c2s, recv_key=key_s2c)


def new_client_ephemeral():
    public, private = nacl.bindings.crypto_box_keypair()
    return public, private
