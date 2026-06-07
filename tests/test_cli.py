"""
Tests for cli.py — CLI entry point.

Covers:
  - --version flag outputs version string
  - --help flag shows help text
  - main() function can be imported and called
  - Version string format
  - CLI argument parser structure
"""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import patch

import pytest


class TestCLIVersion:
    """Tests for the --version flag."""

    def test_version_flag_prints_version(self):
        """'corvustunnel --version' should print the version and exit."""
        from cli import __version__

        with patch("sys.argv", ["corvustunnel", "--version"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from cli import main
                main()
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue().strip()
            assert __version__ in output
            assert "corvustunnel" in output

    def test_version_string_format(self):
        """Version should be a semver-like string (X.Y.Z)."""
        from cli import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2, f"Version '{__version__}' should have at least 2 parts"
        # Each part should be numeric
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"

    def test_version_V_flag(self):
        """'-V' short flag should also print version."""
        from cli import __version__

        with patch("sys.argv", ["corvustunnel", "-V"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from cli import main
                main()
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue().strip()
            assert __version__ in output


class TestCLIHelp:
    """Tests for the --help flag."""

    def test_help_flag_shows_help(self):
        """'corvustunnel --help' should show help text and exit."""
        with patch("sys.argv", ["corvustunnel", "--help"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from cli import main
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue()
            assert "corvustunnel" in output.lower()

    def test_start_help_shows_options(self):
        """'corvustunnel start --help' should list start-specific options."""
        with patch("sys.argv", ["corvustunnel", "start", "--help"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from cli import main
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue()
            # Should mention key options
            assert "--port" in output
            assert "--workspace" in output or "-w" in output


class TestCLIMain:
    """Tests for the main() function and related helpers."""

    def test_main_is_callable(self):
        """main() should be importable and callable."""
        from cli import main
        assert callable(main)

    def test_module_level_version(self):
        """__version__ should be defined at module level."""
        from cli import __version__
        assert isinstance(__version__, str)
        assert len(__version__) > 0


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_ensure_token_generates_when_missing(self, monkeypatch):
        """_ensure_token should auto-generate a token if not set."""
        monkeypatch.delenv("AGENT_TOKEN", raising=False)

        from cli import _ensure_token
        token = _ensure_token()

        assert len(token) > 20
        # Should also set it in the environment
        import os
        assert os.environ.get("AGENT_TOKEN") == token

    def test_ensure_token_uses_existing(self, monkeypatch):
        """_ensure_token should use existing AGENT_TOKEN if set."""
        monkeypatch.setenv("AGENT_TOKEN", "my-preset-token")

        from cli import _ensure_token
        token = _ensure_token()
        assert token == "my-preset-token"

    def test_get_local_ip_returns_string(self):
        """_get_local_ip should return a string (IP address)."""
        from cli import _get_local_ip
        ip = _get_local_ip()
        assert isinstance(ip, str)
        assert len(ip) > 0

    def test_setup_logging_does_not_crash(self):
        """_setup_logging should configure logging without errors."""
        from cli import _setup_logging
        _setup_logging(verbose=False)
        _setup_logging(verbose=True)
