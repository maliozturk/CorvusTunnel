# Changelog

All notable changes to CorvusTunnel will be documented in this file.

## [1.1.1] - 2026-06-22

### Added
- Connect-window timeout: if no device claims the boot token within 60 seconds the
  server shuts down so a stale QR/link cannot linger. Configurable with
  `--claim-timeout` (`0` disables).

### Fixed
- Terminal input now works in desktop browsers: clicking the terminal focuses it,
  the terminal auto-focuses on connect, and mouse-wheel scrolling works. Mobile
  behavior is unchanged.

### Changed
- The Python code is now a single `corvustunnel/` package (entry point
  `corvustunnel.cli:main`; apps under `corvustunnel/apps/`; the web UI ships at
  `corvustunnel/static/`). The redundant `main.py` launcher was removed.
- Source files carry a single header banner and no other comments or docstrings;
  removed dead code and brought the tree to a clean `ruff` state.
- Rewrote the README and trimmed API endpoint listings from the docs.
- Frontend build output now targets `corvustunnel/static/`.

## [1.1.0] - 2026-06-14

### Security
- **End-to-end encryption is now wired into the live data path.** Previously the
  `crypto` module existed but no terminal traffic was encrypted; the browser and
  server now perform an ephemeral X25519 key exchange on connect and encrypt every
  WebSocket frame with NaCl Box (`crypto_box`). The relay forwards ciphertext only.
- **Forward secrecy**: per-session ephemeral keypairs on both ends; no key material
  is written to disk, and keys are dropped on disconnect.
- **X-Forwarded-For hardening**: the header is now trusted only from a trusted proxy
  (loopback by default, plus optional `TRUSTED_PROXIES`). This closes IP-ban,
  rate-limit, and session-IP-binding bypasses for directly-reachable deployments.
- The public port now binds to `127.0.0.1` by default (relay/tunnel modes); use
  `--bind` to expose it. LAN mode (`--no-relay --no-tunnel`) still binds `0.0.0.0`.

### Added
- Connect-window timeout: if no device claims the boot token within 60s the
  server shuts down so a stale QR/link can't linger — run `corvustunnel start`
  again for a fresh code. Configurable via `--claim-timeout` (0 disables).

### Changed
- Single source of truth for the version (`_version.py`); CLI, HTTP banner, package
  metadata, and `/health` no longer drift.
- CLI `--port` / `--internal-port` / `--workspace` now take precedence over env vars.
- Relay bridge reuses one pooled `httpx` client instead of one per request.

### Fixed
- Saturated subscriber queues now drop oldest frames and surface a visible
  `[output truncated]` marker instead of silently corrupting the terminal stream.

## [1.0.0] - 2026-06-07

### Added
- Multi-agent support: Claude Code, Codex CLI, Antigravity
- End-to-end encryption with NaCl/libsodium (XSalsa20-Poly1305)
- QR code connect — scan to pair, no manual URL typing
- Real-time terminal streaming via WebSocket + xterm.js
- Push notifications via Web Push API
- PWA support — installable on mobile devices
- Smart suggestion chips — context-aware action buttons
- Command favorites — pin frequently used prompts
- Recent commands history
- Collapsible terminal view for mobile
- Cloudflare relay for zero-config remote access
- JSONL audit logging with SHA-256 prompt hashing
- Deep forensic logging (plaintext, admin-only)
- Security hardening: IP auto-ban, rate limiting, body size limits, security headers
- Directory browser for workspace navigation
- Chat history browser (Antigravity, Claude, Codex formats)
- Cross-platform terminal support (Unix PTY + Windows ConPTY)
- GitHub Actions CI (lint + test + build on Python 3.10-3.13)
- Terms of Service, Privacy Policy, and CLA
- Contributing guide

### Security
- Bearer token authentication (auto-generated 64-byte)
- X25519 Diffie-Hellman key exchange
- WebSocket ticket-based auth (one-time, 30s TTL, IP-bound)
- Content Security Policy, HSTS, X-Frame-Options headers
- Request body size enforcement
