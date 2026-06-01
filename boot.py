#!/usr/bin/env python3
"""CorvusTunnel Boot Helpers.

Provides compact QR code generation and banner printing for the entrypoint.
Single QR code contains URL#token for one-scan onboarding.
"""

import sys


def print_qr(data: str, label: str) -> None:
    """Print a compact ASCII QR code using Unicode half-block characters.

    Packs 2 vertical pixels per line using ▀ ▄ █ and space,
    resulting in QR codes roughly half the height of standard renderers.
    """
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)

        matrix = qr.get_matrix()
        rows = len(matrix)

        print(f"  {label}:")

        # Process 2 rows at a time using half-block chars
        for y in range(0, rows, 2):
            line = "  "
            for x in range(len(matrix[0])):
                top = matrix[y][x]
                bot = matrix[y + 1][x] if y + 1 < rows else False

                if top and bot:
                    line += "█"
                elif top and not bot:
                    line += "▀"
                elif not top and bot:
                    line += "▄"
                else:
                    line += " "
            print(line)
        print()
    except ImportError:
        print(f"  {label}: {data}")
        print()


def print_banner(tunnel_url: str, token: str) -> None:
    """Print the startup banner with a single QR code."""
    W = 50
    print()
    print("╔" + "═" * W + "╗")
    print("║" + "  🐳 CORVUSTUNNEL v0.2.0".ljust(W) + "║")
    print("║" + "  Secure Remote AI Terminal".ljust(W) + "║")
    print("╠" + "═" * W + "╣")

    if tunnel_url:
        # Single QR: URL with token in fragment (fragment never sent to server/proxy)
        combined = f"{tunnel_url}#token={token}"
        print("║" + "  Scan QR to connect:".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()
        print_qr(combined, "Scan with phone camera")
    else:
        print("║" + "  ⚠ Tunnel not detected".ljust(W) + "║")
        print("║" + "  Local: http://localhost:8000".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()

    print("─" * W)
    print("  Token is one-time-use (consumed on first login)")
    print("  Restart container for a new token")
    print("─" * W)
    print()
    sys.stdout.flush()
