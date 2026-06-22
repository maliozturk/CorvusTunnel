# CorvusTunnel

**Control AI Agents from Your Phone**

Self-hosted remote control for Claude Code, Codex, and Antigravity. Free, open source, E2E encrypted.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/corvustunnel.svg)](https://pypi.org/project/corvustunnel/)

---

## Quick Start

```bash
# Install
pip install corvustunnel

# Start
corvustunnel start

# With a specific workspace
corvustunnel start --workspace /path/to/your/project
```

Scan the QR code with your phone → you're connected.

## Features

- **Multi-agent support** — Claude Code, Codex CLI, Antigravity
- **End-to-end encryption** — NaCl/libsodium, ephemeral key exchange on every connection (relay sees only ciphertext)
- **QR code connect** — scan to connect, no manual URL typing
- **Real-time streaming** — WebSocket-based terminal I/O via xterm.js
- **Push notifications** — Web Push API alerts for agent events
- **PWA support** — install on your phone like a native app
- **Smart suggestions** — context-aware action chips (approve, reject, continue)
- **Command favorites** — pin frequently used prompts for one-tap access
- **Audit logging** — JSONL forensic logs of all sessions
- **Security hardened** — IP ban, rate limiting, body size limits, CORS, security headers
- **Self-hosted** — runs on your machine, your data stays with you
- **Unlimited** — no session limits, no cooldowns, no restrictions

## How It Works

```
Your Phone                    Your Computer
┌─────────┐                  ┌──────────────────┐
│         │   WebSocket      │  CorvusTunnel    │
│  Scan   │ ◄──────────────► │  ├── FastAPI     │
│  QR     │   (E2E encrypted)│  ├── PTY/pexpect │
│  Code   │                  │  └── Agent       │
│         │                  │      (claude/    │
│  Send   │                  │       codex/     │
│  prompts│                  │       agy)       │
└─────────┘                  └──────────────────┘
     ▲                              ▲
     │    Cloudflare Relay          │
     └──────────────────────────────┘
         (TLS + E2E encryption)
```

## Installation

```bash
pip install corvustunnel
corvustunnel start
```

## Security

- **E2E Encryption**: Every terminal frame is encrypted with NaCl Box (`crypto_box`: X25519 key agreement + XSalsa20-Poly1305 authenticated encryption). The browser and your machine are the only endpoints that hold keys — the relay forwards opaque ciphertext.
- **Forward secrecy**: Both sides generate ephemeral X25519 keypairs per connection; keys never touch disk and are dropped on disconnect.
- **Auth**: One-time boot token → session token with IP binding
- **WebSocket**: Ticket-based auth (one-time, 30s TTL, IP-bound)
- **Rate Limiting**: Per-endpoint via slowapi
- **IP Auto-Ban**: After repeated auth failures

See [SECURITY.md](SECURITY.md) for full details and vulnerability reporting.

### Relay & privacy

By default CorvusTunnel registers a session with the hosted relay
(`roost.corvustunnel.com`) so your phone can reach your machine without any
port-forwarding. Because terminal I/O is end-to-end encrypted, **the relay only
ever forwards opaque ciphertext** — it cannot read your prompts, your code, or
the agent's output. If you would rather not use the hosted relay at all:

- `corvustunnel start --no-relay` — use a cloudflared Quick Tunnel instead.
- `corvustunnel start --no-relay --no-tunnel` — LAN only (binds `0.0.0.0`, reachable from your local network).
- `corvustunnel start --host https://your.domain` — front it with your own reverse proxy.

The public port binds to `127.0.0.1` by default (relay/tunnel modes). Use
`--bind 0.0.0.0` to expose it directly, and set `TRUSTED_PROXIES` if a reverse
proxy you control terminates the connection — otherwise `X-Forwarded-For` is
ignored and the direct socket address is used for bans and rate limits.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_TOKEN` | Auto-generated | Bearer token for API auth |
| `ALLOWED_DIRS` | Home + CWD | Comma-separated allowed directories |
| `AUDIT_LOG_DIR` | `./logs` | Audit log directory |
| `PUBLIC_PORT` | `8000` | Public API port |
| `INTERNAL_PORT` | `8001` | Internal admin port |
| `TRUSTED_PROXIES` | _(none)_ | Extra IPs (besides loopback) whose `X-Forwarded-For` is trusted |

## Development

```bash
git clone https://github.com/maliozturk/CorvusTunnel.git
cd CorvusTunnel
pip install -e ".[dev]"
AGENT_TOKEN=dev-token corvustunnel start --verbose
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE)

## Links

- **Website**: [corvustunnel.com](https://corvustunnel.com)
- **GitHub**: [github.com/maliozturk/CorvusTunnel](https://github.com/maliozturk/CorvusTunnel)
