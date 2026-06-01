#!/usr/bin/env python3
"""CorvusTunnel Boot Helpers.

Provides compact QR code generation and banner printing for the entrypoint.
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
    """Print the startup banner with QR codes."""
    W = 50
    print()
    print("╔" + "═" * W + "╗")
    print("║" + "  🐳 CORVUSTUNNEL v0.2.0".ljust(W) + "║")
    print("║" + "  Secure Remote AI Terminal".ljust(W) + "║")
    print("╠" + "═" * W + "╣")

    if tunnel_url:
        print("║" + "  1. SCAN TO OPEN:".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()
        print_qr(tunnel_url, "URL")
    else:
        print("║" + "  ⚠ Tunnel not detected".ljust(W) + "║")
        print("║" + "  Local: http://localhost:8000".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()

    print("╔" + "═" * W + "╗")
    print("║" + "  2. SCAN TO COPY TOKEN:".ljust(W) + "║")
    print("╚" + "═" * W + "╝")
    print()
    print_qr(token, "Token")
    print("─" * W)
    print("  Workspace: /workspace")
    print("─" * W)
    print()
    sys.stdout.flush()
