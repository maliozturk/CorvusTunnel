#!/bin/bash
set -e

# Ensure workspace exists
mkdir -p /workspace

# ── 1. Install AI agents at runtime (not baked into image) ───────────
install_agents() {
    echo "  Installing AI agents..."

    # Antigravity CLI (agy)
    if ! command -v agy &>/dev/null; then
        echo "  → Installing Antigravity CLI..."
        curl -fsSL https://antigravity.google/cli/install.sh | bash 2>/dev/null || true
    fi

    # Codex CLI
    if ! command -v codex &>/dev/null; then
        echo "  → Installing Codex CLI..."
        curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh 2>/dev/null || true
    fi

    # Claude Code
    if ! command -v claude &>/dev/null; then
        echo "  → Installing Claude Code..."
        curl -fsSL https://claude.ai/install.sh | bash 2>/dev/null || true
    fi

    export PATH="/home/corvus/.local/bin:/home/corvus/.codex/bin:${PATH}"
    echo "  Agent install complete."
}

install_agents

# ── 2. Generate ephemeral auth token ─────────────────────────────────
export AGENT_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export ALLOWED_DIRS="${ALLOWED_DIRS:-/workspace}"

# ── 3. Initialize E2E keys (if PyNaCl is available) ──────────────────
python -c "
try:
    from crypto.e2e import get_e2e_crypto
    crypto = get_e2e_crypto()
    if crypto.available:
        print('  E2E encryption: enabled')
    else:
        print('  E2E encryption: disabled (PyNaCl not installed)')
except Exception as e:
    print(f'  E2E encryption: error ({e})')
" 2>/dev/null || true

# ── 4. Validate license (if key is set) ──────────────────────────────
if [ -n "$CORVUS_LICENSE_KEY" ]; then
    python -c "from licensing.validator import validate_or_exit; validate_or_exit()" || exit 1
fi

# ── 5. Start cloudflared Quick Tunnel in background ──────────────────
cloudflared tunnel --url http://localhost:8000 --no-autoupdate 2>/tmp/cloudflared.log &
TUNNEL_PID=$!

# ── 6. Wait for tunnel URL (up to 30s) ──────────────────────────────
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -oP 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

# ── 7. Print QR codes and banner ─────────────────────────────────────
python -c "
import sys
sys.path.insert(0, '/app')
from boot import print_banner
tunnel_url = sys.argv[1] if sys.argv[1] != '' else ''
token = sys.argv[2]
print_banner(tunnel_url, token)
" "${TUNNEL_URL}" "${AGENT_TOKEN}"

# ── 8. Launch CorvusTunnel ───────────────────────────────────────────
exec python /app/main.py
