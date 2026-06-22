<script>
  import { onMount, onDestroy } from 'svelte';
  import { STATE, disconnectTerminal, sendResize, hideUrlToast, addRecent, hapticTap, applyXtermTheme, setupTwoFingerScroll, setupKeyboardResize, wsSend } from './state.svelte.js';
  import { Terminal as Xterm } from '@xterm/xterm';
  import { FitAddon } from '@xterm/addon-fit';
  import { CanvasAddon } from '@xterm/addon-canvas';
  import { WebLinksAddon } from '@xterm/addon-web-links';
  import { 
    ChevronLeft, Keyboard, Star, 
    Globe, Folder, ArrowDownToLine, Home,
    X
  } from 'lucide-svelte';

  // CSS for xterm
  import '@xterm/xterm/css/xterm.css';

  // Sub-components
  import ConnectionStatusBar from './ConnectionStatusBar.svelte';
  import QuickActions from './QuickActions.svelte';
  import InfiniteKeypad from './InfiniteKeypad.svelte';
  import ThemeToggle from './ThemeToggle.svelte';

  let terminalContainer = $state(null);
  let fontSize = $state(parseInt(localStorage.getItem('corvus_font_size') || '13', 10));
  let suggestionChips = $state([]);
  let outputBuffer = $state('');
  let chipTimer = null;

  let showScrollDown = $state(false);

  // Cleanup refs
  let cleanupTwoFingerScroll = null;
  let cleanupKeyboardResize = null;
  let cleanupClickFocus = null;

  // Desktop = a precise pointer (mouse) and no coarse/touch pointer.
  // Used to auto-focus the terminal so a physical keyboard works without
  // requiring a tap, while leaving mobile behavior (no keyboard auto-pop) intact.
  const isDesktop =
    typeof window !== 'undefined' &&
    window.matchMedia('(pointer: fine)').matches &&
    !window.matchMedia('(pointer: coarse)').matches;

  // Focus the xterm textarea (physical keyboard / click-to-focus).
  function focusTerminal() {
    if (STATE.term) {
      try { STATE.term.focus(); } catch (e) {}
    }
  }

  // Re-focus the terminal on desktop whenever the socket (re)connects, so
  // typing works immediately without a manual click.
  $effect(() => {
    if (isDesktop && STATE.wsStatus === 'connected') {
      setTimeout(focusTerminal, 50);
    }
  });

  // Suggested patterns for chips
  const chipPatterns = [
    { regex: /\b(approve|permission|allow|accept)\b.*\?/i, chips: [
      { text: '✅ Yes, approve', cmd: 'y\r\n', cls: 'approve' },
      { text: '❌ No, reject', cmd: 'n\r\n', cls: 'reject' },
      { text: 'Show diff first', cmd: 'diff\r\n', cls: '' },
    ]},
    { regex: /\b(yes|no)\b.*\?/i, chips: [
      { text: 'Yes', cmd: 'yes\r\n', cls: 'approve' },
      { text: 'No', cmd: 'no\r\n', cls: 'reject' },
    ]},
    { regex: /\b(continue|proceed)\b.*\?/i, chips: [
      { text: '▶ Continue', cmd: '\r\n', cls: 'approve' },
      { text: '⏹ Stop', cmd: '\x03', cls: 'reject' },
    ]},
    { regex: /\berror\b|\bfailed\b|\btraceback\b/i, chips: [
      { text: '🔄 Retry', cmd: '!!\r\n', cls: '' },
      { text: '📖 Explain', cmd: 'explain the error\r\n', cls: '' },
      { text: '🛑 Cancel', cmd: '\x03', cls: 'reject' },
    ]},
    { regex: /\b(waiting|press enter|hit enter)\b/i, chips: [
      { text: '⏎ Enter', cmd: '\r\n', cls: 'approve' },
    ]},
    // NEW: git patterns
    { regex: /\bgit\b.*\b(merge|rebase|conflict)\b/i, chips: [
      { text: '✅ Accept', cmd: '\r\n', cls: 'approve' },
      { text: '⏹ Abort', cmd: '\x03', cls: 'reject' },
      { text: 'git status', cmd: 'git status\r\n', cls: '' },
    ]},
    // NEW: npm patterns
    { regex: /\bnpm\b.*\b(audit|install|update)\b.*\?/i, chips: [
      { text: 'Yes', cmd: 'yes\r\n', cls: 'approve' },
      { text: 'No', cmd: 'no\r\n', cls: 'reject' },
    ]},
  ];

  function requestExitToLauncher() {
    if (STATE.wsStatus === 'connected') {
      STATE.showExitConfirm = true;
    } else {
      disconnectTerminal(true);
      STATE.phase = 'launcher';
    }
  }

  // Handle Font change
  function handleFontChange(e) {
    fontSize = parseInt(e.target.value, 10);
    localStorage.setItem('corvus_font_size', String(fontSize));
    if (STATE.term) {
      STATE.term.options.fontSize = fontSize;
      setTimeout(() => {
        sendResize();
      }, 50);
    }
  }

  // Setup terminal
  onMount(() => {
    if (!terminalContainer) return;

    // Get terminal theme
    const termTheme = STATE.terminalTheme;

    // Create Terminal Instance
    const term = new Xterm({
      cursorBlink: true,
      cursorStyle: 'underline',
      fontSize: fontSize,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      theme: termTheme === 'light' ? {
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
      } : {
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
      },
      scrollback: 5000,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    // Mount DOM
    term.open(terminalContainer);
    
    // Canvas Hardware Acceleration (Universal Mobile optimization!)
    try {
      const canvasAddon = new CanvasAddon();
      term.loadAddon(canvasAddon);
      console.log('[xterm] Canvas hardware renderer loaded');
    } catch(e) {
      console.warn('[xterm] Canvas renderer load failed, falling back to DOM:', e);
    }

    // Trigger Initial Fit
    setTimeout(() => {
      try {
        fitAddon.fit();
      } catch(e) {}
      // On desktop, focus the terminal so the physical keyboard works
      // right away. On touch devices we skip this to avoid popping the
      // on-screen keyboard unexpectedly.
      if (isDesktop) focusTerminal();
    }, 150);

    // Click/tap anywhere in the terminal focuses it (fixes desktop typing,
    // harmless on mobile where xterm already focuses on touch).
    const onPointerDown = () => focusTerminal();
    terminalContainer.addEventListener('pointerdown', onPointerDown);
    cleanupClickFocus = () =>
      terminalContainer.removeEventListener('pointerdown', onPointerDown);

    // Save references to STATE
    STATE.term = term;
    STATE.fitAddon = fitAddon;

    // Track scroll position to show/hide "scroll to bottom" button
    term.onScroll(() => {
      const buf = term.buffer.active;
      const atBottom = buf.viewportY >= buf.baseY;
      showScrollDown = !atBottom;
    });
    term.onWriteParsed(() => {
      const buf = term.buffer.active;
      const atBottom = buf.viewportY >= buf.baseY;
      showScrollDown = !atBottom;
    });

    // Listen to keystrokes
    term.onData((data) => {
      wsSend({ type: 'input', data: data });
    });

    // Capture terminal text to parse suggestion chips
    const originalWrite = term.write.bind(term);
    term.write = (data) => {
      originalWrite(data);
      if (typeof data === 'string') {
        processOutputBuffer(data);
      }
    };

    // ── Two-finger scroll for terminal history ──
    cleanupTwoFingerScroll = setupTwoFingerScroll(terminalContainer, term);

    // ── Virtual keyboard resize handler ──
    cleanupKeyboardResize = setupKeyboardResize((keyboardHeight, viewportHeight) => {
      if (terminalContainer && STATE.fitAddon) {
        // Adjust terminal container height when keyboard appears
        if (keyboardHeight > 50) {
          // Keyboard is open
          terminalContainer.style.height = `${viewportHeight - terminalContainer.getBoundingClientRect().top}px`;
        } else {
          // Keyboard is closed
          terminalContainer.style.height = '';
        }
        try {
          STATE.fitAddon.fit();
          sendResize();
          // Auto-scroll to bottom so prompt is not hidden by the keyboard
          setTimeout(() => {
            if (STATE.term) {
              STATE.term.scrollToBottom();
            }
          }, 80);
        } catch(e) {}
      }
    });

    // Window Resize Handler
    window.addEventListener('resize', handleWindowResize);
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleWindowResize);
    if (chipTimer) clearTimeout(chipTimer);
    if (cleanupTwoFingerScroll) cleanupTwoFingerScroll();
    if (cleanupKeyboardResize) cleanupKeyboardResize();
    if (cleanupClickFocus) cleanupClickFocus();
    
    if (STATE.term) {
      try { STATE.term.dispose(); } catch(e) {}
      STATE.term = null;
    }
    STATE.fitAddon = null;
  });

  function handleWindowResize() {
    if (STATE.fitAddon && STATE.phase === 'terminal') {
      try {
        STATE.fitAddon.fit();
        sendResize();
      } catch(e) {}
    }
  }

  // Suggestion pattern parser
  function processOutputBuffer(data) {
    outputBuffer += data;
    if (outputBuffer.length > 2000) outputBuffer = outputBuffer.slice(-2000);
    
    if (chipTimer) clearTimeout(chipTimer);
    chipTimer = setTimeout(updateChips, 200);
  }

  function updateChips() {
    const tail = outputBuffer.slice(-500);
    let matched = null;
    
    for (let i = 0; i < chipPatterns.length; i++) {
      if (chipPatterns[i].regex.test(tail)) {
        matched = chipPatterns[i];
        break;
      }
    }
    
    if (matched) {
      suggestionChips = matched.chips;
    } else {
      suggestionChips = [];
    }
  }

  // Handle suggestion chip click
  function sendChip(cmd) {
    if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
    hapticTap();
    wsSend({ type: 'input', data: cmd });
    suggestionChips = [];
    outputBuffer = '';
    addRecent(cmd.replace(/[\r\n\x03]/g, '').trim());
  }

  // Send key sequence from keypad or quick actions
  function handleKeySend(seq) {
    wsSend({ type: 'input', data: seq });
  }

  function toggleKeyboard() {
    if (!STATE.term) return;
    const textarea = STATE.term.textarea;
    if (!textarea) return;
    
    if (document.activeElement === textarea) {
      textarea.blur();
    } else {
      textarea.focus();
    }
  }

  function runFavorite(fav) {
    if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
    hapticTap();
    wsSend({ type: 'input', data: fav + '\r\n' });
    addRecent(fav);
  }

  function getFolderBase(path) {
    if (!path) return '—';
    return path.split('\\').pop() || path.split('/').pop() || path;
  }

  function scrollToBottom() {
    if (STATE.term) {
      STATE.term.scrollToBottom();
      showScrollDown = false;
    }
  }
</script>

<div class="terminal-screen">
  
  <!-- Header bar -->
  <div class="term-header">
    <button class="header-back-btn" onclick={requestExitToLauncher} title="Back to Launcher">
      <ChevronLeft size={18} />
      <span>EXIT</span>
    </button>
    
    <div class="header-center">
      <div class="term-title">
        <Folder size={11} class="folder-ic" />
        <span>{getFolderBase(STATE.currentFolder)}</span>
      </div>
    </div>
    
    <div class="header-controls">
      <select class="font-select" value={fontSize} onchange={handleFontChange} aria-label="Font size">
        <option value={10}>10</option>
        <option value={11}>11</option>
        <option value={12}>12</option>
        <option value={13}>13</option>
        <option value={14}>14</option>
        <option value={15}>15</option>
        <option value={16}>16</option>
      </select>

      <button class="header-ctrl-btn" onclick={() => { hapticTap(); STATE.showFavModal = true; }} title="Favorites">
        <Star size={14} />
      </button>

      <button class="header-ctrl-btn kb-btn" onclick={toggleKeyboard} title="Toggle keyboard">
        <Keyboard size={14} />
      </button>

      <ThemeToggle />
    </div>
  </div>

  <!-- Connection Status Bar -->
  <ConnectionStatusBar />

  <!-- Main viewport -->
  <div class="terminal-wrapper">
    <!-- URL popup toast -->
    {#if STATE.urlToastVisible}
      <div class="url-toast-wrap">
        <a class="url-toast" href={STATE.urlToastHref} target="_blank" rel="noopener">
          <Globe size={13} />
          <span>{STATE.urlToastText}</span>
        </a>
        <button class="url-toast-close" onclick={hideUrlToast}>
          <X size={12} />
        </button>
      </div>
    {/if}

    <div bind:this={terminalContainer} class="terminal-container"></div>

    <!-- Scroll to bottom FAB -->
    {#if showScrollDown}
      <button class="scroll-fab" onclick={scrollToBottom} title="Scroll to bottom">
        <ArrowDownToLine size={16} />
      </button>
    {/if}
  </div>

  <!-- Smart Suggestion Chips -->
  {#if suggestionChips.length > 0}
    <div class="suggestion-bar">
      {#each suggestionChips as chip}
        <button 
          class="suggestion-chip" 
          class:approve={chip.cls === 'approve'} 
          class:reject={chip.cls === 'reject'} 
          onclick={() => sendChip(chip.cmd)}
        >
          {chip.text}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Command Favorites bar -->
  {#if STATE.favorites.length > 0}
    <div class="favorites-bar">
      <div class="fav-scroll">
        {#each STATE.favorites as fav}
          <button class="fav-chip" onclick={() => runFavorite(fav)}>
            {fav}
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Quick Actions -->
  <QuickActions onSend={handleKeySend} />

  <!-- Infinite Keypad Carousel -->
  <InfiniteKeypad onSend={handleKeySend} />

  <!-- Floating launcher shortcut -->
  <button class="launcher-fab" onclick={requestExitToLauncher} title="Back to launcher">
    <Home size={16} />
  </button>

</div>

<style>
  .terminal-screen {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    overflow: hidden;
    position: relative;
    animation: slideInRight 300ms ease-out;
    transition: background var(--transition-smooth);
  }

  @keyframes slideInRight {
    from { opacity: 0; transform: translateX(30px); }
    to { opacity: 1; transform: translateX(0); }
  }

  .term-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    padding-top: calc(10px + var(--safe-top));
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    font-family: var(--font-mono);
    transition: background var(--transition-smooth);
  }

  .header-back-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    background: rgba(239, 68, 68, 0.06);
    border: 1px solid rgba(239, 68, 68, 0.15);
    color: var(--red);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
  }

  .header-back-btn:hover {
    background: rgba(239, 68, 68, 0.12);
    border-color: rgba(239, 68, 68, 0.3);
  }

  .header-back-btn:active {
    transform: scale(0.95);
  }

  .header-center {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 0;
    max-width: 40%;
  }

  .term-title {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
    justify-content: center;
  }

  :global(.folder-ic) {
    color: var(--purple);
    flex-shrink: 0;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .font-select {
    background: var(--bg-card);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 4px 6px;
    font-family: var(--font-mono);
    font-size: 10px;
    outline: none;
    cursor: pointer;
  }

  .header-ctrl-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    cursor: pointer;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
  }

  .header-ctrl-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
    border-color: var(--border-hover);
  }

  .header-ctrl-btn:active {
    transform: scale(0.9);
  }

  .header-ctrl-btn.kb-btn {
    color: var(--purple);
  }

  /* Viewport wrapper */
  .terminal-wrapper {
    flex: 1;
    position: relative;
    overflow: hidden;
    padding: 4px;
    /* Prevent iOS overscroll on terminal area */
    overscroll-behavior: none;
  }

  /* touch-action:none is only needed on touch devices (tame iOS overscroll/
     gestures); on desktop it's unnecessary and can interfere with pointer
     handling, so scope it to coarse pointers. */
  @media (pointer: coarse) {
    .terminal-wrapper {
      touch-action: none;
    }
  }

  .terminal-container {
    width: 100%;
    height: 100%;
  }

  /* Override xterm rendering */
  :global(.xterm-viewport) {
    /* Prevent native scroll — we handle it with two-finger */
    overscroll-behavior: none;
  }

  /* URL Popup Toast */
  .url-toast-wrap {
    position: absolute;
    top: 8px;
    left: 8px;
    right: 8px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 100;
    padding: 10px 14px;
    font-family: var(--font-mono);
    box-shadow: var(--shadow-md);
    animation: slideDown 200ms ease-out;
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .url-toast {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--purple);
    text-decoration: none;
    font-size: 11px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .url-toast:hover {
    opacity: 0.8;
  }

  .url-toast-close {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-xs);
    transition: all var(--transition-fast);
  }

  .url-toast-close:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  /* Scroll to bottom FAB */
  .scroll-fab {
    position: absolute;
    bottom: 12px;
    right: 12px;
    width: 36px;
    height: 36px;
    background: var(--purple);
    color: #ffffff;
    border: none;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(144, 96, 255, 0.4);
    z-index: 50;
    animation: fadeIn 200ms ease-out;
    transition: all var(--transition-fast);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.8); }
    to { opacity: 1; transform: scale(1); }
  }

  .scroll-fab:active {
    transform: scale(0.9);
  }

  /* Suggestion chips */
  .suggestion-bar {
    display: flex;
    gap: 6px;
    padding: 6px 12px;
    overflow-x: auto;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    flex-shrink: 0;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    animation: slideUp 200ms ease-out;
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .suggestion-bar::-webkit-scrollbar {
    display: none;
  }

  .suggestion-chip {
    flex-shrink: 0;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 7px 14px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    user-select: none;
    -webkit-user-select: none;
    touch-action: manipulation;
  }

  .suggestion-chip:hover {
    color: var(--text-primary);
    border-color: var(--border-hover);
  }

  .suggestion-chip:active {
    transform: scale(0.95);
  }

  .suggestion-chip.approve {
    border-color: rgba(16, 185, 129, 0.4);
    color: var(--green);
    background: rgba(16, 185, 129, 0.05);
  }

  .suggestion-chip.approve:hover {
    background: rgba(16, 185, 129, 0.1);
  }

  .suggestion-chip.reject {
    border-color: rgba(239, 68, 68, 0.4);
    color: var(--red);
    background: rgba(239, 68, 68, 0.05);
  }

  .suggestion-chip.reject:hover {
    background: rgba(239, 68, 68, 0.1);
  }

  /* Favorites bar */
  .favorites-bar {
    display: flex;
    align-items: center;
    background: var(--bg-primary);
    border-top: 1px solid var(--border);
    padding: 4px 12px;
    flex-shrink: 0;
  }

  .fav-scroll {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    flex: 1;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
    align-items: center;
    height: 32px;
  }

  .fav-scroll::-webkit-scrollbar {
    display: none;
  }

  .fav-chip {
    flex-shrink: 0;
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 4px 10px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 10px;
    cursor: pointer;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: all var(--transition-fast);
    touch-action: manipulation;
  }

  .fav-chip:hover {
    color: var(--text-primary);
    border-color: var(--border-hover);
  }

  .fav-chip:active {
    transform: scale(0.95);
  }

  /* Floating launcher shortcut */
  .launcher-fab {
    position: absolute;
    bottom: 100px;
    left: 12px;
    width: 40px;
    height: 40px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border-light);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: var(--shadow-md);
    z-index: 40;
    opacity: 0.6;
    transition: all var(--transition-fast);
  }

  .launcher-fab:hover {
    opacity: 1;
    color: var(--text-primary);
    border-color: var(--border-hover);
  }

  .launcher-fab:active {
    transform: scale(0.9);
    opacity: 1;
  }
</style>
