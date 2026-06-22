# /*--------------------------------*- py -*-----------------------------*\
# | ___                 _____                  _                          |
# || _ \___ _ ___ ___ _|_   _|  _ _ _  _ _  ___| |                         |
# ||   / _ \ '_\ V / || || || || | ' \| ' \/ -_) |                         |
# ||_|_\___/_|  \_/ \_,_||_| \_,_|_||_|_||_\___|_|                         |
# |  CorvusTunnel  -  control AI agents from your phone  -  MIT            |
# *----------------------------------------------------------------------*/
# File:        tests/test_api.py
# Description: Tests for the public HTTP API endpoints.
# \*---------------------------------------------------------------------*/

from __future__ import annotations

import pytest


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, public_client):
        resp = await public_client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_health_version_format(self, public_client):
        resp = await public_client.get("/api/health")
        data = resp.json()
        assert "." in data["version"]

    @pytest.mark.asyncio
    async def test_health_uptime_is_non_negative(self, public_client):
        resp = await public_client.get("/api/health")
        data = resp.json()
        assert data["uptime_seconds"] >= 0


class TestRootHealthEndpoint:
    @pytest.mark.asyncio
    async def test_root_health_returns_200(self, public_client):
        resp = await public_client.get("/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "ok"


class TestBrowseEndpoint:
    @pytest.mark.asyncio
    async def test_browse_without_auth_returns_401(self, public_client):
        resp = await public_client.get("/api/browse")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_browse_with_auth_returns_roots(self, authed_public_client):
        resp = await authed_public_client.get("/api/browse")
        assert resp.status_code == 200

        data = resp.json()
        assert "directories" in data
        assert "current" in data
        assert isinstance(data["directories"], list)

    @pytest.mark.asyncio
    async def test_browse_subdirectory(self, authed_public_client, env_full):
        workspace = str(env_full["workspace"])
        resp = await authed_public_client.get("/api/browse", params={"path": workspace})
        assert resp.status_code == 200

        data = resp.json()
        dir_names = [d["name"] for d in data["directories"]]
        assert "project_alpha" in dir_names
        assert "project_beta" in dir_names
        assert ".hidden" not in dir_names
        assert "__pycache__" not in dir_names

    @pytest.mark.asyncio
    async def test_browse_outside_allowed_dirs(self, authed_public_client):
        resp = await authed_public_client.get("/api/browse", params={"path": "/tmp/nonexistent"})
        assert resp.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_browse_nonexistent_path(self, authed_public_client, env_full):
        fake_path = str(env_full["workspace"] / "does_not_exist")
        resp = await authed_public_client.get("/api/browse", params={"path": fake_path})
        assert resp.status_code == 404


class TestCheckAgentsEndpoint:
    @pytest.mark.asyncio
    async def test_check_agents_without_auth_returns_401(self, public_client):
        resp = await public_client.get("/api/check-agents")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_check_agents_with_auth(self, authed_public_client):
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

        for agent in agents:
            assert "available" in agent
            assert "path" in agent

    @pytest.mark.asyncio
    async def test_check_agents_includes_default_work_dir(self, authed_public_client):
        resp = await authed_public_client.get("/api/check-agents")
        assert resp.status_code == 200

        data = resp.json()
        assert "default_work_dir" in data
        assert isinstance(data["default_work_dir"], str)
        assert len(data["default_work_dir"]) > 0


class TestClaimEndpoint:
    @pytest.mark.asyncio
    async def test_claim_valid_boot_token(self, public_client, env_full):
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
        resp = await public_client.post(
            "/api/claim",
            json={"token": "wrong-token"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_claim_missing_token_field(self, public_client):
        resp = await public_client.post(
            "/api/claim",
            json={"not_token": "abc"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_claim_then_use_session_token(self, public_client, env_full):
        claim_resp = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        session_token = claim_resp.json()["session_token"]

        resp = await public_client.get(
            "/api/check-agents",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_double_claim_fails(self, public_client, env_full):
        resp1 = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        assert resp1.status_code == 200

        resp2 = await public_client.post(
            "/api/claim",
            json={"token": env_full["token"]},
        )
        assert resp2.status_code in (401, 429)


class TestUIEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_html_or_json(self, public_client):
        resp = await public_client.get("/")
        assert resp.status_code == 200

        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type or "application/json" in content_type


class TestWSTicketEndpoint:
    @pytest.mark.asyncio
    async def test_ws_ticket_without_auth_returns_401(self, public_client):
        resp = await public_client.post("/api/ws-ticket")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_ws_ticket_with_auth(self, authed_public_client):
        resp = await authed_public_client.post("/api/ws-ticket")
        assert resp.status_code == 200

        data = resp.json()
        assert "ticket" in data
        assert len(data["ticket"]) > 10


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_health_has_security_headers(self, public_client):
        resp = await public_client.get("/api/health")
        assert resp.status_code == 200

        headers = resp.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert "strict-transport-security" in headers
        assert "referrer-policy" in headers
        assert "x-xss-protection" in headers
