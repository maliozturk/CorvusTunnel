#!/usr/bin/env python3
# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/boot.py
# Description: Renders the connection QR code as terminal block art.
# \*---------------------------------------------------------------------*/

import sys


def print_qr(data: str, label: str) -> None:
    import os

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

        matrix = qr.get_matrix()
        rows = len(matrix)

        print(f"  {label}:")
        print()

        def _render_unicode(matrix, rows):
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

        print("  \033[90mOr open this link on any device (one-time use):\033[0m")
        print(f"  \033[4m{data}\033[0m")
        print()

    except ImportError:
        print(f"  {label}: {data}")
        print()
