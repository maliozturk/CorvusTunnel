<script>
  import { STATE } from './state.svelte.js';
  import { api } from './api.js';
  import { X, ArrowLeft, RefreshCw, Calendar, MessageSquare, Terminal, Eye } from 'lucide-svelte';

  let sessions = $state([]);
  let stats = $state(null);
  let loaded = $state(false);
  let loading = $state(false);
  let error = $state('');

  let currentAgent = $state(''); // '' means All, otherwise 'claude', 'codex', 'antigravity'
  
  // Conversation Detail View
  let activeSessionId = $state(null);
  let activeSession = $state(null);
  let messages = $state([]);
  let totalMessages = $state(0);
  let convoOffset = $state(0);
  let loadingMessages = $state(false);
  let detailView = $state(false); // false = list, true = detail

  // Trigger history loading when panel opens
  $effect(() => {
    if (STATE.showHistoryPanel) {
      if (!loaded) {
        loadHistory();
      }
    }
  });

  async function loadHistory() {
    loading = true;
    error = '';
    try {
      // 1. Load stats
      const statsResp = await api('/api/history/stats');
      if (statsResp.ok) {
        stats = await statsResp.json();
      }
      
      // 2. Load sessions
      let url = '/api/history/sessions?limit=200';
      const r = await api(url);
      if (!r.ok) throw new Error('Failed to load session history');
      const data = await r.json();
      sessions = data.sessions || [];
      loaded = true;
    } catch (err) {
      error = err.message || 'Error loading history';
    } finally {
      loading = false;
    }
  }

  function handleClose() {
    STATE.showHistoryPanel = false;
    detailView = false;
    activeSessionId = null;
    activeSession = null;
  }

  const agentNames = {
    antigravity: 'Antigravity',
    claude: 'Claude Code',
    codex: 'Codex'
  };

  const filteredSessions = $derived.by(() => {
    if (!currentAgent) return sessions;
    return sessions.filter(s => s.agent === currentAgent);
  });

  async function openConversation(session) {
    activeSessionId = session.id;
    activeSession = session;
    messages = [];
    convoOffset = 0;
    totalMessages = 0;
    detailView = true;
    
    loadingMessages = true;
    try {
      const r = await api(`/api/history/sessions/${encodeURIComponent(session.id)}?limit=100&offset=0`);
      if (!r.ok) throw new Error('Failed to load conversation');
      const data = await r.json();
      messages = data.messages || [];
      totalMessages = data.total || 0;
      convoOffset = messages.length;
    } catch (err) {
      console.error(err);
    } finally {
      loadingMessages = false;
    }
  }

  async function loadMoreMessages() {
    if (!activeSessionId || loadingMessages) return;
    
    try {
      const r = await api(`/api/history/sessions/${encodeURIComponent(activeSessionId)}?limit=100&offset=${convoOffset}`);
      if (!r.ok) throw new Error('Failed to load messages');
      const data = await r.json();
      const newMsgs = data.messages || [];
      messages = [...messages, ...newMsgs];
      convoOffset += newMsgs.length;
    } catch (err) {
      console.error(err);
    }
  }

  function formatHistoryTime(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const now = new Date();
      const diff = now - d;
      
      if (d.toDateString() === now.toDateString()) {
        return 'Today ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      if (d.toDateString() === yesterday.toDateString()) {
        return 'Yesterday ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      
      if (diff < 7 * 24 * 60 * 60 * 1000) {
        return d.toLocaleDateString([], { weekday: 'short' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return iso.substring(0, 10);
    }
  }

  function getProjectName(projectPath) {
    if (!projectPath) return '';
    const parts = projectPath.replace(/\\/g, '/').split('/');
    return parts[parts.length - 1] || projectPath;
  }

  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMsgContent(text) {
    if (!text) return '';
    
    let isTruncated = false;
    if (text.length > 3000) {
      text = text.substring(0, 3000);
      isTruncated = true;
    }
    
    let html = escapeHtml(text);
    
    // Code blocks: ```...```
    html = html.replace(/```([\s\S]*?)```/g, (_, code) => {
      return `<pre class="convo-pre-code">${code.trim()}</pre>`;
    });
    
    // Inline code: `...`
    html = html.replace(/`([^`]+)`/g, '<code class="convo-code">$1</code>');
    
    // Bold: **...**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    if (isTruncated) {
      html += `<div class="convo-truncated-msg">Message truncated for mobile readability...</div>`;
    }
    
    return html;
  }
</script>

{#if STATE.showHistoryPanel}
  <div class="history-overlay" onclick={handleClose} onkeydown={(e) => e.key === 'Escape' && handleClose()} role="button" tabIndex={0}></div>
  <div class="history-panel">
    
    <!-- ── 1. List View ─────────────────────────────────────────────── -->
    {#if !detailView}
      <div class="history-layout">
        <div class="history-header">
          <div>
            <div class="history-title">CONVERSATION_HISTORY</div>
            <div class="history-subtitle">
              {currentAgent ? agentNames[currentAgent] : 'All agents'}
            </div>
          </div>
          <button class="close-btn" onclick={handleClose} aria-label="Close logs">
            <X size={18} />
          </button>
        </div>

        <!-- Filter tabs -->
        {#if stats}
          <div class="history-tabs">
            <button class="history-tab" class:active={currentAgent === ''} onclick={() => currentAgent = ''}>
              ALL <span class="tab-count">{stats.total_sessions || 0}</span>
            </button>
            <button class="history-tab" class:active={currentAgent === 'antigravity'} onclick={() => currentAgent = 'antigravity'}>
              ANTIGRAVITY <span class="tab-count">{stats.by_agent?.antigravity || 0}</span>
            </button>
            <button class="history-tab" class:active={currentAgent === 'claude'} onclick={() => currentAgent = 'claude'}>
              CLAUDE <span class="tab-count">{stats.by_agent?.claude || 0}</span>
            </button>
            <button class="history-tab" class:active={currentAgent === 'codex'} onclick={() => currentAgent = 'codex'}>
              CODEX <span class="tab-count">{stats.by_agent?.codex || 0}</span>
            </button>
          </div>
        {/if}

        <div class="history-list">
          {#if loading}
            <div class="list-msg">
              <RefreshCw class="spin-icon" size={16} />
              <span>Fetching disk cache...</span>
            </div>
          {:else if error}
            <div class="list-msg error">{error}</div>
          {:else if filteredSessions.length === 0}
            <div class="list-msg empty">No recorded session found.</div>
          {:else}
            {#each filteredSessions as session}
              <button class="history-card" onclick={() => openConversation(session)}>
                <div class="card-left">
                  <div class="card-agent-badge" class:ag-antigravity={session.agent === 'antigravity'} class:ag-claude={session.agent === 'claude'} class:ag-codex={session.agent === 'codex'}>
                    {session.agent.substring(0, 2).toUpperCase()}
                  </div>
                </div>
                <div class="card-right">
                  <div class="card-top">
                    <span class="card-agent-label">{agentNames[session.agent] || session.agent}</span>
                    <span class="card-time">{formatHistoryTime(session.started_at)}</span>
                  </div>
                  <div class="card-title">{session.title || 'Untitled session'}</div>
                  <div class="card-meta">
                    {#if session.project}
                      <span class="meta-item">
                        <Terminal size={10} />
                        {getProjectName(session.project)}
                      </span>
                    {/if}
                    <span class="meta-item">
                      <MessageSquare size={10} />
                      {session.message_count || 0} msgs
                    </span>
                  </div>
                </div>
              </button>
            {/each}
          {/if}
        </div>
      </div>

    <!-- ── 2. Conversation Detail View ────────────────────────────── -->
    {:else}
      <div class="history-layout">
        <div class="history-header">
          <button class="back-btn" onclick={() => detailView = false} aria-label="Go back to list">
            <ArrowLeft size={18} />
          </button>
          <div class="convo-header-info">
            <div class="convo-title">{activeSession?.title || 'Conversation'}</div>
            <div class="convo-subtitle">
              {agentNames[activeSession?.agent] || activeSession?.agent}
              {activeSession?.project ? ` · ${getProjectName(activeSession.project)}` : ''}
            </div>
          </div>
          <button class="close-btn" onclick={handleClose} aria-label="Close logs">
            <X size={18} />
          </button>
        </div>

        <div class="history-convo-container">
          {#if loadingMessages}
            <div class="convo-status-msg">
              <RefreshCw class="spin-icon" size={16} />
              <span>Decrypting history...</span>
            </div>
          {:else}
            <div class="convo-scroll">
              {#each messages as msg}
                <div class="history-msg" class:msg-user={msg.role === 'user'} class:msg-assistant={msg.role === 'assistant'} class:msg-system={msg.role === 'system'}>
                  <div class="msg-role-lbl">{msg.role.toUpperCase()}</div>
                  <div class="msg-content">
                    {@html formatMsgContent(msg.content)}
                  </div>
                  {#if msg.timestamp}
                    <div class="msg-time-lbl">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  {/if}
                </div>
              {/each}
              
              {#if convoOffset < totalMessages}
                <div class="load-more-container">
                  <button class="load-more-btn" onclick={loadMoreMessages}>
                    LOAD MORE ({totalMessages - convoOffset} REMAINING)
                  </button>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    {/if}

  </div>
{/if}

<style>
  .history-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1500;
  }

  .history-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    max-width: 480px;
    background: #000000;
    border-left: 1px solid var(--border);
    z-index: 1600;
    display: flex;
    flex-direction: column;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.9);
    font-family: var(--font-mono);
  }

  .history-layout {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .history-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid var(--border);
    background: #000000;
    gap: 12px;
  }

  .history-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #ffffff;
  }

  .history-subtitle {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 3px;
  }

  .close-btn, .back-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color var(--transition-fast);
  }

  .close-btn:hover, .back-btn:hover {
    color: #ffffff;
  }

  .history-tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
    background: #080808;
    overflow-x: auto;
    scrollbar-width: none;
  }
  
  .history-tabs::-webkit-scrollbar {
    display: none;
  }

  .history-tab {
    flex: 1;
    min-width: 90px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 12px 6px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    cursor: pointer;
    text-align: center;
    transition: all var(--transition-fast);
    white-space: nowrap;
  }

  .history-tab:hover {
    color: var(--text-secondary);
  }

  .history-tab.active {
    color: #ffffff;
    border-color: #ffffff;
    background: #000000;
  }

  .tab-count {
    font-size: 9px;
    color: var(--text-dim);
    background: #141414;
    padding: 1px 4px;
    border-radius: 2px;
    margin-left: 2px;
  }

  .history-tab.active .tab-count {
    color: var(--text-secondary);
    background: #202020;
  }

  .history-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    -webkit-overflow-scrolling: touch;
  }

  .list-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
    padding: 32px 0;
  }

  .list-msg.error {
    color: var(--red);
  }

  :global(.spin-icon) {
    animation: spin 2s linear infinite;
  }

  @keyframes spin {
    100% { transform: rotate(360deg); }
  }

  .history-card {
    display: flex;
    width: 100%;
    background: #050505;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px;
    cursor: pointer;
    text-align: left;
    transition: all var(--transition-fast);
  }

  .history-card:hover {
    background: #0d0d0d;
    border-color: var(--text-secondary);
  }

  .card-left {
    margin-right: 12px;
    display: flex;
    align-items: flex-start;
  }

  .card-agent-badge {
    width: 28px;
    height: 28px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    color: var(--text-secondary);
  }

  .card-agent-badge.ag-antigravity {
    color: var(--purple);
    border-color: rgba(144, 96, 255, 0.3);
  }

  .card-agent-badge.ag-claude {
    color: #f97316;
    border-color: rgba(249, 115, 22, 0.3);
  }

  .card-agent-badge.ag-codex {
    color: var(--green);
    border-color: rgba(16, 185, 129, 0.3);
  }

  .card-right {
    flex: 1;
    min-width: 0;
  }

  .card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10px;
    margin-bottom: 4px;
  }

  .card-agent-label {
    color: var(--text-muted);
    font-weight: 700;
    text-transform: uppercase;
  }

  .card-time {
    color: var(--text-dim);
  }

  .card-title {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-meta {
    display: flex;
    gap: 12px;
    font-size: 10px;
    color: var(--text-muted);
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* ── Conversation detail styles ── */
  .convo-header-info {
    flex: 1;
    min-width: 0;
  }

  .convo-title {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .convo-subtitle {
    font-size: 10px;
    color: var(--text-secondary);
    margin-top: 2px;
  }

  .history-convo-container {
    flex: 1;
    overflow: hidden;
    background: #000000;
    display: flex;
    flex-direction: column;
  }

  .convo-status-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
    padding: 40px;
  }

  .convo-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    -webkit-overflow-scrolling: touch;
  }

  .history-msg {
    max-width: 90%;
    padding: 12px 14px;
    border-radius: var(--radius-sm);
    font-size: 12px;
    line-height: 1.5;
    word-break: break-word;
  }

  .history-msg.msg-user {
    align-self: flex-end;
    background: #080808;
    border: 1px solid var(--border);
    color: #ffffff;
  }

  .history-msg.msg-assistant {
    align-self: flex-start;
    background: #000000;
    border: 1px solid var(--border);
    color: var(--text-secondary);
  }

  .history-msg.msg-system {
    align-self: center;
    background: #0c0c0c;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 10px;
    text-align: center;
    padding: 6px 12px;
    max-width: 80%;
  }

  .msg-role-lbl {
    font-size: 9px;
    font-weight: 700;
    color: var(--text-dim);
    margin-bottom: 6px;
    letter-spacing: 0.5px;
  }

  .history-msg.msg-user .msg-role-lbl {
    color: var(--purple);
  }

  .msg-content {
    white-space: pre-wrap;
  }

  :global(.convo-code) {
    font-family: var(--font-mono);
    font-size: 11px;
    background: #101010;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 1px 4px;
    border-radius: 2px;
    color: #ffffff;
  }

  :global(.convo-pre-code) {
    font-family: var(--font-mono);
    font-size: 11px;
    background: #050505;
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 8px 10px;
    margin: 8px 0;
    overflow-x: auto;
    color: #e0e0e0;
    line-height: 1.4;
  }

  :global(.convo-truncated-msg) {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 6px;
    font-style: italic;
  }

  .msg-time-lbl {
    font-size: 9px;
    color: var(--text-dim);
    margin-top: 6px;
    text-align: right;
  }

  .load-more-container {
    display: flex;
    justify-content: center;
    padding: 16px 0;
  }

  .load-more-btn {
    background: #080808;
    color: var(--text-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 16px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .load-more-btn:hover {
    background: #141414;
    color: #ffffff;
  }
</style>
