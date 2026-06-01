#!/bin/bash
set -e

# Ensure workspace exists
mkdir -p /workspace

# 1. Generate ephemeral auth token
export AGENT_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export ALLOWED_DIRS="${ALLOWED_DIRS:-/workspace}"

# 2. Validate license (if key is set)
if [ -n "$CORVUS_LICENSE_KEY" ]; then
    python -c "from licensing.validator import validate_or_exit; validate_or_exit()" || exit 1
fi

# 2. Start cloudflared Quick Tunnel in background
cloudflared tunnel --url http://localhost:8000 --no-autoupdate 2>/tmp/cloudflared.log &
TUNNEL_PID=$!

# 3. Wait for tunnel URL (up to 30s)
TUNNEL_URL=""
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -oP 'https://[a-zA-Z0-9\-]+\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

# 4. Print QR codes and banner
python -c "
import sys
sys.path.insert(0, '/app')
from boot import print_banner
tunnel_url = sys.argv[1] if sys.argv[1] != '' else ''
token = sys.argv[2]
print_banner(tunnel_url, token)
" "${TUNNEL_URL}" "${AGENT_TOKEN}"

# 5. Launch CorvusTunnel (replaces this shell, cloudflared stays as background process)
exec python /app/main.py
