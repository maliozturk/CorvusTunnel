# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_channel_endpoint.py
# Description: Tests for WS /api/channel: handshake, channel-bound claim,
#              control ops over the encrypted channel, and auth gating.
# \*---------------------------------------------------------------------*/

import json
import os

from starlette.testclient import TestClient

from corvustunnel.crypto import channel as ch


def _open(ws):
    client_eph_pub, client_eph_priv = ch.new_client_ephemeral()
    client_nonce = os.urandom(32)
    ws.send_text(json.dumps({"e": ch._b64e(client_eph_pub), "n": ch._b64e(client_nonce)}))
    server_hello = json.loads(ws.receive_text())
    identity_pub = ch.get_server_identity().public_key
    return ch.client_handshake(identity_pub, client_eph_priv, client_nonce, server_hello)


def _call(ws, channel, payload):
    ws.send_bytes(channel.encrypt(json.dumps(payload).encode()))
    return json.loads(channel.decrypt(ws.receive_bytes()))


def test_handshake_claim_and_control_ops(env_full):
    from corvustunnel.apps.public import app

    client = TestClient(app)
    with client.websocket_connect("/api/channel") as ws:
        channel = _open(ws)

        claim = _call(ws, channel, {"op": "claim", "id": 1, "token": env_full["token"]})
        assert claim["ok"] is True

        agents = _call(ws, channel, {"op": "check_agents", "id": 2})
        assert agents["ok"] is True
        assert "agents" in agents["data"]

        roots = _call(ws, channel, {"op": "browse", "id": 3})
        assert roots["ok"] is True
        names = [d["name"] for d in roots["data"]["directories"]]
        assert os.path.basename(str(env_full["workspace"])) in names

        sub = _call(
            ws, channel, {"op": "browse", "id": 4, "path": str(env_full["workspace"])}
        )
        sub_names = [d["name"] for d in sub["data"]["directories"]]
        assert "project_alpha" in sub_names
        assert ".hidden" not in sub_names


def test_op_before_claim_is_rejected(env_full):
    from corvustunnel.apps.public import app

    client = TestClient(app)
    with client.websocket_connect("/api/channel") as ws:
        channel = _open(ws)
        resp = _call(ws, channel, {"op": "check_agents", "id": 1})
        assert resp["ok"] is False
        assert resp["status"] == 401


def test_bad_token_rejected(env_full):
    from corvustunnel.apps.public import app

    client = TestClient(app)
    with client.websocket_connect("/api/channel") as ws:
        channel = _open(ws)
        resp = _call(ws, channel, {"op": "claim", "id": 1, "token": "wrong"})
        assert resp["ok"] is False
        assert resp["status"] == 401
