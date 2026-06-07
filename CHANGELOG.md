# Changelog

All notable changes to CorvusTunnel will be documented in this file.

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
