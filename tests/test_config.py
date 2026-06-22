"""
Tests for config/settings.py — Pydantic Settings configuration.

Covers:
  - Settings loads successfully with AGENT_TOKEN set
  - Settings fails without AGENT_TOKEN (required field)
  - Port validation (public and internal ports must differ)
  - allowed_dir_list parsing (comma-separated)
  - Default values for optional fields
  - audit_log_dir creates directory if missing
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError


class TestSettingsLoading:
    """Tests for Settings initialization."""

    def test_settings_loads_with_token(self, monkeypatch, tmp_path):
        """Settings should load when AGENT_TOKEN is set."""
        monkeypatch.setenv("AGENT_TOKEN", "test-token-xyz")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.agent_token == "test-token-xyz"

    def test_settings_fails_without_token(self, monkeypatch, tmp_path):
        """Settings should raise ValidationError when AGENT_TOKEN is missing."""
        monkeypatch.delenv("AGENT_TOKEN", raising=False)
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        with pytest.raises(ValidationError):
            Settings()

    def test_settings_default_ports(self, monkeypatch, tmp_path):
        """Default ports should be 8000 (public) and 8001 (internal)."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.public_port == 8000
        assert s.internal_port == 8001

    def test_settings_custom_ports(self, monkeypatch, tmp_path):
        """Custom ports should be respected."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("PUBLIC_PORT", "9000")
        monkeypatch.setenv("INTERNAL_PORT", "9001")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.public_port == 9000
        assert s.internal_port == 9001

    def test_get_settings_returns_cached(self, env_token, monkeypatch, tmp_path):
        """get_settings should return the same instance (lru_cache)."""
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestPortValidation:
    """Tests for port validation (ports must differ)."""

    def test_same_ports_raises_error(self, monkeypatch, tmp_path):
        """public_port == internal_port should raise ValidationError."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("PUBLIC_PORT", "8000")
        monkeypatch.setenv("INTERNAL_PORT", "8000")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        with pytest.raises(ValidationError, match="must be different"):
            Settings()

    def test_different_ports_ok(self, monkeypatch, tmp_path):
        """Different public and internal ports should be accepted."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("PUBLIC_PORT", "8080")
        monkeypatch.setenv("INTERNAL_PORT", "8081")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.public_port == 8080
        assert s.internal_port == 8081

    def test_port_below_range_rejected(self, monkeypatch, tmp_path):
        """Ports below 1024 should be rejected."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("PUBLIC_PORT", "80")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        with pytest.raises(ValidationError):
            Settings()

    def test_port_above_range_rejected(self, monkeypatch, tmp_path):
        """Ports above 65535 should be rejected."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("PUBLIC_PORT", "70000")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        with pytest.raises(ValidationError):
            Settings()



class TestAllowedDirList:
    """Tests for the allowed_dir_list property."""

    def test_single_directory(self, monkeypatch, tmp_path):
        """A single directory should be returned as a one-element list."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("ALLOWED_DIRS", "/workspace")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.allowed_dir_list == ["/workspace"]

    def test_multiple_directories(self, monkeypatch, tmp_path):
        """Comma-separated dirs should be parsed into a list."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("ALLOWED_DIRS", "/home/user,/opt/projects, /tmp/test ")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))

        from corvustunnel.config.settings import Settings
        s = Settings()
        dirs = s.allowed_dir_list
        assert len(dirs) == 3
        assert "/home/user" in dirs
        assert "/opt/projects" in dirs
        assert "/tmp/test" in dirs  # should be stripped

    def test_empty_allowed_dirs(self, monkeypatch, tmp_path):
        """Empty ALLOWED_DIRS should fall back to current working directory."""
        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("ALLOWED_DIRS", "")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(tmp_path / "logs"))
    
        from corvustunnel.config.settings import Settings
        s = Settings()
        assert s.allowed_dir_list == [os.getcwd()]


class TestAuditLogDir:
    """Tests for audit_log_dir auto-creation."""

    def test_audit_log_dir_created(self, monkeypatch, tmp_path):
        """audit_log_dir should be created if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        assert not log_dir.exists()

        monkeypatch.setenv("AGENT_TOKEN", "test")
        monkeypatch.setenv("AUDIT_LOG_DIR", str(log_dir))

        from corvustunnel.config.settings import Settings
        s = Settings()
        assert log_dir.exists()
        assert log_dir.is_dir()
