import { STATE, handleLogout } from './state.svelte.js';

export function authHdr() {
  return { 
    'Authorization': 'Bearer ' + STATE.token, 
    'Content-Type': 'application/json' 
  };
}

export async function api(url, opts = {}) {
  const headers = { ...authHdr(), ...(opts.headers || {}) };
  
  try {
    const r = await fetch(url, {
      ...opts,
      headers,
      signal: opts.signal || AbortSignal.timeout(30000),
    });
    
    if (r.status === 401 || r.status === 403) {
      handleLogout();
      STATE.error = 'Session expired. Please re-authenticate.';
      throw new Error('Unauthorized');
    }
    
    return r;
  } catch (err) {
    if (err.name === 'TimeoutError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw err;
  }
}
