#!/usr/bin/env python3
# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/cli.py
# Description: Command-line entry point: starts the public/internal
#              servers, registers the relay, prints the QR/link, runs the
#              relay bridge, and enforces the connect-window timeout.
# \*---------------------------------------------------------------------*/


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

from corvustunnel.version import __version__


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _ensure_token() -> str:
    token = os.environ.get("AGENT_TOKEN", "")
    if not token:
        token = secrets.token_urlsafe(48)
        os.environ["AGENT_TOKEN"] = token
        logging.getLogger("corvustunnel").info("Auto-generated AGENT_TOKEN (no token was set)")
    return token


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


RELAY_API = "https://roost.corvustunnel.com"
APP_ORIGIN = os.environ.get("CORVUS_APP_ORIGIN", "https://corvustunnel.com/app")


def _identity_pubkey() -> str:
    try:
        from corvustunnel.crypto.channel import get_server_identity

        return get_server_identity().public_key_b64
    except Exception:
        return ""


def _register_relay_session() -> dict | None:
    import json as _json
    import urllib.request

    logger = logging.getLogger("corvustunnel")
    logger.info("Registering with relay at %s...", RELAY_API)

    req = urllib.request.Request(
        f"{RELAY_API}/api/tunnel/create",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"CorvusTunnel/{__version__}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            logger.info("Relay session established")
            return data
    except Exception as e:
        logger.warning("Relay registration failed: %s", e)
        return None


def _start_cloudflared(public_port: int) -> str | None:
    logger = logging.getLogger("corvustunnel")

    cloudflared_path = shutil.which("cloudflared")
    if not cloudflared_path:
        logger.info("cloudflared not found — skipping tunnel")
        return None

    logger.info("Starting cloudflared tunnel (fallback)...")

    log_path = os.path.join(os.path.expanduser("~"), ".corvustunnel", "cloudflared.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "w") as log_file:
        subprocess.Popen(
            [
                cloudflared_path,
                "tunnel",
                "--url",
                f"http://localhost:{public_port}",
                "--no-autoupdate",
            ],
            stdout=subprocess.DEVNULL,
            stderr=log_file,
        )

    tunnel_url = None
    for _ in range(30):
        time.sleep(1)
        try:
            with open(log_path) as f:
                content = f.read()
            match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", content)
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
    relay_data: dict | None = None,
    host_url: str | None = None,
    claim_timeout: int = 60,
) -> None:
    from urllib.parse import quote

    from corvustunnel.boot import print_qr

    idpub = _identity_pubkey()
    fragment = f"t={token}&k={idpub}"

    if relay_data:
        fragment += f"&w={quote(relay_data['ws_browser'], safe='')}"
        qr_data = f"{APP_ORIGIN}/#{fragment}"
    elif host_url:
        qr_data = f"{host_url.rstrip('/')}/app/#{fragment}"
    else:
        local_ip = _get_local_ip()
        qr_data = f"http://{local_ip}:{public_port}/app/#{fragment}"

    W = 58
    print()
    print("+" + "=" * W + "+")
    print("|" + "  CORVUSTUNNEL v" + __version__.ljust(W - 17) + "|")
    print("|" + "  AI Agent Control from Any Device".ljust(W) + "|")
    print("+" + "=" * W + "+")
    print("|" + f"  Local:  http://localhost:{public_port}".ljust(W) + "|")
    if relay_data:
        print("|" + "  Mode:   Relay (end-to-end encrypted)".ljust(W) + "|")
    elif host_url:
        print("|" + f"  Remote: {host_url}".ljust(W) + "|")
    print("+" + "=" * W + "+")
    print("|" + "  Scan QR to connect from any device:".ljust(W) + "|")
    print("+" + "=" * W + "+")
    print()

    print_qr(qr_data, "Connect")

    print("-" * (W + 2))
    if claim_timeout and claim_timeout > 0:
        print(f"  Connect within {int(claim_timeout)}s or this code expires")
        print("  (server stops; run 'corvustunnel start' for a new one)")
    if relay_data:
        print("  Once connected, the session stays open until you stop it")
        print("  Press Ctrl+C to stop the server")
    else:
        print("  Token is one-time-use (consumed on first login)")
        print("  Restart corvustunnel for a new token")
    print("-" * (W + 2))
    print()
    sys.stdout.flush()


async def _relay_bridge(relay_data: dict, public_port: int) -> None:
    logger = logging.getLogger("corvustunnel")

    try:
        import websockets
    except ImportError:
        logger.error("websockets package required for relay mode. pip install websockets")
        return

    ws_cli = relay_data["ws_cli"]
    local_url = f"ws://127.0.0.1:{public_port}/api/channel"

    async def _pump(src, dst):
        try:
            async for message in src:
                await dst.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def bridge():
        async with websockets.connect(
            ws_cli, max_size=2**20, ping_interval=20, ping_timeout=20
        ) as relay_ws:
            async with websockets.connect(local_url, max_size=2**20) as local_ws:
                logger.info("Relay bridge connected")
                tasks = [
                    asyncio.create_task(_pump(relay_ws, local_ws)),
                    asyncio.create_task(_pump(local_ws, relay_ws)),
                ]
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in tasks:
                    task.cancel()
                # Retrieve every task result so no exception is left unhandled.
                await asyncio.gather(*tasks, return_exceptions=True)

    attempt = 0
    while True:
        try:
            await bridge()
            attempt = 0
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Relay bridge task cancelled")
            break
        except Exception as e:
            attempt += 1
            wait = min(2 ** min(attempt, 5), 30)
            logger.warning("Relay bridge error, reconnecting in %ds: %s", wait, e)
            await asyncio.sleep(wait)


async def _run_server(
    public_port: int,
    internal_port: int,
    relay_data: dict | None = None,
    bind_host: str = "127.0.0.1",
    claim_timeout: float = 60.0,
) -> None:
    import uvicorn

    logger = logging.getLogger("corvustunnel")

    public_config = uvicorn.Config(
        "corvustunnel.apps.public:app",
        host=bind_host,
        port=public_port,
        log_level="info",
        access_log=True,
    )
    internal_config = uvicorn.Config(
        "corvustunnel.apps.internal:app",
        host="127.0.0.1",
        port=internal_port,
        log_level="info",
        access_log=True,
    )

    public_server = uvicorn.Server(public_config)
    internal_server = uvicorn.Server(internal_config)

    logger.info("Starting dual servers...")

    server_tasks = [
        asyncio.create_task(public_server.serve()),
        asyncio.create_task(internal_server.serve()),
    ]
    bridge_task = (
        asyncio.create_task(_relay_bridge(relay_data, public_port)) if relay_data else None
    )

    async def _claim_watchdog() -> None:
        from corvustunnel.auth.bearer import get_token_manager

        manager = get_token_manager()
        waited = 0.0
        step = 0.5
        while waited < claim_timeout:
            if manager.is_claimed:
                return
            await asyncio.sleep(step)
            waited += step

        if not manager.is_claimed:
            logger.warning(
                "No device connected within %ds — shutting down. "
                "Run 'corvustunnel start' again for a fresh QR code.",
                int(claim_timeout),
            )
            print(
                f"\n  Link expired (no connection within {int(claim_timeout)}s)."
                "\n  Run 'corvustunnel start' again to get a new QR code.\n"
            )
            public_server.should_exit = True
            internal_server.should_exit = True
            if bridge_task:
                bridge_task.cancel()

    watchdog = (
        asyncio.create_task(_claim_watchdog()) if claim_timeout and claim_timeout > 0 else None
    )

    all_tasks = server_tasks + ([bridge_task] if bridge_task else [])
    try:
        await asyncio.gather(*all_tasks)
    except asyncio.CancelledError:
        pass
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
    finally:
        if watchdog:
            watchdog.cancel()
        logger.info("CorvusTunnel stopped")


def cmd_start(args: argparse.Namespace) -> None:
    _setup_logging(args.verbose)

    if args.port:
        os.environ["PUBLIC_PORT"] = str(args.port)
    if args.internal_port:
        os.environ["INTERNAL_PORT"] = str(args.internal_port)

    if args.workspace:
        os.environ["ALLOWED_DIRS"] = ",".join(args.workspace)
    else:
        home = os.path.expanduser("~")
        cwd = os.getcwd()
        dirs = [home] if home == cwd else [home, cwd]
        os.environ.setdefault("ALLOWED_DIRS", ",".join(dirs))

    token = _ensure_token()

    public_port = int(os.environ.get("PUBLIC_PORT", "8000"))
    internal_port = int(os.environ.get("INTERNAL_PORT", "8001"))

    logger = logging.getLogger("corvustunnel")
    if not _identity_pubkey():
        logger.error(
            "PyNaCl is required for end-to-end encryption. Install it with: pip install PyNaCl"
        )
        sys.exit(1)

    relay_data = None
    host_url = None

    if args.host:
        host_url = args.host
        if not host_url.startswith("http"):
            host_url = f"https://{host_url}"
    elif not args.no_relay:
        relay_data = _register_relay_session()
        if not relay_data:
            logging.getLogger("corvustunnel").info("Relay unavailable, trying cloudflared...")
            if not args.no_tunnel:
                host_url = _start_cloudflared(public_port)
    elif not args.no_tunnel:
        host_url = _start_cloudflared(public_port)

    if args.bind:
        bind_host = args.bind
    elif relay_data or host_url:
        bind_host = "127.0.0.1"
    else:
        bind_host = "0.0.0.0"

    if bind_host not in ("127.0.0.1", "::1", "localhost"):
        logger.warning(
            "Public port bound to %s — reachable beyond localhost. "
            "IP bans/rate limits use the direct connecting address; only set "
            "TRUSTED_PROXIES if a reverse proxy you control fronts this server.",
            bind_host,
        )

    if relay_data:
        logger.info(
            "Relay mode: traffic routes through %s (end-to-end encrypted — "
            "the relay only ever forwards ciphertext)",
            RELAY_API.replace("https://", ""),
        )

    claim_timeout = getattr(args, "claim_timeout", 60)
    _print_startup_info(token, public_port, relay_data, host_url, claim_timeout)

    try:
        asyncio.run(_run_server(public_port, internal_port, relay_data, bind_host, claim_timeout))
    except KeyboardInterrupt:
        print("\nCorvusTunnel stopped.")


def cmd_version(args: argparse.Namespace) -> None:
    print(f"corvustunnel {__version__}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="corvustunnel",
        description="Control AI coding agents from your phone",
        epilog="Docs: https://corvustunnel.com/docs",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser(
        "start",
        help="Start the CorvusTunnel server",
    )
    start_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help="Public API port (default: 8000)",
    )
    start_parser.add_argument(
        "--internal-port",
        type=int,
        default=None,
        help="Internal admin port (default: 8001)",
    )
    start_parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        action="append",
        default=None,
        help="Workspace directory (repeatable, e.g. -w /dir1 -w /dir2). "
        "Default: home dir + current directory.",
    )
    start_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host URL for QR code. Overrides relay and tunnel.",
    )
    start_parser.add_argument(
        "--bind",
        type=str,
        default=None,
        help="Address to bind the public port to. Default: 127.0.0.1 (relay/"
        "tunnel modes) or 0.0.0.0 (LAN mode). Use 0.0.0.0 to expose on "
        "the LAN — only behind a trusted network.",
    )
    start_parser.add_argument(
        "--claim-timeout",
        type=int,
        default=60,
        help="Seconds to wait for a device to connect before shutting down. "
        "The QR/link is one-time; if unused within this window the server "
        "exits and you run 'corvustunnel start' again. 0 disables.",
    )
    start_parser.add_argument(
        "--no-relay",
        action="store_true",
        help="Don't use roost.corvustunnel.com relay (try cloudflared instead)",
    )
    start_parser.add_argument(
        "--no-tunnel",
        action="store_true",
        help="Don't start cloudflared tunnel (use LAN IP instead)",
    )
    start_parser.add_argument(
        "--verbose",
        "-v",
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
        args.port = None
        args.internal_port = None
        args.workspace = None
        args.host = None
        args.bind = None
        args.claim_timeout = 60
        args.no_relay = False
        args.no_tunnel = False
        args.verbose = False
        cmd_start(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
