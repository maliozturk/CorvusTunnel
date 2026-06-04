#!/usr/bin/env python3
"""CorvusTunnel Boot Helpers.

Provides compact QR code generation and banner printing for the entrypoint.
Single QR code contains URL#token for one-scan onboarding.
"""

import sys


def print_qr(data: str, label: str) -> None:
    """Print a QR code directly in the terminal as Unicode block art.

    Uses the compact half-block technique (▀▄█ ) so the QR fits nicely
    in a standard 80-column terminal. Falls back to ASCII on terminals
    that don't support Unicode.
    """
    import os

    # Ensure stdout can handle Unicode blocks on Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Get the QR matrix
        matrix = qr.get_matrix()
        rows = len(matrix)

        print(f"  {label}:")
        print()

        def _render_unicode(matrix, rows):
            """Render using Unicode half-block characters (compact)."""
            for y in range(0, rows, 2):
                line = "  "
                for x in range(len(matrix[0])):
                    top = matrix[y][x]
                    bottom = matrix[y + 1][x] if (y + 1) < rows else False
                    if top and bottom:
                        line += "\u2588"
                    elif top and not bottom:
                        line += "\u2580"
                    elif not top and bottom:
                        line += "\u2584"
                    else:
                        line += " "
                print(line)

        def _render_ascii(matrix, rows):
            """Render using ASCII characters (fallback)."""
            for y in range(rows):
                line = "  "
                for x in range(len(matrix[0])):
                    line += "##" if matrix[y][x] else "  "
                print(line)

        try:
            _render_unicode(matrix, rows)
        except UnicodeEncodeError:
            _render_ascii(matrix, rows)

        print()

        # Print the URL as a clickable fallback (strip the token fragment)
        url_base = data.split("#")[0]
        print(f"  URL: {url_base}")
        print()

    except ImportError:
        # No qrcode library — just print the URL
        print(f"  {label}: {data}")
        print()
