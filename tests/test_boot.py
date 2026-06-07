"""
Tests for boot.py — QR code generation helper.

Verifies that print_qr:
  - Doesn't crash on normal input
  - Handles URLs with fragments (token data)
  - Gracefully degrades when qrcode library is missing
"""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import patch

import pytest


class TestPrintQR:
    """Tests for the print_qr function."""

    def test_print_qr_does_not_crash(self):
        """print_qr should run without raising exceptions."""
        from boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("https://example.com", "Test Label")
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert len(output) > 0, "print_qr should produce some output"

    def test_print_qr_with_url_and_fragment(self):
        """print_qr should handle URLs with hash fragments (token data)."""
        from boot import print_qr

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
        # Should print the label
        assert "Connect" in output
        # URL fallback should strip the fragment
        assert "https://example.com/" in output

    def test_print_qr_shows_label(self):
        """print_qr should display the provided label."""
        from boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("https://localhost:8000", "My Label")
        finally:
            sys.stdout = sys.__stdout__

        output = captured.getvalue()
        assert "My Label" in output

    def test_print_qr_fallback_without_qrcode(self):
        """When qrcode is not installed, print_qr should print the URL directly."""
        from boot import print_qr

        with patch.dict("sys.modules", {"qrcode": None}):
            # Force ImportError on import qrcode
            captured = StringIO()
            sys.stdout = captured
            try:
                # Reimport to trigger fallback path
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
        """print_qr should handle empty string data without crashing."""
        from boot import print_qr

        captured = StringIO()
        sys.stdout = captured
        try:
            print_qr("", "Empty")
        finally:
            sys.stdout = sys.__stdout__

        # Should not crash — output may vary
        output = captured.getvalue()
        assert "Empty" in output
