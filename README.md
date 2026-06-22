# CorvusTunnel

Control your AI coding agents from your phone, tablet, or any other computer.
CorvusTunnel runs on the machine where your code lives, shows a QR code, and
lets you drive Claude Code, Codex, or Antigravity from a browser anywhere.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/corvustunnel.svg)](https://pypi.org/project/corvustunnel/)

---

## What this is

CorvusTunnel is a small, self-hosted tool. You install it next to your project,
start it, and scan the QR code it prints. From then on your phone (or any
browser) is a terminal into the agent running on your machine. You can step away
from your desk and still review diffs, answer prompts, and keep work moving.

It is free and open source, and it is run as a community project rather than a
business. There is no paid plan, no account to create, no analytics, and nothing
about your sessions is sold or shared. Your code and the agent's output stay on
your machine; everything that leaves it is end-to-end encrypted. The project is
not run for profit, and it never will be.

## Quick start

```bash
pip install corvustunnel

cd /path/to/your/project
corvustunnel start
```

Scan the QR code that appears, and you are connected. You can also point it at a
specific folder instead of the current one:

```bash
corvustunnel start --workspace /path/to/your/project
```

The QR code is one-time use. If nobody connects within 60 seconds the server
shuts down on its own, so a stale link cannot linger — just run the command
again for a fresh code.

## How it works

```
   Your device                 Relay                 Your computer
  ┌────────────┐          ┌────────────┐          ┌────────────────┐
  │  browser   │◄────────►│  forwards  │◄────────►│  CorvusTunnel  │
  │  (xterm)   │   wss     │ ciphertext │   wss     │  FastAPI + PTY │
  └────────────┘          └────────────┘          │  agent (claude │
        ▲                                          │  / codex / agy)│
        │            end-to-end encrypted          └────────────────┘
        └──────────────────────────────────────────────────►
```

The browser and the server perform an ephemeral key exchange and encrypt every
terminal frame. The relay in the middle only ever forwards opaque bytes; it
cannot read anything that passes through it.

## Features

- Works with Claude Code, Codex CLI, and Antigravity.
- End-to-end encryption with NaCl (X25519 key agreement, XSalsa20-Poly1305),
  with fresh keys per connection.
- Connect by scanning a QR code — no URLs to copy.
- Live terminal streaming over WebSocket, rendered with xterm.js.
- Works on phones, tablets, and desktop browsers alike.
- Installable as a PWA, with optional push notifications for agent events.
- Quick-action chips and pinned favorite commands for one-tap replies.
- Audit and forensic logging of every session, kept on your machine.
- Hardened by default: IP bans, rate limiting, body-size limits, security
  headers, and spoof-resistant client-IP handling.

## Connecting from outside your network

By default CorvusTunnel registers a session with a hosted relay
(`roost.corvustunnel.com`) so your phone can reach your machine without any
port forwarding. The relay is a free convenience that the project runs; because
traffic is end-to-end encrypted, it only sees ciphertext.

If you would rather not use the hosted relay, you have options:

```bash
corvustunnel start --no-relay              # use a cloudflared Quick Tunnel
corvustunnel start --no-relay --no-tunnel  # LAN only, reachable on your network
corvustunnel start --host https://your.domain   # front it with your own proxy
```

The public port binds to `127.0.0.1` by default in relay and tunnel modes. Use
`--bind 0.0.0.0` to expose it on your network directly. If you put your own
reverse proxy in front, set `TRUSTED_PROXIES` so its `X-Forwarded-For` header is
honored — otherwise that header is ignored and the real socket address is used
for bans and rate limiting.

## Security

- Every terminal frame is encrypted end to end with NaCl Box (`crypto_box`:
  X25519 plus XSalsa20-Poly1305). Only the browser and your machine hold keys.
- Forward secrecy: both sides use ephemeral keypairs that are never written to
  disk and are discarded when the connection closes.
- Access starts with a one-time boot token delivered in the QR code, which is
  exchanged for a session token bound to the connecting IP.
- WebSocket connections use one-time, IP-bound tickets with a 30-second life.
- Repeated failed attempts get the source IP rate-limited and then banned.

Found a security problem? Please email admin@kalai-tech.com privately rather than
opening a public issue.

## Configuration

Settings are read from the environment:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_TOKEN` | Auto-generated | Bearer token used for authentication |
| `ALLOWED_DIRS` | Home + current dir | Comma-separated folders the browser may open |
| `AUDIT_LOG_DIR` | `./logs` | Where audit logs are written |
| `PUBLIC_PORT` | `8000` | Public port |
| `INTERNAL_PORT` | `8001` | Internal, localhost-only admin port |
| `TRUSTED_PROXIES` | _(none)_ | Extra IPs whose `X-Forwarded-For` is trusted |

Useful flags: `--workspace`, `--bind`, `--no-relay`, `--no-tunnel`, `--host`,
`--claim-timeout` (seconds before an unused QR expires; `0` disables), and
`--verbose`.

## Project layout

```
corvustunnel/
├── cli.py            command-line entry point: servers, relay, the QR code
├── boot.py           renders the QR code in the terminal
├── version.py        single source of the version string
├── apps/
│   ├── public.py     public app (port 8000): web UI and API, via the relay
│   └── internal.py   internal app (port 8001): localhost-only admin views
├── auth/             boot/session tokens, IP binding, WebSocket tickets
├── crypto/           end-to-end encryption (X25519 + NaCl Box)
├── executor/         the PTY session that runs the agent
├── routers/          HTTP and WebSocket route handlers
├── middleware/       client-IP trust, IP bans, rate limits, security headers
├── audit/            audit and forensic logging
├── config/           settings loaded from the environment
├── history/          reads past Claude / Codex / Antigravity sessions
└── static/           the built web UI
frontend/             web UI source (Svelte + Vite)
tests/                test suite
```

## Development

```bash
git clone https://github.com/maliozturk/CorvusTunnel.git
cd CorvusTunnel
pip install -e ".[dev]"

AGENT_TOKEN=dev-token corvustunnel start --verbose
python -m pytest
```

The web UI lives in `frontend/` (Svelte + Vite). Build it with
`npm install && npm run build`, which writes the bundle into
`corvustunnel/static/`.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get
set up and what to expect.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: [corvustunnel.com](https://corvustunnel.com)
- Maintained by: [kalai-tech.com](https://kalai-tech.com)
- Source: [github.com/maliozturk/CorvusTunnel](https://github.com/maliozturk/CorvusTunnel)
- Contact: admin@kalai-tech.com
