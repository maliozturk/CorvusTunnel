# CorvusTunnel

**AI Agent Control with Voice — Talk to Your Code**

Control Claude, Codex, and Antigravity from your phone. Free and open source.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/corvustunnel.svg)](https://pypi.org/project/corvustunnel/)

---

## Quick Start

```bash
# Install (30 seconds)
pip install corvustunnel

# Start
corvustunnel start

# With a specific workspace
corvustunnel start --workspace /path/to/your/project
```

Scan the QR code with your phone → you're connected.

## Features

### 🆓 Free (MIT, Open Source)

- **Unlimited sessions** — no time limits, no cooldowns
- **Multi-agent support** — Claude Code, Codex CLI, Antigravity
- **End-to-end encryption** — PyNaCl/libsodium, key exchange via QR code
- **QR code connect** — scan to connect, no manual URL typing
- **Real-time streaming** — WebSocket-based terminal I/O
- **Audit logging** — JSONL forensic logs of all sessions
- **Security hardened** — IP ban, rate limiting, body size limits, CORS, security headers
- **Self-hosted** — runs on your machine, your data stays with you

### 💎 Pro ($9/mo)

- **Telegram Voice Interaction** — agent sends voice questions, you reply via voice notes
- **Multi-Agent Orchestration** — run 2+ agents on the same prompt, compare results
- **Agent Performance Dashboard** — session stats, error rates, usage graphs
- **Priority Support** — email support with response SLA

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
     │    Cloudflare Tunnel         │
     └──────────────────────────────┘
         (TLS + E2E encryption)
```

## Installation Options

### pip (recommended)

```bash
pip install corvustunnel
corvustunnel start
```

### pip + voice features

```bash
pip install corvustunnel[voice]
```

### Docker

```bash
docker pull corvustunnel/corvustunnel:latest
docker run -v $(pwd):/workspace corvustunnel/corvustunnel:latest
```

### Docker Compose

```yaml
version: '3.8'
services:
  corvustunnel:
    image: corvustunnel/corvustunnel:latest
    volumes:
      - ./workspace:/workspace
    ports:
      - "8000:8000"
      - "8001:8001"
    environment:
      - ALLOWED_DIRS=/workspace
      # Optional: Pro license key
      # - CORVUS_LICENSE_KEY=your-jwt-license-key
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
| `ALLOWED_DIRS` | `/workspace` | Comma-separated allowed directories |
| `AUDIT_LOG_DIR` | `./logs` | Audit log directory |
| `PUBLIC_PORT` | `8000` | Public API port |
| `INTERNAL_PORT` | `8001` | Internal admin port |
| `CORVUS_LICENSE_KEY` | (empty) | Pro license key (JWT) |

## Development

```bash
git clone https://github.com/corvustunnel/corvustunnel.git
cd corvustunnel
pip install -e ".[dev]"
AGENT_TOKEN=dev-token corvustunnel start --verbose
```

## License

MIT — see [LICENSE](LICENSE)

## Links

- **Website**: [corvustunnel.com](https://corvustunnel.com)
- **Docs**: [corvustunnel.com/docs](https://corvustunnel.com/docs)
- **GitHub**: [github.com/corvustunnel/corvustunnel](https://github.com/corvustunnel/corvustunnel)
- **Discord**: [discord.gg/corvustunnel](https://discord.gg/corvustunnel)
