<script>
  import { onMount, onDestroy } from 'svelte';
  import { STATE, disconnectTerminal, sendResize, hideUrlToast, addRecent } from './state.svelte.js';
  import { Terminal as Xterm } from '@xterm/xterm';
  import { FitAddon } from '@xterm/addon-fit';
  import { CanvasAddon } from '@xterm/addon-canvas';
  import { WebLinksAddon } from '@xterm/addon-web-links';
  import { 
    ChevronLeft, Settings, Keyboard, Star, HelpCircle, 
    CornerDownLeft, Compass, Globe, Folder, ShieldCheck, ChevronUp, ChevronDown, ArrowDownToLine, Bot, Trash2 
  } from 'lucide-svelte';

  // CSS for xterm
  import '@xterm/xterm/css/xterm.css';

  let terminalContainer = $state(null);
  let fontSize = $state(13);
  let suggestionChips = $state([]);
  let outputBuffer = $state('');
  let chipTimer = null;

  // Virtual Keypad States
  let ctrlActive = $state(false);
  let altActive = $state(false);
  let showScrollDown = $state(false);

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
  ];

  function backToLauncher() {
    disconnectTerminal(true);
    STATE.phase = 'launcher';
  }

  // Handle local Font change
  function handleFontChange(e) {
    fontSize = parseInt(e.target.value, 10);
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

    // Create Terminal Instance
    const term = new Xterm({
      cursorBlink: true,
      cursorStyle: 'underline',
      fontSize: fontSize,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      theme: {
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
      STATE.canvasAddon = canvasAddon;
      console.log('[xterm] Canvas hardware renderer loaded');
    } catch(e) {
      console.warn('[xterm] Canvas renderer load failed, falling back to DOM:', e);
    }

    // Trigger Initial Fit
    setTimeout(() => {
      try {
        fitAddon.fit();
      } catch(e) {}
    }, 150);

    // Save references to STATE
    STATE.term = term;
    STATE.fitAddon = fitAddon;

    // Track scroll position to show/hide "scroll to bottom" button
    // Use xterm's native scroll API (DOM scroll events don't fire reliably on mobile)
    term.onScroll(() => {
      const buf = term.buffer.active;
      const atBottom = buf.viewportY >= buf.baseY;
      showScrollDown = !atBottom;
    });
    // Also detect when new content arrives and user is scrolled up
    term.onWriteParsed(() => {
      const buf = term.buffer.active;
      const atBottom = buf.viewportY >= buf.baseY;
      showScrollDown = !atBottom;
    });

    // Listen to keystrokes
    term.onData((data) => {
      if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;

      let sendData = data;
      
      if (ctrlActive && sendData.length === 1) {
        const code = sendData.toUpperCase().charCodeAt(0);
        if (code >= 64 && code <= 95) {
          sendData = String.fromCharCode(code - 64);
        }
        ctrlActive = false;
      }
      
      if (altActive && sendData.length === 1) {
        sendData = '\x1b' + sendData;
        altActive = false;
      }

      STATE.ws.send(JSON.stringify({ type: 'input', data: sendData }));
    });

    // Capture terminal text to parse suggestion chips
    term.onWriteParsed && term.onWriteParsed(() => {}); // placeholder for deep hook
    
    // Custom write wrapper to feed buffer
    const originalWrite = term.write.bind(term);
    term.write = (data) => {
      originalWrite(data);
      // Process buffer
      if (typeof data === 'string') {
        processOutputBuffer(data);
      }
    };

    // Window Resize Handler
    window.addEventListener('resize', handleWindowResize);
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleWindowResize);
    if (chipTimer) clearTimeout(chipTimer);
    
    if (STATE.term) {
      try { STATE.term.dispose(); } catch(e) {}
      STATE.term = null;
    }
    STATE.fitAddon = null;
    STATE.canvasAddon = null;
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
    STATE.ws.send(JSON.stringify({ type: 'input', data: cmd }));
    suggestionChips = [];
    outputBuffer = '';
    
    // Add to history
    addRecent(cmd.replace(/[\r\n\x03]/g, '').trim());
  }

  // Send virtual key sequences
  function sendVK(seq) {
    if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
    STATE.ws.send(JSON.stringify({ type: 'input', data: seq }));
  }

  function toggleVK(which) {
    if (which === 'ctrl') {
      ctrlActive = !ctrlActive;
      altActive = false;
    } else {
      altActive = !altActive;
      ctrlActive = false;
    }
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
    STATE.ws.send(JSON.stringify({ type: 'input', data: fav + '\r\n' }));
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

  function sendAgentCommand(cmd) {
    if (!STATE.ws || STATE.ws.readyState !== WebSocket.OPEN) return;
    STATE.ws.send(JSON.stringify({ type: 'input', data: cmd + '\r\n' }));
  }
</script>

<div class="terminal-screen" class:collapsed={STATE.terminalCollapsed}>
  
  <!-- Header bar -->
  <div class="term-header">
    <button class="header-back-btn" onclick={backToLauncher} title="Back to Launcher">
      <ChevronLeft size={16} />
      <span>EXIT</span>
    </button>
    
    <div class="header-center">
      <div class="term-title">
        <Folder size={11} class="folder-ic" />
        <span>{getFolderBase(STATE.currentFolder)}</span>
      </div>
      <div class="term-status" class:online={STATE.wsStatus === 'connected'} class:connecting={STATE.wsStatus === 'connecting'}>
        {STATE.wsStatus.toUpperCase()}
      </div>
    </div>
    
    <div class="header-controls">
      <select class="font-select" value={fontSize} onchange={handleFontChange} aria-label="Font size">
        <option value={11}>11px</option>
        <option value={12}>12px</option>
        <option value={13}>13px</option>
        <option value={14}>14px</option>
        <option value={15}>15px</option>
        <option value={16}>16px</option>
      </select>

      <button class="header-ctrl-btn" onclick={() => sendAgentCommand('/model')} title="Change model">
        <Bot size={14} />
      </button>

      <button class="header-ctrl-btn" onclick={() => sendAgentCommand('/clear')} title="Clear terminal">
        <Trash2 size={14} />
      </button>

      <button class="header-ctrl-btn" onclick={() => STATE.showFavModal = true} title="Favorites">
        <Star size={14} />
      </button>
    </div>
  </div>

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
  <div class="favorites-bar">
    <div class="fav-scroll">
      {#if STATE.favorites.length === 0}
        <span class="fav-empty-lbl">No shortcuts configured</span>
      {:else}
        {#each STATE.favorites as fav}
          <button class="fav-chip" onclick={() => runFavorite(fav)}>
            {fav}
          </button>
        {/each}
      {/if}
    </div>
    
    <!-- Collapse controls -->
    <button class="collapse-btn" onclick={() => STATE.terminalCollapsed = !STATE.terminalCollapsed}>
      {#if STATE.terminalCollapsed}
        <ChevronUp size={14} />
      {:else}
        <ChevronDown size={14} />
      {/if}
    </button>
  </div>

  <!-- Keyboard keypad -->
  <div class="keypad-bar">
    <button class="keypad-btn active-toggle" class:active={ctrlActive} onclick={() => toggleVK('ctrl')}>
      CTRL
    </button>
    <button class="keypad-btn" onclick={() => sendVK('\x1b')}>
      ESC
    </button>
    <button class="keypad-btn arrow" onclick={() => sendVK('\x1b[A')}>
      ▲
    </button>
    <button class="keypad-btn arrow" onclick={() => sendVK('\x1b[B')}>
      ▼
    </button>
    <button class="keypad-btn arrow" onclick={() => sendVK('\x1b[D')}>
      ◀
    </button>
    <button class="keypad-btn arrow" onclick={() => sendVK('\x1b[C')}>
      ▶
    </button>
    <button class="keypad-btn enter" onclick={() => sendVK('\r')}>
      ⏎
    </button>
    <button class="keypad-btn scroll-bottom" onclick={scrollToBottom} title="Scroll to bottom">
      <ArrowDownToLine size={14} />
    </button>
    <button class="keypad-btn kb-toggle" onclick={toggleKeyboard}>
      <Keyboard size={14} />
    </button>
  </div>

</div>

<style>
  .terminal-screen {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #000000;
    overflow: hidden;
    position: relative;
  }

  .term-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: #000000;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    font-family: var(--font-mono);
  }

  .header-back-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    padding: 4px 6px;
    border-radius: var(--radius-sm);
  }

  .header-back-btn:hover {
    color: #ffffff;
    background: #0c0c0c;
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
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
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

  .term-status {
    font-size: 8px;
    font-weight: 700;
    color: var(--text-muted);
    margin-top: 2px;
    letter-spacing: 0.5px;
  }

  .term-status.online {
    color: var(--green);
  }

  .term-status.connecting {
    color: var(--yellow);
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .font-select {
    background: #000000;
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 3px 6px;
    font-family: var(--font-mono);
    font-size: 10px;
    outline: none;
  }

  .header-ctrl-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-secondary);
    cursor: pointer;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition-fast);
  }

  .header-ctrl-btn:hover {
    color: #ffffff;
    background: #0c0c0c;
    border-color: var(--text-secondary);
  }

  /* Viewport wrapper */
  .terminal-wrapper {
    flex: 1;
    position: relative;
    overflow: hidden;
    background: #000000;
    padding: 6px;
  }

  .terminal-container {
    width: 100%;
    height: 100%;
  }

  /* Override xterm rendering to make it cleaner */
  :global(.xterm-viewport) {
    background-color: #000000 !important;
  }
  
  :global(.xterm-screen) {
    background-color: #000000 !important;
  }

  /* URL Popup Toast */
  .url-toast-wrap {
    position: absolute;
    top: 8px;
    left: 8px;
    right: 8px;
    background: #0c0c0c;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 100;
    padding: 8px 12px;
    font-family: var(--font-mono);
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
    color: #c084fc;
  }

  .url-toast-close {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .url-toast-close:hover {
    color: #ffffff;
  }


  /* Suggestion chips */
  .suggestion-bar {
    display: flex;
    gap: 6px;
    padding: 6px 12px;
    overflow-x: auto;
    background: #080808;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }

  .suggestion-bar::-webkit-scrollbar {
    display: none;
  }

  .suggestion-chip {
    flex-shrink: 0;
    background: #141414;
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 6px 12px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .suggestion-chip:hover {
    color: #ffffff;
    border-color: var(--text-secondary);
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
    background: #000000;
    border-top: 1px solid var(--border);
    padding: 4px 12px;
    flex-shrink: 0;
    gap: 8px;
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

  .fav-empty-lbl {
    font-size: 10px;
    color: var(--text-dim);
    font-family: var(--font-mono);
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
  }

  .fav-chip:hover {
    color: #ffffff;
    border-color: var(--text-secondary);
  }

  .collapse-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .collapse-btn:hover {
    color: #ffffff;
  }

  /* Keypad bar */
  .keypad-bar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    background: #000000;
    border-top: 1px solid var(--border);
    padding: 4px;
    gap: 4px;
    flex-shrink: 0;
  }

  .terminal-screen.collapsed .keypad-bar {
    display: none;
  }

  .keypad-btn {
    background: #080808;
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 0;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
    -webkit-user-select: none;
    touch-action: manipulation;
    transition: all var(--transition-fast);
  }

  .keypad-btn:active {
    background: #141414;
    transform: scale(0.96);
  }

  .keypad-btn.active-toggle.active {
    background: rgba(144, 96, 255, 0.15);
    border-color: var(--purple);
    color: var(--purple);
  }

  .keypad-btn.arrow {
    background: #0a0a0a;
    font-size: 12px;
  }

  .keypad-btn.kb-toggle {
    color: var(--purple);
    background: #080808;
  }

  .keypad-btn.enter {
    color: var(--green);
    font-size: 14px;
  }

  .keypad-btn.scroll-bottom {
    color: var(--purple);
  }
</style>
