/**
 * CorvusTunnel Relay — Cloudflare Worker
 *
 * Transparent HTTP proxy over WebSocket. Routes:
 *   POST /api/tunnel/create    — CLI creates a session
 *   GET  /api/tunnel/ws/:id    — CLI WebSocket (authenticated)
 *   GET  /:id/*                — HTTP proxy (phone → CLI → localhost)
 *   WS   /:id/*                — WebSocket proxy (phone terminal → CLI → localhost)
 *
 * Zero-knowledge design: relay never reads content. HTML rewriting is
 * done CLI-side so the relay sees only opaque bytes.
 */

// ── Constants ────────────────────────────────────────────────────
const SESSION_ID_BYTES = 16;
const MAX_MESSAGE_SIZE = 1_048_576; // 1 MB (increased for HTML proxying)
const SESSION_TTL_MS = 2 * 60 * 60 * 1000; // 2 hours
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX_CREATES = 5;

const rateLimitMap = new Map();

// ── Helpers ──────────────────────────────────────────────────────

function generateId(bytes = SESSION_ID_BYTES) {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return btoa(String.fromCharCode(...buf))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function secureCompare(a, b) {
  if (a.length !== b.length) return false;
  const enc = new TextEncoder();
  const ab = enc.encode(a), bb = enc.encode(b);
  let r = 0;
  for (let i = 0; i < ab.length; i++) r |= ab[i] ^ bb[i];
  return r === 0;
}

function getClientIp(req) {
  return req.headers.get('cf-connecting-ip') || '0.0.0.0';
}

function checkRateLimit(ip) {
  const now = Date.now();
  let e = rateLimitMap.get(ip);
  if (!e || now > e.resetAt) { e = { count: 0, resetAt: now + RATE_LIMIT_WINDOW_MS }; rateLimitMap.set(ip, e); }
  return ++e.count <= RATE_LIMIT_MAX_CREATES;
}

function errRes(status, msg) {
  return new Response(JSON.stringify({ error: msg }), {
    status, headers: { 'Content-Type': 'application/json', 'X-Content-Type-Options': 'nosniff' },
  });
}

function jsonRes(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}

function handleCors(req) {
  const origin = req.headers.get('Origin') || '';
  const allowed = ['https://corvustunnel.com', 'https://www.corvustunnel.com', 'https://roost.corvustunnel.com'];
  const h = { 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Authorization', 'Access-Control-Max-Age': '86400' };
  if (allowed.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return new Response(null, { status: 204, headers: h });
}

// ── Worker Entry ─────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') return handleCors(request);

    // POST /api/tunnel/create — CLI creates a session
    if (request.method === 'POST' && path === '/api/tunnel/create') {
      return handleCreate(request, env);
    }

    // GET /api/tunnel/ws/:id — CLI WebSocket
    const cliWsMatch = path.match(/^\/api\/tunnel\/ws\/([A-Za-z0-9_-]+)$/);
    if (cliWsMatch && request.headers.get('Upgrade') === 'websocket') {
      const doId = env.TUNNEL_SESSION.idFromName(cliWsMatch[1]);
      return env.TUNNEL_SESSION.get(doId).fetch(
        new Request('https://internal/ws/cli', { headers: request.headers })
      );
    }

    // GET / — redirect to landing page
    if (path === '/' || path === '') {
      return Response.redirect('https://corvustunnel.com', 302);
    }

    // /<session_id>/* — proxy to CLI via Durable Object
    const proxyMatch = path.match(/^\/([A-Za-z0-9_-]{15,30})(\/.*)?$/);
    if (proxyMatch) {
      const sessionId = proxyMatch[1];
      const proxyPath = proxyMatch[2] || '/';
      const doId = env.TUNNEL_SESSION.idFromName(sessionId);
      const stub = env.TUNNEL_SESSION.get(doId);

      // WebSocket upgrade → WS proxy
      if (request.headers.get('Upgrade') === 'websocket') {
        const wsProxyUrl = new URL('https://internal/proxy-ws');
        wsProxyUrl.searchParams.set('path', proxyPath);
        wsProxyUrl.searchParams.set('query', url.search.substring(1));
        return stub.fetch(new Request(wsProxyUrl.toString(), { headers: request.headers }));
      }

      // HTTP → proxy
      return stub.fetch(new Request(`https://internal/proxy${proxyPath}${url.search}`, {
        method: request.method,
        headers: request.headers,
        body: request.body,
      }));
    }

    return errRes(404, 'Not found');
  },
};

// ── Session Creation ─────────────────────────────────────────────

async function handleCreate(request, env) {
  const ip = getClientIp(request);
  if (!checkRateLimit(ip)) return errRes(429, 'Rate limit exceeded');

  let body;
  try { body = await request.json(); } catch { return errRes(400, 'Invalid JSON'); }

  const sessionId = generateId();
  const cliSecret = generateId(32);

  const doId = env.TUNNEL_SESSION.idFromName(sessionId);
  const stub = env.TUNNEL_SESSION.get(doId);

  const init = await stub.fetch(new Request('https://internal/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId,
      cliSecret,
      serverPublicKey: body.server_public_key || '',
      cliIp: ip,
      createdAt: Date.now(),
      ttl: SESSION_TTL_MS,
    }),
  }));

  if (!init.ok) return errRes(500, 'Failed to create session');

  return jsonRes({
    session_id: sessionId,
    cli_secret: cliSecret,
    relay_url: `https://roost.corvustunnel.com/${sessionId}`,
    ws_url: `wss://roost.corvustunnel.com/api/tunnel/ws/${sessionId}`,
    ttl_seconds: SESSION_TTL_MS / 1000,
  });
}

// ── Durable Object: TunnelSession ────────────────────────────────

export class TunnelSession {
  constructor(state, env) {
    this.state = state;
    this.env = env;

    // Persisted session data (loaded from storage)
    this.sessionId = null;
    this.cliSecret = null;
    this.createdAt = 0;
    this.ttl = SESSION_TTL_MS;
    this.initialized = false;
    this.authFailures = 0;

    // Runtime (not persisted)
    this.cliWs = null;
    this.cliAuthenticated = false;
    this.phoneWs = null;
    this._pending = new Map(); // reqId → { resolve, timeout }

    this._restoreWs();
  }

  /** Restore WebSocket refs after hibernation. */
  _restoreWs() {
    for (const ws of this.state.getWebSockets()) {
      const tags = this.state.getTags(ws);
      if (tags.includes('cli'))      { this.cliWs = ws; this.cliAuthenticated = true; }
      if (tags.includes('phone_ws')) { this.phoneWs = ws; }
    }
  }

  async _load() {
    if (this.initialized) return;
    const d = await this.state.storage.get('session');
    if (d) {
      this.sessionId = d.sessionId;
      this.cliSecret = d.cliSecret;
      this.createdAt = d.createdAt;
      this.ttl = d.ttl;
      this.authFailures = d.authFailures || 0;
      this.initialized = true;
    }
  }

  async _save() {
    await this.state.storage.put('session', {
      sessionId: this.sessionId,
      cliSecret: this.cliSecret,
      createdAt: this.createdAt,
      ttl: this.ttl,
      authFailures: this.authFailures,
    });
  }

  // ── Fetch Router ─────────────────────────────────────────────

  async fetch(request) {
    await this._load();
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === '/init' && request.method === 'POST') return this._handleInit(request);
    if (path === '/ws/cli') return this._handleCliWs(request);
    if (path === '/proxy-ws') return this._handleWsProxy(request, url);
    if (path.startsWith('/proxy')) return this._handleHttpProxy(request, path.substring(6) || '/');

    return errRes(404, 'Not found');
  }

  // ── Init ─────────────────────────────────────────────────────

  async _handleInit(request) {
    if (this.initialized) return errRes(409, 'Already initialized');
    const b = await request.json();
    this.sessionId = b.sessionId;
    this.cliSecret = b.cliSecret;
    this.createdAt = b.createdAt || Date.now();
    this.ttl = b.ttl || SESSION_TTL_MS;
    this.initialized = true;
    await this._save();
    this.state.storage.setAlarm(this.createdAt + this.ttl);
    return jsonRes({ ok: true });
  }

  // ── CLI WebSocket ────────────────────────────────────────────

  _handleCliWs(request) {
    if (!this.initialized) return errRes(404, 'Session not found');
    if (Date.now() > this.createdAt + this.ttl) { this._destroy(); return errRes(410, 'Expired'); }
    if (this.cliWs) return errRes(409, 'CLI already connected');
    if (this.authFailures >= 5) return errRes(403, 'Session locked');

    const [client, server] = Object.values(new WebSocketPair());
    this.state.acceptWebSocket(server, ['cli']);
    this.cliWs = server;
    return new Response(null, { status: 101, webSocket: client });
  }

  // ── HTTP Proxy ───────────────────────────────────────────────

  async _handleHttpProxy(request, proxyPath) {
    if (!this.cliWs || !this.cliAuthenticated) {
      return errRes(503, 'CLI not connected — start corvustunnel on your machine');
    }
    if (Date.now() > this.createdAt + this.ttl) { this._destroy(); return errRes(410, 'Expired'); }

    const reqId = crypto.randomUUID();
    const url = new URL(request.url);
    const fullPath = proxyPath + url.search; // include query string (?path=..., etc.)

    // Read body for non-GET/HEAD
    let body = null;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try { body = await request.text(); } catch { body = null; }
    }

    // Forward a subset of headers
    const fwd = {};
    for (const key of ['content-type', 'authorization', 'accept', 'cookie', 'user-agent']) {
      const v = request.headers.get(key);
      if (v) fwd[key] = v;
    }

    this.cliWs.send(JSON.stringify({
      type: 'http_req', id: reqId,
      method: request.method, path: fullPath, headers: fwd, body,
    }));

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        this._pending.delete(reqId);
        resolve(errRes(504, 'Gateway timeout — CLI did not respond'));
      }, 30_000);
      this._pending.set(reqId, { resolve, timeout });
    });
  }

  // ── WebSocket Proxy ──────────────────────────────────────────

  _handleWsProxy(request, url) {
    if (!this.cliWs || !this.cliAuthenticated) return errRes(503, 'CLI not connected');

    // Close previous phone WS if reconnecting (don't reject)
    if (this.phoneWs) {
      try { this.phoneWs.close(1000, 'Replaced by new connection'); } catch {}
      this.phoneWs = null;
      // Tell CLI to close old local WS before opening new one
      this.cliWs.send(JSON.stringify({ type: 'ws_close' }));
    }

    const proxyPath = url.searchParams.get('path') || '/api/terminal/ws';
    const proxyQuery = url.searchParams.get('query') || '';

    const [client, server] = Object.values(new WebSocketPair());
    this.state.acceptWebSocket(server, ['phone_ws']);
    this.phoneWs = server;

    // Tell CLI to open a local WebSocket
    this.cliWs.send(JSON.stringify({
      type: 'ws_open',
      path: proxyPath + (proxyQuery ? '?' + proxyQuery : ''),
    }));

    return new Response(null, { status: 101, webSocket: client });
  }

  // ── WebSocket Message Handler ────────────────────────────────

  async webSocketMessage(ws, message) {
    await this._load();

    const raw = typeof message === 'string' ? message : new TextDecoder().decode(message);
    if (raw.length > MAX_MESSAGE_SIZE) return;

    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    const tags = this.state.getTags(ws);
    const isCli = tags.includes('cli');
    const isPhone = tags.includes('phone_ws');

    // ── CLI auth ──
    if (msg.type === 'auth' && isCli) {
      if (secureCompare(msg.token || '', this.cliSecret)) {
        this.cliAuthenticated = true;
        ws.send(JSON.stringify({ type: 'auth_ok' }));
      } else {
        this.authFailures++;
        await this._save();
        ws.send(JSON.stringify({ type: 'auth_fail' }));
        if (this.authFailures >= 5) { ws.close(4003, 'Locked'); this._destroy(); }
      }
      return;
    }

    // ── HTTP response from CLI ──
    if (msg.type === 'http_res' && isCli) {
      const p = this._pending.get(msg.id);
      if (p) {
        clearTimeout(p.timeout);
        this._pending.delete(msg.id);

        const headers = new Headers(msg.headers || {});
        headers.delete('transfer-encoding');

        let body = msg.body ?? null;
        if (msg.encoding === 'base64' && body) {
          body = Uint8Array.from(atob(body), c => c.charCodeAt(0));
        }

        p.resolve(new Response(body, { status: msg.status || 200, headers }));
      }
      return;
    }

    // ── WS forward: CLI → phone ──
    if (msg.type === 'ws_fwd' && isCli) {
      if (this.phoneWs) try { this.phoneWs.send(msg.data); } catch {}
      return;
    }

    // ── WS forward: phone → CLI ──
    if (isPhone) {
      if (this.cliWs && this.cliAuthenticated) {
        this.cliWs.send(JSON.stringify({ type: 'ws_fwd', data: raw }));
      }
      return;
    }
  }

  webSocketClose(ws) {
    const tags = this.state.getTags(ws);
    if (tags.includes('cli')) {
      this.cliWs = null;
      this.cliAuthenticated = false;
      if (this.phoneWs) try { this.phoneWs.close(1001, 'CLI disconnected'); } catch {}
      this.phoneWs = null;
      for (const [, p] of this._pending) { clearTimeout(p.timeout); p.resolve(errRes(503, 'CLI disconnected')); }
      this._pending.clear();
    }
    if (tags.includes('phone_ws')) {
      this.phoneWs = null;
      if (this.cliWs && this.cliAuthenticated) {
        this.cliWs.send(JSON.stringify({ type: 'ws_close' }));
      }
    }
  }

  webSocketError(ws) { this.webSocketClose(ws); }

  async alarm() { this._destroy(); }

  _destroy() {
    if (this.cliWs) try { this.cliWs.close(1000, 'Session expired'); } catch {}
    if (this.phoneWs) try { this.phoneWs.close(1000, 'Session expired'); } catch {}
    this.state.storage.deleteAll();
  }
}
