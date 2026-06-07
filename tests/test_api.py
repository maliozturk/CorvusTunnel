"""
Tests for API endpoints — public_app.py and routers/public.py.

Covers:
  - GET /api/health (no auth)
  - GET /api/browse (auth required, directory listing)
  - GET /api/check-agents (auth required)
  - POST /api/submit (auth required — 401 without)
  - POST /api/claim (boot token exchange)
  - GET / (serves UI HTML)
  - GET /health (root-level health redirect)
  - Security headers presence
"""

from __future__ import annotations

import pytest


class TestHealthEndpoint:
    """Tests for GET /api/health (no authentication required)."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, public_client):
        """GET /api/health should return 200 with status info."""
        resp = await public_client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_health_version_format(self, public_client):
        """Health response version should be a semver-like string."""
        resp = await public_client.get("/api/health")
        data = resp.json()
        assert "." in data["version"]  # e.g. "0.4.0"

    @pytest.mark.asyncio
    async def test_health_uptime_is_non_negative(self, public_client):
        """Uptime should be a non-negative number."""
        resp = await public_client.get("/api/health")
        data = resp.json()
        assert data["uptime_seconds"] >= 0


class TestRootHealthEndpoint:
    """Tests for GET /health (root-level health check)."""

    @pytest.mark.asyncio
    async def test_root_health_returns_200(self, public_client):
        """GET /health should return 200 (redirects to API health)."""
        resp = await public_client.get("/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "ok"


class TestBrowseEndpoint:
    """Tests for GET /api/browse (requires authentication)."""

    @pytest.mark.asyncio
    async def test_browse_without_auth_returns_401(self, public_client):
        """GET /api/browse without auth should return 401."""
        resp = await public_client.get("/api/browse")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_browse_with_auth_returns_roots(self, authed_public_client):
        """GET /api/browse with auth should return root directories."""
        resp = await authed_public_client.get("/api/browse")
        assert resp.status_code == 200

        data = resp.json()
        assert "directories" in data
        assert "current" in data
        assert isinstance(data["directories"], list)

    @pytest.mark.asyncio
    async def test_browse_subdirectory(self, authed_public_client, env_full):
        """GET /api/browse?path=<workspace> should list subdirectories."""
        workspace = str(env_full["workspace"])
        resp = await authed_public_client.get(
            "/api/browse", params={"path": workspace}
        )
        assert resp.status_code == 200

        data = resp.json()
        dir_names = [d["name"] for d in data["directories"]]
        # Should include visible dirs, but not hidden (.) or dunder (__)
        assert "project_alpha" in dir_names
        assert "project_beta" in dir_names
        assert ".hidden" not in dir_names
        assert "__pycache__" not in dir_names

    @pytest.mark.asyncio
    async def test_browse_outside_allowed_dirs(self, authed_public_client):
        """Browsing outside ALLOWED_DIRS should return 403."""
        resp = await authed_public_client.get(
            "/api/browse", params={"path": "/tmp/nonexistent"}
        )
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_browse_nonexistent_path(self, authed_public_client, env_full):
        """Browsing a non-existent path within allowed dirs should return 404."""
        fake_path = str(env_full["workspace"] / "does_not_exist")
        resp = await authed_public_client.get(
            "/api/browse", params={"path": fake_path}
        )
        assert resp.status_code == 404


class TestCheckAgentsEndpoint:
    """Tests for GET /api/check-agents."""

    @pytest.mark.asyncio
    async def test_check_agents_without_auth_returns_401(self, public_client):
        """GET /api/check-agents without auth should return 401."""
        resp = await public_client.get("/api/check-agents")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_check_agents_with_auth(self, authed_public_client):
        """GET /api/check-agents with auth should return agent list."""
        resp = await authed_public_client.get("/api/check-agents")
        assert resp.status_code == 200

        data = resp.json()
        assert "agents" in data
        agents = data["agents"]
        assert isinstance(agents, list)
        assert len(agents) >= 3

        agent_names = [a["name"] for a in agents]
        assert "agy" in agent_names
        assert "codex" in agent_names
        assert "claude" in agent_names

        # Each agent should have 'available' and 'path' fields
        for agent in agents:
            assert "available" in agent
            assert "path" in agent

    @pytest.mark.asyncio
    async def test_check_agents_includes_default_work_dir(self, authed_public_client):
        """GET /api/check-agents should include default_work_dir."""
        resp = await authed_public_client.get("/api/check-agents")
        assert resp.status_code == 200

        data = resp.json()
        assert "default_work_dir" in data
        assert isinstance(data["default_work_dir"], str)
        assert len(data["default_work_dir"]) > 0


class TestClaimEndpoint:
    """Tests for POST /api/claim (boot token exchange)."""

    @pytest.mark.asyncio
    async def test_claim_valid_boot_token(self, public_client, env_full):
        """Claiming with the correct boot token should return a session token."""
        resp = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "session_token" in data
        assert len(data["session_token"]) > 20

    @pytest.mark.asyncio
    async def test_claim_invalid_token(self, public_client):
        """Claiming with a wrong token should return 401."""
        resp = await public_client.post(
            "/api/claim",
            json={"token": "wrong-token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_claim_missing_token_field(self, public_client):
        """Claiming without 'token' field should return 400."""
        resp = await public_client.post(
            "/api/claim",
            json={"not_token": "abc"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_claim_then_use_session_token(self, public_client, env_full):
        """After claiming, the session token should work for API calls."""
        # Claim
        claim_resp = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        session_token = claim_resp.json()["session_token"]

        # Use session token on a protected endpoint
        resp = await public_client.get(
            "/api/check-agents",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_double_claim_fails(self, public_client, env_full):
        """Second claim attempt should fail."""
        # First claim
        resp1 = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        assert resp1.status_code == 200

        # Second claim
        resp2 = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        assert resp2.status_code in (401, 429)  # 401 (consumed) or 429 (rate-limited)


class TestUIEndpoint:
    """Tests for GET / (serves the Chat UI)."""

    @pytest.mark.asyncio
    async def test_root_returns_html_or_json(self, public_client):
        """GET / should return HTML (if index.html exists) or a JSON fallback."""
        resp = await public_client.get("/")
        assert resp.status_code == 200

        content_type = resp.headers.get("content-type", "")
        # Either serves HTML or JSON message
        assert "text/html" in content_type or "application/json" in content_type


class TestWSTicketEndpoint:
    """Tests for POST /api/ws-ticket."""

    @pytest.mark.asyncio
    async def test_ws_ticket_without_auth_returns_401(self, public_client):
        """POST /api/ws-ticket without auth should return 401."""
        resp = await public_client.post("/api/ws-ticket")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ws_ticket_with_auth(self, authed_public_client):
        """POST /api/ws-ticket with auth should return a ticket."""
        resp = await authed_public_client.post("/api/ws-ticket")
        assert resp.status_code == 200

        data = resp.json()
        assert "ticket" in data
        assert len(data["ticket"]) > 10


class TestSecurityHeaders:
    """Tests for security headers on responses."""

    @pytest.mark.asyncio
    async def test_health_has_security_headers(self, public_client):
        """Responses should include security headers from middleware."""
        resp = await public_client.get("/api/health")
        assert resp.status_code == 200

        headers = resp.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert "strict-transport-security" in headers
        assert "referrer-policy" in headers
        assert "x-xss-protection" in headers
