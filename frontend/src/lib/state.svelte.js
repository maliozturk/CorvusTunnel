import { ChannelClient } from './channel.js';

// Map terminal messages onto channel ops. Kept as wsSend() so the terminal
// components do not need to change.
export function wsSend(obj) {
  const ch = STATE.channel;
  if (!ch || !ch.ready) return false;
  if (obj.type === 'input') ch.send('term_input', { data: obj.data });
  else if (obj.type === 'resize') ch.send('term_resize', { cols: obj.cols, rows: obj.rows });
  else if (obj.type === 'ping') ch.send('ping');
  return true;
}

// Screen Wake Lock reference
let wakeLock = null;

// ── Theme Initialization ──────────────────────────────────────────
function getInitialTheme() {
  const stored = localStorage.getItem('corvus_theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return 'dark'; // default
}

function getInitialTerminalTheme() {
  const stored = localStorage.getItem('corvus_terminal_theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return 'dark'; // default
}

// Apply theme to DOM immediately
function applyThemeToDOM(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

// Apply initial theme before Svelte mounts
applyThemeToDOM(getInitialTheme());

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
  ws: null,
  channel: null,
  identityPub: '',
  relayWs: '',
  sessionToken: localStorage.getItem('corvus_session') || '',
  reconnectAttempt: 0,
  maxReconnect: 10,
  ctrlActive: false,
  altActive: false,

  recentCommands: JSON.parse(sessionStorage.getItem('corvus_recent') || '[]'),
  favorites: JSON.parse(localStorage.getItem('corvus_favorites') || '[]'),
  
  // UI Panels
  showFolderModal: false,
  showFavModal: false,
  showHistoryPanel: false,
  terminalCollapsed: false,
  
  // Notification Banner
  showNotifBanner: false,

  // ── NEW: Theme ──────────────────────────────────────────────
  theme: getInitialTheme(),           // 'dark' | 'light'
  terminalTheme: getInitialTerminalTheme(), // 'dark' | 'light'
  
  // ── NEW: Onboarding ─────────────────────────────────────────
  showOnboarding: false,
  onboardingComplete: localStorage.getItem('corvus_onboarding_done') === 'true',
  
  // ── NEW: Exit Confirmation ──────────────────────────────────
  showExitConfirm: false,
  
  // ── NEW: Settings Panel ─────────────────────────────────────
  showSettings: false,
  
  // ── NEW: Screen Transition ──────────────────────────────────
  screenTransition: '', // 'slide-left', 'slide-right', 'fade'
});

// ── Theme Management ──────────────────────────────────────────────
function setTheme(theme) {
  STATE.theme = theme;
  localStorage.setItem('corvus_theme', theme);
  applyThemeToDOM(theme);
}

export function toggleTheme() {
  setTheme(STATE.theme === 'dark' ? 'light' : 'dark');
}

function setTerminalTheme(theme) {
  STATE.terminalTheme = theme;
  localStorage.setItem('corvus_terminal_theme', theme);
  
  // Update xterm theme if terminal is active
  if (STATE.term) {
    applyXtermTheme(STATE.term, theme);
  }
}

export function toggleTerminalTheme() {
  setTerminalTheme(STATE.terminalTheme === 'dark' ? 'light' : 'dark');
}

export function applyXtermTheme(term, theme) {
  if (theme === 'light') {
    term.options.theme = {
      background: '#f8f9fa',
      foreground: '#1a1a2e',
      cursor: '#7c3aed',
      cursorAccent: '#f8f9fa',
      selectionBackground: 'rgba(124, 58, 237, 0.2)',
      black: '#1a1a2e',
      red: '#dc2626',
      green: '#059669',
      yellow: '#d97706',
      blue: '#2563eb',
      magenta: '#7c3aed',
      cyan: '#0891b2',
      white: '#e5e5e7',
      brightBlack: '#718096',
      brightRed: '#ef4444',
      brightGreen: '#10b981',
      brightYellow: '#f59e0b',
      brightBlue: '#3b82f6',
      brightMagenta: '#9060ff',
      brightCyan: '#06b6d4',
      brightWhite: '#1a1a2e',
    };
  } else {
    term.options.theme = {
      background: '#000000',
      foreground: '#e6e6e6',
      cursor: '#9060ff',
      cursorAccent: '#000000',
      selectionBackground: 'rgba(144, 96, 255, 0.25)',
      black: '#000000',
      red: '#ef4444',
      green: '#10b981',
      yellow: '#f59e0b',
      blue: '#3b82f6',
      magenta: '#9060ff',
      cyan: '#06b6d4',
      white: '#e6e6e6',
      brightBlack: '#606060',
      brightRed: '#f87171',
      brightGreen: '#4ade80',
      brightYellow: '#fde047',
      brightBlue: '#60a5fa',
      brightMagenta: '#c084fc',
      brightCyan: '#22d3ee',
      brightWhite: '#ffffff',
    };
  }
}

// ── Onboarding Management ─────────────────────────────────────────
export function completeOnboarding() {
  STATE.onboardingComplete = true;
  STATE.showOnboarding = false;
  localStorage.setItem('corvus_onboarding_done', 'true');
}

export function resetOnboarding() {
  STATE.onboardingComplete = false;
  localStorage.removeItem('corvus_onboarding_done');
}

function showOnboardingIfNeeded() {
  if (!STATE.onboardingComplete) {
    STATE.showOnboarding = true;
  }
}

// ── Haptic Feedback ───────────────────────────────────────────────
export function hapticTap() {
  if ('vibrate' in navigator) {
    try {
      navigator.vibrate(10);
    } catch (e) { /* ignore */ }
  }
}

export function hapticHeavy() {
  if ('vibrate' in navigator) {
    try {
      navigator.vibrate(25);
    } catch (e) { /* ignore */ }
  }
}

// ── Auth & Session ────────────────────────────────────────────────
function showAuthErr(msg) {
  STATE.error = msg;
}

export function handleLogout() {
  STATE.token = '';
  STATE.sessionToken = '';
  localStorage.removeItem('corvus_token');
  localStorage.removeItem('corvus_session');
  if (STATE.healthTimer) {
    clearInterval(STATE.healthTimer);
    STATE.healthTimer = null;
  }

  disconnectTerminal(true);
  if (STATE.channel) {
    STATE.channel.close();
    STATE.channel = null;
  }
  STATE.connected = false;
  STATE.phase = 'launcher';
}

export async function bootFromFragment() {
  const params = new URLSearchParams(window.location.hash.substring(1));
  const t = params.get('t');
  const k = params.get('k');
  const w = params.get('w');
  if (k) STATE.identityPub = k;
  if (w) STATE.relayWs = decodeURIComponent(w);
  if (t || k || w) {
    window.history.replaceState(null, '', window.location.pathname);
  }
  if (!STATE.identityPub) {
    showAuthErr('Open the link from the QR code shown by "corvustunnel start".');
    return;
  }
  const ok = await connectChannel();
  if (!ok) return;
  if (t) {
    await claimAndBoot(t);
  } else if (STATE.sessionToken) {
    await resumeAndBoot();
  }
}

async function connectChannel() {
  const wsUrl = STATE.relayWs ||
    ((window.location.protocol === 'https:' ? 'wss' : 'ws') + '://' + window.location.host + '/api/channel');
  const ch = new ChannelClient();
  ch.onEvent = handleTerminalEvent;
  ch.onClose = () => {
    STATE.connected = false;
    if (STATE.wsStatus !== 'exited') STATE.wsStatus = 'disconnected';
    if (STATE.phase === 'terminal') attemptReconnect();
  };
  try {
    await ch.connect(wsUrl, STATE.identityPub);
    STATE.channel = ch;
    STATE.connected = true;
    return true;
  } catch (e) {
    console.error('[channel] connect failed', e);
    showAuthErr('Secure connection failed: ' + e.message);
    return false;
  }
}

export async function claimAndBoot(token) {
  try {
    const data = await STATE.channel.request('claim', { token });
    STATE.sessionToken = data.session_token;
    localStorage.setItem('corvus_session', data.session_token);
    STATE.token = data.session_token;
    localStorage.setItem('corvus_token', data.session_token);
    bootApp();
  } catch (e) {
    showAuthErr('Token rejected — it may have already been used.');
    handleLogout();
  }
}

async function resumeAndBoot() {
  try {
    await STATE.channel.request('resume', { session_token: STATE.sessionToken });
    STATE.token = STATE.sessionToken;
    bootApp();
  } catch (e) {
    handleLogout();
  }
}

function handleTerminalEvent(msg) {
  if (msg.ev === 'output' || msg.ev === 'replay') {
    if (STATE.term && msg.data) {
      STATE.term.write(msg.data);
      detectUrl(msg.data);
    }
  } else if (msg.ev === 'exited') {
    STATE.wsStatus = 'exited';
    if (STATE.term) {
      STATE.term.writeln(`\r\n\x1b[31m[${STATE.selectedAgent} exited with code ${msg.code ?? '?'}]\x1b[0m`);
    }
    sendBrowserNotification('Agent Exited', `${STATE.selectedAgent} exited with code ${msg.code ?? '?'}`);
    setTimeout(() => { STATE.phase = 'launcher'; }, 2000);
  }
}

export function bootApp() {
  STATE.error = '';
  STATE.phase = 'launcher';
  startHealth();
  checkAgentAvailability();
  
  // Show onboarding for first-time users
  showOnboardingIfNeeded();
}

function startHealth() {
  if (STATE.healthTimer) clearInterval(STATE.healthTimer);

  const checkHealth = () => {
    STATE.connected = !!(STATE.channel && STATE.channel.ready);
    if (STATE.connected) STATE.channel.send('ping');
  };

  checkHealth();
  STATE.healthTimer = setInterval(checkHealth, 15000);
}

async function checkAgentAvailability() {
  if (STATE.checkingAvailability) return;
  STATE.checkingAvailability = true;
  try {
    const data = await STATE.channel.request('check_agents');
    STATE.agents = data.agents || [];
    if (!STATE.currentFolder && data.default_work_dir) {
      STATE.currentFolder = data.default_work_dir;
      localStorage.setItem('corvus_workdir', data.default_work_dir);
    }
  } catch (e) {
    console.warn('Failed to check agent availability', e);
  } finally {
    STATE.checkingAvailability = false;
  }
}

// ── Screen Wake Lock ───────────────────────────────────────────────
async function acquireWakeLock() {
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

// ── Terminal connection (multiplexed over the encrypted channel) ──
let reconnectTimer = null;

export function disconnectTerminal(userExited = false) {
  clearTimeout(reconnectTimer);
  if (userExited) {
    wsSend({ type: 'input', data: '\x03' });
  }
  STATE.wsStatus = 'disconnected';
  releaseWakeLock();
}

export async function connectTerminal() {
  clearTimeout(reconnectTimer);
  STATE.wsStatus = 'connecting';

  _urlBuf = '';
  _lastShownLen = 0;
  _autoScrollSent = false;
  if (_urlToastTimer) {
    clearTimeout(_urlToastTimer);
    _urlToastTimer = null;
  }

  if (STATE.term) {
    STATE.term.write('\r\n\x1b[33mConnecting to ' + STATE.currentFolder + '...\x1b[0m\r\n');
  }

  if (!STATE.channel || !STATE.channel.ready) {
    const ok = await connectChannel();
    if (ok && STATE.sessionToken) {
      try {
        await STATE.channel.request('resume', { session_token: STATE.sessionToken });
      } catch (e) { /* will surface on term_start */ }
    }
  }

  try {
    await STATE.channel.request('term_start', {
      work_dir: STATE.currentFolder,
      agent: STATE.selectedAgent,
    });
    STATE.reconnectAttempt = 0;
    STATE.wsStatus = 'connected';
    acquireWakeLock();
    sendResize();
  } catch (err) {
    STATE.wsStatus = 'disconnected';
    if (STATE.term) {
      STATE.term.writeln(`\r\n\x1b[31mConnection failed: ${err.message}\x1b[0m\r\n`);
    }
    if (STATE.phase === 'terminal') attemptReconnect();
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
  if (!STATE.term || !STATE.channel || !STATE.channel.ready) return;
  try {
    STATE.fitAddon.fit();
    wsSend({ type: 'resize', cols: STATE.term.cols, rows: STATE.term.rows });
  } catch(e) {
    console.warn('Failed to resize terminal', e);
  }
}

// ── Manual Reconnect (for status bar tap) ─────────────────────────
export function manualReconnect() {
  STATE.reconnectAttempt = 0;
  connectTerminal();
}

// URL detection toast (catches long wrapped URLs in terminal output)
let _urlBuf = '';
let _urlToastTimer = null;
let _lastShownLen = 0;
let _autoScrollSent = false;

function showUrlToast(url, complete) {
  STATE.urlToastHref = url;
  if (complete) {
    STATE.urlToastText = '🔗 Tap to Open Link';
  } else {
    STATE.urlToastText = '⏳ Loading full URL...';
  }
  STATE.urlToastVisible = true;

  // Auto-hide after 60s
  if (_urlToastTimer) clearTimeout(_urlToastTimer);
  _urlToastTimer = setTimeout(hideUrlToast, 60000);
}

function detectUrl(chunk) {
  // Strip ANSI escape codes and accumulate
  const clean = chunk.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
  _urlBuf += clean;
  // Keep only last 8KB
  if (_urlBuf.length > 8192) _urlBuf = _urlBuf.slice(-8192);

  // Strip pager UI artifacts before URL detection
  let stripped = _urlBuf;
  stripped = stripped.replace(/\(\d+-\d+\s*of\s*\d+\s*lines?\)/gi, ' ');
  stripped = stripped.replace(/shift\+up\/down\s*Navigate/gi, ' ');
  stripped = stripped.replace(/Press\s*q\s*to\s*quit/gi, ' ');
  stripped = stripped.replace(/\(END\)/g, ' ');
  stripped = stripped.replace(/Open\s*this\s*link\s*in\s*the\s*browser[^h]*/gi, ' ');

  // Remove all whitespace/newlines to reassemble wrapped URLs
  const flat = stripped.replace(/[\r\n\s]+/g, '');

  // Match https:// URLs — stop at characters that shouldn't be in URLs
  const matches = flat.match(/https?:\/\/[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+/g);
  if (!matches) return;

  // Take the longest (most complete) URL found
  let url = matches.reduce(function(a, b) { return a.length >= b.length ? a : b; });

  // Trim trailing artifacts
  url = url.replace(/[)}\]]+$/, '');

  // Skip short URLs
  if (url.length < 40) return;

  // Only track URLs that look like auth URLs (Google OAuth, etc)
  const isAuthUrl = url.indexOf('accounts.google.com') !== -1 || url.indexOf('oauth') !== -1;
  if (!isAuthUrl && url.length < 80) return;

  // Check if URL looks complete (has key OAuth params)
  const looksComplete = !isAuthUrl ||
    (url.indexOf('response_type') !== -1 && url.indexOf('scope') !== -1);

  // Update toast if URL grew longer
  if (url.length > _lastShownLen) {
    _lastShownLen = url.length;
    showUrlToast(url, looksComplete);

    // If URL is incomplete and we haven't auto-scrolled yet, send Down keys to advance pager
    if (!looksComplete && !_autoScrollSent && STATE.ws && STATE.ws.readyState === WebSocket.OPEN) {
      _autoScrollSent = true;
      // Send space/down keys with delay to scroll through the pager
      let scrollCount = 0;
      const scrollInterval = setInterval(function() {
        if (scrollCount >= 15 || !STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) {
          clearInterval(scrollInterval);
          return;
        }
        wsSend({ type: 'input', data: '\x1b[1;2B' }); // shift+down in agy pager
        scrollCount++;
      }, 300);
    }
  }
}

export function hideUrlToast() {
  STATE.urlToastVisible = false;
  STATE.urlToastText = '';
  STATE.urlToastHref = '';
  if (_urlToastTimer) {
    clearTimeout(_urlToastTimer);
    _urlToastTimer = null;
  }
  _lastShownLen = 0;
  _autoScrollSent = false;
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

// ── Two-Finger Scroll Setup ──────────────────────────────────────
export function setupTwoFingerScroll(terminalContainer, term) {
  if (!terminalContainer || !term) return null;
  
  let touchCount = 0;
  let lastTwoFingerY = 0;
  let isTwoFinger = false;
  
  const onTouchStart = (e) => {
    touchCount = e.touches.length;
    if (touchCount === 2) {
      isTwoFinger = true;
      lastTwoFingerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      e.preventDefault();
    } else {
      isTwoFinger = false;
    }
  };
  
  const onTouchMove = (e) => {
    if (isTwoFinger && e.touches.length === 2) {
      e.preventDefault();
      const currentY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      const delta = lastTwoFingerY - currentY;
      lastTwoFingerY = currentY;
      
      // Scroll xterm buffer
      const lineHeight = 18; // approximate
      const lines = Math.round(delta / lineHeight);
      if (lines !== 0) {
        term.scrollLines(lines);
      }
    }
  };
  
  const onTouchEnd = (e) => {
    if (e.touches.length < 2) {
      isTwoFinger = false;
    }
    touchCount = e.touches.length;
  };
  
  terminalContainer.addEventListener('touchstart', onTouchStart, { passive: false });
  terminalContainer.addEventListener('touchmove', onTouchMove, { passive: false });
  terminalContainer.addEventListener('touchend', onTouchEnd, { passive: true });
  
  // Return cleanup function
  return () => {
    terminalContainer.removeEventListener('touchstart', onTouchStart);
    terminalContainer.removeEventListener('touchmove', onTouchMove);
    terminalContainer.removeEventListener('touchend', onTouchEnd);
  };
}

// ── Visual Viewport Keyboard Handler ─────────────────────────────
export function setupKeyboardResize(callback) {
  if (!window.visualViewport) return null;
  
  const handler = () => {
    const vv = window.visualViewport;
    // When keyboard opens, visualViewport.height < window.innerHeight
    const keyboardHeight = window.innerHeight - vv.height;
    callback(keyboardHeight, vv.height);
  };
  
  window.visualViewport.addEventListener('resize', handler);
  window.visualViewport.addEventListener('scroll', handler);
  
  return () => {
    window.visualViewport.removeEventListener('resize', handler);
    window.visualViewport.removeEventListener('scroll', handler);
  };
}
