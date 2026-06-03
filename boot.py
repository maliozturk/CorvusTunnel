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
    """Print the startup banner with a single QR code.

    QR code contains: URL#token=<token>&e2e=<server_public_key_b64>
    The fragment is never sent to proxy/server by the browser.
    """
    # Try to get E2E public key
    e2e_key = ""
    try:
        from crypto.e2e import get_e2e_crypto
        crypto = get_e2e_crypto()
        if crypto.available:
            e2e_key = crypto.server_public_key_b64
    except Exception:
        pass

    W = 54
    print()
    print("╔" + "═" * W + "╗")
    print("║" + "  🚀 CORVUSTUNNEL v0.4.0".ljust(W) + "║")
    print("║" + "  AI Agent Control with Voice".ljust(W) + "║")
    print("╠" + "═" * W + "╣")

    if tunnel_url:
        # Single QR: URL with token + E2E key in fragment
        fragment = f"token={token}"
        if e2e_key:
            fragment += f"&e2e={e2e_key}"
        combined = f"{tunnel_url}#{fragment}"
        print("║" + f"  Tunnel: {tunnel_url}".ljust(W) + "║")
        if e2e_key:
            print("║" + "  E2E:    🔒 Enabled (PyNaCl)".ljust(W) + "║")
        else:
            print("║" + "  E2E:    ⚠ Disabled (install PyNaCl)".ljust(W) + "║")
        print("║" + "  Scan QR to connect:".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()
        print_qr(combined, "Scan with phone camera")
    else:
        print("║" + "  ⚠ Tunnel not detected".ljust(W) + "║")
        print("║" + "  Local: http://localhost:8000".ljust(W) + "║")
        if e2e_key:
            print("║" + "  E2E:   🔒 Enabled".ljust(W) + "║")
        print("╚" + "═" * W + "╝")
        print()

    print("─" * W)
    print("  Token is one-time-use (consumed on first login)")
    print("  Restart corvustunnel for a new token")
    print("─" * W)
    print()
    sys.stdout.flush()
