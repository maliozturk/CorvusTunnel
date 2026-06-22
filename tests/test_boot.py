# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        tests/test_boot.py
# Description: Tests for QR-code rendering.
# \*---------------------------------------------------------------------*/



import sys
from io import StringIO
from unittest.mock import patch


class TestPrintQR:
    def test_print_qr_does_not_crash(self):
        from corvustunnel.boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("https://example.com", "Test Label")
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert len(output) > 0, "print_qr should produce some output"

    def test_print_qr_with_url_and_fragment(self):
        from corvustunnel.boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr(
                "https://example.com/#token=abc123&e2e=xyz",
                "Connect",
            )
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert "Connect" in output
        assert "https://example.com/" in output

    def test_print_qr_shows_label(self):
        from corvustunnel.boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("https://localhost:8000", "My Label")
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert "My Label" in output

    def test_print_qr_fallback_without_qrcode(self):

        with patch.dict("sys.modules", {"qrcode": None}):
            captured = StringIO()
            sys.stdout = captured
            try:
                import importlib

                import boot

                importlib.reload(boot)
                boot.print_qr("https://example.com", "Fallback Test")
            finally:
                sys.stdout = sys.__stdout__

            output = captured.getvalue()
            assert "Fallback Test" in output
            assert "https://example.com" in output

    def test_print_qr_with_empty_data(self):
        from corvustunnel.boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("", "Empty")
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert "Empty" in output
