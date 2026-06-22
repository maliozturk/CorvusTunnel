import { STATE } from './state.svelte.js';

// Compatibility adapter: components still call api('/api/...'), but every call
// now runs as an op inside the authenticated channel. Returns a minimal
// fetch-like response so callers do not need to change.
function fakeResponse(ok, data, status = 200) {
  return {
    ok,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

export function authHdr() {
  return {};
}

export async function api(url, opts = {}) {
  const ch = STATE.channel;
  if (!ch || !ch.ready) throw new Error('Not connected');

  const u = new URL(url, 'http://local');
  const path = u.pathname;
  let body = {};
  if (opts.body) {
    try { body = JSON.parse(opts.body); } catch (e) { body = {}; }
  }

  try {
    let data;
    if (path === '/api/check-agents') {
      data = await ch.request('check_agents');
    } else if (path === '/api/browse') {
      data = await ch.request('browse', { path: u.searchParams.get('path') || undefined });
    } else if (path === '/api/browse/mkdir') {
      data = await ch.request('mkdir', { parent: body.parent, name: body.name });
    } else if (path === '/api/history/sessions') {
      data = await ch.request('history_list', {
        agent: u.searchParams.get('agent') || undefined,
        limit: Number(u.searchParams.get('limit') || 50),
        offset: Number(u.searchParams.get('offset') || 0),
      });
    } else if (path.startsWith('/api/history/sessions/')) {
      const id = decodeURIComponent(path.slice('/api/history/sessions/'.length));
      data = await ch.request('history_get', {
        session_id: id,
        limit: Number(u.searchParams.get('limit') || 200),
        offset: Number(u.searchParams.get('offset') || 0),
      });
    } else if (path === '/api/history/stats') {
      data = await ch.request('history_stats');
    } else if (path === '/api/health') {
      data = { status: 'ok' };
    } else {
      throw Object.assign(new Error('Unsupported endpoint: ' + path), { status: 404 });
    }
    return fakeResponse(true, data);
  } catch (e) {
    const status = e.status || 500;
    if (status === 401 || status === 403) {
      STATE.error = 'Session expired. Please reconnect.';
    }
    return fakeResponse(false, { detail: e.message }, status);
  }
}
