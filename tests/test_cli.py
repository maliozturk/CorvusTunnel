# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_cli.py
# Description: Tests for the command-line entry point.
# \*---------------------------------------------------------------------*/



import sys
from io import StringIO
from unittest.mock import patch

import pytest


class TestCLIVersion:
    def test_version_flag_prints_version(self):
        from corvustunnel.cli import __version__

        with patch("sys.argv", ["corvustunnel", "--version"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from corvustunnel.cli import main

                main()
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue().strip()
            assert __version__ in output
            assert "corvustunnel" in output

    def test_version_string_format(self):
        from corvustunnel.cli import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2, f"Version '{__version__}' should have at least 2 parts"
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"

    def test_version_V_flag(self):
        from corvustunnel.cli import __version__

        with patch("sys.argv", ["corvustunnel", "-V"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from corvustunnel.cli import main

                main()
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue().strip()
            assert __version__ in output


class TestCLIHelp:
    def test_help_flag_shows_help(self):
        with patch("sys.argv", ["corvustunnel", "--help"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from corvustunnel.cli import main

                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue()
            assert "corvustunnel" in output.lower()

    def test_start_help_shows_options(self):
        with patch("sys.argv", ["corvustunnel", "start", "--help"]):
            captured = StringIO()
            sys.stdout = captured
            try:
                from corvustunnel.cli import main

                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue()
            assert "--port" in output
            assert "--workspace" in output or "-w" in output


class TestCLIMain:
    def test_main_is_callable(self):
        from corvustunnel.cli import main

        assert callable(main)

    def test_module_level_version(self):
        from corvustunnel.cli import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0


class TestCLIHelpers:
    def test_ensure_token_generates_when_missing(self, monkeypatch):
        monkeypatch.delenv("AGENT_TOKEN", raising=False)

        from corvustunnel.cli import _ensure_token

        token = _ensure_token()

        assert len(token) > 20
        import os

        assert os.environ.get("AGENT_TOKEN") == token

    def test_ensure_token_uses_existing(self, monkeypatch):
        monkeypatch.setenv("AGENT_TOKEN", "my-preset-token")

        from corvustunnel.cli import _ensure_token

        token = _ensure_token()
        assert token == "my-preset-token"

    def test_get_local_ip_returns_string(self):
        from corvustunnel.cli import _get_local_ip

        ip = _get_local_ip()
        assert isinstance(ip, str)
        assert len(ip) > 0

    def test_setup_logging_does_not_crash(self):
        from corvustunnel.cli import _setup_logging

        _setup_logging(verbose=False)
        _setup_logging(verbose=True)
