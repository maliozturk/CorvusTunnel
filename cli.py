#!/usr/bin/env python3
"""
CorvusTunnel CLI — Entry point for `corvustunnel` command.

Usage:
    corvustunnel start              Start the server (default)
    corvustunnel start --port 9000  Custom public port
    corvustunnel start --host corvustunnel.com  Use a specific host
    corvustunnel --version          Show version
    corvustunnel --help             Show help

Environment Variables:
    AGENT_TOKEN       Bearer token for API auth (auto-generated if not set)
    ALLOWED_DIRS      Comma-separated directories visible in folder browser
    AUDIT_LOG_DIR     Directory for audit logs (default: ./logs)
    CORVUS_LICENSE_KEY  License key for Pro features (optional)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time

__version__ = "0.4.0"


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _ensure_token() -> str:
    """Ensure AGENT_TOKEN is set. Auto-generate if not."""
    token = os.environ.get("AGENT_TOKEN", "")
    if not token:
        token = secrets.token_urlsafe(48)
        os.environ["AGENT_TOKEN"] = token
        logging.getLogger("corvustunnel").info(
            "Auto-generated AGENT_TOKEN (no token was set)"
        )
    return token


def _get_local_ip() -> str:
    """Get the machine's local network IP (for LAN access)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _start_cloudflared(public_port: int) -> str | None:
    """Start cloudflared Quick Tunnel in background.

    Returns the tunnel URL if successful, None otherwise.
    """
    logger = logging.getLogger("corvustunnel")

    cloudflared_path = shutil.which("cloudflared")
    if not cloudflared_path:
        logger.info("cloudflared not found — skipping tunnel (using LAN IP)")
        return None

    logger.info("Starting cloudflared tunnel...")

    # Start cloudflared in background
    log_path = os.path.join(
        os.path.expanduser("~"), ".corvustunnel", "cloudflared.log"
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            [
                cloudflared_path, "tunnel",
                "--url", f"http://localhost:{public_port}",
                "--no-autoupdate",
            ],
            stdout=subprocess.DEVNULL,
            stderr=log_file,
        )

    # Wait for tunnel URL (up to 30s)
    tunnel_url = None
    for _ in range(30):
        time.sleep(1)
        try:
            with open(log_path) as f:
                content = f.read()
            match = re.search(
                r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", content
            )
            if match:
                tunnel_url = match.group(0)
                break
        except Exception:
            continue

    if tunnel_url:
        logger.info("Tunnel ready: %s", tunnel_url)
    else:
        logger.warning("Tunnel failed to start (check %s)", log_path)

    return tunnel_url


def _print_startup_info(
    token: str,
    public_port: int,
    host_url: str | None = None,
) -> None:
    """Print startup info with QR code."""
    from boot import print_qr

    # Determine the URL for the QR code
    if host_url:
        # Use provided host (tunnel or manual --host)
        base_url = host_url.rstrip("/")
    else:
        # Fallback to local network IP
        local_ip = _get_local_ip()
        base_url = f"http://{local_ip}:{public_port}"

    # Build E2E fragment
    e2e_key = ""
    try:
        from crypto.e2e import get_e2e_crypto
        crypto = get_e2e_crypto()
        if crypto.available:
            e2e_key = crypto.server_public_key_b64
    except Exception:
        pass

    fragment = f"token={token}"
    if e2e_key:
        fragment += f"&e2e={e2e_key}"
    qr_data = f"{base_url}#{fragment}"

    W = 54
    print()
    print("╔" + "═" * W + "╗")
    print("║" + "  🚀 CORVUSTUNNEL v" + __version__.ljust(W - 20) + "║")
    print("║" + "  AI Agent Control with Voice".ljust(W) + "║")
    print("╠" + "═" * W + "╣")
    print("║" + f"  Local:  http://localhost:{public_port}".ljust(W) + "║")
    print("║" + f"  Remote: {base_url}".ljust(W) + "║")
    if e2e_key:
        print("║" + "  E2E:    🔒 Enabled".ljust(W) + "║")
    print("╠" + "═" * W + "╣")
    print("║" + "  Scan QR to connect from your phone:".ljust(W) + "║")
    print("╚" + "═" * W + "╝")
    print()

    print_qr(qr_data, "Connect")

    print("─" * W)
    print("  Token is one-time-use (consumed on first login)")
    print("  Restart corvustunnel for a new token")
    print("─" * W)
    print()
    sys.stdout.flush()


async def _run_server(public_port: int, internal_port: int) -> None:
    """Run both public and internal servers concurrently."""
    import uvicorn

    logger = logging.getLogger("corvustunnel")

    public_config = uvicorn.Config(
        "public_app:app",
        host="0.0.0.0",
        port=public_port,
        log_level="info",
        access_log=True,
    )
    internal_config = uvicorn.Config(
        "internal_app:app",
        host="127.0.0.1",
        port=internal_port,
        log_level="info",
        access_log=True,
    )

    public_server = uvicorn.Server(public_config)
    internal_server = uvicorn.Server(internal_config)

    logger.info("Starting dual servers...")

    try:
        await asyncio.gather(
            public_server.serve(),
            internal_server.serve(),
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
    finally:
        logger.info("CorvusTunnel stopped")


def cmd_start(args: argparse.Namespace) -> None:
    """Handle the 'start' command."""
    _setup_logging(args.verbose)

    # Set port env vars so Settings picks them up
    if args.port:
        os.environ.setdefault("PUBLIC_PORT", str(args.port))
    if args.internal_port:
        os.environ.setdefault("INTERNAL_PORT", str(args.internal_port))

    # Set allowed dirs if provided
    if args.workspace:
        os.environ.setdefault("ALLOWED_DIRS", args.workspace)
    else:
        # Default to current directory
        os.environ.setdefault("ALLOWED_DIRS", os.getcwd())

    # Ensure token exists
    token = _ensure_token()

    # Get resolved ports
    public_port = int(os.environ.get("PUBLIC_PORT", "8000"))
    internal_port = int(os.environ.get("INTERNAL_PORT", "8001"))

    # Determine host URL
    host_url = None
    if args.host:
        # Manual host override
        host_url = args.host
        if not host_url.startswith("http"):
            host_url = f"https://{host_url}"
    elif not args.no_tunnel:
        # Try to start cloudflared
        host_url = _start_cloudflared(public_port)

    # Print startup info
    _print_startup_info(token, public_port, host_url)

    # Run the server
    try:
        asyncio.run(_run_server(public_port, internal_port))
    except KeyboardInterrupt:
        print("\nCorvusTunnel stopped.")


def cmd_version(args: argparse.Namespace) -> None:
    """Handle the '--version' flag."""
    print(f"corvustunnel {__version__}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="corvustunnel",
        description="AI Agent Control with Voice — Talk to Your Code",
        epilog="Docs: https://corvustunnel.com/docs",
    )
    parser.add_argument(
        "--version", "-V",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command")

    # -- start subcommand --
    start_parser = subparsers.add_parser(
        "start",
        help="Start the CorvusTunnel server",
    )
    start_parser.add_argument(
        "--port", "-p",
        type=int, default=None,
        help="Public API port (default: 8000)",
    )
    start_parser.add_argument(
        "--internal-port",
        type=int, default=None,
        help="Internal admin port (default: 8001)",
    )
    start_parser.add_argument(
        "--workspace", "-w",
        type=str, default=None,
        help="Workspace directory (default: current directory)",
    )
    start_parser.add_argument(
        "--host",
        type=str, default=None,
        help="Host URL for QR code (e.g., corvustunnel.com). "
             "Overrides cloudflared tunnel.",
    )
    start_parser.add_argument(
        "--no-tunnel",
        action="store_true",
        help="Don't start cloudflared tunnel (use LAN IP instead)",
    )
    start_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.version:
        cmd_version(args)
        return

    if args.command == "start":
        cmd_start(args)
    elif args.command is None:
        # Default: start
        args.port = None
        args.internal_port = None
        args.workspace = None
        args.host = None
        args.no_tunnel = False
        args.verbose = False
        cmd_start(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

