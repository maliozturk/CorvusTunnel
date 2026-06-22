# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/conftest.py
# Description: Shared pytest fixtures, environment setup, and singleton
#              resets.
# \*---------------------------------------------------------------------*/



import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_TOKEN = "test-token-12345"


@pytest.fixture(autouse=True)
def _reset_singletons():
    yield

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
        from corvustunnel.audit.deep_logger import DeepLogger, get_deep_logger

        get_deep_logger.cache_clear()
        DeepLogger._BOOT_LOGGED = False
    except Exception:
        pass

    try:
        import corvustunnel.auth.bearer as _bearer

        _bearer._manager = None
    except Exception:
        pass

    try:
        import corvustunnel.crypto.e2e as _e2e

        _e2e._e2e_crypto = None
    except Exception:
        pass

    try:
        import corvustunnel.crypto.channel as _channel

        _channel._identity = None
    except Exception:
        pass

    try:
        from corvustunnel.middleware.ip_ban import IPBanTracker

        IPBanTracker._instance = None
    except Exception:
        pass


@pytest.fixture
def env_token(monkeypatch):
    monkeypatch.setenv("AGENT_TOKEN", TEST_TOKEN)
    return TEST_TOKEN


@pytest.fixture
def tmp_log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def env_full(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("PUBLIC_PORT", "8000")
    monkeypatch.setenv("INTERNAL_PORT", "8001")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "project_alpha").mkdir()
    (workspace / "project_beta").mkdir()
    (workspace / ".hidden").mkdir()
    (workspace / "__pycache__").mkdir()
    monkeypatch.setenv("ALLOWED_DIRS", str(workspace))

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
    from corvustunnel.config.settings import get_settings

    return get_settings()


@pytest_asyncio.fixture
async def public_client(env_full):
    from corvustunnel.apps.public import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def internal_client(env_full):
    from corvustunnel.apps.internal import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authed_public_client(env_full):
    from corvustunnel.apps.public import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    ) as client:
        yield client
