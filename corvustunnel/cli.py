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

from corvustunnel.version import __version__


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


RELAY_API = "https://roost.corvustunnel.com"


def _register_relay_session(e2e_key: str = "") -> dict | None:
    """Register a session with the roost relay server.

    Returns dict with session_id, cli_secret, phone_token, relay_url, ws_url.
    Returns None on failure.
    """
    import json as _json
    import urllib.request

    logger = logging.getLogger("corvustunnel")
    logger.info("Registering with relay at %s...", RELAY_API)

    payload = _json.dumps({"server_public_key": e2e_key}).encode("utf-8")

    req = urllib.request.Request(
        f"{RELAY_API}/api/tunnel/create",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"CorvusTunnel/{__version__}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            logger.info("Relay session: %s", data.get("relay_url", ""))
            return data
    except Exception as e:
        logger.warning("Relay registration failed: %s", e)
        return None


def _start_cloudflared(public_port: int) -> str | None:
    """Start cloudflared Quick Tunnel in background (fallback).

    Returns the tunnel URL if successful, None otherwise.
    """
    logger = logging.getLogger("corvustunnel")

    cloudflared_path = shutil.which("cloudflared")
    if not cloudflared_path:
        logger.info("cloudflared not found — skipping tunnel")
        return None

    logger.info("Starting cloudflared tunnel (fallback)...")

    log_path = os.path.join(
        os.path.expanduser("~"), ".corvustunnel", "cloudflared.log"
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "w") as log_file:
        subprocess.Popen(
            [
                cloudflared_path, "tunnel",
                "--url", f"http://localhost:{public_port}",
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
    relay_data: dict | None = None,
    host_url: str | None = None,
    claim_timeout: int = 60,
) -> None:
    """Print startup info with QR code."""
    from corvustunnel.boot import print_qr

    # Determine the URL for the QR code
    if relay_data:
        # Relay mode: QR points to roost.corvustunnel.com/<session_id>
        base_url = relay_data["relay_url"]
    elif host_url:
        base_url = host_url.rstrip("/")
    else:
        local_ip = _get_local_ip()
        base_url = f"http://{local_ip}:{public_port}"

    # Build E2E fragment
    e2e_key = ""
    try:
        from corvustunnel.crypto.e2e import get_e2e_crypto
        crypto = get_e2e_crypto()
        if crypto.available:
            e2e_key = crypto.server_public_key_b64
    except Exception:
        pass

    # Build fragment — always use boot token (relay proxies directly to FastAPI)
    fragment = f"token={token}"
    if e2e_key:
        fragment += f"&e2e={e2e_key}"
    qr_data = f"{base_url}/#{fragment}"

    W = 58
    print()
    print("+" + "=" * W + "+")
    print("|" + "  CORVUSTUNNEL v" + __version__.ljust(W - 17) + "|")
    print("|" + "  AI Agent Control from Your Phone".ljust(W) + "|")
    print("+" + "=" * W + "+")
    print("|" + f"  Local:  http://localhost:{public_port}".ljust(W) + "|")
    if relay_data:
        print("|" + f"  Roost:  {base_url}".ljust(W) + "|")
        print("|" + "  Mode:   Relay (roost.corvustunnel.com)".ljust(W) + "|")
    elif host_url:
        print("|" + f"  Remote: {host_url}".ljust(W) + "|")
    if e2e_key:
        print("|" + "  E2E:    [LOCKED] Enabled".ljust(W) + "|")
    print("+" + "=" * W + "+")
    print("|" + "  Scan QR to connect from your phone:".ljust(W) + "|")
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
    """Transparent HTTP/WS proxy bridge between relay and localhost.

    Receives HTTP requests from the relay (sent by the phone), proxies them
    to localhost:public_port, and sends the response back. Also bridges
    WebSocket connections for the terminal.

    The bridge is persistent:
      - Sends heartbeat pings every 30s to keep the session alive.
      - Auto-re-registers a new relay session if the old one expires.
      - Retries indefinitely with exponential backoff.
    """
    import base64 as _b64
    import json as _json

    logger = logging.getLogger("corvustunnel")

    try:
        import websockets
    except ImportError:
        logger.error(
            "websockets package required for relay mode. "
            "Install with: pip install websockets"
        )
        return

    try:
        import httpx
    except ImportError:
        logger.error(
            "httpx package required for relay mode. "
            "Install with: pip install httpx"
        )
        return

    # Mutable state — updated on re-registration
    current = {
        "ws_url": relay_data["ws_url"],
        "cli_secret": relay_data["cli_secret"],
        "session_id": relay_data["session_id"],
    }

    def _rewrite_html(html: str) -> str:
        """Rewrite HTML so browser loads assets through /<session_id>/ prefix."""
        prefix = f"/{current['session_id']}"

        # Rewrite static resource paths in HTML attributes
        html = html.replace('href="/static/', f'href="{prefix}/static/')
        html = html.replace('src="/static/', f'src="{prefix}/static/')
        html = html.replace("href='/static/", f"href='{prefix}/static/")
        html = html.replace("src='/static/", f"src='{prefix}/static/")

        # Inject fetch/WebSocket URL rewriter + auto-claim after <head>
        inject = (
            "<script>"
            "(function(){"
            f"var S='{prefix}';"
            "var of=window.fetch;"
            "window.fetch=function(u,o){"
            "if(typeof u==='string'&&u.startsWith('/'))u=S+u;"
            "return of.call(this,u,o);"
            "};"
            "var OW=window.WebSocket;"
            "window.WebSocket=function(u,p){"
            "var h=location.host;"
            "u=u.replace('://'+h+'/','://'+h+S+'/');"
            "return new OW(u,p);"
            "};"
            "window.WebSocket.prototype=OW.prototype;"
            "window.WebSocket.CONNECTING=OW.CONNECTING;"
            "window.WebSocket.OPEN=OW.OPEN;"
            "window.WebSocket.CLOSING=OW.CLOSING;"
            "window.WebSocket.CLOSED=OW.CLOSED;"
            "var fg=new URLSearchParams(location.hash.substring(1));"
            "var bt=fg.get('token');"
            "if(bt){history.replaceState(null,'',location.pathname);"
            "window._corvusAutoToken=bt;}"
            "})();"
            "</script>"
        )

        # Inject auto-claim before </body>
        auto_claim = (
            "<script>"
            "if(window._corvusAutoToken){"
            "window.addEventListener('DOMContentLoaded',function(){"
            "setTimeout(function(){"
            "if(typeof claimAndBoot==='function')"
            "claimAndBoot(window._corvusAutoToken);"
            "},200);"
            "});"
            "}"
            "</script>"
        )

        html = html.replace("<head>", "<head>" + inject, 1)
        html = html.replace("</body>", auto_claim + "</body>", 1)

        return html

    async def _heartbeat(ws):
        """Send periodic heartbeat pings to keep the relay session alive."""
        try:
            while True:
                await asyncio.sleep(30)
                try:
                    await ws.send(_json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def bridge():
        async with websockets.connect(
            current["ws_url"],
            max_size=2**20,
            ping_interval=20,
            ping_timeout=20,
        ) as ws:
            # Authenticate with relay
            await ws.send(_json.dumps({
                "type": "auth", "token": current["cli_secret"],
            }))
            auth_msg = _json.loads(await ws.recv())
            if auth_msg.get("type") != "auth_ok":
                logger.error("Relay auth failed: %s", auth_msg)
                return

            logger.info("Relay bridge connected and authenticated")

            # Start heartbeat task
            hb_task = asyncio.create_task(_heartbeat(ws))

            local_ws = None
            local_ws_task = None
            # One pooled HTTP client for all proxied requests this connection.
            http_client = httpx.AsyncClient(timeout=25, follow_redirects=True)

            try:
                async def _fwd_local_to_relay(lws, rws):
                    """Forward local terminal WS messages to relay."""
                    try:
                        async for msg in lws:
                            await rws.send(_json.dumps({"type": "ws_fwd", "data": msg}))
                    except websockets.exceptions.ConnectionClosed:
                        pass
                    except Exception as e:
                        logger.debug("Local→relay WS error: %s", e)

                async for message in ws:
                    try:
                        msg = _json.loads(message)
                    except Exception:
                        continue

                    msg_type = msg.get("type", "")

                    # ── HTTP proxy request ──
                    if msg_type == "http_req":
                        req_id = msg.get("id")
                        method = msg.get("method", "GET")
                        path = msg.get("path", "/")
                        headers = msg.get("headers", {})
                        body = msg.get("body")

                        try:
                            url = f"http://localhost:{public_port}{path}"
                            resp = await http_client.request(
                                method, url,
                                headers=headers,
                                content=body.encode("utf-8") if body else None,
                            )

                            ct = resp.headers.get("content-type", "")
                            is_text = ct.startswith(("text/", "application/json",
                                                     "application/javascript",
                                                     "application/xml"))

                            if is_text:
                                resp_body = resp.text
                                encoding = None
                                # Rewrite HTML responses
                                if "text/html" in ct:
                                    resp_body = _rewrite_html(resp_body)
                            else:
                                resp_body = _b64.b64encode(resp.content).decode("ascii")
                                encoding = "base64"

                            resp_headers = dict(resp.headers)
                            for h in ("transfer-encoding", "connection", "keep-alive"):
                                resp_headers.pop(h, None)

                            await ws.send(_json.dumps({
                                "type": "http_res",
                                "id": req_id,
                                "status": resp.status_code,
                                "headers": resp_headers,
                                "body": resp_body,
                                "encoding": encoding,
                            }))
                        except Exception as e:
                            logger.warning("Proxy error for %s %s: %s", method, path, e)
                            await ws.send(_json.dumps({
                                "type": "http_res",
                                "id": req_id,
                                "status": 502,
                                "headers": {"content-type": "application/json"},
                                "body": _json.dumps({"error": str(e)}),
                            }))

                    # ── Open local WebSocket for terminal ──
                    elif msg_type == "ws_open":
                        ws_path = msg.get("path", "/api/terminal/ws")
                        local_url = f"ws://localhost:{public_port}{ws_path}"
                        try:
                            local_ws = await websockets.connect(local_url, max_size=2**20)
                            local_ws_task = asyncio.create_task(
                                _fwd_local_to_relay(local_ws, ws)
                            )
                            logger.info("Local terminal WebSocket bridged: %s", ws_path)
                        except Exception as e:
                            logger.warning("Local WS connect failed: %s", e)
                            await ws.send(_json.dumps({
                                "type": "ws_fwd",
                                "data": _json.dumps({
                                    "type": "error",
                                    "message": f"Terminal connection failed: {e}",
                                }),
                            }))

                    # ── Forward phone WS message to local WS ──
                    elif msg_type == "ws_fwd":
                        if local_ws:
                            try:
                                data = msg.get("data", "")
                                await local_ws.send(data)
                            except Exception as e:
                                logger.debug("WS forward error: %s", e)

                    # ── Close local WS (phone disconnected) ──
                    elif msg_type == "ws_close":
                        if local_ws:
                            try:
                                await local_ws.close()
                            except Exception:
                                pass
                            local_ws = None
                        if local_ws_task:
                            local_ws_task.cancel()
                            local_ws_task = None

            finally:
                # Cleanup
                hb_task.cancel()
                await http_client.aclose()
                if local_ws:
                    try:
                        await local_ws.close()
                    except Exception:
                        pass
                if local_ws_task:
                    local_ws_task.cancel()

    def _re_register() -> bool:
        """Re-register with the relay for a new session."""
        e2e_key = ""
        try:
            from corvustunnel.crypto.e2e import get_e2e_crypto
            crypto = get_e2e_crypto()
            if crypto.available:
                e2e_key = crypto.server_public_key_b64
        except Exception:
            pass

        new_data = _register_relay_session(e2e_key)
        if new_data:
            current["ws_url"] = new_data["ws_url"]
            current["cli_secret"] = new_data["cli_secret"]
            current["session_id"] = new_data["session_id"]
            logger.info(
                "Re-registered relay session: %s",
                new_data.get("relay_url", ""),
            )
            return True
        return False

    # Persistent retry loop — keeps tunnel alive until the server is stopped
    attempt = 0
    max_backoff = 30  # cap backoff at 30 seconds
    while True:
        try:
            await bridge()
            # Bridge exited cleanly (relay closed the connection)
            logger.info("Relay bridge disconnected, re-registering...")
            attempt = 0  # reset backoff on clean disconnect
            if not _re_register():
                logger.warning("Re-registration failed, retrying in 5s...")
                await asyncio.sleep(5)
                continue
        except asyncio.CancelledError:
            logger.info("Relay bridge task cancelled")
            break
        except Exception as e:
            attempt += 1
            wait = min(2 ** min(attempt, 5), max_backoff)
            logger.warning(
                "Relay bridge error (attempt %d), reconnecting in %ds: %s",
                attempt, wait, e,
            )
            await asyncio.sleep(wait)
            # After several failures, try re-registering for a fresh session
            if attempt % 3 == 0:
                logger.info("Attempting relay re-registration...")
                _re_register()



async def _run_server(
    public_port: int,
    internal_port: int,
    relay_data: dict | None = None,
    bind_host: str = "127.0.0.1",
    claim_timeout: float = 60.0,
) -> None:
    """Run both public and internal servers concurrently, plus relay bridge.

    If ``claim_timeout`` is positive and no client claims the boot token within
    that many seconds, the server shuts down so a stale QR/link cannot linger.
    The user simply runs ``corvustunnel start`` again for a fresh code.
    """
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
        asyncio.create_task(_relay_bridge(relay_data, public_port))
        if relay_data else None
    )

    async def _claim_watchdog() -> None:
        """Shut the server down if the boot token isn't claimed in time."""
        from corvustunnel.auth.bearer import get_token_manager

        manager = get_token_manager()
        waited = 0.0
        step = 0.5
        while waited < claim_timeout:
            if manager.is_claimed:
                return  # someone connected — disarm and run normally
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
        asyncio.create_task(_claim_watchdog()) if claim_timeout and claim_timeout > 0
        else None
    )

    all_tasks = server_tasks + ([bridge_task] if bridge_task else [])
    try:
        await asyncio.gather(*all_tasks)
    except asyncio.CancelledError:
        pass  # watchdog cancelled the relay bridge during shutdown
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received")
    finally:
        if watchdog:
            watchdog.cancel()
        logger.info("CorvusTunnel stopped")


def cmd_start(args: argparse.Namespace) -> None:
    """Handle the 'start' command."""
    _setup_logging(args.verbose)

    # Explicit CLI flags win over pre-existing env vars; env is only a fallback.
    if args.port:
        os.environ["PUBLIC_PORT"] = str(args.port)
    if args.internal_port:
        os.environ["INTERNAL_PORT"] = str(args.internal_port)

    # Set allowed dirs if provided
    if args.workspace:
        os.environ["ALLOWED_DIRS"] = ",".join(args.workspace)
    else:
        # Default: home dir + current working directory (env wins if already set)
        home = os.path.expanduser("~")
        cwd = os.getcwd()
        dirs = [home] if home == cwd else [home, cwd]
        os.environ.setdefault("ALLOWED_DIRS", ",".join(dirs))

    # Ensure token exists
    token = _ensure_token()

    # Get resolved ports
    public_port = int(os.environ.get("PUBLIC_PORT", "8000"))
    internal_port = int(os.environ.get("INTERNAL_PORT", "8001"))

    # Get E2E key for relay registration
    e2e_key = ""
    try:
        from corvustunnel.crypto.e2e import get_e2e_crypto
        crypto = get_e2e_crypto()
        if crypto.available:
            e2e_key = crypto.server_public_key_b64
    except Exception:
        pass

    # Determine connection mode
    relay_data = None
    host_url = None

    if args.host:
        # Manual host override (skips relay)
        host_url = args.host
        if not host_url.startswith("http"):
            host_url = f"https://{host_url}"
    elif not args.no_relay:
        # Default: register with roost relay
        relay_data = _register_relay_session(e2e_key)
        if not relay_data:
            # Relay failed — fallback to cloudflared
            logging.getLogger("corvustunnel").info(
                "Relay unavailable, trying cloudflared..."
            )
            if not args.no_tunnel:
                host_url = _start_cloudflared(public_port)
    elif not args.no_tunnel:
        # --no-relay but not --no-tunnel → try cloudflared
        host_url = _start_cloudflared(public_port)

    # Determine bind host. Default is loopback (safe): the relay bridge and
    # cloudflared both connect over localhost. Pure LAN mode (no relay, no
    # tunnel, no host) must listen on all interfaces so phones can reach it.
    logger = logging.getLogger("corvustunnel")
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
        # E2E is active whenever PyNaCl is installed; the client performs a
        # live key exchange so the relay only ever forwards ciphertext.
        from corvustunnel.crypto.e2e import get_e2e_crypto
        secure = get_e2e_crypto().available
        logger.info(
            "Relay mode: traffic routes through %s (%s)",
            RELAY_API.replace("https://", ""),
            "end-to-end encrypted — relay sees only ciphertext"
            if secure else "TLS to relay only; install PyNaCl for E2E",
        )

    # Print startup info
    claim_timeout = getattr(args, "claim_timeout", 60)
    _print_startup_info(token, public_port, relay_data, host_url, claim_timeout)

    # Run the server (claim_timeout resolved above for the banner)
    try:
        asyncio.run(
            _run_server(public_port, internal_port, relay_data, bind_host, claim_timeout)
        )
    except KeyboardInterrupt:
        print("\nCorvusTunnel stopped.")


def cmd_version(args: argparse.Namespace) -> None:
    """Handle the '--version' flag."""
    print(f"corvustunnel {__version__}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="corvustunnel",
        description="Control AI coding agents from your phone",
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
        type=str, action="append", default=None,
        help="Workspace directory (repeatable, e.g. -w /dir1 -w /dir2). "
             "Default: home dir + current directory.",
    )
    start_parser.add_argument(
        "--host",
        type=str, default=None,
        help="Host URL for QR code. Overrides relay and tunnel.",
    )
    start_parser.add_argument(
        "--bind",
        type=str, default=None,
        help="Address to bind the public port to. Default: 127.0.0.1 (relay/"
             "tunnel modes) or 0.0.0.0 (LAN mode). Use 0.0.0.0 to expose on "
             "the LAN — only behind a trusted network.",
    )
    start_parser.add_argument(
        "--claim-timeout",
        type=int, default=60,
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
        args.workspace = None  # will use home + cwd default
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

