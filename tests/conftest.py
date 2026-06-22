"""
CorvusTunnel Test Suite — Shared Fixtures.

Provides common pytest fixtures used across all test modules:
  - Environment variable setup (AGENT_TOKEN, ALLOWED_DIRS, etc.)
  - FastAPI test clients (httpx.AsyncClient)
  - Temporary directories for logs
  - Settings fixture with singleton cache clearing
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
import httpx

# ── Ensure project root is importable ────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Constants ────────────────────────────────────────────────────────
TEST_TOKEN = "test-token-12345"


# ── Environment Setup ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_singletons():
    """Clear lru_cache singletons and module-level singletons between tests.

    This prevents state leakage between tests that modify settings or
    create TokenManager / E2ECrypto instances.
    """
    yield

    # Clear lru_cache on get_settings, get_audit_logger, get_deep_logger
    try:
        from corvustunnel.config.settings import get_settings
        get_settings.cache_clear()
    except Exception:
        pass

    try:
        from corvustunnel.audit.logger import get_audit_logger
        get_audit_logger.cache_clear()
    except Exception:
        pass

    try:
        from corvustunnel.audit.deep_logger import get_deep_logger, DeepLogger
        get_deep_logger.cache_clear()
        DeepLogger._BOOT_LOGGED = False
    except Exception:
        pass

    # Reset bearer TokenManager singleton
    try:
        import corvustunnel.auth.bearer as _bearer
        _bearer._manager = None
    except Exception:
        pass

    # Reset E2ECrypto singleton
    try:
        import corvustunnel.crypto.e2e as _e2e
        _e2e._e2e_crypto = None
    except Exception:
        pass

    # Reset IPBanTracker singleton
    try:
        from corvustunnel.middleware.ip_ban import IPBanTracker
        IPBanTracker._instance = None
    except Exception:
        pass


@pytest.fixture
def env_token(monkeypatch):
    """Set the AGENT_TOKEN environment variable for tests."""
    monkeypatch.setenv("AGENT_TOKEN", TEST_TOKEN)
    return TEST_TOKEN


@pytest.fixture
def tmp_log_dir(tmp_path):
    """Provide a temporary directory for audit/deep logs."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def env_full(monkeypatch, tmp_path):
    """Full environment setup: token, ports, allowed dirs, log dirs."""
    monkeypatch.setenv("AGENT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("PUBLIC_PORT", "8000")
    monkeypatch.setenv("INTERNAL_PORT", "8001")

    # Use tmp_path for allowed dirs so browse tests work
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "project_alpha").mkdir()
    (workspace / "project_beta").mkdir()
    (workspace / ".hidden").mkdir()
    (workspace / "__pycache__").mkdir()
    monkeypatch.setenv("ALLOWED_DIRS", str(workspace))

    # Use tmp_path for log dirs
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("AUDIT_LOG_DIR", str(log_dir))
    monkeypatch.setenv("DEEP_LOG_DIR", str(log_dir))

    return {
        "token": TEST_TOKEN,
        "workspace": workspace,
        "log_dir": log_dir,
    }


@pytest.fixture
def settings(env_full):
    """Return a fresh Settings instance with test env vars."""
    from corvustunnel.config.settings import get_settings
    return get_settings()


# ── FastAPI Test Clients ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def public_client(env_full):
    """Async httpx client for the public FastAPI app (port 8000)."""
    # Import app after env is configured so Settings loads correctly
    from corvustunnel.apps.public import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def internal_client(env_full):
    """Async httpx client for the internal FastAPI app (port 8001)."""
    from corvustunnel.apps.internal import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authed_public_client(env_full):
    """Public client with the boot token pre-set in the Authorization header.

    The boot token (unclaimed) can be used for API calls before claiming.
    """
    from corvustunnel.apps.public import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    ) as client:
        yield client
