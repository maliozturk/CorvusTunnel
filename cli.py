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


RELAY_API = "https://roost.corvustunnel.com"


def _register_relay_session(e2e_key: str = "") -> dict | None:
    """Register a session with the roost relay server.

    Returns dict with session_id, cli_secret, phone_token, relay_url, ws_url.
    Returns None on failure.
    """
    import urllib.request
    import json as _json

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
) -> None:
    """Print startup info with QR code."""
    from boot import print_qr

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
        from crypto.e2e import get_e2e_crypto
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
    print("|" + "  AI Agent Control with Voice".ljust(W) + "|")
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
    if relay_data:
        ttl = relay_data.get("ttl_seconds", 1800)
        print(f"  Session expires in {int(ttl // 60)} minutes")
        print("  Restart corvustunnel for a new session")
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
    """
    import json as _json
    import base64 as _b64

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

    ws_url = relay_data["ws_url"]
    cli_secret = relay_data["cli_secret"]
    session_id = relay_data["session_id"]

    def _rewrite_html(html: str) -> str:
        """Rewrite HTML so browser loads assets through /<session_id>/ prefix."""
        prefix = f"/{session_id}"

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

    async def bridge():
        async with websockets.connect(ws_url, max_size=2**20) as ws:
            # Authenticate with relay
            await ws.send(_json.dumps({"type": "auth", "token": cli_secret}))
            auth_msg = _json.loads(await ws.recv())
            if auth_msg.get("type") != "auth_ok":
                logger.error("Relay auth failed: %s", auth_msg)
                return

            logger.info("Relay bridge connected and authenticated")

            local_ws = None
            local_ws_task = None

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
                        async with httpx.AsyncClient() as client:
                            url = f"http://localhost:{public_port}{path}"
                            resp = await client.request(
                                method, url,
                                headers=headers,
                                content=body.encode("utf-8") if body else None,
                                timeout=25,
                                follow_redirects=True,
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

            # Cleanup on bridge disconnect
            if local_ws:
                try:
                    await local_ws.close()
                except Exception:
                    pass
            if local_ws_task:
                local_ws_task.cancel()

    # Retry loop with exponential backoff
    for attempt in range(3):
        try:
            await bridge()
            break
        except Exception as e:
            logger.warning("Relay bridge error (attempt %d): %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error("Relay bridge failed after 3 attempts")



async def _run_server(
    public_port: int,
    internal_port: int,
    relay_data: dict | None = None,
) -> None:
    """Run both public and internal servers concurrently, plus relay bridge."""
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

    tasks = [
        public_server.serve(),
        internal_server.serve(),
    ]

    # Add relay bridge if in relay mode
    if relay_data:
        tasks.append(_relay_bridge(relay_data, public_port))

    try:
        await asyncio.gather(*tasks)
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
        os.environ.setdefault("ALLOWED_DIRS", os.getcwd())

    # Ensure token exists
    token = _ensure_token()

    # Get resolved ports
    public_port = int(os.environ.get("PUBLIC_PORT", "8000"))
    internal_port = int(os.environ.get("INTERNAL_PORT", "8001"))

    # Get E2E key for relay registration
    e2e_key = ""
    try:
        from crypto.e2e import get_e2e_crypto
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

    # Print startup info
    _print_startup_info(token, public_port, relay_data, host_url)

    # Run the server
    try:
        asyncio.run(_run_server(public_port, internal_port, relay_data))
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
        help="Host URL for QR code. Overrides relay and tunnel.",
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
        args.workspace = None
        args.host = None
        args.no_relay = False
        args.no_tunnel = False
        args.verbose = False
        cmd_start(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

