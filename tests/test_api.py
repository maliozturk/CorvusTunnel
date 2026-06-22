# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_api.py
# Description: Tests for the public app surface that remains after cutover:
#              the liveness probe, the served UI, and security headers.
# \*---------------------------------------------------------------------*/

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
        assert "." in resp.json()["version"]

    @pytest.mark.asyncio
    async def test_health_uptime_non_negative(self, public_client):
        resp = await public_client.get("/api/health")
        assert resp.json()["uptime_seconds"] >= 0


class TestRootHealthEndpoint:
    @pytest.mark.asyncio
    async def test_root_health_returns_200(self, public_client):
        resp = await public_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestUIEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_html_or_json(self, public_client):
        resp = await public_client.get("/")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type or "application/json" in content_type


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
