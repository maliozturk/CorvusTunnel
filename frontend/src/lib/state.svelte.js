import { api } from './api.js';

// Screen Wake Lock reference
let wakeLock = null;

export const STATE = $state({
  token: localStorage.getItem('corvus_token') || '',
  connected: false,
  healthTimer: null,
  agents: [],       // [{name, available}]
  selectedAgent: localStorage.getItem('corvus_agent') || 'agy',
  phase: 'launcher', // 'launcher', 'terminal'
  currentFolder: localStorage.getItem('corvus_workdir') || '',
  checkingAvailability: false,
  error: '',
  wsStatus: 'disconnected', // 'connecting', 'connected', 'disconnected', 'exited'
  
  // URL Toast
  urlToastText: '',
  urlToastHref: '',
  urlToastVisible: false,
  
  // Terminal state
  term: null,
  fitAddon: null,
  canvasAddon: null,
  ws: null,
  reconnectAttempt: 0,
  maxReconnect: 10,
  ctrlActive: false,
  altActive: false,
  autoApprove: false,
  recentCommands: JSON.parse(sessionStorage.getItem('corvus_recent') || '[]'),
  favorites: JSON.parse(localStorage.getItem('corvus_favorites') || '[]'),
  
  // UI Panels
  showFolderModal: false,
  showFavModal: false,
  showHistoryPanel: false,
  terminalCollapsed: false,
  
  // Notification Banner
  showNotifBanner: false,
});

export function showAuthErr(msg) {
  STATE.error = msg;
}

export function handleLogout() {
  STATE.token = '';
  localStorage.removeItem('corvus_token');
  if (STATE.healthTimer) {
    clearInterval(STATE.healthTimer);
    STATE.healthTimer = null;
  }
  
  disconnectTerminal(true);
  STATE.phase = 'launcher';
}

export async function claimAndBoot(token) {
  try {
    const resp = await fetch('/api/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token }),
    });
    
    if (resp.ok) {
      const data = await resp.json();
      STATE.token = data.session_token;
      localStorage.setItem('corvus_token', data.session_token);
      bootApp();
      return;
    }
    
    // If claim fails, try token directly as session token
    STATE.token = token;
    localStorage.setItem('corvus_token', token);
    const health = await fetch('/api/health');
    if (health.ok) {
      bootApp();
    } else {
      showAuthErr('Token rejected — it may have already been used.');
      handleLogout();
    }
  } catch (e) {
    showAuthErr('Connection error: ' + e.message);
    handleLogout();
  }
}

export function bootApp() {
  STATE.error = '';
  STATE.phase = 'launcher';
  startHealth();
  checkAgentAvailability();
}

export function startHealth() {
  if (STATE.healthTimer) clearInterval(STATE.healthTimer);
  
  const checkHealth = async () => {
    try {
      const resp = await api('/api/health');
      if (resp.ok) {
        STATE.connected = true;
      } else {
        STATE.connected = false;
      }
    } catch (e) {
      STATE.connected = false;
    }
  };
  
  checkHealth();
  STATE.healthTimer = setInterval(checkHealth, 10000);
}

export async function checkAgentAvailability() {
  if (STATE.checkingAvailability) return;
  STATE.checkingAvailability = true;
  try {
    const r = await api('/api/check-agents');
    if (r.ok) {
      const data = await r.json();
      STATE.agents = data.agents || [];
      // Auto-set working directory if not already chosen
      if (!STATE.currentFolder && data.default_work_dir) {
        STATE.currentFolder = data.default_work_dir;
        localStorage.setItem('corvus_workdir', data.default_work_dir);
      }
    }
  } catch (e) {
    console.warn('Failed to check agent availability', e);
  } finally {
    STATE.checkingAvailability = false;
  }
}

// ── Screen Wake Lock ───────────────────────────────────────────────
export async function acquireWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try {
    wakeLock = await navigator.wakeLock.request('screen');
    wakeLock.addEventListener('release', () => {
      wakeLock = null;
    });
  } catch (e) {
    console.warn('[wakelock] Failed to acquire:', e.message);
  }
}

export function releaseWakeLock() {
  if (wakeLock) {
    wakeLock.release();
    wakeLock = null;
  }
}

// ── Suggestion & Command History ──────────────────────────────────
export function addRecent(cmd) {
  if (!cmd || typeof cmd !== 'string') return;
  cmd = cmd.trim();
  if (!cmd) return;
  
  let recent = STATE.recentCommands.filter(c => c !== cmd);
  recent.unshift(cmd);
  if (recent.length > 50) recent = recent.slice(0, 50);
  
  STATE.recentCommands = recent;
  try {
    sessionStorage.setItem('corvus_recent', JSON.stringify(recent));
  } catch(e) {}
}

export function addFavorite(cmd) {
  if (!cmd || typeof cmd !== 'string') return;
  cmd = cmd.trim();
  if (!cmd) return;
  
  const favs = STATE.favorites.filter(c => c !== cmd);
  favs.unshift(cmd);
  STATE.favorites = favs;
  localStorage.setItem('corvus_favorites', JSON.stringify(favs));
}

export function removeFavorite(cmd) {
  const favs = STATE.favorites.filter(c => c !== cmd);
  STATE.favorites = favs;
  localStorage.setItem('corvus_favorites', JSON.stringify(favs));
}

// ── Terminal WebSocket connections ───────────────────────────
let reconnectTimer = null;

export function disconnectTerminal(userExited = false) {
  clearTimeout(reconnectTimer);
  if (STATE.ws) {
    if (userExited) {
      // Send exit command
      try { STATE.ws.send(JSON.stringify({ type: 'input', data: '\x03' })); } catch(e) {}
    }
    STATE.ws.close();
    STATE.ws = null;
  }
  
  STATE.wsStatus = 'disconnected';
  releaseWakeLock();
}

export async function connectTerminal() {
  disconnectTerminal();
  STATE.wsStatus = 'connecting';
  
  if (STATE.term) {
    STATE.term.write('\r\n\x1b[33mConnecting to ' + STATE.currentFolder + '...\x1b[0m\r\n');
  }
  
  try {
    // 1. Get ticket
    const ticketResp = await api('/api/ws-ticket', { method: 'POST' });
    if (!ticketResp.ok) {
      throw new Error('Failed to get WebSocket ticket');
    }
    
    const ticketData = await ticketResp.json();
    const ticket = ticketData.ticket;
    
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let url = `${proto}://${window.location.host}/api/terminal/ws`
      + `?ticket=${encodeURIComponent(ticket)}`
      + `&work_dir=${encodeURIComponent(STATE.currentFolder)}`
      + `&agent=${encodeURIComponent(STATE.selectedAgent)}`;
      
    if (STATE.autoApprove) {
      url += '&flags=' + encodeURIComponent('auto-approve');
    }
    
    const ws = new WebSocket(url);
    STATE.ws = ws;
    
    ws.onopen = () => {
      STATE.reconnectAttempt = 0;
      STATE.wsStatus = 'connected';
      acquireWakeLock();
      
      // Send initial resize
      sendResize();
      
      // Ping interval to avoid tunnel timeouts
      ws.pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 15000);
    };
    
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'output' || msg.type === 'replay') {
          if (STATE.term && msg.data) {
            STATE.term.write(msg.data);
            detectUrl(msg.data);
          }
        } else if (msg.type === 'exited') {
          STATE.wsStatus = 'exited';
          if (STATE.term) {
            STATE.term.writeln(`\r\n\x1b[31m[${STATE.selectedAgent} exited with code ${msg.code ?? '?'}]\x1b[0m`);
          }
          sendBrowserNotification('Agent Exited', `${STATE.selectedAgent} exited with code ${msg.code ?? '?'}`);
          
          setTimeout(() => {
            STATE.phase = 'launcher';
          }, 2000);
        }
      } catch (e) {
        console.warn('[terminal] Parse error:', e);
      }
    };
    
    ws.onclose = (ev) => {
      if (ws.pingInterval) clearInterval(ws.pingInterval);
      
      if (STATE.wsStatus === 'exited') return;
      STATE.wsStatus = 'disconnected';
      
      // Attempt reconnect if unexpected
      if (STATE.phase === 'terminal') {
        attemptReconnect();
      }
    };
    
    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  } catch (err) {
    STATE.wsStatus = 'disconnected';
    if (STATE.term) {
      STATE.term.writeln(`\r\n\x1b[31mConnection failed: ${err.message}\x1b[0m\r\n`);
    }
  }
}

function attemptReconnect() {
  if (STATE.reconnectAttempt >= STATE.maxReconnect) {
    if (STATE.term) {
      STATE.term.writeln('\r\n\x1b[31mConnection lost. Max reconnect attempts reached.\x1b[0m\r\n');
    }
    return;
  }
  
  STATE.reconnectAttempt++;
  if (STATE.term) {
    STATE.term.writeln(`\r\n\x1b[33mReconnecting (attempt ${STATE.reconnectAttempt}/${STATE.maxReconnect})...\x1b[0m\r\n`);
  }
  
  reconnectTimer = setTimeout(() => {
    connectTerminal();
  }, Math.min(1000 * STATE.reconnectAttempt, 5000));
}

export function sendResize() {
  if (!STATE.term || !STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
  
  // In Svelte, fit addon fits to the container
  try {
    STATE.fitAddon.fit();
    const cols = STATE.term.cols;
    const rows = STATE.term.rows;
    STATE.ws.send(JSON.stringify({ type: 'resize', cols, rows }));
  } catch(e) {
    console.warn('Failed to resize terminal', e);
  }
}

// URL detection toast
let _urlBuf = '';
function detectUrl(data) {
  _urlBuf += data;
  if (_urlBuf.length > 5000) _urlBuf = _urlBuf.slice(-2000);
  
  // Simple regex to detect localhost ports or generic URLs
  const urlRegex = /(https?:\/\/[^\s"'()<>]+|localhost:\d+|127\.0\.0\.1:\d+)/gi;
  const matches = [..._urlBuf.matchAll(urlRegex)];
  
  if (matches.length > 0) {
    const lastMatch = matches[matches.length - 1][0];
    let fullUrl = lastMatch;
    
    // Resolve short localhost entries
    if (!fullUrl.startsWith('http')) {
      fullUrl = 'http://' + fullUrl;
    }
    
    STATE.urlToastText = `Open Link: ${lastMatch}`;
    STATE.urlToastHref = fullUrl;
    STATE.urlToastVisible = true;
  }
}

export function hideUrlToast() {
  STATE.urlToastVisible = false;
  STATE.urlToastText = '';
  STATE.urlToastHref = '';
}

// Browser notification helper
function sendBrowserNotification(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  if (document.visibilityState === 'visible') return;
  
  new Notification(title, {
    body,
    icon: '/static/icons/icon-192.png',
    tag: 'corvus-agent',
    renotify: true,
  });
}
