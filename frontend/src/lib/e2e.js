// CorvusTunnel end-to-end encryption (client side).
//
// Uses tweetnacl's crypto_box (X25519 + XSalsa20-Poly1305), which is wire
// compatible with the server's PyNaCl Box. On connect we generate an
// ephemeral keypair, exchange public keys with the server, and then encrypt
// every WebSocket frame so the relay only ever sees opaque ciphertext.
//
// Frame format: base64url( nonce[24] || ciphertext )  (ciphertext holds the tag)

import nacl from 'tweetnacl';

let _serverPub = null;   // Uint8Array(32) — server ephemeral public key
let _clientPriv = null;  // Uint8Array(32) — our ephemeral secret key
let _active = false;
let _sessionId = null;

const _enc = new TextEncoder();
const _dec = new TextDecoder();

function b64urlEnc(u8) {
  let bin = '';
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function b64urlDec(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  const bin = atob(s);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}

export function isE2EActive() {
  return _active;
}

/** Generate a fresh, URL-safe session id. */
export function newSessionId() {
  return b64urlEnc(nacl.randomBytes(16));
}

/** Forget all key material (call on disconnect). */
export function resetE2E() {
  _serverPub = null;
  _clientPriv = null;
  _active = false;
  _sessionId = null;
}

/**
 * Perform the key exchange for `sessionId`.
 * Returns true if E2E is established, false to fall back to plaintext
 * (e.g. the server has no PyNaCl installed and returns 501).
 */
export async function establishE2E(sessionId) {
  resetE2E();
  const kp = nacl.box.keyPair();
  try {
    const resp = await fetch('/api/e2e/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        client_public_key: b64urlEnc(kp.publicKey),
      }),
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    if (!data.server_public_key) return false;
    _serverPub = b64urlDec(data.server_public_key);
    _clientPriv = kp.secretKey;
    _sessionId = sessionId;
    _active = true;
    return true;
  } catch (e) {
    console.warn('[e2e] key exchange failed, falling back to plaintext:', e);
    return false;
  }
}

/** Encrypt a JS object → base64url string. */
export function encryptMsg(obj) {
  const nonce = nacl.randomBytes(24);
  const ct = nacl.box(_enc.encode(JSON.stringify(obj)), nonce, _serverPub, _clientPriv);
  const combined = new Uint8Array(nonce.length + ct.length);
  combined.set(nonce, 0);
  combined.set(ct, nonce.length);
  return b64urlEnc(combined);
}

/** Decrypt a base64url frame → JS object, or null if it can't be decrypted. */
export function decryptMsg(b64) {
  try {
    const combined = b64urlDec(b64);
    const nonce = combined.slice(0, 24);
    const ct = combined.slice(24);
    const opened = nacl.box.open(ct, nonce, _serverPub, _clientPriv);
    if (!opened) return null;
    return JSON.parse(_dec.decode(opened));
  } catch (e) {
    return null;
  }
}
