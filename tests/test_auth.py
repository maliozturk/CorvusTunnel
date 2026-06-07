"""
Tests for auth/bearer.py and auth/dependencies.py — Bearer token auth.

Covers:
  - TokenManager: boot token claim, session token verification, IP binding
  - verify_bearer_token: header parsing, valid/invalid tokens
  - WebSocket ticket system: creation, consumption, expiry, IP binding
  - require_public_auth dependency via the public app
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
import pytest_asyncio


class TestTokenManager:
    """Tests for auth.bearer.TokenManager."""

    def test_verify_with_boot_token(self, env_token):
        """Unclaimed boot token should be accepted by verify()."""
        from auth.bearer import TokenManager
        mgr = TokenManager()
        assert mgr.verify(env_token) is True

    def test_verify_with_wrong_token(self, env_token):
        """An incorrect token should be rejected."""
        from auth.bearer import TokenManager
        mgr = TokenManager()
        assert mgr.verify("wrong-token") is False

    def test_claim_boot_token(self, env_token):
        """Claiming the boot token should return a session token."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None
        assert len(session_token) > 20
        assert mgr.is_claimed is True

    def test_boot_token_consumed_after_claim(self, env_token):
        """Boot token should be rejected after it has been claimed."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert session_token is not None

        # Boot token no longer valid
        assert mgr.verify(env_token) is False
        # Session token is valid
        assert mgr.verify(session_token) is True

    def test_claim_fails_with_wrong_token(self, env_token):
        """Claiming with a wrong token should return None."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        result = mgr.claim_boot_token("wrong-token")
        assert result is None
        assert mgr.is_claimed is False

    def test_double_claim_rejected(self, env_token):
        """Second claim attempt should return None."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        first = mgr.claim_boot_token(env_token)
        assert first is not None

        second = mgr.claim_boot_token(env_token)
        assert second is None

    def test_session_token_ip_binding(self, env_token):
        """After claiming with IP binding, only the bound IP should be accepted."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token, client_ip="1.2.3.4")
        assert session_token is not None

        # Same IP — should work
        assert mgr.verify(session_token, client_ip="1.2.3.4") is True
        # Different IP — should fail
        assert mgr.verify(session_token, client_ip="5.6.7.8") is False

    def test_session_verify_without_ip_still_works(self, env_token):
        """Session token without IP should work when no IP bound."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        session_token = mgr.claim_boot_token(env_token)
        assert mgr.verify_session_token(session_token) is True


class TestWSTicket:
    """Tests for WebSocket ticket system in TokenManager."""

    def test_create_and_consume_ticket(self, env_token):
        """A freshly created ticket should be consumable from the same IP."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert ticket is not None
        assert len(ticket) > 10

        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is True

    def test_ticket_consumed_once(self, env_token):
        """A ticket should be rejected on second use (one-time)."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is True
        # Second attempt
        assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is False

    def test_ticket_ip_mismatch(self, env_token):
        """A ticket should be rejected when consumed from a different IP."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")
        assert mgr.consume_ws_ticket(ticket, "10.0.0.2") is False

    def test_ticket_expired(self, env_token):
        """An expired ticket should be rejected."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        ticket = mgr.create_ws_ticket("10.0.0.1")

        # Fast-forward time past TTL (30 seconds)
        with patch("auth.bearer.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 60
            assert mgr.consume_ws_ticket(ticket, "10.0.0.1") is False

    def test_nonexistent_ticket(self, env_token):
        """A made-up ticket should be rejected."""
        from auth.bearer import TokenManager
        mgr = TokenManager()

        assert mgr.consume_ws_ticket("fake-ticket", "10.0.0.1") is False


class TestVerifyBearerToken:
    """Tests for the verify_bearer_token() helper function."""

    def test_valid_bearer_header(self, env_token):
        """A proper 'Bearer <token>' header with correct token should pass."""
        from auth.bearer import verify_bearer_token
        assert verify_bearer_token(f"Bearer {env_token}") is True

    def test_invalid_bearer_header(self, env_token):
        """A proper 'Bearer <token>' header with wrong token should fail."""
        from auth.bearer import verify_bearer_token
        assert verify_bearer_token("Bearer wrong-token") is False

    def test_missing_bearer_prefix(self, env_token):
        """Headers without 'Bearer ' prefix should fail."""
        from auth.bearer import verify_bearer_token
        assert verify_bearer_token(env_token) is False

    def test_empty_authorization(self, env_token):
        """Empty authorization string should fail."""
        from auth.bearer import verify_bearer_token
        assert verify_bearer_token("") is False

    def test_basic_auth_rejected(self, env_token):
        """'Basic' auth scheme should be rejected."""
        from auth.bearer import verify_bearer_token
        assert verify_bearer_token(f"Basic {env_token}") is False


class TestAuthEndpoints:
    """Integration tests for auth via the public app endpoints."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, public_client):
        """Accessing a protected endpoint without auth should return 401."""
        resp = await public_client.get("/api/browse")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, public_client):
        """A wrong Bearer token should return 401."""
        resp = await public_client.get(
            "/api/browse",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_passes_auth(self, authed_public_client):
        """A valid boot token (unclaimed) should pass auth on protected endpoints."""
        resp = await authed_public_client.get("/api/browse")
        # Should get 200 (directory listing), not 401
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self, public_client):
        """A request with no Authorization header should return 401."""
        resp = await public_client.get("/api/check-agents")
        assert resp.status_code == 401
