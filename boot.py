#!/usr/bin/env python3
"""CorvusTunnel Boot Helpers.

Provides compact QR code generation and banner printing for the entrypoint.
Single QR code contains URL#token for one-scan onboarding.
"""

import sys


def print_qr(data: str, label: str) -> None:
    """Generate a QR code as PNG image and open it.

    Saves to ~/.corvustunnel/qr.png and opens with the default image viewer.
    Also prints the URL as a clickable fallback.
    """
    import os
    import webbrowser

    qr_dir = os.path.join(os.path.expanduser("~"), ".corvustunnel")
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, "qr.png")

    try:
        import qrcode
        import qrcode.image.pil

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)

        print(f"  {label}:")
        print(f"  QR saved to: {qr_path}")
        print(f"  URL: {data.split('#')[0]}")
        print()

        # Auto-open the QR image
        try:
            if sys.platform == "win32":
                os.startfile(qr_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", qr_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", qr_path])
        except Exception:
            print(f"  Open the QR image manually: {qr_path}")

    except ImportError:
        # No qrcode library — just print the URL
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
