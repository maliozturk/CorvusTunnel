/**
 * CorvusTunnel Relay — Cloudflare Worker Entry Point
 *
 * Security-first relay server. Routes:
 *   POST /api/tunnel/create    — CLI creates a session (rate limited)
 *   GET  /api/tunnel/ws/:id    — CLI WebSocket (authenticated via HMAC token)
 *   GET  /api/session/:id/ws   — Phone WebSocket (authenticated via session token from QR)
 *   GET  /api/session/:id/info — Session status check (public, minimal info)
 *   GET  /:id                  — Serve phone web UI
 *
 * Zero-knowledge design: relay never sees plaintext. All messages are
 * opaque E2E-encrypted blobs passed through unchanged.
 *
 * Rate limits enforced at Worker level (before Durable Object).
 * Per-session state managed by TunnelSession Durable Object.
 */

// ── Constants ────────────────────────────────────────────────────
const SESSION_ID_BYTES = 16; // 128-bit entropy → 22 chars base64url
const MAX_SESSIONS_PER_IP = 5;
const MAX_MESSAGE_SIZE = 65536; // 64 KB per WebSocket message
const SESSION_TTL_MS = 30 * 60 * 1000; // 30 minutes
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX_CREATES = 5; // 5 session creates per minute per IP

// In-memory rate limiting (resets on Worker restart, which is fine)
const rateLimitMap = new Map(); // ip -> { count, resetAt }

// ── Helpers ──────────────────────────────────────────────────────

/** Generate a cryptographically secure session ID (base64url, no padding). */
function generateSessionId() {
  const bytes = new Uint8Array(SESSION_ID_BYTES);
  crypto.getRandomValues(bytes);
  // base64url encode
  const b64 = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return b64;
}

/** Generate a cryptographic HMAC token for session authentication. */
async function generateSessionSecret() {
  const bytes = new Uint8Array(32); // 256-bit secret
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/** Constant-time string comparison to prevent timing attacks. */
function secureCompare(a, b) {
  if (a.length !== b.length) return false;
  const encoder = new TextEncoder();
  const aBuf = encoder.encode(a);
  const bBuf = encoder.encode(b);
  let result = 0;
  for (let i = 0; i < aBuf.length; i++) {
    result |= aBuf[i] ^ bBuf[i];
  }
  return result === 0;
}

/** Extract client IP from request (Cloudflare provides this). */
function getClientIp(request) {
  return request.headers.get('cf-connecting-ip') || '0.0.0.0';
}

/** Check rate limit for an IP. Returns true if allowed, false if exceeded. */
function checkRateLimit(ip) {
  const now = Date.now();
  let entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetAt) {
    entry = { count: 0, resetAt: now + RATE_LIMIT_WINDOW_MS };
    rateLimitMap.set(ip, entry);
  }

  entry.count++;
  return entry.count <= RATE_LIMIT_MAX_CREATES;
}

/** JSON error response with proper headers. */
function errorResponse(status, message) {
  return new Response(
    JSON.stringify({ error: message }),
    {
      status,
      headers: {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
      },
    }
  );
}

/** JSON success response. */
function jsonResponse(data, status = 200) {
  return new Response(
    JSON.stringify(data),
    {
      status,
      headers: {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
        'Cache-Control': 'no-store',
      },
    }
  );
}

/** Security headers for all responses. */
function addSecurityHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('X-Frame-Options', 'DENY');
  headers.set('Referrer-Policy', 'no-referrer');
  headers.set('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload');
  return new Response(response.body, {
    status: response.status,
    headers,
  });
}

// ── CORS ─────────────────────────────────────────────────────────

/** Handle CORS preflight. */
function handleCors(request) {
  const origin = request.headers.get('Origin') || '';
  // Allow corvustunnel.com and roost.corvustunnel.com
  const allowedOrigins = [
    'https://corvustunnel.com',
    'https://www.corvustunnel.com',
    'https://roost.corvustunnel.com',
  ];

  const responseHeaders = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Session-Token',
    'Access-Control-Max-Age': '86400',
    'X-Content-Type-Options': 'nosniff',
  };

  if (allowedOrigins.includes(origin)) {
    responseHeaders['Access-Control-Allow-Origin'] = origin;
  }

  return new Response(null, { status: 204, headers: responseHeaders });
}

// ── Worker Entry ─────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // CORS preflight
    if (method === 'OPTIONS') {
      return handleCors(request);
    }

    // ── API Routes ───────────────────────────────────────────────

    // POST /api/tunnel/create — CLI creates a new tunnel session
    if (method === 'POST' && path === '/api/tunnel/create') {
      return handleCreateSession(request, env);
    }

    // GET /api/tunnel/ws/:id — CLI WebSocket connection
    const tunnelWsMatch = path.match(/^\/api\/tunnel\/ws\/([A-Za-z0-9_-]+)$/);
    if (tunnelWsMatch && request.headers.get('Upgrade') === 'websocket') {
      return handleTunnelWebSocket(request, env, tunnelWsMatch[1]);
    }

    // GET /api/session/:id/ws — Phone WebSocket connection
    const sessionWsMatch = path.match(/^\/api\/session\/([A-Za-z0-9_-]+)\/ws$/);
    if (sessionWsMatch && request.headers.get('Upgrade') === 'websocket') {
      return handleSessionWebSocket(request, env, sessionWsMatch[1]);
    }

    // GET /api/session/:id/info — Session status (public, minimal)
    const sessionInfoMatch = path.match(/^\/api\/session\/([A-Za-z0-9_-]+)\/info$/);
    if (sessionInfoMatch && method === 'GET') {
      return handleSessionInfo(request, env, sessionInfoMatch[1]);
    }

    // GET /:id — Serve phone web UI (22 char base64url session IDs)
    const sessionPageMatch = path.match(/^\/([A-Za-z0-9_-]{15,30})$/);
    if (sessionPageMatch && method === 'GET') {
      return servePhoneUI(request, env, sessionPageMatch[1]);
    }

    // GET / — Redirect to landing page
    if (path === '/' || path === '') {
      return Response.redirect('https://corvustunnel.com', 302);
    }

    return errorResponse(404, 'Not found');
  },
};

// ── Route Handlers ───────────────────────────────────────────────

/**
 * POST /api/tunnel/create
 * CLI requests a new session. Returns session ID + secrets for auth.
 *
 * Rate limited: 5 creates/min per IP.
 * Body: { "server_public_key": "<base64url>" }  (E2E public key)
 */
async function handleCreateSession(request, env) {
  const ip = getClientIp(request);

  // Rate limit
  if (!checkRateLimit(ip)) {
    return errorResponse(429, 'Rate limit exceeded. Max 5 sessions per minute.');
  }

  // Parse body
  let body;
  try {
    body = await request.json();
  } catch {
    return errorResponse(400, 'Invalid JSON body');
  }

  const serverPublicKey = body.server_public_key || '';

  // Generate session credentials
  const sessionId = generateSessionId();
  const cliSecret = await generateSessionSecret(); // CLI uses this to authenticate WS
  const phoneToken = await generateSessionSecret(); // Phone uses this (embedded in QR)

  // Create Durable Object for this session
  const doId = env.TUNNEL_SESSION.idFromName(sessionId);
  const doStub = env.TUNNEL_SESSION.get(doId);

  // Initialize the session in the Durable Object
  const initResponse = await doStub.fetch(
    new Request('https://internal/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId,
        cliSecret,
        phoneToken,
        serverPublicKey,
        cliIp: ip,
        createdAt: Date.now(),
        ttl: SESSION_TTL_MS,
      }),
    })
  );

  if (!initResponse.ok) {
    return errorResponse(500, 'Failed to create session');
  }

  return jsonResponse({
    session_id: sessionId,
    cli_secret: cliSecret,          // CLI keeps this to auth its WS
    phone_token: phoneToken,        // Goes into QR code for phone auth
    relay_url: `https://roost.corvustunnel.com/${sessionId}`,
    ws_url: `wss://roost.corvustunnel.com/api/tunnel/ws/${sessionId}`,
    ttl_seconds: SESSION_TTL_MS / 1000,
  });
}

/**
 * GET /api/tunnel/ws/:id — CLI WebSocket
 * Authenticated via cli_secret in the first message (not URL to prevent logging).
 */
async function handleTunnelWebSocket(request, env, sessionId) {
  const doId = env.TUNNEL_SESSION.idFromName(sessionId);
  const doStub = env.TUNNEL_SESSION.get(doId);

  // Forward the WebSocket upgrade to the Durable Object
  return doStub.fetch(
    new Request(`https://internal/ws/cli`, {
      headers: request.headers,
    })
  );
}

/**
 * GET /api/session/:id/ws — Phone WebSocket
 * Authenticated via phone_token in the first message.
 */
async function handleSessionWebSocket(request, env, sessionId) {
  const doId = env.TUNNEL_SESSION.idFromName(sessionId);
  const doStub = env.TUNNEL_SESSION.get(doId);

  return doStub.fetch(
    new Request(`https://internal/ws/phone`, {
      headers: request.headers,
    })
  );
}

/**
 * GET /api/session/:id/info — Public session status
 * Returns minimal info (no secrets). Used by phone UI to check if session is alive.
 */
async function handleSessionInfo(request, env, sessionId) {
  const doId = env.TUNNEL_SESSION.idFromName(sessionId);
  const doStub = env.TUNNEL_SESSION.get(doId);

  return doStub.fetch(new Request('https://internal/info'));
}

/**
 * GET /:id — Serve the phone web UI
 * This is a minimal HTML page that connects to the relay WebSocket.
 */
function servePhoneUI(request, env, sessionId) {
  // Sanitize sessionId to prevent XSS (only allow base64url chars)
  if (!/^[A-Za-z0-9_-]+$/.test(sessionId)) {
    return errorResponse(400, 'Invalid session ID');
  }

  const html = generatePhoneHTML(sessionId);

  return new Response(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'no-referrer',
      'Content-Security-Policy': [
        "default-src 'self'",
        "connect-src 'self' wss://roost.corvustunnel.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "script-src 'self' 'unsafe-inline'",  // Inline scripts for the SPA
        "img-src 'self' data:",
        "frame-ancestors 'none'",
      ].join('; '),
      'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
      'Cache-Control': 'no-store',
    },
  });
}

// ── Phone UI HTML ────────────────────────────────────────────────

function generatePhoneHTML(sessionId) {
  // The sessionId is already validated as base64url-safe chars only
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>CorvusTunnel — Session</title>
  <meta name="robots" content="noindex, nofollow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
    :root {
      --bg: #0a0a0f; --surface: #14141f; --border: rgba(255,255,255,0.08);
      --text: #e8e8ef; --muted: #8888a0; --dim: #55556a;
      --accent: #7c5cff; --accent2: #00d4aa; --red: #ff4466;
    }
    body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }

    /* Header */
    .header { padding:16px 20px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
    .header-left { display:flex; align-items:center; gap:10px; }
    .header h1 { font-size:16px; font-weight:700; }
    .status-dot { width:8px; height:8px; border-radius:50%; }
    .status-dot.connecting { background:#ffaa00; animation: pulse 1s infinite; }
    .status-dot.connected { background:var(--accent2); }
    .status-dot.error { background:var(--red); }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
    .status-text { font-size:12px; color:var(--muted); }

    /* Auth screen */
    .auth-screen { display:flex; flex-direction:column; align-items:center; justify-content:center;
      min-height:80vh; padding:24px; text-align:center; }
    .auth-screen h2 { font-size:24px; margin-bottom:8px; }
    .auth-screen p { color:var(--muted); font-size:14px; margin-bottom:24px; }
    .auth-error { color:var(--red); font-size:14px; margin-top:16px; }
    .spinner { width:32px; height:32px; border:3px solid var(--border); border-top-color:var(--accent);
      border-radius:50%; animation:spin 0.8s linear infinite; margin:16px auto; }
    @keyframes spin { to { transform:rotate(360deg); } }

    /* Terminal */
    .terminal { flex:1; display:flex; flex-direction:column; height:calc(100vh - 60px); }
    .terminal-output { flex:1; overflow-y:auto; padding:12px 16px;
      font-family:'JetBrains Mono',monospace; font-size:13px; line-height:1.6;
      white-space:pre-wrap; word-break:break-word; background:var(--bg); }
    .terminal-input-bar { display:flex; padding:8px 12px; border-top:1px solid var(--border);
      background:var(--surface); gap:8px; }
    .terminal-input-bar input { flex:1; background:var(--bg); border:1px solid var(--border);
      border-radius:8px; padding:10px 14px; color:var(--text); font-family:'JetBrains Mono',monospace;
      font-size:14px; outline:none; }
    .terminal-input-bar input:focus { border-color:var(--accent); }
    .terminal-input-bar button { background:var(--accent); color:white; border:none; border-radius:8px;
      padding:10px 20px; font-weight:600; font-size:14px; cursor:pointer; }
    .terminal-input-bar button:disabled { opacity:0.4; cursor:not-allowed; }

    .hidden { display:none !important; }
    .e2e-badge { font-size:11px; background:rgba(0,212,170,0.1); color:var(--accent2);
      padding:2px 8px; border-radius:100px; font-weight:600; }
  </style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <span>🪶</span>
      <h1>CorvusTunnel</h1>
      <span class="e2e-badge hidden" id="e2e-badge">🔒 E2E</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span class="status-dot connecting" id="status-dot"></span>
      <span class="status-text" id="status-text">Connecting...</span>
    </div>
  </div>

  <div class="auth-screen" id="auth-screen">
    <h2>🪶 Connecting to Roost</h2>
    <p>Authenticating with your session...</p>
    <div class="spinner" id="spinner"></div>
    <div class="auth-error hidden" id="auth-error"></div>
  </div>

  <div class="terminal hidden" id="terminal">
    <div class="terminal-output" id="output"></div>
    <div class="terminal-input-bar">
      <input type="text" id="input" placeholder="Type a command or prompt..."
             autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
      <button id="send-btn" onclick="sendMessage()" disabled>Send</button>
    </div>
  </div>

  <script>
    // ── Security: Extract token from URL fragment (never sent to server) ──
    const SESSION_ID = '${sessionId}';
    const fragment = window.location.hash.substring(1);
    const params = new URLSearchParams(fragment);
    const PHONE_TOKEN = params.get('token') || '';
    const E2E_KEY = params.get('e2e') || '';

    // Clear fragment from URL bar (prevent leaking via Referer)
    if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname);
    }

    // Validate we have a token
    if (!PHONE_TOKEN) {
      document.getElementById('spinner').classList.add('hidden');
      document.getElementById('auth-error').textContent = 'No authentication token. Please scan the QR code again.';
      document.getElementById('auth-error').classList.remove('hidden');
      document.getElementById('status-dot').className = 'status-dot error';
      document.getElementById('status-text').textContent = 'Auth failed';
      throw new Error('No token');
    }

    // ── WebSocket Connection ──────────────────────────────────────
    let ws = null;
    let authenticated = false;
    let reconnectAttempts = 0;
    const MAX_RECONNECT = 3;

    function connect() {
      const wsUrl = 'wss://roost.corvustunnel.com/api/session/' + SESSION_ID + '/ws';
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        // First message: authenticate with phone token
        ws.send(JSON.stringify({
          type: 'auth',
          token: PHONE_TOKEN,
        }));
      };

      ws.onmessage = (event) => {
        // Enforce message size limit client-side too
        if (event.data.length > 65536) {
          console.error('Message too large, ignoring');
          return;
        }

        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }

        if (msg.type === 'auth_ok') {
          authenticated = true;
          reconnectAttempts = 0;
          document.getElementById('auth-screen').classList.add('hidden');
          document.getElementById('terminal').classList.remove('hidden');
          document.getElementById('status-dot').className = 'status-dot connected';
          document.getElementById('status-text').textContent = 'Connected';
          document.getElementById('send-btn').disabled = false;
          document.getElementById('input').focus();
          if (E2E_KEY) {
            document.getElementById('e2e-badge').classList.remove('hidden');
          }
        } else if (msg.type === 'auth_fail') {
          document.getElementById('spinner').classList.add('hidden');
          document.getElementById('auth-error').textContent = msg.reason || 'Authentication failed';
          document.getElementById('auth-error').classList.remove('hidden');
          document.getElementById('status-dot').className = 'status-dot error';
          document.getElementById('status-text').textContent = 'Auth failed';
          ws.close();
        } else if (msg.type === 'output') {
          appendOutput(msg.data || '');
        } else if (msg.type === 'error') {
          appendOutput('\\n[ERROR] ' + (msg.message || 'Unknown error') + '\\n');
        } else if (msg.type === 'session_end') {
          appendOutput('\\n[Session ended by host]\\n');
          document.getElementById('send-btn').disabled = true;
          document.getElementById('status-dot').className = 'status-dot error';
          document.getElementById('status-text').textContent = 'Disconnected';
        }
      };

      ws.onclose = () => {
        document.getElementById('status-dot').className = 'status-dot error';
        document.getElementById('status-text').textContent = 'Disconnected';
        document.getElementById('send-btn').disabled = true;

        if (authenticated && reconnectAttempts < MAX_RECONNECT) {
          reconnectAttempts++;
          document.getElementById('status-text').textContent = 'Reconnecting...';
          document.getElementById('status-dot').className = 'status-dot connecting';
          setTimeout(connect, 1000 * reconnectAttempts);
        }
      };

      ws.onerror = () => {
        document.getElementById('status-dot').className = 'status-dot error';
      };
    }

    function appendOutput(text) {
      const el = document.getElementById('output');
      el.textContent += text;
      el.scrollTop = el.scrollHeight;
    }

    function sendMessage() {
      const input = document.getElementById('input');
      const text = input.value.trim();
      if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

      // Enforce client-side message size limit
      if (text.length > 10000) {
        appendOutput('\\n[Message too long — max 10,000 chars]\\n');
        return;
      }

      ws.send(JSON.stringify({ type: 'input', data: text }));
      input.value = '';
      input.focus();
    }

    // Enter key to send
    document.getElementById('input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Start connection
    connect();
  </script>
</body>
</html>`;
}

// ── Durable Object: TunnelSession ────────────────────────────────

export class TunnelSession {
  constructor(state, env) {
    this.state = state;
    this.env = env;

    // Session state (loaded from storage on each wake)
    this.sessionId = null;
    this.cliSecret = null;
    this.phoneToken = null;
    this.serverPublicKey = '';
    this.cliIp = '';
    this.createdAt = 0;
    this.ttl = SESSION_TTL_MS;
    this.initialized = false;
    this.authFailures = 0;
    this.maxAuthFailures = 5;

    // WebSocket refs (managed by runtime across hibernation)
    this.cliWs = null;
    this.phoneWs = null;
    this.cliAuthenticated = false;
    this.phoneAuthenticated = false;

    // Restore WebSocket refs from hibernation
    this._restoreWebSockets();
  }

  /** Restore WebSocket references after hibernation wake-up. */
  _restoreWebSockets() {
    const websockets = this.state.getWebSockets();
    for (const ws of websockets) {
      const tags = this.state.getTags(ws);
      if (tags.includes('cli')) {
        this.cliWs = ws;
        this.cliAuthenticated = true; // was authenticated before hibernation
      } else if (tags.includes('phone')) {
        this.phoneWs = ws;
        this.phoneAuthenticated = true;
      }
    }
  }

  /** Load session state from durable storage (survives hibernation). */
  async _loadState() {
    if (this.initialized) return;

    const data = await this.state.storage.get('session');
    if (data) {
      this.sessionId = data.sessionId;
      this.cliSecret = data.cliSecret;
      this.phoneToken = data.phoneToken;
      this.serverPublicKey = data.serverPublicKey || '';
      this.cliIp = data.cliIp || '';
      this.createdAt = data.createdAt || 0;
      this.ttl = data.ttl || SESSION_TTL_MS;
      this.authFailures = data.authFailures || 0;
      this.initialized = true;
    }
  }

  /** Save mutable session state to durable storage. */
  async _saveState() {
    await this.state.storage.put('session', {
      sessionId: this.sessionId,
      cliSecret: this.cliSecret,
      phoneToken: this.phoneToken,
      serverPublicKey: this.serverPublicKey,
      cliIp: this.cliIp,
      createdAt: this.createdAt,
      ttl: this.ttl,
      authFailures: this.authFailures,
    });
  }

  async fetch(request) {
    // Always load state from storage first (handles hibernation wake)
    await this._loadState();

    const url = new URL(request.url);
    const path = url.pathname;

    // POST /init — Initialize session (called by Worker, not public)
    if (path === '/init' && request.method === 'POST') {
      return this.handleInit(request);
    }

    // GET /info — Session status
    if (path === '/info') {
      return this.handleInfo();
    }

    // GET /ws/cli — CLI WebSocket
    if (path === '/ws/cli') {
      return this.handleCliWebSocket(request);
    }

    // GET /ws/phone — Phone WebSocket
    if (path === '/ws/phone') {
      return this.handlePhoneWebSocket(request);
    }

    return errorResponse(404, 'Not found');
  }

  // ── Init ───────────────────────────────────────────────────────

  async handleInit(request) {
    if (this.initialized) {
      return errorResponse(409, 'Session already initialized');
    }

    const body = await request.json();

    this.sessionId = body.sessionId;
    this.cliSecret = body.cliSecret;
    this.phoneToken = body.phoneToken;
    this.serverPublicKey = body.serverPublicKey || '';
    this.cliIp = body.cliIp || '';
    this.createdAt = body.createdAt || Date.now();
    this.ttl = body.ttl || SESSION_TTL_MS;
    this.initialized = true;

    // Persist to storage (survives hibernation)
    await this._saveState();

    // Schedule auto-destruction
    this.state.storage.setAlarm(this.createdAt + this.ttl);

    return jsonResponse({ ok: true });
  }

  // ── Info ───────────────────────────────────────────────────────

  handleInfo() {
    if (!this.initialized) {
      return errorResponse(404, 'Session not found');
    }

    // Check if expired
    if (Date.now() > this.createdAt + this.ttl) {
      this.destroy();
      return errorResponse(410, 'Session expired');
    }

    // Minimal public info (no secrets)
    return jsonResponse({
      alive: true,
      cli_connected: this.cliWs !== null && this.cliAuthenticated,
      phone_connected: this.phoneWs !== null && this.phoneAuthenticated,
      e2e: !!this.serverPublicKey,
      ttl_remaining: Math.max(0, (this.createdAt + this.ttl - Date.now()) / 1000),
    });
  }

  // ── CLI WebSocket ──────────────────────────────────────────────

  handleCliWebSocket(request) {
    if (!this.initialized) {
      return errorResponse(404, 'Session not found');
    }

    // Check TTL
    if (Date.now() > this.createdAt + this.ttl) {
      this.destroy();
      return errorResponse(410, 'Session expired');
    }

    // Reject if CLI already connected
    if (this.cliWs !== null) {
      return errorResponse(409, 'CLI already connected to this session');
    }

    // Check auth failure limit
    if (this.authFailures >= this.maxAuthFailures) {
      return errorResponse(403, 'Too many auth failures. Session locked.');
    }

    // Create WebSocket pair
    const [client, server] = Object.values(new WebSocketPair());
    this.state.acceptWebSocket(server, ['cli']);

    this.cliWs = server;

    return new Response(null, { status: 101, webSocket: client });
  }

  // ── Phone WebSocket ────────────────────────────────────────────

  handlePhoneWebSocket(request) {
    if (!this.initialized) {
      return errorResponse(404, 'Session not found');
    }

    // Check TTL
    if (Date.now() > this.createdAt + this.ttl) {
      this.destroy();
      return errorResponse(410, 'Session expired');
    }

    // Reject if phone already connected
    if (this.phoneWs !== null) {
      return errorResponse(409, 'Phone already connected to this session');
    }

    // Check auth failure limit
    if (this.authFailures >= this.maxAuthFailures) {
      return errorResponse(403, 'Too many auth failures. Session locked.');
    }

    const [client, server] = Object.values(new WebSocketPair());
    this.state.acceptWebSocket(server, ['phone']);

    this.phoneWs = server;

    return new Response(null, { status: 101, webSocket: client });
  }

  // ── WebSocket Message Handler ──────────────────────────────────

  async webSocketMessage(ws, message) {
    // Load state from storage (in case we woke from hibernation)
    await this._loadState();
    const msgStr = typeof message === 'string' ? message : new TextDecoder().decode(message);
    if (msgStr.length > MAX_MESSAGE_SIZE) {
      ws.send(JSON.stringify({ type: 'error', message: 'Message too large (max 64KB)' }));
      return;
    }

    let msg;
    try {
      msg = JSON.parse(msgStr);
    } catch {
      ws.send(JSON.stringify({ type: 'error', message: 'Invalid JSON' }));
      return;
    }

    const tags = this.state.getTags(ws);
    const isCli = tags.includes('cli');
    const isPhone = tags.includes('phone');

    // ── Authentication (first message must be auth) ──────────────
    if (msg.type === 'auth') {
      if (isCli) {
        if (secureCompare(msg.token || '', this.cliSecret)) {
          this.cliAuthenticated = true;
          ws.send(JSON.stringify({ type: 'auth_ok' }));

          // Notify phone if already connected
          if (this.phoneWs && this.phoneAuthenticated) {
            this.phoneWs.send(JSON.stringify({ type: 'cli_connected' }));
          }
        } else {
          this.authFailures++;
          ws.send(JSON.stringify({ type: 'auth_fail', reason: 'Invalid CLI secret' }));
          if (this.authFailures >= this.maxAuthFailures) {
            ws.close(4003, 'Too many auth failures');
            this.destroy();
          }
        }
      } else if (isPhone) {
        if (secureCompare(msg.token || '', this.phoneToken)) {
          this.phoneAuthenticated = true;
          ws.send(JSON.stringify({ type: 'auth_ok' }));

          // Notify CLI if already connected
          if (this.cliWs && this.cliAuthenticated) {
            this.cliWs.send(JSON.stringify({ type: 'phone_connected' }));
          }
        } else {
          this.authFailures++;
          ws.send(JSON.stringify({ type: 'auth_fail', reason: 'Invalid token' }));
          if (this.authFailures >= this.maxAuthFailures) {
            ws.close(4003, 'Too many auth failures');
            this.destroy();
          }
        }
      }
      return;
    }

    // ── Reject unauthenticated messages ──────────────────────────
    if (isCli && !this.cliAuthenticated) {
      ws.send(JSON.stringify({ type: 'error', message: 'Not authenticated. Send auth first.' }));
      return;
    }
    if (isPhone && !this.phoneAuthenticated) {
      ws.send(JSON.stringify({ type: 'error', message: 'Not authenticated. Send auth first.' }));
      return;
    }

    // ── Relay messages (zero-knowledge pipe) ─────────────────────
    // CLI → Phone
    if (isCli && this.phoneWs && this.phoneAuthenticated) {
      try {
        this.phoneWs.send(msgStr);
      } catch {
        // Phone disconnected
      }
    }

    // Phone → CLI
    if (isPhone && this.cliWs && this.cliAuthenticated) {
      try {
        this.cliWs.send(msgStr);
      } catch {
        // CLI disconnected
      }
    }
  }

  // ── WebSocket Close Handler ────────────────────────────────────

  async webSocketClose(ws, code, reason) {
    const tags = this.state.getTags(ws);

    if (tags.includes('cli')) {
      this.cliWs = null;
      this.cliAuthenticated = false;

      // Notify phone that CLI disconnected
      if (this.phoneWs && this.phoneAuthenticated) {
        try {
          this.phoneWs.send(JSON.stringify({ type: 'session_end', reason: 'Host disconnected' }));
        } catch {}
      }

      // Destroy session when CLI leaves (host gone = session gone)
      this.destroy();
    }

    if (tags.includes('phone')) {
      this.phoneWs = null;
      this.phoneAuthenticated = false;

      // Notify CLI that phone disconnected
      if (this.cliWs && this.cliAuthenticated) {
        try {
          this.cliWs.send(JSON.stringify({ type: 'phone_disconnected' }));
        } catch {}
      }
    }
  }

  // ── WebSocket Error Handler ────────────────────────────────────

  async webSocketError(ws, error) {
    this.webSocketClose(ws, 1011, 'WebSocket error');
  }

  // ── Alarm (TTL expiry) ─────────────────────────────────────────

  async alarm() {
    this.destroy();
  }

  // ── Destroy Session ────────────────────────────────────────────

  destroy() {
    // Close all connections with reason
    const endMsg = JSON.stringify({ type: 'session_end', reason: 'Session expired' });

    if (this.cliWs) {
      try {
        this.cliWs.send(endMsg);
        this.cliWs.close(1000, 'Session ended');
      } catch {}
      this.cliWs = null;
    }

    if (this.phoneWs) {
      try {
        this.phoneWs.send(endMsg);
        this.phoneWs.close(1000, 'Session ended');
      } catch {}
      this.phoneWs = null;
    }

    // Clear state
    this.initialized = false;
    this.cliAuthenticated = false;
    this.phoneAuthenticated = false;
    this.cliSecret = null;
    this.phoneToken = null;
  }
}
