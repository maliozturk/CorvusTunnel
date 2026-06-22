// CorvusTunnel relay — a zero-knowledge transport.
//
// The relay pairs the host's CLI socket with the browser socket for a session
// and forwards opaque frames between them. All traffic is end-to-end encrypted
// and authenticated by the two endpoints, so the relay never sees plaintext,
// cannot read the session, and cannot tamper without detection. A Durable
// Object per session holds the two hibernatable sockets; a per-session HMAC
// secret stops a stranger attaching as the host.

export interface Env {
  TUNNEL: DurableObjectNamespace;
  RELAY_SECRET: string;
}

const CONTINENT_TO_HINT: Record<string, DurableObjectLocationHint> = {
  NA: "enam",
  EU: "weur",
  AS: "apac",
  SA: "sam",
  OC: "oc",
  AF: "afr",
};

function b64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function randomToken(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return b64url(bytes);
}

async function hmac(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return b64url(new Uint8Array(sig));
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return new Response("ok", { headers: { "content-type": "text/plain" } });
    }

    if (request.method === "POST" && url.pathname === "/api/tunnel/create") {
      const sessionId = randomToken(18);
      const cliSecret = await hmac(env.RELAY_SECRET, sessionId);
      const continent = (request.cf?.continent as string) || "";
      const hint = CONTINENT_TO_HINT[continent];

      const id = env.TUNNEL.idFromName(sessionId);
      const stub = hint ? env.TUNNEL.get(id, { locationHint: hint }) : env.TUNNEL.get(id);
      await stub.fetch("https://relay.internal/init");

      const host = url.host;
      return Response.json({
        session_id: sessionId,
        cli_secret: cliSecret,
        ws_cli: `wss://${host}/s/${sessionId}/cli?k=${cliSecret}`,
        ws_browser: `wss://${host}/s/${sessionId}/browser`,
      });
    }

    const match = url.pathname.match(/^\/s\/([A-Za-z0-9_-]{8,64})\/(cli|browser)$/);
    if (match) {
      const sessionId = match[1];
      const role = match[2];

      if (role === "cli") {
        const presented = url.searchParams.get("k") || "";
        const expected = await hmac(env.RELAY_SECRET, sessionId);
        if (!timingSafeEqual(presented, expected)) {
          return new Response("unauthorized", { status: 401 });
        }
      }

      const id = env.TUNNEL.idFromName(sessionId);
      return env.TUNNEL.get(id).fetch(request);
    }

    return new Response("not found", { status: 404 });
  },
};

export class TunnelSession {
  private ctx: DurableObjectState;

  constructor(ctx: DurableObjectState, _env: Env) {
    this.ctx = ctx;
    this.ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/init") {
      return new Response("ok");
    }

    const match = url.pathname.match(/\/(cli|browser)$/);
    const role = match ? match[1] : "";
    if (request.headers.get("Upgrade") !== "websocket" || !role) {
      return new Response("expected websocket", { status: 400 });
    }

    for (const existing of this.ctx.getWebSockets(role)) {
      try {
        existing.close(4000, "replaced");
      } catch {}
    }

    const pair = new WebSocketPair();
    const client = pair[0];
    const server = pair[1];
    this.ctx.acceptWebSocket(server, [role]);

    return new Response(null, { status: 101, webSocket: client });
  }

  private peerRole(ws: WebSocket): string {
    const tags = this.ctx.getTags(ws);
    return tags[0] === "cli" ? "browser" : "cli";
  }

  async webSocketMessage(ws: WebSocket, message: ArrayBuffer | string): Promise<void> {
    for (const peer of this.ctx.getWebSockets(this.peerRole(ws))) {
      try {
        peer.send(message);
      } catch {}
    }
  }

  async webSocketClose(ws: WebSocket): Promise<void> {
    for (const peer of this.ctx.getWebSockets(this.peerRole(ws))) {
      try {
        peer.close(1000, "peer closed");
      } catch {}
    }
  }

  async webSocketError(ws: WebSocket): Promise<void> {
    for (const peer of this.ctx.getWebSockets(this.peerRole(ws))) {
      try {
        peer.close(1011, "peer error");
      } catch {}
    }
  }
}
