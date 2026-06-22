// CorvusTunnel authenticated channel client.
//
// Mirrors corvustunnel/crypto/channel.py: a signed X25519 handshake (the server
// signature is verified against the identity key pinned in the QR, so a relay
// cannot MITM) followed by per-direction XSalsa20-Poly1305 framing. Every
// control op and the terminal stream are multiplexed inside the encrypted
// channel as request/response and event messages.

import nacl from 'tweetnacl';

const CONTEXT = new TextEncoder().encode('corvustunnel-channel-v1');
const BAR = new TextEncoder().encode('|');
const ENC = new TextEncoder();
const DEC = new TextDecoder();

function b64e(u8) {
  return btoa(String.fromCharCode(...u8)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64d(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  const bin = atob(s);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}
function cat(...parts) {
  let n = 0;
  for (const p of parts) n += p.length;
  const out = new Uint8Array(n);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
function transcript(cE, sE, cN, sN) {
  return nacl.hash(cat(cE, sE, cN, sN));
}
function derive(label, shared, tr) {
  return nacl.hash(cat(ENC.encode(label), BAR, CONTEXT, BAR, shared, BAR, tr)).slice(0, 32);
}
function nonce(counter) {
  const n = new Uint8Array(24);
  let c = BigInt(counter);
  for (let i = 23; i >= 0 && c > 0n; i--) { n[i] = Number(c & 0xffn); c >>= 8n; }
  return n;
}

export class ChannelClient {
  constructor() {
    this.ws = null;
    this.sendKey = null;
    this.recvKey = null;
    this.sendCtr = 0;
    this.recvCtr = 0;
    this.reqId = 0;
    this.pending = new Map();
    this.onEvent = () => {};
    this.onClose = () => {};
    this._ready = false;
  }

  connect(wsUrl, identityPubB64) {
    return new Promise((resolve, reject) => {
      const kp = nacl.box.keyPair();
      const clientNonce = nacl.randomBytes(32);
      const identityPub = b64d(identityPubB64);
      let handshaken = false;

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      this.ws = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ e: b64e(kp.publicKey), n: b64e(clientNonce) }));
      };

      ws.onmessage = (ev) => {
        if (!handshaken) {
          try {
            const hello = JSON.parse(ev.data);
            const sE = b64d(hello.e);
            const sN = b64d(hello.n);
            const sig = b64d(hello.sig);
            const tr = transcript(kp.publicKey, sE, clientNonce, sN);
            if (!nacl.sign.detached.verify(tr, sig, identityPub)) {
              reject(new Error('Server identity verification failed'));
              ws.close();
              return;
            }
            const shared = nacl.scalarMult(kp.secretKey, sE);
            this.sendKey = derive('c2s', shared, tr);
            this.recvKey = derive('s2c', shared, tr);
            handshaken = true;
            this._ready = true;
            resolve();
          } catch (e) {
            reject(e);
            ws.close();
          }
          return;
        }
        let msg;
        try {
          const pt = nacl.secretbox.open(new Uint8Array(ev.data), nonce(this.recvCtr), this.recvKey);
          if (!pt) throw new Error('frame auth failed');
          this.recvCtr++;
          msg = JSON.parse(DEC.decode(pt));
        } catch (e) {
          this.close();
          return;
        }
        if (msg.id !== undefined && this.pending.has(msg.id)) {
          const { resolve: res, reject: rej } = this.pending.get(msg.id);
          this.pending.delete(msg.id);
          if (msg.ok) res(msg.data || {});
          else rej(Object.assign(new Error(msg.error || 'error'), { status: msg.status }));
        } else if (msg.ev) {
          this.onEvent(msg);
        }
      };

      ws.onclose = () => {
        this._ready = false;
        for (const { reject: rej } of this.pending.values()) rej(new Error('channel closed'));
        this.pending.clear();
        this.onClose();
      };
      ws.onerror = () => {
        if (!handshaken) reject(new Error('Connection failed'));
      };
    });
  }

  _frame(obj) {
    const ct = nacl.secretbox(ENC.encode(JSON.stringify(obj)), nonce(this.sendCtr), this.sendKey);
    this.sendCtr++;
    this.ws.send(ct);
  }

  request(op, params = {}) {
    return new Promise((resolve, reject) => {
      if (!this._ready) { reject(new Error('channel not ready')); return; }
      const id = ++this.reqId;
      this.pending.set(id, { resolve, reject });
      this._frame({ op, id, ...params });
    });
  }

  send(op, params = {}) {
    if (this._ready) this._frame({ op, ...params });
  }

  get ready() {
    return this._ready;
  }

  close() {
    try { this.ws && this.ws.close(); } catch (e) { /* ignore */ }
  }
}
