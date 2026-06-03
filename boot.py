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

