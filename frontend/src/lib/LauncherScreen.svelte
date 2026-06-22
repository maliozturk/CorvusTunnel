<script>
  import { STATE, connectTerminal, handleLogout, hapticTap, resetOnboarding } from './state.svelte.js';
  import { FolderOpen, Play, AlertTriangle, ChevronDown, ChevronUp, Settings, LogOut, Bell, BellOff, HelpCircle, Star, ExternalLink } from 'lucide-svelte';
  import ThemeToggle from './ThemeToggle.svelte';
  import CorvusIcon from './CorvusIcon.svelte';

  // Extract directory name for friendly display
  const folderName = $derived.by(() => {
    const path = STATE.currentFolder;
    if (!path) return 'No folder selected';
    return path.split('\\').pop() || path.split('/').pop() || path;
  });

  // Calculate connection button eligibility
  const selectedAgentInfo = $derived(
    STATE.agents.find(a => a.name === STATE.selectedAgent)
  );
  
  const isAgentAvailable = $derived(
    selectedAgentInfo ? selectedAgentInfo.available : false
  );

  const canConnect = $derived(
    isAgentAvailable && STATE.currentFolder !== '' && STATE.currentFolder !== 'Projects'
  );

  let notificationsEnabled = $state(
    typeof Notification !== 'undefined' && Notification.permission === 'granted'
  );

  function selectAgent(agent) {
    if (!agent.available) return;
    hapticTap();
    STATE.selectedAgent = agent.name;
    localStorage.setItem('corvus_agent', agent.name);
  }

  function handleConnectClick() {
    if (!canConnect) return;
    hapticTap();
    STATE.phase = 'terminal';
    connectTerminal();
  }



  function toggleNotifications() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') {
      // Can't revoke, just toggle local flag
      notificationsEnabled = !notificationsEnabled;
      localStorage.setItem('corvus_notif_enabled', notificationsEnabled ? 'true' : 'false');
    } else {
      Notification.requestPermission().then((perm) => {
        if (perm === 'granted') {
          notificationsEnabled = true;
          localStorage.setItem('corvus_notif_enabled', 'true');
        }
      });
    }
  }

  function showHelp() {
    resetOnboarding();
    STATE.showOnboarding = true;
  }
</script>

<div class="launcher-screen">
  <div class="launcher-container">
    
    <!-- Workspace Folder Card -->
    <div class="section-title">WORKSPACE_DIRECTORY</div>
    <button class="folder-card" onclick={() => STATE.showFolderModal = true}>
      <div class="folder-icon-wrap">
        <FolderOpen size={20} />
      </div>
      <div class="folder-info">
        <div class="folder-display-name" class:empty={!STATE.currentFolder}>
          {folderName}
        </div>
        <div class="folder-full-path">
          {STATE.currentFolder || 'Tap to browse directories'}
        </div>
      </div>
    </button>

    <!-- Agent Selector -->
    <div class="section-title">ACTIVE_AI_AGENT</div>
    <div class="agent-grid">
      {#if STATE.agents.length === 0}
        <div class="agents-loading">Checking system path...</div>
      {:else}
        {#each STATE.agents as agent}
          <button
            class="agent-card"
            class:selected={STATE.selectedAgent === agent.name}
            disabled={!agent.available}
            onclick={() => selectAgent(agent)}
          >
            <span class="agent-title">{agent.name.toUpperCase()}</span>
            <span class="agent-status">
              {agent.available ? 'AVAILABLE' : 'NOT_INSTALLED'}
            </span>
          </button>
        {/each}
      {/if}
    </div>



    <!-- Connection Launcher Button -->
    <div class="action-wrap">
      <button
        class="connect-launch-btn"
        disabled={!canConnect}
        onclick={handleConnectClick}
      >
        <Play size={16} fill="currentColor" />
        <span>CONNECT_TO_{STATE.selectedAgent.toUpperCase()}</span>
      </button>

      <!-- Connection Hints -->
      {#if STATE.agents.length > 0}
        {#if !isAgentAvailable}
          <div class="connect-hint error">
            <AlertTriangle size={12} />
            <span>Agent '{STATE.selectedAgent}' is not installed in the container environment.</span>
          </div>
        {:else if !STATE.currentFolder || STATE.currentFolder === 'Projects'}
          <div class="connect-hint">
            <span>Choose a project workspace folder to start coding.</span>
          </div>
        {/if}
      {/if}
    </div>

    <!-- Settings Panel (Collapsible) -->
    <div class="settings-section">
      <button class="settings-header" onclick={() => { hapticTap(); STATE.showSettings = !STATE.showSettings; }}>
        <div class="settings-header-left">
          <Settings size={14} />
          <span>SETTINGS</span>
        </div>
        {#if STATE.showSettings}
          <ChevronUp size={14} />
        {:else}
          <ChevronDown size={14} />
        {/if}
      </button>

      {#if STATE.showSettings}
        <div class="settings-body">
          <!-- Theme (drives both the app and the terminal) -->
          <div class="setting-row">
            <div class="setting-info">
              <div class="setting-label">Theme</div>
              <div class="setting-desc">Switch between dark and light mode</div>
            </div>
            <ThemeToggle />
          </div>

          <!-- Notifications -->
          <div class="setting-row">
            <div class="setting-info">
              <div class="setting-label">Notifications</div>
              <div class="setting-desc">Alert when agent completes jobs</div>
            </div>
            <button class="setting-toggle-btn" onclick={toggleNotifications}>
              {#if notificationsEnabled}
                <Bell size={14} />
                <span>ON</span>
              {:else}
                <BellOff size={14} />
                <span>OFF</span>
              {/if}
            </button>
          </div>

          <!-- Show Walkthrough -->
          <div class="setting-row">
            <div class="setting-info">
              <div class="setting-label">Walkthrough</div>
              <div class="setting-desc">Re-show the getting started guide</div>
            </div>
            <button class="setting-toggle-btn" onclick={showHelp}>
              <HelpCircle size={14} />
              <span>SHOW</span>
            </button>
          </div>

          <!-- Logout -->
          <button class="logout-btn" onclick={handleLogout}>
            <LogOut size={14} />
            <span>LOGOUT</span>
          </button>
        </div>
      {/if}
    </div>

    <!-- GitHub Star -->
    <a class="github-star-link" href="https://github.com/maliozturk/CorvusTunnel" target="_blank" rel="noopener">
      <Star size={13} />
      <span>Star on GitHub</span>
      <ExternalLink size={10} />
    </a>

  </div>
</div>

<style>
  .launcher-screen {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 24px 16px;
    padding-bottom: calc(40px + var(--safe-bottom));
    background: var(--bg-primary);
    display: flex;
    justify-content: center;
    align-items: flex-start;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
    transition: background var(--transition-smooth);
  }

  .launcher-container {
    width: 100%;
    max-width: 440px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    animation: fadeInUp 400ms ease-out;
  }

  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .section-title {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 2px;
  }

  /* Folder Card */
  .folder-card {
    display: flex;
    align-items: center;
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 16px 18px;
    cursor: pointer;
    text-align: left;
    transition: all var(--transition-fast);
    box-shadow: var(--shadow-sm);
  }

  .folder-card:hover {
    background: var(--bg-hover);
    border-color: var(--border-hover);
    box-shadow: var(--shadow-md);
  }

  .folder-card:active {
    transform: scale(0.99);
  }

  .folder-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--purple);
    margin-right: 14px;
    flex-shrink: 0;
  }

  .folder-info {
    flex: 1;
    min-width: 0;
  }

  .folder-display-name {
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.2;
  }

  .folder-display-name.empty {
    color: var(--text-secondary);
  }

  .folder-full-path {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--text-muted);
    margin-top: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Agent Grid */
  .agent-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .agents-loading {
    grid-column: span 3;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    text-align: center;
    padding: 16px 0;
  }

  .agent-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 14px 6px;
    cursor: pointer;
    transition: all var(--transition-fast);
    box-shadow: var(--shadow-sm);
  }

  .agent-card:hover:not(:disabled) {
    background: var(--bg-hover);
    border-color: var(--border-hover);
  }

  .agent-card:active:not(:disabled) {
    transform: scale(0.97);
  }

  .agent-card.selected {
    border-color: var(--purple);
    background: var(--purple-soft);
    box-shadow: var(--shadow-glow);
  }

  .agent-card:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .agent-title {
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .agent-card:disabled .agent-title {
    color: var(--text-muted);
  }

  .agent-card.selected .agent-title {
    color: var(--purple);
  }

  .agent-status {
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--text-muted);
    margin-top: 4px;
  }


  /* Launch button */
  .action-wrap {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .connect-launch-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    background: var(--btn-primary-bg);
    color: var(--btn-primary-text);
    border: 1px solid var(--btn-primary-border);
    border-radius: var(--radius-md);
    padding: 16px;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all var(--transition-fast);
    letter-spacing: 1px;
    box-shadow: var(--shadow-sm);
  }

  .connect-launch-btn:hover:not(:disabled) {
    background: var(--btn-primary-hover);
  }

  .connect-launch-btn:active:not(:disabled) {
    transform: scale(0.98);
  }

  .connect-launch-btn:disabled {
    background: var(--btn-disabled-bg);
    border-color: var(--btn-disabled-border);
    color: var(--btn-disabled-text);
    cursor: not-allowed;
    box-shadow: none;
  }

  .connect-hint {
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--text-secondary);
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 4px 0;
  }

  .connect-hint.error {
    color: var(--red);
  }

  /* ── Settings Panel ────────────────────────────────────────── */
  .settings-section {
    margin-top: 8px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
  }

  .settings-header {
    display: flex;
    width: 100%;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    background: none;
    border: none;
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    letter-spacing: 1.5px;
    transition: all var(--transition-fast);
  }

  .settings-header:hover {
    color: var(--text-secondary);
    background: var(--bg-hover);
  }

  .settings-header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .settings-body {
    border-top: 1px solid var(--border);
    padding: 8px 0;
  }

  .setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    gap: 12px;
  }

  .setting-info {
    flex: 1;
    min-width: 0;
  }

  .setting-label {
    font-family: var(--font-sans);
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .setting-desc {
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  .setting-toggle-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }

  .setting-toggle-btn:hover {
    color: var(--text-primary);
    border-color: var(--border-hover);
  }

  .setting-toggle-btn:active {
    transform: scale(0.95);
  }

  .logout-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: calc(100% - 32px);
    margin: 8px 16px;
    padding: 12px;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.15);
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--red);
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .logout-btn:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
  }

  .logout-btn:active {
    transform: scale(0.98);
  }

  /* GitHub Star */
  .github-star-link {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 12px;
    margin-top: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-decoration: none;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
  }

  .github-star-link:hover {
    color: var(--yellow);
    background: rgba(245, 158, 11, 0.05);
  }

  .github-star-link:active {
    transform: scale(0.97);
  }
</style>
