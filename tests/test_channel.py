# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_channel.py
# Description: Tests for the authenticated channel: handshake roundtrip,
#              relay MITM / forged-signature rejection, and replay rejection.
# \*---------------------------------------------------------------------*/

import os

import pytest

from corvustunnel.crypto import channel as ch


def _establish():
    identity = ch.ServerIdentity()
    client_eph_pub, client_eph_priv = ch.new_client_ephemeral()
    client_nonce = os.urandom(32)
    client_hello = {"e": ch._b64e(client_eph_pub), "n": ch._b64e(client_nonce)}

    server_hello, server_channel = ch.server_handshake(identity, client_hello)
    client_channel = ch.client_handshake(
        identity.public_key, client_eph_priv, client_nonce, server_hello
    )
    return identity, client_channel, server_channel, client_eph_priv, client_nonce, server_hello


def test_roundtrip_both_directions():
    _, client, server, *_ = _establish()

    blob = "ls -la │ é █ 日本語".encode()
    assert server.decrypt(client.encrypt(blob)) == blob
    assert client.decrypt(server.encrypt(blob)) == blob


def test_same_plaintext_differs_on_wire():
    _, client, server, *_ = _establish()
    a = client.encrypt(b"same")
    b = client.encrypt(b"same")
    assert a != b


def test_relay_cannot_swap_server_key():
    identity, _, _, client_eph_priv, client_nonce, server_hello = _establish()

    forged = dict(server_hello)
    rogue_pub, _ = ch.new_client_ephemeral()
    forged["e"] = ch._b64e(rogue_pub)

    with pytest.raises(ch.HandshakeError):
        ch.client_handshake(identity.public_key, client_eph_priv, client_nonce, forged)


def test_relay_cannot_forge_signature_with_its_own_identity():
    identity, _, _, client_eph_priv, client_nonce, _ = _establish()

    rogue = ch.ServerIdentity()
    client_eph_pub = __import__("nacl").bindings.crypto_scalarmult_base(client_eph_priv)
    rogue_eph_pub, rogue_eph_priv = ch.new_client_ephemeral()
    server_nonce = os.urandom(32)
    transcript = ch._transcript(client_eph_pub, rogue_eph_pub, client_nonce, server_nonce)
    rogue_hello = {
        "e": ch._b64e(rogue_eph_pub),
        "n": ch._b64e(server_nonce),
        "sig": ch._b64e(rogue.sign(transcript)),
    }

    with pytest.raises(ch.HandshakeError):
        ch.client_handshake(identity.public_key, client_eph_priv, client_nonce, rogue_hello)


def test_tampered_frame_rejected():
    _, client, server, *_ = _establish()
    ct = bytearray(client.encrypt(b"hello"))
    ct[-1] ^= 0x01
    with pytest.raises(ch.HandshakeError):
        server.decrypt(bytes(ct))


def test_replayed_frame_rejected():
    _, client, server, *_ = _establish()
    first = client.encrypt(b"one")
    second = client.encrypt(b"two")
    assert server.decrypt(first) == b"one"
    assert server.decrypt(second) == b"two"
    with pytest.raises(ch.HandshakeError):
        server.decrypt(first)


def test_reordered_frame_rejected():
    _, client, server, *_ = _establish()
    first = client.encrypt(b"one")
    second = client.encrypt(b"two")
    with pytest.raises(ch.HandshakeError):
        server.decrypt(second)
    assert server.decrypt(first) == b"one"
