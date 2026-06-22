# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        tests/test_auth.py
# Description: Tests for bearer-token authentication and WebSocket
#              tickets.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import time
from unittest.mock import patch

import pytest


class TestTokenManager:
    def test_verify_with_boot_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.verify(env_token) is True

    def test_verify_with_wrong_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()
        assert mgr.verify("wrong-token") is False

    def test_claim_boot_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None
        assert len(session_token) > 20
        assert mgr.is_claimed is True

    def test_boot_token_consumed_after_claim(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None

        assert mgr.verify(env_token) is False
        assert mgr.verify(session_token) is True

    def test_claim_fails_with_wrong_token(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        result = mgr.claim_boot_token("wrong-token")
        assert result is None
        assert mgr.is_claimed is False

    def test_double_claim_rejected(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        first = mgr.claim_boot_token(env_token)
        assert first is not None

        second = mgr.claim_boot_token(env_token)
        assert second is None

    def test_session_token_ip_binding(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token, client_ip="1.2.3.4")
        assert session_token is not None

        assert mgr.verify(session_token, client_ip="1.2.3.4") is True
        assert mgr.verify(session_token, client_ip="5.6.7.8") is False

    def test_session_verify_without_ip_still_works(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert mgr.verify(session_token) is True


class TestWSTicket:
    def test_create_and_consume_ticket(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert ticket is not None
        assert len(ticket) > 10

        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is True

    def test_ticket_consumed_once(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is True
        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is False

    def test_ticket_ip_mismatch(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert mgr.consume_ws_ticket(ticket, "10.0.0.2") is False

    def test_ticket_expired(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")

        with patch("corvustunnel.auth.bearer.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 60
            assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is False

    def test_nonexistent_ticket(self, env_token):
        from corvustunnel.auth.bearer import TokenManager

        mgr = TokenManager()

        assert mgr.consume_ws_ticket("fake-ticket", "10.0.0.1") is False


class TestVerifyBearerToken:
    def test_valid_bearer_header(self, env_token):
        from corvustunnel.auth.bearer import verify_bearer_token

        assert verify_bearer_token(f"Bearer {env_token}") is True

    def test_invalid_bearer_header(self, env_token):
        from corvustunnel.auth.bearer import verify_bearer_token

        assert verify_bearer_token("Bearer wrong-token") is False

    def test_missing_bearer_prefix(self, env_token):
        from corvustunnel.auth.bearer import verify_bearer_token

        assert verify_bearer_token(env_token) is False

    def test_empty_authorization(self, env_token):
        from corvustunnel.auth.bearer import verify_bearer_token

        assert verify_bearer_token("") is False

    def test_basic_auth_rejected(self, env_token):
        from corvustunnel.auth.bearer import verify_bearer_token

        assert verify_bearer_token(f"Basic {env_token}") is False


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, public_client):
        resp = await public_client.get("/api/browse")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, public_client):
        resp = await public_client.get(
            "/api/browse",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_passes_auth(self, authed_public_client):
        resp = await authed_public_client.get("/api/browse")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self, public_client):
        resp = await public_client.get("/api/check-agents")
        assert resp.status_code == 401
