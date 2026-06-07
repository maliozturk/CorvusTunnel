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
- **End-to-end encryption** — NaCl/libsodium, key exchange via QR code
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

- **E2E Encryption**: All terminal I/O encrypted with NaCl SecretBox (XSalsa20-Poly1305)
- **Key Exchange**: X25519 Diffie-Hellman during QR code scanning
- **Auth**: One-time boot token → session token with IP binding
- **WebSocket**: Ticket-based auth (one-time, 30s TTL, IP-bound)
- **Rate Limiting**: Per-endpoint via slowapi
- **IP Auto-Ban**: After repeated auth failures

See [SECURITY.md](SECURITY.md) for full details and vulnerability reporting.

## API

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/health` | No | Health check |
| `POST /api/e2e/exchange` | No | E2E key exchange |
| `POST /api/claim` | Boot token | Exchange boot token for session token |
| `GET /api/browse` | Session | Directory browser |
| `GET /api/check-agents` | Session | List available AI agents |
| `POST /api/ws-ticket` | Session | Get WebSocket connection ticket |
| `WS /api/terminal/ws` | Ticket | Interactive terminal session |

Internal API (localhost:8001):

| Endpoint | Description |
|----------|-------------|
| `GET /audit` | View audit logs |
| `GET /deeplog` | View deep (plaintext) logs |
| `GET /terminal/status` | Terminal session status |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_TOKEN` | Auto-generated | Bearer token for API auth |
| `ALLOWED_DIRS` | Home + CWD | Comma-separated allowed directories |
| `AUDIT_LOG_DIR` | `./logs` | Audit log directory |
| `PUBLIC_PORT` | `8000` | Public API port |
| `INTERNAL_PORT` | `8001` | Internal admin port |

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
